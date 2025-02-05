from twilio.rest import Client
import os
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


def send_whatsapp_message(message, destination_number):
    try:
        load_dotenv()
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        client = Client(account_sid, auth_token)

        from_whatsapp_number = 'whatsapp:+14155238886'
        formatted_number = format_to_e164(destination_number)
        to_whatsapp_number = f'whatsapp:{formatted_number}'

        client.messages.create(body=message,
                               from_=from_whatsapp_number,
                               to=to_whatsapp_number)

        logging.info(f"Message has been sent to {formatted_number}")
    except Exception as e:
        logging.error(f"Error when sending message to {destination_number}: {str(e)}")


def send_whatsapp_download_message(urls, host_url, destination_number):
    download_urls = [f"{host_url}audio/download?audio_url={url}" for url in urls if url]  # Apenas URLs válidas

    message_body = f"Sagalover, suas músicas estão prontas para serem ouvidas!\n" \
                   f"Geramos duas músicas para que possa escolher a que mais gostou:\n" \
                   f"\n".join(download_urls)
    send_whatsapp_message(message_body, destination_number)


def format_to_e164(phone_number, country_code='BR'):
    try:
        parsed_number = phonenumbers.parse(phone_number, country_code)
        
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError("Invalid phone number")
        
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException as e:
        raise ValueError(f"Error parsing phone number: {e}")

