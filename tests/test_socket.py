import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print("Conectado ao servidor WebSocket!")

@sio.on('error_message')
def on_error(data):
    print(f"Erro recebido: {data}")

sio.connect('http://localhost:5001')
sio.emit('request_audio_url', { "task_id": "3d942c29-cebf-4584-a098-354c5e9826fa", "phone": "11996984576"})
sio.wait()
