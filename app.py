import logging
import os
import uuid
import redis
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from utils.openai_util import moderation_ok, generate_lyrics
from utils.sms_util import send_sms_download_message, send_sms_message
from utils.error_util import save_system_error

from config.mongo_config import mongo, init_mongo
from config.socket_config import socketio

from routes.user import user_bp
from routes.audio import audio_bp
from routes.tasks import task_bp

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
CORS(app)

# Inicializar MongoDB e SocketIO
init_mongo(app)
socketio.init_app(app)

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
    send_sms_message(message, phone)
    if not lyrics:
        logger.info(f"Task not enqueued for phone: {phone}")
        return jsonify({"error": "Lyrics parameter is missing"}), 400

    # Enfileira as letras para processamento posterior
    id = enqueue_task(lyrics, phone)
    logger.info(f"Task {id} enqueued for phone: {phone}")

    # Chama o socket para atualizar a fila no frontend
    queue_items = task_db.lrange("lyrics_queue", 0, -1)
    queue_items = [json.loads(task.decode("utf-8")) for task in queue_items]
    socketio.emit("queue_list", queue_items, namespace="/")
    logger.info(f"Queue updated after enqueue. Total: {len(queue_items)} items.")

    return jsonify({"status": "Your task has been enqueued", "task_id": id}), 202

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
def send_queue():
    """Envia a lista atual da fila para o frontend."""
    queue_items = [json.loads(task.decode("utf-8")) for task in task_db.lrange("lyrics_queue", 0, -1)]
    socketio.emit("queue_list", queue_items)
    logger.info(f"Queue sent to client. Total: {len(queue_items)} items.")

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
    send_sms_download_message(message_url, phone)

    # Responde ao WebSocket com os áudios encontrados
    emit('audio_response', {'audio_urls': local_audio_urls}, namespace='/')

# Registrar rotas do Mongo
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(audio_bp, url_prefix="/api")
app.register_blueprint(task_bp, url_prefix="/api")

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
    return id
    
def dequeue_task():
    """ Remove e retorna a primeira tarefa da fila FIFO no Redis """
    return task_db.lpop('lyrics_queue')

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    if os.getenv('LOCAL_SERVER'):
        socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
    else:
        socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True, ssl_context=('priv/fullchain.pem', 'priv/privkey.pem'))