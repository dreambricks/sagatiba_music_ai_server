import os
import requests
import logging
import phonenumbers
from phonenumbers import NumberParseException

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# API de envio de SMS (smsdev.com.br)
api_url = os.getenv('SMS_API_URL')
api_key = os.getenv('SMS_API_KEY')

def send_sms_message(message, destination_number):
    """
    Envia um SMS para o número de destino usando a API `smsdev.com.br`.
    """
    try:
        if not api_key or not api_url:
            raise ValueError("API_KEY ou API_URL não configurados corretamente.")

        formatted_number = format_to_e164(destination_number)

        payload = {
            "key": api_key,
            "type": 9,
            "number": formatted_number,
            "msg": message
        }

        response = requests.post(api_url, json=payload)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("status") == "success":
            logger.info(f"[SMS] SMS enviado para {formatted_number}")
            return True
        else:
            logger.error(f"[SMS] Falha ao enviar SMS para {formatted_number}: {response_data}")
            return False

    except Exception as e:
        logger.error(f"[SMS] Erro ao enviar SMS para {destination_number}: {e}")
        return False


def send_sms_download_message(message_url, destination_number):
    """
    Envia um SMS com o link para download das músicas.
    """
    message_body = (
        "Sagalover, suas músicas estão prontas! 🎶🔥\n"
        "Acesse o link abaixo para escolher sua favorita:\n\n"
        f"{message_url}"
    )

    return send_sms_message(message_body, destination_number)


def format_to_e164(phone_number, country_code='BR'):
    """
    Formata o número de telefone para o padrão internacional E.164.
    """
    try:
        parsed_number = phonenumbers.parse(phone_number, country_code)

        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError("Número de telefone inválido.")

        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

    except NumberParseException as e:
        raise ValueError(f"Erro ao processar o número {phone_number}: {e}")
