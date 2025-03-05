import os
import logging
from flask import Blueprint, request, jsonify
from config.mongo_config import mongo
from schemas.generated_audios import GeneratedAudioSchema
from schemas.worker_events import WorkerEventSchema
from bson import ObjectId
from datetime import datetime, timezone
import utils.db_util as db_util
from flask_socketio import emit
from config.socket_config import socketio
from utils.error_util import save_system_error
from utils.sms_util import send_sms_download_message

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

audio_bp = Blueprint("audio_bp", __name__)

@audio_bp.route("/audios/save_file", methods=["POST"])
def save_generated_audio():
    """Salva arquivos de áudio no servidor e registra a atividade do usuário."""
    user_oid = request.form.get("user_oid")
    id = request.form.get("id")
    phone = request.form.get("phone")
    lyrics = request.form.get("lyrics")
    file1 = request.files.get("audio1")
    file2 = request.files.get("audio2")

    if not user_oid or not id or not file1 or not file2:
        return jsonify({"error": "user_oid, id, and two audio files are required"}), 400

    try:
        # Salvar os arquivos de áudio
        file1_path, error1 = db_util.store_audio_file(file1, id)
        file2_path, error2 = db_util.store_audio_file(file2, id)

        if error1 or error2:
            return jsonify({"error": error1 or error2}), 400

        # URLs locais dos arquivos
        host_url = os.getenv("HOST_URL")
        local_audio_urls = [f"{host_url}/{path}" for path in [file1_path, file2_path]]

        # Log das URLs armazenadas
        logger.info(f"[AUDIO] Audio files stored: {local_audio_urls}")

        # Envia mensagem via SMS com o link para acesso
        message_url = f"https://seguenasaga.sagatiba.com/mensagem?task_id={id}"
        send_sms_download_message(message_url, phone)

        # Criar entrada na coleção GeneratedAudios
        audio_data = {
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "audio_urls": [file1_path, file2_path],
            "timestamp": datetime.now(timezone.utc)
        }
        audios = GeneratedAudioSchema(**audio_data)
        audio_id = mongo.db.GeneratedAudios.insert_one(audios.model_dump()).inserted_id

        # Registrar evento na coleção UsersEvents
        event_data = {
            "user_oid": str(ObjectId(user_oid)),
            "action": f"audio_file_saved_{str(audio_id)}",
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "timestamp": datetime.now(timezone.utc)
        }
        event = WorkerEventSchema(**event_data)
        mongo.db.UsersEvents.insert_one(event.model_dump())

        # Emitir sinal para notificar que os áudios foram gerados
        socketio.emit('audio_response', {'audio_urls': local_audio_urls, 'task_id': id}, namespace='/')

        return jsonify({"message": "Generated audio saved successfully"}), 201

    except Exception as e:
        save_system_error("SAVE_AUDIO_FILE", f"id_{id}", "No audio saved for the given id.")
        logger.error(f"[ERROR] Failed to save audio: {str(e)}")
        return jsonify({"error": str(e)}), 400

@audio_bp.route("/audios/save_url", methods=["POST"])
def save_generated_audio_from_url():
    """Baixa arquivos de áudio de URLs, salva no servidor e registra a atividade do usuário."""
    data = request.json
    user_oid = data.get("user_oid")
    id = data.get("id")
    phone = data.get("phone")
    lyrics = data.get("lyrics")
    audio_url1 = data.get("audio_url1")
    audio_url2 = data.get("audio_url2")

    if not user_oid or not id or not audio_url1 or not audio_url2:
        return jsonify({"error": "user_oid, id, and two audio URLs are required"}), 400

    try:
        # Baixar e armazenar os áudios das URLs
        file1_path, error1 = db_util.store_audio_url(audio_url1, id)
        file2_path, error2 = db_util.store_audio_url(audio_url2, id)

        if error1 or error2:
            return jsonify({"error": error1 or error2}), 400

        # URLs locais dos arquivos
        host_url = os.getenv("HOST_URL")
        local_audio_urls = [f"{host_url}/{path}" for path in [file1_path, file2_path]]

        # Log das URLs armazenadas
        logger.info(f"[AUDIO] Audio files stored: {local_audio_urls}")

        # Envia mensagem via SMS com o link para acesso
        message_url = f"https://seguenasaga.sagatiba.com/mensagem?task_id={id}"
        send_sms_download_message(message_url, phone)

        # Criar entrada na coleção GeneratedAudios
        audio_data = {
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "audio_urls": [file1_path, file2_path],
            "timestamp": datetime.now(timezone.utc)
        }
        audios = GeneratedAudioSchema(**audio_data)
        audio_id = mongo.db.GeneratedAudios.insert_one(audios.model_dump()).inserted_id

        # Registrar evento na coleção UsersEvents
        event_data = {
            "user_oid": str(ObjectId(user_oid)),
            "action": f"audio_url_saved_{str(audio_id)}",
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "timestamp": datetime.now(timezone.utc)
        }
        event = WorkerEventSchema(**event_data)
        mongo.db.UsersEvents.insert_one(event.model_dump())

        # Emitir sinal para notificar que os áudios foram gerados
        socketio.emit('audio_response', {'audio_urls': local_audio_urls, 'task_id': id}, namespace='/')

        return jsonify({"message": "Generated audio saved successfully"}), 201

    except Exception as e:
        save_system_error("SAVE_AUDIO_URL", f"id_{id}", "No audio saved for the given id.")
        logger.error(f"[ERROR] Failed to save audio from URL: {str(e)}")
        return jsonify({"error": str(e)}), 400
