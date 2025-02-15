import threading
import requests
import time
import random
import socketio

BASE_URL = "http://localhost:5001"
socket = socketio.Client()

# Simulação de números de telefone
PHONE_NUMBERS = ["11987654321", "11876543210", "11765432109"]

def generate_lyrics():
    """Simula clientes pedindo músicas"""
    payload = {
        "lyrics": f"Sample lyrics {random.randint(100, 999)}",
        "phone": random.choice(PHONE_NUMBERS)
    }
    response = requests.post(f"{BASE_URL}/lyrics/generate", json=payload)
    print("📥 Lyrics Requested:", response.json())

def process_task():
    """Simula trabalhadores retirando tarefas da fila"""
    response = requests.post(f"{BASE_URL}/lyrics/process", json={"phone": random.choice(PHONE_NUMBERS)})
    data = response.json()
    
    if "task_id" in data:
        task_id = data["task_id"]
        print(f"👷 Worker Processing Task {task_id}")

        # Simula tempo de trabalho
        time.sleep(random.randint(2, 5))

        # 20% de chance de o trabalhador **não concluir** a tarefa
        if random.random() > 0.2:
            complete_task(task_id)
        else:
            print(f"⚠️ Worker abandoned Task {task_id}!")

def complete_task(task_id):
    """Simula trabalhadores concluindo a tarefa"""
    payload = {"id": task_id, "success": True}
    socket.emit("task_completed", payload)
    print(f"✅ Task {task_id} completed!")

def check_status():
    """Verifica o status do sistema"""
    response = requests.get(f"{BASE_URL}/api/check/status")
    print("🔍 System Status:", response.json())

def get_queue():
    """Verifica a fila de tarefas"""
    socket.emit("get_queue")
    print("📊 Queue Requested")

@socket.on("queue_list")
def on_queue_list(data):
    """Recebe a lista da fila de tarefas"""
    print("📊 Current Queue:", data)

def requeue_task():
    """Reinsere uma tarefa na fila caso ela tenha ficado pendente"""
    response = requests.get(f"{BASE_URL}/api/check/status")
    status_data = response.json()
    
    if "errors" in status_data and status_data["errors"]:
        failed_task_id = status_data["errors"][0]["identifier"]
        payload = {"id": failed_task_id}
        socket.emit("requeue_task", payload)
        print(f"🔄 Task {failed_task_id} manually requeued!")

# Conectar ao WebSocket
socket.connect(BASE_URL)

# Criar múltiplas threads para simular carga
threads = [
    threading.Thread(target=generate_lyrics),
    threading.Thread(target=generate_lyrics),
    threading.Thread(target=generate_lyrics),
    threading.Thread(target=process_task),
    threading.Thread(target=process_task),
    threading.Thread(target=process_task),
    threading.Thread(target=check_status),
    threading.Thread(target=get_queue),
]

# Executar as threads concorrentes
for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

# Reenfileirar uma tarefa se necessário
time.sleep(5)
requeue_task()

print("✅ Concurrent API Test Completed!")

# Fechar conexão do WebSocket
socket.disconnect()
