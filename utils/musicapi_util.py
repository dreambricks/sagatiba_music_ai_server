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
        # Parse the JSON string into a Python dictionary
        data = json.loads(json_string)

        # Extract the list of audio URLs from the data
        audio_urls = [item.get("audio_url") for item in data.get("data", [])]
        print(audio_urls)

        return audio_urls[0]
    except json.JSONDecodeError:
        # Handle the case where the input is not a valid JSON string
        print("Invalid JSON string")
        return None


def create_music(lyrics):
    conn = http.client.HTTPSConnection("api.musicapi.ai")
    payload = json.dumps({
       "custom_mode": True,
       "prompt": lyrics,

       "tags": "sertanejo with female voice maiara e maraisa style",
       "gpt_description_prompt": "",
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


if __name__ == "__main__":
    task_id = 'd5284f49-6fb2-4684-bbed-24aac0807dfe'
    title = "Teste quinta feira com o zé"
    lyrics = """
    **Título: Quinta do Zé**  

*(Verso 1)*  
Hoje é quinta, já sei que é você,  
Zé chegou no bar pra gente se divertir,  
Garçons correndo, a cerveja a fluir,  
Cento e cinquenta, vamos nos permitir!  

*(Refrão)*  
Cento e cinquenta, vem, vamo gastar,  
Rindo e cantando, não podemos parar,  
Zé no batuque, anima a galera,  
Essa noite é nossa, a melhor era!  

*(Verso 2)*  
Petiscos na mesa, o clima tá bom,  
Sorrisos e histórias, tudo em seu tom,  
Os amigos tão juntos, não há o que temer,  
Zé na cachaça, deixa a tristeza em dobro correr!  

*(Refrão)*  
Cento e cinquenta, vem, vamo gastar,  
Rindo e cantando, não podemos parar,  
Zé no batuque, anima a galera,  
Essa noite é nossa, a melhor era!  

*(Ponte)*  
E quando a luz do bar começa a brilhar,  
A música toca e a gente quer dançar,  
Zé me diz: "Amigo, tá tudo bem,  
Com essa vibe, não queremos mais ninguém!"  

*(Refrão)*  
Cento e cinquenta, vem, vamo gastar,  
Rindo e cantando, não podemos parar,  
Zé no batuque, anima a galera,  
Essa noite é nossa, a melhor era!  

*(Final)*  
Então levanta o copo, faz um brinde, vai,  
Às quintas com Zé, não tem "não" nem "talvez",  
O céu é o limite, e a noite é você,  
Hoje é festa, vem, vamos celebrar mais uma vez!  

**Refrão final:**  
Cento e cinquenta, vem, vamo gastar,  
Rindo e cantando, não podemos parar,  
Zé no batuque, anima a galera,  
Essa noite é nossa, a melhor era!  
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
