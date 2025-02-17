import os
from flask import Blueprint, request, jsonify
from config.mongo_config import mongo
from schemas.generated_audios import GeneratedAudioSchema
from schemas.user_events import UserEventSchema
from bson import ObjectId
from datetime import datetime, timezone
import utils.db_util as db_util

audio_bp = Blueprint("audio_bp", __name__)

@audio_bp.route("/audios/save_file", methods=["POST"])
def save_generated_audio():
    """Salva arquivos de áudio no servidor e registra a atividade do usuário."""
    user_oid = request.form.get("user_oid")
    id = request.form.get("id")
    phone = request.form.get("phone")
    lyrics = request.form.get("lyrics")
    file1 = request.files.get("audio1")  # Obtém o primeiro arquivo de áudio
    file2 = request.files.get("audio2")  # Obtém o segundo arquivo de áudio

    if not user_oid or not id or not file1 or not file2:
        return jsonify({"error": "user_oid, id, and two audio files are required"}), 400

    try:
        # Salvar os arquivos de áudio
        file1_path, error1 = db_util.store_audio_file(file1, id)
        file2_path, error2 = db_util.store_audio_file(file2, id)

        if error1 or error2:
            return jsonify({"error": error1 or error2}), 400

        # Criar entrada na coleção GeneratedAudios
        audio_data = {
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "audio_urls": [file1_path, file2_path],
            "timestamp": datetime.now(timezone.utc)
        }
        audios = GeneratedAudioSchema(**audio_data)
        audio_id = mongo.db.GeneratedAudios.insert_one(audios.model_dump()).inserted_id  # Convertendo para dict antes de salvar

        # Registrar evento na coleção UsersEvents
        event_data = {
            "user_oid": str(ObjectId(user_oid)),  # Convertendo ObjectId para string
            "action": f"audio_file_saved_{str(audio_id)}",
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "timestamp": datetime.now(timezone.utc)
        }
        event = UserEventSchema(**event_data)
        mongo.db.UsersEvents.insert_one(event.model_dump())  # Convertendo para dict antes de salvar

        return jsonify({"message": "Generated audio saved successfully"}), 201
    except Exception as e:
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
            "user_oid": str(ObjectId(user_oid)),  # Convertendo ObjectId para string
            "action": f"audio_url_saved_{str(audio_id)}",
            "redis_id": id,
            "phone": phone,
            "lyrics": lyrics,
            "timestamp": datetime.now(timezone.utc)
        }
        event = UserEventSchema(**event_data)
        mongo.db.UsersEvents.insert_one(event.model_dump())

        return jsonify({"message": "Generated audio saved successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
