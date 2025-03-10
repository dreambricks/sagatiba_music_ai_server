from flask import Blueprint, request, jsonify
import json
import logging
import redis
from bson import ObjectId
from datetime import datetime, timezone
from config.mongo_config import mongo
from flask_socketio import emit
from utils.error_util import save_system_error
from config.socket_config import socketio
from utils.twilio_util import send_whatsapp_message

task_bp = Blueprint("task_bp", __name__)

# Configuração do logger
logger = logging.getLogger(__name__)

# Conexão com Redis
redis_host = "localhost"
redis_port = 6379
task_db = redis.Redis(host=redis_host, port=redis_port, db=0)  # Fila de tarefas
processing_db = redis.Redis(host=redis_host, port=redis_port, db=4)  # Tarefas em andamento

def emit_queue_list():
    """Emite o evento `queue_list` para atualizar a fila no frontend."""
    queue_items = task_db.lrange("lyrics_queue", 0, -1)
    queue_items = [json.loads(task.decode("utf-8")) for task in queue_items]
    socketio.emit("queue_list", queue_items, namespace="/")
    logger.info(f"Queue updated. Total: {len(queue_items)} items.")

@task_bp.route("/tasks/process", methods=["POST"])
def process_task():
    """Remove temporariamente o primeiro item da fila e o retorna para ser processado."""
    raw_task = task_db.lpop("lyrics_queue")

    if not raw_task:
        return jsonify({"status": "error", "message": "No tasks available."}), 404

    task = json.loads(raw_task.decode("utf-8"))
    id = task["id"]
    processing_db.set(id, json.dumps(task))  # Marca como em processamento

    logger.info(f"Task assigned: {task}")

    # Atualiza a fila no frontend
    emit_queue_list()

    return jsonify({"status": "success", "task": task}), 200


@task_bp.route("/tasks/complete", methods=["POST"])
def task_completed():
    """Marca a tarefa como concluída e a remove do Redis."""
    data = request.json
    id = data.get("id")
    success = data.get("success")

    if not id:
        return jsonify({"status": "error", "message": "Invalid task Id."}), 400

    if success:
        processing_db.delete(id)  # Remove do registro de tarefas em andamento
        logger.info(f"Task {id} completed and dequeued successfully.")

        # Atualiza a fila no frontend
        emit_queue_list()

        return jsonify({"status": "success", "message": "Task completed successfully."}), 200
    else:
        # Se falhou, recoloca no topo da fila
        raw_task = processing_db.get(id)
        if raw_task:
            task_db.lpush("lyrics_queue", raw_task)
            processing_db.delete(id)
            logger.warning(f"Task {id} failed and requeued.")
            save_system_error("TASK_DEQUEUE_FAILED", f"task_id_{id}", f"Task {id} completion failed. Requeued.")

            # Atualiza a fila no frontend
            emit_queue_list()

            return jsonify({"status": "failed", "message": "Task completion failed. Requeued."}), 200

    return jsonify({"status": "error", "message": "Unexpected error."}), 500


@task_bp.route("/tasks/requeue", methods=["POST"])
def requeue_task():
    """Recoloca uma tarefa na fila manualmente a pedido do frontend."""
    data = request.json
    id = data.get("id")

    if not id:
        return jsonify({"status": "error", "message": "Invalid task Id for requeue."}), 400

    raw_task = processing_db.get(id)

    if raw_task:
        task_db.lpush("lyrics_queue", raw_task)  # Recoloca no topo da fila
        processing_db.delete(id)  # Remove dos processamentos
        logger.info(f"Task {id} manually requeued.")

        # Atualiza a fila no frontend
        emit_queue_list()

        return jsonify({"status": "requeued", "message": "Task manually requeued."}), 200

    return jsonify({"status": "error", "message": "Task not found for requeue."}), 404

@task_bp.route("/tasks/fail", methods=["POST"])
def report_task_failure():
    """Registra a falha na geração de música, remove a tarefa da fila e envia uma mensagem de erro ao cliente."""
    data = request.json
    id = data.get("id")
    phone = data.get("phone")
    lyrics = data.get("lyrics")
    user_oid = data.get("user_oid")

    if not id or not user_oid:
        return jsonify({"status": "error", "message": "Both 'id' and 'user_oid' are required."}), 400

    # Tenta remover diretamente sem precisar percorrer toda a fila
    task_db.lrem("lyrics_queue", 0, json.dumps({"id": id}))

    # Remove também do banco de tarefas em processamento
    processing_db.delete(id)

    # Registrar evento de falha no MongoDB (UsersEvents)
    event_data = {
        "user_oid": ObjectId(user_oid),
        "action": "music_generation_failed",
        "redis_id": id,
        "phone": phone,
        "lyrics": lyrics,
        "timestamp": datetime.now(timezone.utc)
    }
    mongo.db.UsersEvents.insert_one(event_data)

    # Salvar erro no Redis (para status do sistema)
    save_system_error("TASK_GENERATION_FAILED", f"task_id_{id}", f"Task {id} failed during music generation. User {user_oid} could not complete the task")

    # Enviar mensagem de erro ao usuário
    error_message = "Oi! Infelizmente houve um problema na geração da sua música. Por favor, tente novamente."
    send_whatsapp_message(error_message, phone)

    # Atualizar fila no frontend
    emit_queue_list()

    return jsonify({"status": "failed", "message": f"Failure recorded, {phone} notified."}), 200
