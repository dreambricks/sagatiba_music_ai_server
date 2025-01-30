import http.client
import json
from time import sleep


def get_task_id(json_string):
    try:
        # Parse the JSON string into a Python dictionary
        data = json.loads(json_string)

        # Extract the task_id value
        task_id = data.get("task_id")

        return task_id
    except json.JSONDecodeError:
        # Handle the case where the input is not a valid JSON string
        print("Invalid JSON string")
        return None


def get_audio_url(json_string):
    try:
        data = json.loads(json_string)

        audio_urls = [item.get("audio_url") for item in data.get("data", [])]
        print(audio_urls)

        if audio_urls and audio_urls[0]:
            return audio_urls[0]

    except json.JSONDecodeError:
        # Handle the case where the input is not a valid JSON string
        print("Invalid JSON string")
        return None

    except json.JSONDecodeError:
        # Handle the case where the input is not a valid JSON string
        print("Invalid JSON string")
        return None


def create_music1(lyrics):
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
    print(result)
    return get_task_id(result)


def create_persona():
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
    print(data.decode("utf-8"))


def upload_song():
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
        #"url": "https://sagatibamusicai.ddns.net:5002/static/MARAISA_01_50s.mp3"
        #"url": "https://sagatibamusicai.ddns.net:5002/static/karina.mp3"
        "url": "https://sagatibamusicai.ddns.net:5002/static/narcisista.m4a"
        #"url": "https://sagatibamusicai.ddns.net:5002/static/mm_medo_bobo_live_50s.mp3"
        #"url": "https://audio.jukehost.co.uk/Ij5SXdAJKLg4tggS8T1xIH1Z0DuOWq5e.mp3"
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }
    conn.request("POST", "/api/v1/sonic/upload", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    # {"code": 200, "clip_id": "05722510-0bc9-4e8c-a3cc-1f72277a1752", "message": "success"}


def create_music2(lyrics):
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
        "task_type": "persona_music",
        "custom_mode": True,
        "prompt": lyrics,
        "tags": "sertanejo, country, back vocals, strong female voice, joyfully, uplifting",
        "persona_id": "804f9d62-bef4-436d-813d-48fc54847e8e",  # generated in the API
        # "persona_id": "6e2bf4db-6ba5-408a-aa5e-9eb1fc1641f1", # generated in SUNO
        "continue_clip_id": "838d8482-10fe-475b-8ae4-cae5eea5c98e",
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
    print(result)
    return get_task_id(result)


def create_music3(lyrics):
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
       "task_type": "extend_upload_music",
       "custom_mode": True,
       "prompt": lyrics,
       "tags": "sertanejo, country, back vocals, strong female voice, joyfully, uplifting",
       "continue_clip_id": "b4193d54-c9fe-440d-83c9-ecfb3f1bb6ee",
       "continue_at": 18,
       "mv": "sonic-v4"
    })
    headers = {
       'Content-Type': 'application/json',
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }

    conn.request("POST", "/api/v1/sonic/create", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = data.decode("utf-8")
    print(result)
    return get_task_id(result)


def create_music(lyrics):
    # return create_music01(lyrics) # no persona
    return create_music3(lyrics)


def get_music(task_id):
    import http.client

    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = ""
    headers = {
        'Authorization': 'Bearer 6f3be2db59c7afa567d97bdf01626fc8'
    }
    conn.request("GET", f"/api/v1/sonic/task/{task_id}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    result = data.decode("utf-8")
    print(f"Data is: {data}")
    print(f"Result is: {result}")

    return get_audio_url(result)


def test_create_persona():
    create_persona()


def test_upload_song():
    print("uploading song")
    upload_song()


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

    print("Creating Music")
    task_id = create_music(lyrics)
    print(f"Music created with task_id: {task_id}")
    while True:
        print("Waiting...")
        for i in range(10):
            print(i)
            sleep(1)
        try:
            audio_url = get_music(task_id)
            if audio_url:
                break
        except:
            pass

    print(f"download the music from: {audio_url}")


if __name__ == "__main__":
    #test_upload_song()
    test_create_song()