import logging
import os
import uuid
import requests
import time
import redis
import re
import json
import asyncio

from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_apscheduler import APScheduler # type: ignore
from apscheduler.triggers.cron import CronTrigger # type: ignore

from utils.openai_util import moderation_ok, generate_lyrics
from utils.twilio_util import send_whatsapp_download_message, send_whatsapp_message
from config.mongo_config import mongo
import utils.db_util as db_util
import utils.audio_util as audio_util

from config.mongo_config import init_mongo
from routes.user import user_bp
from routes.audio import audio_bp

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8", mode="a"),
        logging.StreamHandler()
    ],
    force=True 
)
logger = logging.getLogger(__name__)

# Força a escrita imediata dos logs no arquivo
for handler in logger.handlers:
    if isinstance(handler, logging.FileHandler):
        handler.flush()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Inicializar MongoDB
init_mongo(app)

redis_host = "localhost"
redis_port = 6379
# Configuração dos bancos de dados Redis
task_db = redis.Redis(host=redis_host, port=redis_port, db=0)   # Banco para enfileiramento de tarefas
lyrics_db = redis.Redis(host=redis_host, port=redis_port, db=1) # Banco para armazenamento das letras de músicas
# Atualiza o Redis URL apenas para o limiter, apontando para db=2
limiter_redis_url = "redis://localhost:6379/2"
error_db = redis.Redis(host=redis_host, port=redis_port, db=3)
processing_db = redis.Redis(host=redis_host, port=redis_port, db=4)  # Armazena tarefas em processamento


# Configuração do Rate Limiter no DB 2
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  
    storage_uri=limiter_redis_url,
    storage_options={"socket_connect_timeout": 30}
)

scheduler = APScheduler()

# Função para limpar as tarefas do Redis
def clear_task_db():
    task_db.flushdb()
    logger.info("[SCHEDULER] Redis task database cleaned at 04:00 AM")

scheduler.add_job(
    id='clear_task_db',
    func=clear_task_db,
    trigger=CronTrigger(hour=4, minute=0),  # Roda todo dia às 04:00 AM
    replace_existing=True
)

# Executa o scheduler
scheduler.start()

@app.route('/check', methods=['GET'])
def health_check():
    logger.info("Alive check endpoint accessed.")
    return jsonify({"status": "healthy"}), 200

@app.route("/check/status", methods=["GET"])
def check_system_status():
    """
    Endpoint que retorna o status das principais operações do sistema.
    Se houver erros, ele retorna uma lista com os problemas encontrados.
    """

    # Recupera todos os erros armazenados no Redis (DB 3)
    errors = error_db.hgetall("system_errors")

    if not errors:
        return jsonify({
            "status": "ok",
            "message": "Everything's shiny, Cap'n!"
        }), 200

    # Converte os erros de JSON para um formato legível
    error_list = []
    for key, value in errors.items():
        error_data = json.loads(value.decode("utf-8"))
        error_list.append({
            "error_id": key.decode("utf-8"),  # Inclui a chave como identificador do erro
            "context": error_data["context"],
            "identifier": error_data["identifier"],
            "error_message": error_data["error_message"],
            "timestamp": error_data["timestamp"]
        })


    return jsonify({
        "status": "error",
        "message": "I've got a bad feeling about this...",
        "errors": error_list
    }), 500

@app.route("/lyrics", methods=["POST"])
#@limiter.limit("1 per 5 minutes")
#@limiter.limit("10 per day")
def call_generate_lyrics():
    """Gera letras com base nos dados do formulário e retorna JSON com as letras ou erro."""
    destination = request.form.get("destination")
    invite_options = request.form.get("invite_options")
    weekdays = request.form.get("weekdays")
    message = request.form.get("message")
    #phone = request.form.get("phone")

    logger.info(f"Received form data: destination={destination}, invite_options={invite_options}, "
                f"weekdays={weekdays}, message={message}")

    is_ok, error_msg = moderation_ok(destination, message)
    if is_ok:
        lyrics_path = "static/lyrics"
        lyrics = generate_lyrics(destination, invite_options, weekdays, message, lyrics_path)
        logger.info("Lyrics generated successfully.")
        #return redirect(url_for('display_lyrics', lyrics=lyrics, phonw=phonw))
        return jsonify({"lyrics": lyrics})
    else:
        logger.warning("Submitted text violates moderation rules.")
        return jsonify({"error": error_msg}), 403

@app.route("/lyrics/generate", methods=["GET", "POST"])
def generate_task_id():
    """Enfileira a geração de música para as letras fornecidas."""
    data = request.get_json()
    lyrics = data.get("lyrics")
    phone = data.get("phone")
    message = "Oi Sagalover! Sua música está sendo preparada."
    send_whatsapp_message(message, phone)
    if not lyrics:
        logger.info(f"Task not enqueued for phone: {phone}")
        return jsonify({"error": "Lyrics parameter is missing"}), 400

    # Enfileira as letras para processamento posterior
    enqueue_task(lyrics, phone)
    logger.info(f"Task enqueued for phone: {phone}")
    return jsonify({"status": "Your task has been enqueued"}), 202

@app.route("/lyrics/get", methods=["GET"])
def get_lyrics_and_audio():
    """Retorna as letras da música e os arquivos de áudio associados ao id."""
    id = request.args.get("task_id")
    host_url = os.getenv("HOST_URL")

    if not id:
        return jsonify({"error": "Id is required"}), 400

    try:
        # Busca a música no MongoDB usando o campo `redis_id`
        audio_entry = mongo.db.GeneratedAudios.find_one({"redis_id": id})

        if not audio_entry:
            return jsonify({"error": "Lyrics and audio not found for the given Id"}), 404

        # Obtém letras e caminhos dos áudios
        lyrics = audio_entry.get("lyrics", "No lyrics found")
        audio_files = [
            f"{host_url}/{file}" for file in audio_entry.get("audio_urls", [])
        ]

        return jsonify({
            "audio_urls": audio_files,
            "lyrics": lyrics
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving lyrics and audio: {e}")
        save_system_error("GET_LYRICS_AUDIO", f"id_{id}", "No audio and no lyrics found for the given id.")
        return jsonify({"error": "Internal server error"}), 500

@socketio.on("get_queue")
async def send_queue():
    """Envia a lista atual da fila para o frontend."""
    queue_items = [json.loads(task.decode("utf-8")) for task in task_db.lrange("task_queue", 0, -1)]
    await socketio.emit("queue_list", queue_items)
    logger.info(f"Queue sent to client. Total: {len(queue_items)} items.")

@socketio.on("process_task")
async def process_task():
    """Remove temporariamente o primeiro item da fila e envia para o frontend processar."""
    raw_task = task_db.lpop("task_queue")

    if not raw_task:
        await socketio.emit("task_result", {"status": "error", "message": "No tasks available."})
        return

    task = json.loads(raw_task.decode("utf-8"))
    id = task["id"]
    processing_db.set(id, json.dumps(task))  # Marca como em processamento

    logger.info(f"Task assigned: {task}")

    # Enviar tarefa ao frontend para processamento
    await socketio.emit("task_assigned", task)

@socketio.on("task_completed")
async def task_completed(data):
    """Marca a tarefa como concluída e remove do Redis."""
    id = data.get("id")
    success = data.get("success")

    if not id:
        await socketio.emit("task_result", {"status": "error", "message": "Invalid task Id."})
        return

    if success:
        processing_db.delete(id)  # Remove do registro de tarefas em andamento
        await socketio.emit("task_result", {"status": "success", "message": "Task completed successfully."})
        logger.info(f"Task {id} completed and dequeued successfully.")
    else:
        # Se falhou, recoloca no topo da fila
        raw_task = processing_db.get(id)
        if raw_task:
            task_db.lpush("task_queue", raw_task)
            processing_db.delete(id)
            await socketio.emit("task_result", {"status": "failed", "message": "Task completion failed. Requeued."})
            logger.warning(f"Task {id} failed and requeued.")
            save_system_error("TASK_DEQUEUE_FAILED", f"task_id_{id}", f"Task {id} completion failed. Requeued.")

@socketio.on("requeue_task")
async def requeue_task(data):
    """Recoloca a tarefa na fila manualmente a pedido do frontend."""
    id = data.get("id")

    if not id:
        await socketio.emit("task_result", {"status": "error", "message": "Invalid task Id for requeue."})
        return

    raw_task = processing_db.get(id)

    if raw_task:
        task_db.lpush("task_queue", raw_task)  # Recoloca no topo da fila
        processing_db.delete(id)  # Remove dos processamentos
        await socketio.emit("task_result", {"status": "requeued", "message": "Task manually requeued."})
        logger.info(f"Task {id} manually requeued.")

@socketio.on('request_audio_url')
def request_audio(json):
    """Recebe uma requisição de áudio via WebSocket e envia o áudio para o número correto."""
    logger.info(f"[SOCKET] Request received: {json}")

    id = json.get('task_id')
    phone = json.get('phone')
    host_url = os.getenv("HOST_URL")

    # Validação dos parâmetros obrigatórios
    if not id:
        logger.warning("[SOCKET] Request without Task Id")
        emit('error_message', {'error': 'Task Id is required', 'code': 400}, namespace='/')
        return

    if not phone:
        logger.warning("[SOCKET] Request without phone number")
        emit('error_message', {'error': 'Phone number is required', 'code': 400}, namespace='/')
        return

    # Busca no banco de dados `GeneratedAudios` pelo `redis_id`
    audio_entry = mongo.db.GeneratedAudios.find_one({"redis_id": id})

    if not audio_entry:
        logger.warning(f"[SOCKET] No audio found for id={id}")
        save_system_error("REQUEST_AUDIO", f"id_{id}", "No audio found for the given id.")
        emit('error_message', {'error': 'No audio found for the given id', 'code': 404}, namespace='/')
        return

    # Obtém os caminhos dos arquivos de áudio armazenados
    file_paths = audio_entry.get("audio_urls", [])
    local_audio_urls = [f"{host_url}/{file}" for file in file_paths]

    logger.info(f"[SOCKET] Audio files stored: {file_paths}")

    # Envia mensagem via WhatsApp
    message_url = f"https://seguenasaga.sagatiba.com/mensagem?task_id={id}"
    send_whatsapp_download_message(message_url, phone)

    # Responde ao WebSocket com os áudios encontrados
    emit('audio_response', {'audio_urls': local_audio_urls}, namespace='/')

# Registrar rotas do Mongo
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(audio_bp, url_prefix="/api")

def save_system_error(context, identifier, error_message):
    """ Salva informações sobre falhas na geração de áudio no Redis """
    error_data = {
        "context": context,
        "identifier": identifier,
        "error_message": error_message,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    error_db.hset("system_errors", identifier, json.dumps(error_data))
    logger.error(f"[ERROR] Error saved in context {context} for identifier={identifier}: {error_message}")

def enqueue_task(lyrics, phone):
    """ Adiciona uma tarefa à fila FIFO no Redis, armazenando um ID, a letra e o telefone do usuário """
    id = str(uuid.uuid4())  # Gera um UUID único para cada tarefa
    task_data = json.dumps({
        "id": id,
        "lyrics": lyrics,
        "phone": phone
    })

    logger.info(f"Enqueuing task: {task_data}")
    task_db.rpush('lyrics_queue', task_data)
    
def dequeue_task():
    """ Remove e retorna a primeira tarefa da fila FIFO no Redis """
    return task_db.lpop('lyrics_queue')

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    if os.getenv('LOCAL_SERVER'):
        socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
    else:
        socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True, ssl_context=('priv/fullchain.pem', 'priv/privkey.pem'))