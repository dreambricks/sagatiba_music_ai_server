import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from utils.email_utils import send_verification_email
from flask import request, jsonify, url_for, redirect
from config.mongo_config import mongo
from schemas.users import UserSchema
from schemas.workers import WorkerSchema
from schemas.worker_events import WorkerEventSchema
from flask import Blueprint
from bson import ObjectId
from datetime import datetime, timezone

# Chave secreta para gerar JWT
SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
serializer = URLSafeTimedSerializer(SECRET_KEY)

user_bp = Blueprint("user_bp", __name__)

@user_bp.route("/users/register", methods=["POST"])
def register_user():
    """Registra um novo usuário"""
    data = request.json
    email = data.get("email")
    password_hash = data.get("password_hash")
    user_info_hash = data.get("user_info_hash")

    
    if not email or not password_hash or not user_info_hash:
        return jsonify({"error": "Não foi possível concluir o cadastro do usuário, dados estão incompletos"}), 400
    
    save_data = {
        "email": email,
        "password_hash": bcrypt.hashpw(password_hash.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "user_info_hash": user_info_hash,
        "validated": False,
        "created_at": datetime.now(timezone.utc)
    }

    try:
        user = UserSchema(**save_data)
        user_id = mongo.db.Users.insert_one(user.model_dump()).inserted_id

        # Gera um token de validação com prazo de 24h
        token = serializer.dumps(str(user_id), salt='email-confirm-salt')

        # Envia o e-mail de verificação
        verification_link = url_for('user_bp.verify_email', token=token, _external=True)
        send_verification_email(email, verification_link)

        return jsonify({"message": "Ususuário registrado com sucesso"}), 201
    except Exception as e:
        return jsonify({"error": f"Não foi possível concluir o cadastro do usuário, erro ao salvar os dados: {str(e)}"}), 400

@user_bp.route("/users/verify_email/<token>", methods=["GET"])
def verify_email(token):
    """Valida o e-mail do usuário e redireciona para o login"""
    try:
        # Decodifica o token e obtém o ID do usuário
        user_id = serializer.loads(token, salt='email-confirm-salt', max_age=86400)  # 24 horas

        # Atualiza o status do usuário para validado
        result = mongo.db.Users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"validated": True}}
        )

        if result.modified_count == 1:
            return redirect("https://seguenasaga.sagatiba.com/", code=302)
        else:
            return jsonify({"error": "Usuário não encontrado ou já validado."}), 400

    except SignatureExpired:
        return jsonify({"error": "O link de verificação expirou. Solicite um novo e-mail de validação."}), 400

    except BadSignature:
        return jsonify({"error": "O link de verificação é inválido."}), 400

@user_bp.route("/users/worker/register", methods=["POST"])
def register_worker():
    """Registra um novo usuário"""
    data = request.json
    try:
        user = WorkerSchema(**data)
        # Hash da senha antes de salvar
        user.password_hash = bcrypt.hashpw(user.password_hash.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        mongo.db.Workers.insert_one(user.model_dump())
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_bp.route("/users/worker/login", methods=["POST"])
def login_worker():
    """Verifica as credenciais do usuário e retorna um token de autenticação"""
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Buscar usuário no banco de dados
    user = mongo.db.Workers.find_one({"email": email})
    
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
        event = WorkerEventSchema(**data)
        mongo.db.UsersEvents.insert_one(event.model_dump())
        return jsonify({"message": "Event logged successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400