import os
import requests
import logging
import phonenumbers
from phonenumbers import NumberParseException
from dotenv import load_dotenv

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
        formatted_number = format_to_e164(destination_number)

        payload = {
            "key": api_key,
            "type": 9,  # Tipo de envio de SMS
            "number": formatted_number,
            "msg": message
        }

        # Enviar a requisição para a API de SMS
        response = requests.post(api_url, json=payload)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("status") == "success":
            logger.info(f"SMS sent to {formatted_number}")
        else:
            logger.error(f"Error sending message to {formatted_number}: {response_data}")

    except Exception as e:
        logger.error(f"Error sending message to {destination_number}: {str(e)}")


def send_sms_download_message(message_url, destination_number):
    """
    Envia um SMS com o link para download das músicas.
    """
    message_body = f"Sagalover, suas músicas estão prontas! 🎶🔥\n" \
                   f"Acesse o link abaixo para escolher sua favorita:\n\n" \
                   f"{message_url}"

    send_sms_message(message_body, destination_number)


def format_to_e164(phone_number, country_code='BR'):
    """
    Formata o número de telefone para o padrão internacional E.164.
    """
    try:
        parsed_number = phonenumbers.parse(phone_number, country_code)

        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError("Invalid phone number")

        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException as e:
        raise ValueError(f"Error while processing the phone number {phone_number}: {e}")
