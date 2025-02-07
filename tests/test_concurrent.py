import requests
import socketio
import threading
import json
import time
import random

# Configuração
BASE_URL = "http://localhost:5001"
WS_URL = "http://localhost:5001"

sio = socketio.Client(reconnection=True)

# Lista de telefones simulados
phones = ["+5511987654301", "+5511987654302", "+5511987654303"]
lyrics_samples = [
    """
    **Título: "Sextou com Cachaça"**
    
    *Introdução:*  
    Olha quem chegou, é José!  
    Sexta-feira já tá a nos querer,  
    Cachaça Sagatiba na mão,  
    Vamos brindar a diversão!  

    *Verso:*  
    Amigos reunidos, risadas no ar,  
    Histórias contadas, vamos celebrar,  
    Um brinde à vida, sem preocupação,  
    Coração leve, só alegria no coração.  

    *Refrão:*  
    Sextou, sextou, vem cá, vamos beber!  
    Com a cachaça na mesa, não há como esquecer,  
    É pura amizade, a gente vai dançar,  
    José, meu amigo, vem pra festejar!  

    Vamos juntos nessa boa vibração,  
    Com um sorriso, e da vida, a sensação.  
    Sextou com cachaça, um brinde pra valer,  
    A felicidade é aqui, vamos aproveitar!
    """,

    """
    **Título: "Sexta à Vista"**
    
    *Introdução:*  
    A noite desponta, tô com a melhor companhia,  
    José chegou, a energia é pura alegria!  
    Barzinho animado, a galera tá a mil,  
    A felicidade tá no ar, vamos juntos, é o perfil!  

    *Verso:*  
    Luz de neon, risadas vão ecoar,  
    Um brinde à amizade, vamos celebrar!  
    Na mesa do bar, histórias vão rolar,  
    Com um copo na mão, é hora de aproveitar!  

    *Refrão:*  
    Sexta à vista, é hora de brindar,  
    José e os amigos, prontos pra dançar!  
    Vamos beber, mas sem exagerar,  
    A festa é na risada, deixa a vida deslizar!  
    """,

    """
    **Título: "Sexta-feira de Alegria"**
    
    *Introdução:*  
    Sexta-feira chegou, vamos celebrar,  
    Com cachaça Sagatiba, é hora de brindar,  
    José tá no som, vem todo mundo dançar,  
    A festa começou, vamos nos alegrar!  

    *Verso:*  
    Os copos levantados, risadas no ar,  
    O amigo verdadeiro é quem vem pra ficar.  
    No calor da amizade, a gente vai se encontrar,  
    Coração batendo forte, não tem como errar.  

    *Refrão:*  
    Vamos beber, vamos brindar,  
    Com alegria e amigos pra alegrar,  
    Na batida da vida, é só deixar rolar,  
    Sexta-feira é festa, vem todo mundo amar!  

    *Repetição do refrão:*  
    Vamos beber, vamos brindar,  
    Com alegria e amigos pra alegrar,  
    Na batida da vida, é só deixar rolar,  
    Sexta-feira é festa, vem todo mundo amar!  
    """
]

# Dicionário para armazenar task_ids por telefone
task_map = {}

# Conectar ao servidor WebSocket
def connect_socket():
    print("[WebSocket] Conectando...")
    sio.connect(WS_URL)
    print("[WebSocket] Conectado")

# Evento de mensagem recebida do WebSocket
@sio.on("message")
def on_message(data):
    print(f"[WebSocket] Mensagem recebida: {data}")

# Evento de erro do WebSocket
@sio.on("error_message")
def on_error(data):
    print(f"[WebSocket] Erro recebido: {data}")

# Evento de resposta de áudio
@sio.on("audio_response")
def on_audio_response(data):
    print(f"[WebSocket] Áudio recebido: {data}")

# Função para enfileirar letras
def enqueue_lyrics(phone, lyrics):
    response = requests.post(f"{BASE_URL}/lyrics/generate", json={"lyrics": lyrics, "phone": phone})
    print(f"[Enqueue] {phone}: {response.json()}")

# Função para processar a fila e pegar task_id
def process_task(phone):
    response = requests.post(f"{BASE_URL}/lyrics/process", json={"phone": phone})
    data = response.json()
    if "task_id" in data:
        task_map[phone] = data["task_id"]
        print(f"[Process] {phone}: Task ID {data['task_id']}")
    else:
        print(f"[Process] {phone}: {data}")

# Função para testar WebSocket e solicitar áudio
def request_audio(phone, task_id):
    print(f"[WebSocket] Enviando requisição de áudio para {phone}, Task ID: {task_id}")
    sio.emit("request_audio_url", {"task_id": task_id, "phone": phone})

# Simula uma desconexão e reconexão durante o processamento
def simulate_disconnect_reconnect(phone):
    print(f"[Disconnect Test] {phone} Disconnecting...")
    sio.disconnect()
    time.sleep(random.randint(2, 5))
    print(f"[Disconnect Test] {phone} Reconnecting...")
    connect_socket()
    process_task(phone)

# Executa as operações concorrentes
def run_concurrent_tests():
    threads = []

    connect_socket()  # Conecta ao WebSocket antes de iniciar os testes

    # Enfileira as letras para cada telefone
    for phone, lyrics in zip(phones, lyrics_samples):
        t = threading.Thread(target=enqueue_lyrics, args=(phone, lyrics))
        threads.append(t)
        t.start()

    # Aguarda enfileiramento antes de processar
    time.sleep(3)

    # Processa as tarefas
    for phone in phones:
        t = threading.Thread(target=process_task, args=(phone,))
        threads.append(t)
        t.start()

    # Aguarda processamento antes de testar WebSocket
    time.sleep(5)

    # Testa WebSockets para cada telefone
    for phone in phones:
        if phone in task_map:
            t = threading.Thread(target=request_audio, args=(phone, task_map[phone]))
            threads.append(t)
            t.start()

    # Simula desconexão e reconexão aleatória
    time.sleep(3)
    t = threading.Thread(target=simulate_disconnect_reconnect, args=(random.choice(phones),))
    threads.append(t)
    t.start()

    # Aguarda todas as threads finalizarem
    for t in threads:
        t.join()

    sio.disconnect()  # Desconectar o WebSocket ao final do teste

# Executa o teste
if __name__ == "__main__":
    run_concurrent_tests()
