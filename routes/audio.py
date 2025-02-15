from flask import Blueprint, request, jsonify
from config.mongo_config import mongo
from schemas.generated_audios import GeneratedAudioSchema

audio_bp = Blueprint("audio_bp", __name__)

@audio_bp.route("/audios/save", methods=["POST"])
def save_generated_audio():
    """Salva os links dos áudios gerados na Suno na coleção Generated Audios"""
    data = request.json
    try:
        audio = GeneratedAudioSchema(**data)
        mongo.db.GeneratedAudios.insert_one(audio.model_dump())
        return jsonify({"message": "Generated audio saved successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
