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

def send_whatsapp_message(url, host_url, destination_number):
    try:
        load_dotenv()
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        client = Client(account_sid, auth_token)

        from_whatsapp_number = 'whatsapp:+14155238886'
        formatted_number = format_to_e164(destination_number)
        to_whatsapp_number = f'whatsapp:{formatted_number}'

        download_url = f"{host_url}audio/download?audio_url={url}"
        
        message_body = f"Sagalover, sua música está pronta para ser ouvida e compartilhada! {download_url}" 

        client.messages.create(body=message_body,
                               from_=from_whatsapp_number,
                               to=to_whatsapp_number)

        logging.info("Message has been sent to %s", formatted_number)
    except Exception as e:
        logging.error("Error when sending message to %s: %s", formatted_number, str(e))
    

def format_to_e164(phone_number, country_code='BR'):
    try:
        parsed_number = phonenumbers.parse(phone_number, country_code)
        
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError("Invalid phone number")
        
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException as e:
        raise ValueError(f"Error parsing phone number: {e}")
    

 # send_whatsapp_message('Não confiar em carécas', '11959174501')
