import logging
import os
import uuid
import redis
import json
from bson import ObjectId
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

from utils.openai_util import moderation_ok, generate_lyrics
from utils.error_util import save_system_error

from config.mongo_config import mongo, init_mongo
from config.socket_config import socketio
from schemas.user_events import UserEventSchema

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

#Incializar o servidor de email
mail = Mail()

# if os.getenv('LOCAL_SERVER'):
#     app.config.update(
#         MAIL_SERVER='localhost',
#         MAIL_PORT=8025,
#         MAIL_USE_TLS=False,
#         MAIL_USERNAME=None,
#         MAIL_PASSWORD=None,
#         MAIL_DEFAULT_SENDER=('Segue na Saga', 'guilhermebegotti@dreambricks.com.br')
#     )
# else: 

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv('EMAIL_USER'),
    MAIL_PASSWORD= os.getenv('EMAIL_SECRET_KEY'),
    MAIL_DEFAULT_SENDER=('Segue na Saga', 'seguenasaga@gmail.com'),
    # MAIL_DEBUG=True  # Ativar logs de erro no Flask-Mail
)

mail.init_app(app)

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
    user_oid = request.form.get("user_oid")

    #phone = request.form.get("phone")

    logger.info(f"Received form data: destination={destination}, invite_options={invite_options}, "
                f"weekdays={weekdays}, message={message}, user_oid={str(ObjectId(user_oid))}")
    
    is_ok, error_msg = moderation_ok(destination, message)
    if is_ok:
        lyrics_path = "static/lyrics"
        lyrics, lyrics_oid = generate_lyrics(destination, invite_options, weekdays, message, user_oid, lyrics_path)
        register_user_event(user_oid, "lyrics_processing", lyrics_oid)

        logger.info("Lyrics generated successfully.")
        #return redirect(url_for('display_lyrics', lyrics=lyrics, phonw=phonw))
        return jsonify({"lyrics": lyrics, "lyrics_oid": lyrics_oid})
    else:
        logger.warning("Submitted text violates moderation rules.")
        return jsonify({"error": f"Erro o texto submetido viola as regras de moderação: {error_msg}"}), 403

@app.route("/lyrics/generate", methods=["POST"])
def generate_task_id():
    """Enfileira a geração de música para as letras fornecidas."""
    data = request.get_json()
    lyrics_oid = data.get("lyrics_oid")

    if not lyrics_oid:
        logger.info(f"Task not enqueued: lyrics_oid missing")
        return jsonify({"error": "O Id da Letra é obrigatório."}), 400

    try:
        # Buscar a letra no banco de dados pelo ObjectId
        lyrics_entry = mongo.db.GeneratedLyrics.find_one({"_id": ObjectId(lyrics_oid)})
        
        if not lyrics_entry:
            logger.info(f"Task not enqueued: Lyrics not found for id {lyrics_oid}")
            return jsonify({"error": "Nenhuma letra encontrada para o Id fornecido."}), 404

        # Pega a letra do documento retornado
        lyrics = lyrics_entry.get("lyrics", "")

        if not lyrics:
            logger.info(f"Task not enqueued: Letra vazia para id {lyrics_oid}")
            return jsonify({"error": "A Letra está ausente ou vazia."}), 400

        # Enfileira as letras para processamento posterior
        task_id = enqueue_task(lyrics, lyrics_oid)
        logger.info(f"Task {task_id} enqueued for lyrics_id: {lyrics_oid}")

        # Atualiza a fila no frontend via socket
        queue_items = task_db.lrange("lyrics_queue", 0, -1)
        queue_items = [json.loads(task.decode("utf-8")) for task in queue_items]
        socketio.emit("queue_list", queue_items, namespace="/")
        logger.info(f"Queue updated after enqueue. Total: {len(queue_items)} items.")

        return jsonify({"status": "Sua tarefa foi enfileirada", "task_id": task_id}), 202

    except Exception as e:
        logger.error(f"Erro ao buscar letra ou enfileirar tarefa: {str(e)}")
        return jsonify({"error": "Erro interno ao processar a requisição."}), 500


@app.route("/lyrics/get", methods=["GET"])
def get_lyrics_and_audio():
    """Retorna as letras da música e os arquivos de áudio associados ao id."""
    id = request.args.get("task_id")
    host_url = os.getenv("HOST_URL")

    if not id:
        return jsonify({"error": "O Id é obrigatório."}), 400

    try:
        # Busca a música no MongoDB usando o campo `redis_id` para buscar os dados de áudio e a letra correspondente
        pipeline = [
            {"$match": {"redis_id": id}},  
            {
                "$lookup": {
                    "from": "GeneratedLyrics",  
                    "localField": "lyrics_oid",  
                    "foreignField": "_id", 
                    "as": "lyrics_data",  
                }
            },
            {"$unwind": "$lyrics_data"},
            {
                "$project": {
                    "_id": 0,  
                    "redis_id": 1,
                    "lyrics": "$lyrics_data.lyrics",  
                    "audio_urls": 1,  
                }
            }
        ]

        result = list(mongo.db.GeneratedAudios.aggregate(pipeline))

        # Se não houver resultado, retorna erro
        if not result:
            return jsonify({"error": "Letras e áudio não encontrados para o ID fornecido."}), 404

        audio_entry = result[0]

        # Obtém os URLs dos áudios
        host_url = request.host_url.rstrip("/")  # Garante que a URL base esteja correta
        audio_files = [f"{host_url}/{file}" for file in audio_entry.get("audio_urls", [])]

        return jsonify({
            "audio_urls": audio_files,
            "lyrics": audio_entry["lyrics"],
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving lyrics and audio: {e}")
        save_system_error("GET_LYRICS_AUDIO", f"id_{id}", "No audio and no lyrics found for the given id.")
        return jsonify({"error": f"Erro ao recuperar letras e áudio: {e}"}), 500

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
    host_url = os.getenv("HOST_URL")

    # Validação dos parâmetros obrigatórios
    if not id:
        logger.warning("[SOCKET] Request without Task Id")
        emit('error_message', {'error': 'Task Id é obrigatório', 'code': 400}, namespace='/')
        return

    # Busca no banco de dados `GeneratedAudios` pelo `redis_id`
    audio_entry = mongo.db.GeneratedAudios.find_one({"redis_id": id})

    if not audio_entry:
        logger.warning(f"[SOCKET] No audio found for id={id}")
        save_system_error("REQUEST_AUDIO", f"id_{id}", "No audio found for the given id.")
        emit('error_message', {'error': "Nenhum áudio encontrado para o ID fornecido.", 'code': 404}, namespace='/')
        return

    # Obtém os caminhos dos arquivos de áudio armazenados
    file_paths = audio_entry.get("audio_urls", [])
    local_audio_urls = [f"{host_url}/{file}" for file in file_paths]

    logger.info(f"[SOCKET] Audio files stored: {file_paths}")

    # Responde ao WebSocket com os áudios encontrados
    emit('audio_response', {'audio_urls': local_audio_urls, 'task_id': id}, namespace='/')

# Registrar rotas do Mongo
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(audio_bp, url_prefix="/api")
app.register_blueprint(task_bp, url_prefix="/api")

def enqueue_task(lyrics, lyrics_oid):
    """ Adiciona uma tarefa à fila FIFO no Redis, armazenando um ID, a letra e o telefone do usuário """
    id = str(uuid.uuid4())  # Gera um UUID único para cada tarefa
    task_data = json.dumps({
        "id": id,
        "lyrics": lyrics,
        "lyrics_oid": lyrics_oid
    })

    try:
        # Atualiza o campo `redis_id` na coleção `GeneratedLyrics`
        result = mongo.db.GeneratedLyrics.update_one(
            {"_id": ObjectId(lyrics_oid)},  # Filtra pelo OID da letra
            {"$set": {"redis_id": id}}  # Atualiza o campo redis_id
        )

        if result.matched_count == 0:
            logger.warning(f"Nenhuma letra encontrada para lyrics_oid: {lyrics_oid}")
        elif result.modified_count == 1:
            logger.info(f"redis_id atualizado para {id} na letra {lyrics_oid}")

        logger.info(f"Enqueuing task: {task_data}")
        task_db.rpush('lyrics_queue', task_data)
        return id

    except Exception as e:
        logger.error(f"Erro ao atualizar redis_id no MongoDB: {str(e)}")

    return id
    
def dequeue_task():
    """ Remove e retorna a primeira tarefa da fila FIFO no Redis """
    return task_db.lpop('lyrics_queue')

def register_user_event(user_oid, action, lyrics_oid, audio_oid=None):
    """
    Registra um evento na coleção UsersEvents.

    :param user_oid: ID do usuário (ObjectId)
    :param action: Texto de identificação da tarefa
    :param lyrics_oid: ID da Letra associada (ObjectId)
    :param audio_oid: (Opcional) ID do áudio associado (ObjectId)
    """
    try:
        # Criando o dicionário de evento
        event_data = {
            "user_oid": user_oid,
            "action": action,
            "lyrics_oid": lyrics_oid,
            "timestamp": datetime.now(timezone.utc)
        }

        # Adiciona o audio_oid apenas se não for None
        if audio_oid is not None:
            event_data["audio_oid"] = audio_oid

        # Criando o evento e salvando no MongoDB
        event = UserEventSchema(**event_data)
        mongo.db.UsersEvents.insert_one(event.model_dump())

        return True  # Retorna sucesso
    except Exception as e:
        logger.error(f"Erro ao registrar evento do usuário: {str(e)}")
        return False  # Retorna falha

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    if os.getenv('LOCAL_SERVER'):
        socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
    else:
        socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True, ssl_context=('priv/fullchain.pem', 'priv/privkey.pem'))