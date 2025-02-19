import os
import logging
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from flask import Flask

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do logger
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    logger.critical("MONGO_URI is not set!")
    raise ValueError("MONGO_URI is missing.")

logger.info("MONGO_URI successfully loaded.")

# Inicializar o PyMongo sem a instäncia do app
mongo = PyMongo()

def init_mongo(app: Flask):
    """Inicializa a conexão com o MongoDB corretamente."""
    app.config["MONGO_URI"] = MONGO_URI
    mongo.init_app(app)

    with app.app_context():
        try:
            db = mongo.db  # Testa acesso ao banco
            collections = db.list_collection_names()

            if not collections:
                logger.warning("No collections found! Ensure the database is populated.")

            logger.info("MongoDB successfully connected!")

        except Exception as e:
            logger.critical(f"Failed to connect to MongoDB: {e}", exc_info=True) 
            raise RuntimeError("MongoDB connection failed.")
