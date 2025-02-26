import socketio

# Criar cliente SocketIO
sio = socketio.Client()

# Eventos do WebSocket
@sio.on('connect')
def on_connect():
    print("Conectado ao servidor WebSocket!")

@sio.on('disconnect')
def on_disconnect():
    print("Desconectado do servidor WebSocket!")

@sio.on('error_message')
def on_error(data):
    print(f"Erro recebido: {data}")

@sio.on('audio_response')
def on_audio_response(data):
    print(f"Resposta recebida: {data}")

# Conectar ao servidor WebSocket
try:
    sio.connect('http://localhost:5001')  # Alterar a porta se necessário
    print("Conexão estabelecida!")
except Exception as e:
    print(f"Erro ao conectar: {e}")
    exit()

# Enviar requisição para `request_audio_url`
print("Enviando requisição de áudio...")
sio.emit('request_audio_url', {
    "task_id": "785fb1c3-fc65-4345-a357-d7540aed0e47",
    "phone": "11996984576"
})

# Aguardar respostas do servidor
sio.wait()
