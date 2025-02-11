import logging
import csv
import os
import http.client
import json
from time import sleep
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CLIP_ID_DIR = "storage"
CLIP_ID_FILE = os.path.join(CLIP_ID_DIR, "clip_id.csv")

# Atualização da função set_clip_id e get_clip_id para usar CSV
def set_clip_id(clip_id, timestamp):
    os.makedirs(CLIP_ID_DIR, exist_ok=True) 
    with open(CLIP_ID_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([clip_id, timestamp])
    logger.info(f"Saved clip_id: {clip_id} at {timestamp}")

def get_clip_id():
    if os.path.exists(CLIP_ID_FILE):
        with open(CLIP_ID_FILE, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            if rows:
                return {"clip_id": rows[-1][0], "timestamp": rows[-1][1]}
    logger.info("No Clip ID found.")
    return None

def clear_clip_id_file():
    if os.path.exists(CLIP_ID_FILE):
        os.remove(CLIP_ID_FILE)
        logger.info("[SCHEDULER] clip_id.csv file cleaned before starting the scheduler.")

def get_task_id(data):
    try:
        task_id = data.get("task_id")
        logger.info(f"Task ID extracted: {task_id}")
        return task_id
    except json.JSONDecodeError:
        logger.error("Invalid JSON string")
        return None

def get_audio_url(result):
    try:
        data = json.loads(result)
        audio_urls = [item.get("audio_url") for item in data.get("data", [])]
        logger.info(f"Audio URLs extracteds: {audio_urls}")
        return audio_urls if audio_urls and audio_urls[0] else None
    except json.JSONDecodeError:
        logger.error("Invalid JSON string")
        return None

def create_music1(lyrics):
    logger.info("Creating music 1")
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
        "custom_mode": True,
        "prompt": lyrics,
        "tags": "sertanejo, country, back vocals, strong female voice, joyfully, uplifting",
        "make_instrumental": False,
        "mv": "sonic-v3-5"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }
    conn.request("POST", "/api/v1/sonic/create", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = data.decode("utf-8")
    logger.info(f"API response (create_music2): {result}")
    return get_task_id(result)

def create_persona():
    logger.info("Creating persona")
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
        "name": "MM01",
        "description": "sertanejo, country, female voice, maiara e maraisa style",
        "continue_clip_id": "838d8482-10fe-475b-8ae4-cae5eea5c98e"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }
    conn.request("POST", "/api/v1/sonic/persona", payload, headers)
    res = conn.getresponse()
    data = res.read()
    logger.info(f"API response (create_persona): {data.decode('utf-8')}")

def upload_song(host_url):
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload_url = f"{host_url}static/trechos/vai_la_02.mp3"
    logger.info(f"Music upload started with URL: {payload_url}")
    payload = json.dumps({"url": payload_url})         # "url":"https://audio.jukehost.co.uk/wTybKVrMkkZ8LU2JmTYeA2Iad7lKxCNL"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }
    conn.request("POST", "/api/v1/sonic/upload", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = data.decode("utf-8")
    logger.info(f"API response (upload_song): {result}")
    return result

def create_music2(lyrics):
    logger.info("Creating music 2")
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
        "task_type": "persona_music",
        "custom_mode": True,
        "prompt": lyrics,
        #"tags": "sertanejo, country, back vocals, strong female voice, joyfully, uplifting",
        #"persona_id": "3c480613-4ec4-44c8-895f-080e8c683964",  # generated in the API persona MM2
        #"continue_clip_id": "33fae5fb-f72c-4251-a9b4-0167f23699ad",
        "tags": "sertanejo, two female voices, back vocals",
        "persona_id": "c0de1239-534f-4cdf-88aa-8f728b1515e2",  # generated using Suno persona: SunoPersonaI
        "continue_clip_id": "8c0e2762-2ea3-4cfe-85b6-8264200a29cd",
        "mv": "sonic-v4"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }

    conn.request("POST", "/api/v1/sonic/create", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = json.loads(data.decode("utf-8"))
    logger.info(f"API response (create_music2): {result}")
    return get_task_id(result)


def create_music3(lyrics):
    logger.info("Creating music 3")
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    clip_data = get_clip_id()
    clip_id = clip_data.get("clip_id") if clip_data else None
    
    if clip_id is None:
        logger.info("No clip_id found, uploading music...")
        response = upload_song(os.getenv("HOST_URL"))
        if response:
            try:
                data = json.loads(response)
                if data.get("code") == 200 and "clip_id" in data:
                    clip_id = data["clip_id"]
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    set_clip_id(clip_id, timestamp)
                    logger.info(f"Saved new clip_id: {clip_id}")
            except json.JSONDecodeError:
                logger.error("Error decoding JSON response from upload_song")
                return "[ERROR] Error decoding JSON response from upload_song"
    
    payload = json.dumps({
        "task_type": "extend_upload_music",
        "custom_mode": True,
        "prompt": lyrics,
        "tags": "sertanejo, female, back vocals, 30 seconds long",
        "continue_clip_id": clip_id,
        "continue_at": 24,
        "mv": "sonic-v4"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }

    logger.info("Sending request for music creation...")
    conn.request("POST", "/api/v1/sonic/create", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = json.loads(data.decode("utf-8"))
    logger.info(f"API response (create_music3): {result}")
    
    # Check the HTTP status code to handle errors
    if res.status == 401:  # Unauthorized
        logger.error("Erro 401: Unauthorized")
        if 'Authorization header is missing.' in result.get('error', ''):
            return "Error: Authorization header is missing."
        elif 'Invalid authorization format.' in result.get('error', ''):
            return "Error: Invalid authorization format."
    elif res.status == 403:  # Forbidden
        logger.error(f"Erro 403: Forbidden - {result.get('error', '')}")
        if 'The lyrics contain copyrighted content:' in result.get('error', ''):
            return f"Error: {result['error']}"
        elif 'The lyrics contain inappropriate content:' in result.get('error', ''):
            return f"Error: {result['error']}"
        elif 'The song description needs moderation review.' in result.get('error', ''):
            return "Error: Song description needs moderation."
        else:
            return f"Error: {result['error']}"
    elif res.status == 400:  # Bad Request
        logger.error("Erro 400: Bad Request - Task not found")
        if 'task not found.' in result.get('error', ''):
            return "Error: Task not found."
    elif res.status == 500:  # Server Error
        logger.error("Erro 500: Internal Server Error")
        return "Error: Internal Server Error."
    elif res.status == 504:  # Timeout
        logger.error("Erro 504: Timeout")
        return "Error: Task failed due to timeout. Credits were refunded."
    else:
        logger.info("Music successfully created, getting task_id")
        return get_task_id(result)

def create_music(lyrics):
    return create_music2(lyrics)

def get_music(task_id):
    logger.info(f"Searching for music for task_id: {task_id}")
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = ""
    headers = {
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }
    conn.request("GET", f"/api/v1/sonic/task/{task_id}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = data.decode("utf-8")

    try:
        message = json.loads(result)  # Decodifica a resposta JSON
    except json.JSONDecodeError:
        logger.error("Error: Unable to decode server response.")
        return "Error: Unable to decode server response."

    # Check the HTTP status code to handle errors
    if res.status == 401:  # Unauthorized
        logger.error("Erro 401: Unauthorized")
        if 'Authorization header is missing.' in message.get('error', ''):
            return "Error: Authorization header is missing."
        elif 'Invalid authorization format.' in message.get('error', ''):
            return "Error: Invalid authorization format."
    elif res.status == 403:  # Forbidden
        logger.error(f"Erro 403: Forbidden - {message.get('error', '')}")
        if 'The lyrics contain copyrighted content:' in message.get('error', ''):
            return f"Error: {message['error']}"
        elif 'The lyrics contain inappropriate content:' in message.get('error', ''):
            return f"Error: {message['error']}"
        elif 'The song description needs moderation review.' in message.get('error', ''):
            return "Error: Song description needs moderation."
        else:
            return f"Error: {message['error']}"
    elif res.status == 400:  # Bad Request
        logger.error("Erro 400: Bad Request - Task not found")
        if 'task not found.' in message.get('error', ''):
            return "Error: Task not found."
    elif res.status == 500:  # Server Error
        logger.error("Erro 500: Internal Server Error")
        return "Status: Music is still being processed. Please wait."
    elif res.status == 504:  # Timeout
        logger.error("Erro 504: Timeout")
        return "Error: Task failed due to timeout. Credits were refunded."
    else:
        logger.info("Musics found, returning audio URLs.")
        logger.info(f"Data: {data}")
        logger.info(f"Result: {result}")
        return get_audio_url(result)

def test_create_persona():
    create_persona()

def test_upload_song():
    logger.info("Starting music upload test")
    upload_song(os.getenv("HOST_URL"))

def test_create_song():
    task_id = '19cc9ebd-f1a2-4346-8211-c86a17697a1a'
    title = "Sagatiba"
    lyrics = """
        [Intro]
        E aí, galera. Bora seguir na saga? 
        Essa música é pra quem faz acontecer. 
        Pra quem é da equipe. 
        E sabe seguir na saga. 

        [Verse1]
        Então bora? 
        Bora levar Sagatiba pra cada esquina. 
        Pra cada mesa de bar. 
        Pra cada conversa gostosa. 

        [Chorus]
        Pra quem tá na rua. 
        Pra quem tá na loja. 
        Os donos do show. 
        Pra quem tá na rua. 
        Pra quem tá na loja. 
        Os donos do show. 

        [Verse2]
        Essa música é pra quem faz sucesso. 
        Pra quem faz Sagatiba brilhar. 
        Pra quem tem Sagatiba no coração. 
        E coloca Sagatiba no copo. 

        [Chorus]
        Pra quem tá na rua. 
        Pra quem tá na loja. 
        Os donos do show.
        Pra quem tá na rua. 
        Pra quem tá na loja. 
        Os donos do show. 
        """

    logger.info("Creating test music")
    task_id = create_music(lyrics)
    logger.info(f"Music created with task_id: {task_id}")
    while True:
        logger.info("Waiting for processing...")
        sleep(10)
        try:
            audio_url = get_music(task_id)
            if audio_url:
                break
        except:
            pass
    logger.info(f"Download at: {audio_url}")

if __name__ == "__main__":
    test_upload_song()
    # test_create_song()
