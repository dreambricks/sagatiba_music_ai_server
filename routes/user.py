import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from flask import request, jsonify
from config.mongo_config import mongo
from schemas.users import UserSchema
from schemas.user_events import UserEventSchema
from flask import Blueprint
from bson import ObjectId

# Chave secreta para gerar JWT
SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

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

@user_bp.route("/users/login", methods=["POST"])
def login_user():
    """Verifica as credenciais do usuário e retorna um token de autenticação"""
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Buscar usuário no banco de dados
    user = mongo.db.Users.find_one({"email": email})
    
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # Comparar a senha fornecida com o hash armazenado
    if not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        return jsonify({"error": "Invalid email or password"}), 401

    # Gerar token JWT (caso precise autenticação)
    token_payload = {
        "user_oid": str(user["_id"]),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2)  # Expira em 2 horas
    }
    token = jwt.encode(token_payload, SECRET_KEY, algorithm="HS256")

    # Registrar evento no UsersEvents
    event_data = {
        "user_oid": ObjectId(user["_id"]),
        "action": "user_login",
        "token": token,
        "timestamp": datetime.now(timezone.utc)
    }
    mongo.db.UsersEvents.insert_one(event_data)

    return jsonify({"message": "Login successful", "user_oid": user["_id"], "token": token}), 200
    # return jsonify({"message": "Login successful", "token": token}), 200


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