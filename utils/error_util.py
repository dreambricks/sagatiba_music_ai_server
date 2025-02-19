import json
import logging
import redis
from datetime import datetime, timezone

# Configuração do logger
logger = logging.getLogger(__name__)

# Conexão com Redis
redis_host = "localhost"
redis_port = 6379
error_db = redis.Redis(host=redis_host, port=redis_port, db=3)  # Banco de erros no Redis

def save_system_error(context, identifier, error_message):
    """ Salva informações sobre falhas no sistema no Redis """
    error_data = {
        "context": context,
        "identifier": identifier,
        "error_message": error_message,
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    }
    error_db.hset("system_errors", identifier, json.dumps(error_data))
    logger.error(f"[ERROR] Error saved in context {context} for identifier={identifier}: {error_message}")
