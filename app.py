import logging
import os
import requests
import time
import redis
import re
import json

from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_apscheduler import APScheduler

from utils.musicapi_util import create_music, get_music, upload_song, set_clip_id, get_clip_id
from utils.openai_util import moderation_ok, generate_lyrics
from utils.twilio_util import send_whatsapp_download_message, send_whatsapp_message

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Configuração dos bancos de dados Redis
task_db = redis.Redis(host='localhost', port=6379, db=0)   # Banco para enfileiramento de tarefas
lyrics_db = redis.Redis(host='localhost', port=6379, db=1) # Banco para armazenamento das letras de músicas

# Atualiza o Redis URL apenas para o limiter, apontando para db=2
limiter_redis_url = "redis://localhost:6379/2"

# Configuração do Rate Limiter no DB 2
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  
    storage_uri=limiter_redis_url,
    storage_options={"socket_connect_timeout": 30}
)

scheduler = APScheduler()


def worker_upload_song():
    """
    Tarefa agendada que faz upload de música e armazena o clip_id.
    """
    now = datetime.now()
    logger.info(f"[WORKER] Executando upload às {now.strftime('%Y-%m-%d %H:%M:%S')}")

    host_url = os.getenv("HOST_URL")  # Usa a variável de ambiente
    response = upload_song(host_url)

    if response:
        try:
            data = json.loads(response)
            if data.get("code") == 200 and "clip_id" in data:
                clip_id = data["clip_id"]
                set_clip_id(clip_id)
                logger.info(f"[WORKER] Upload bem-sucedido! Clip ID salvo: {clip_id}")
            else:
                logger.warning(f"[WORKER] Falha no upload: {data}")
        except json.JSONDecodeError:
            logger.error(f"[WORKER] Erro ao decodificar JSON: {response}")


# Adiciona a tarefa ao scheduler para rodar diariamente
# scheduler.add_job(id='daily_upload', func=daily_upload, trigger='interval', minutes=1)
scheduler.add_job(id='daily_upload', func=worker_upload_song, trigger='interval', hours=24, next_run_time=datetime.now())
scheduler.start()


@app.route('/alive', methods=['GET'])
def health_check():
    logger.info("Alive check endpoint accessed.")
    return jsonify({"status": "healthy"}), 200


@app.route("/check/clip_id", methods=["GET"])
def check_clip_id():
    """
    Retorna o valor atual do clip_id armazenado.
    Se não houver um clip_id, informa que ele ainda não foi gerado.
    """
    clip_id = get_clip_id()  # Obtém o valor do clip_id salvo

    if clip_id:
        return jsonify({"clip_id": clip_id}), 200
    else:
        return jsonify({"error": "clip_id ainda não foi gerado"}), 404


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
        lyrics = generate_lyrics(destination, invite_options, weekdays, message)
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


@app.route("/lyrics/process", methods=["POST"])
def process_music_tasks():
    """Processa a próxima tarefa da fila e retorna o task_id se o telefone for o mesmo"""
    phone = request.json.get("phone")  # O telefone vem no corpo da requisição
    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    raw_task = dequeue_task()  # Retira a primeira tarefa FIFO
    if not raw_task:
        return jsonify({"error": "No tasks in the queue"}), 404

    try:
        task_data = json.loads(raw_task.decode("utf-8"))  
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid task data format"}), 500

    lyrics = task_data["lyrics"]
    task_phone = task_data["phone"]

    # Verifica se a música já foi processada para este telefone e adiciona novo task_id
    existing_task_ids = lyrics_db.lrange(f"lyrics_store:{phone}", 0, -1)

    if existing_task_ids and len(existing_task_ids) > 0:
        decoded_task_ids = [task_id.decode("utf-8") for task_id in existing_task_ids]
        logger.info(f"Existing task IDs for {phone}: {decoded_task_ids}")


    # Cria a música e retorna um task_id
    task_id = create_music(lyrics)

    if task_phone == phone:
        if task_id:
            # Salva task_id no Redis (Banco de tarefas)
            task_db.hset("processed_tasks", phone, task_id)

            # Salva a música no Redis (Banco de letras/músicas)
            lyrics_db.rpush(f"lyrics_store:{phone}", task_id)  # Adiciona um novo task_id na lista
            lyrics_db.hset("lyrics_store", task_id, lyrics)  # Salva as letras associadas ao task_id
            lyrics_db.hset("lyrics_store", phone, task_id) # Uso futuro: Se quisermos recuperar a última música gerada para um usuário ou telefone

            return jsonify({"task_id": task_id}), 200
        else:
            return jsonify({"error": "Failed to create music task"}), 500
    else:
        # Se o telefone não bate, envia o áudio ao telefone correto
        request_audio({"task_id": task_id, "phone": task_phone})
        return jsonify({"status": "Audio sent to original requester"}), 202


@app.route("/lyrics/get", methods=["GET"])
def get_lyrics_and_audio():
    """Retorna as letras da música e os arquivos de áudio associados ao task_id."""
    task_id = request.args.get("task_id")
    host_url = os.getenv("HOST_URL")
    if not task_id:
        return jsonify({"error": "Task ID is required"}), 400

    try:
        # Recupera as letras associadas ao task_id
        lyrics = lyrics_db.hget("lyrics_store", task_id)
        if not lyrics:
            return jsonify({"error": "Lyrics not found for the given Task ID"}), 404

        lyrics_decoded = lyrics.decode("utf-8")

        # Diretório onde os áudios estão armazenados
        audio_dir = "static/mp3/"
        audio_files = [
            f"{host_url}{audio_dir}{file}"
            for file in os.listdir(audio_dir)
            if file.startswith(f"sagatiba_{task_id}_")
        ]

        return jsonify({
            "audio_urls": audio_files,
            "lyrics": lyrics_decoded
        }), 200

    except Exception as e:
        logger.error(f"Erro ao buscar letras e áudios: {e}")
        return jsonify({"error": "Internal server error"}), 500


@socketio.on('request_audio_url')
def request_audio(json):
    """Recebe uma requisição de áudio via WebSocket e envia o áudio para o número correto."""

    MAX_TRIES = 50
    logger.info(f"Recebida requisição de áudio: {json}")  # Log dos dados de entrada

    task_id = json.get('task_id')
    phone = json.get('phone')  # Obtém o número de telefone
    host_url = os.getenv("HOST_URL")  # Obtém a URL do host para envio

    if not task_id:
        logger.warning("Requisição sem Task ID")
        emit('error_message', {'error': 'Task ID is required', 'code': 400}, namespace='/')
        return

    if not phone:
        logger.warning("Requisição sem número de telefone")
        emit('error_message', {'error': 'Phone number is required', 'code': 400}, namespace='/')
        return

    attempts = 0
    while attempts < MAX_TRIES:
        logger.info(f"Tentativa {attempts + 1}: buscando áudios para task_id={task_id}")
        emit('message', {'message': f"Tentativa {attempts + 1}", 'code': 204}, namespace='/')

        audio_urls = get_music(task_id)
        
        if isinstance(audio_urls, str):
            if audio_urls.startswith("Status"):  # Se for um status, não interrompe o loop
                logger.info(f"Status recebido para task_id={task_id}: {audio_urls}")
                emit('message', {'status': audio_urls}, namespace='/')
            else:  # Se for um erro real, interrompe o loop e responde
                logger.error(f"Erro ao obter áudio para task_id={task_id}: {audio_urls}")
                emit('error_message', {'error': audio_urls, 'code': 500}, namespace='/')
                return

        if isinstance(audio_urls, list) and len(audio_urls) > 0:
            file_paths = [store_audio(url, task_id) for url in audio_urls]
            local_audio_urls = [f"{host_url}/{file}" for file in file_paths]
            logger.info(f"Áudios armazenados: {file_paths}")

            # Gerar link para o usuário acessar no frontend
            message_url = f"{host_url}mensagem?id={task_id}"
            send_whatsapp_download_message(message_url, phone)
            emit('audio_response', {'audio_urls': local_audio_urls}, namespace='/')
            return

        socketio.sleep(10)
        attempts += 1

    logger.error(f"Falha ao gerar áudio para task_id={task_id} após {MAX_TRIES} tentativas")
    emit('error_message', {'error': 'Failed to generate audio after several attempts', 'code': 500}, namespace='/')


@app.route("/audio/download", methods=["GET"])
def download_audio():
    """Provides a file download for the generated audio."""
    audio_url = request.args.get('audio_url')
    if not audio_url:
        return jsonify({"error": "Audio URL not provided"}), 400

    temp_path = store_audio(audio_url)
    file_name = os.path.basename(temp_path)
    return send_file(temp_path, as_attachment=True, download_name=file_name, mimetype="audio/mpeg")

# @app.route("/audio/download", methods=["POST"])
# def download_audio():
#     """Faz o download de múltiplos arquivos de áudio e retorna um ZIP contendo os arquivos."""
#     data = request.get_json()
#     audio_urls = data.get("audio_urls", [])

#     if not audio_urls or len(audio_urls) == 0:
#         return jsonify({"error": "Audio URLs not provided"}), 400

#     try:

#         # Criar buffer de memória para o ZIP
#         zip_buffer = BytesIO()

#         with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for index, audio_url in enumerate(audio_urls):
#                 try:
#                     response = requests.get(audio_url, stream=True)
#                     if response.status_code != 200:
#                         return jsonify({"error": f"Failed to download file from {audio_url}"}), 500

#                     file_name = f"audio_{index+1}.mp3"
                    
#                     # Escrever diretamente no ZIP
#                     zipf.writestr(file_name, response.content)

#                 except requests.exceptions.RequestException as e:
#                     logger.error(f"Request failed: {e}")
#                     return jsonify({"error": str(e)}), 500

#         # Garantir que o buffer está no início antes de enviar
#         zip_buffer.seek(0)

#         return send_file(zip_buffer, as_attachment=True, download_name="audio_files.zip", mimetype="application/zip")

#     except requests.exceptions.RequestException as e:
#         logger.error(f"Request failed: {e}")
#         return jsonify({"error": str(e)}), 500


def get_task_id_from_url(url):
    """
    Extracts the task_id from a given URL.
    
    Supported formats:
    - 'https://audiopipe.suno.ai/?item_id=<task_id>'
    - 'https://cdn1.suno.ai/<task_id>.mp3'
    """
    pattern = re.compile(r'([a-f0-9-]{36})')  # Matches UUID-like patterns
    match = pattern.search(url)
    return match.group(1) if match else None


def store_audio(url, task_id, max_size=1177*1024):
    """
    Baixa e armazena um arquivo de áudio, garantindo que múltiplos arquivos para o mesmo task_id não sejam sobrescritos.
    """
    tmp_dir = 'static/mp3/'
    
    # Se não existir, extrai o task_id
    if not task_id:
        task_id = get_task_id_from_url(url)

    # Garante que o diretório de destino exista
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    # Define um nome de arquivo único
    count = 1
    while True:
        file_name = f"sagatiba_{task_id}_{count}.mp3"
        temp_path = os.path.join(tmp_dir, file_name)
        if not os.path.exists(temp_path):  # Se o arquivo ainda não existe, usamos esse nome
            break
        count += 1  # Caso contrário, incrementa e tenta novamente

    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return jsonify({"error": "Failed to download file"}), 500

        file_size = 0
        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file_size += len(chunk)
                if chunk:
                    file.write(chunk)
                    if file_size >= max_size:
                        break  # Para o download se atingir o limite de tamanho

        time.sleep(1)
        return temp_path  # Retorna o caminho do arquivo salvo

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar áudio: {e}")
        return jsonify({"error": str(e)}), 500


def enqueue_task(lyrics, phone):
    """ Adiciona uma tarefa à fila FIFO no Redis, armazenando a letra e o telefone do usuário """
    task_data = json.dumps({"lyrics": lyrics, "phone": phone})
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