from flask import Blueprint, request, jsonify
from config.mongo_config import mongo
from schemas.users import UserSchema
from schemas.user_events import UserEventSchema
import bcrypt

user_bp = Blueprint("user_bp", __name__)

@user_bp.route("/users/register", methods=["POST"])
def register_user():
    """Registra um novo usuário"""
    data = request.json
    try:
        user = UserSchema(**data)
        # Hash da senha antes de salvar
        user.password_hash = bcrypt.hashpw(user.password_hash.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        mongo.db.Users.insert_one(user.model_dump())
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/events/log", methods=["POST"])
def log_user_event():
    """Registra uma ação do usuário na coleção Users Events"""
    data = request.json
    try:
        event = UserEventSchema(**data)
        mongo.db.UsersEvents.insert_one(event.model_dump())
        return jsonify({"message": "Event logged successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400