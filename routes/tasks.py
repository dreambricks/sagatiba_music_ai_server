from flask import Blueprint, request, jsonify
import json
import logging
import redis
from config.mongo_config import mongo
from flask_socketio import emit
from utils.error_util import save_system_error
from config.socket_config import socketio

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