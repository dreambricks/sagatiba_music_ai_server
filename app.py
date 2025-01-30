import logging
from datetime import datetime
import random
import os
import requests
import time

from flask import Flask, request, render_template, url_for, jsonify, send_file, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from utils.musicapi_util import create_music, get_music
from utils.openai_util import moderation_ok, generate_lyrics

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app)
CORS(app)

@app.route('/alive', methods=['GET'])
def health_check():
    logger.info("Alive check endpoint accessed.")
    return jsonify({"status": "healthy"}), 200

@app.route("/lyrics/form", methods=["GET"])
def display_lyrics_form():
    """Renderiza o formulário para geração de letras."""
    logger.info("Rendering lyrics generation form.")
    return render_template("form-generate-lyrics-test.html")

@app.route("/lyrics", methods=["POST"])
def call_generate_lyrics():
    """Gera letras com base nos dados do formulário e retorna JSON com as letras ou erro."""
    destination = request.form.get("destination")
    invite_options = request.form.get("invite_options")
    weekdays = request.form.get("weekdays")
    message = request.form.get("message")

    logger.info(f"Received form data: destination={destination}, invite_options={invite_options}, "
                f"weekdays={weekdays}, message={message}")

    if moderation_ok(destination, message):
        lyrics = generate_lyrics(destination, invite_options, weekdays, message)
        logger.info("Lyrics generated successfully.")
        return redirect(url_for('display_lyrics', lyrics=lyrics))
        #return jsonify({"lyrics": lyrics}), 201 #(JULIO - APLICAR ESSE TIPO DE RESPOSTA NA PAGINA OFICIAL)
    else:
        logger.warning("Submitted text violates moderation rules.")
        return jsonify({"error": "Content blocked due to inappropriate references."}), 403

@app.route("/lyrics/display", methods=["GET"])
def display_lyrics():
    """Exibe a página com as letras geradas."""
    lyrics = request.args.get('lyrics')
    return render_template("lyrics-generated-test.html", lyrics=lyrics)

@app.route("/lyrics/submit", methods=["POST"])
def submit_lyrics():
    """Recebe as letras via formulário POST e exibe na página de letras."""
    lyrics = request.form.get('lyrics', '')
    if lyrics:
        return render_template("lyrics-generated-test.html", lyrics=lyrics)
    else:
        return render_template("lyrics-generated-test.html", lyrics="Nenhuma letra foi enviada.")

@app.route("/lyrics/generate", methods=["GET"])
def generate_task_id():
    """Generate a task ID for the provided lyrics and return as JSON."""
    lyrics = request.args.get("lyrics")
    if not lyrics:
        return jsonify({"error": "Lyrics parameter is missing"}), 400

    task_id = create_music(lyrics)
    if task_id:
        return task_id
        # return jsonify({"task_id": task_id}), 201 #(JULIO - APLICAR ESSE TIPO DE RESPOSTA NA PAGINA OFICIAL)
    else:
        return jsonify({"error": "Failed to create task ID"}), 500

# @app.route("/lyrics/audio", methods=["GET"])
# def get_audio():
#     """Returns audio URL or error status."""
#     task_id = request.args.get('task_id')
#     if not task_id:
#         return jsonify({"error": "Task ID is required"}), 400

#     audio_url = get_music(task_id)
#     if audio_url:
#         return audio_url
#         # return jsonify({"audio_url": audio_url}), 200
#     else:
#         return jsonify({"error": "Audio generation pending"}), 202

@socketio.on('request_audio_url')
def request_audio(json):
    task_id = json.get('task_id')
    if not task_id:
        emit('audio_response', {'error': 'Task ID is required', 'code': 400}, namespace='/')
        return

    attempts = 0
    while attempts < 30:
        audio_url = get_music(task_id)
        if audio_url:
            emit('audio_response', {'audio_url': audio_url}, namespace='/')
            return
        socketio.sleep(10)
        attempts += 1

    emit('audio_response', {'error': 'Failed to generate audio after several attempts', 'code': 500}, namespace='/')

@app.route("/audio/download", methods=["GET"])
def download_audio():
    """Provides a file download for the generated audio."""
    audio_url = request.args.get('audio_url')
    if not audio_url:
        return jsonify({"error": "Audio URL not provided"}), 400

    tmp_dir = 'temp/'
    numero = random.randint(0, 99999)
    data_atual = datetime.now().strftime("%d%m%Y%H%M%S")
    result_name = f"{numero}_{data_atual}"
    file_name = f"{result_name}.mp3"
    temp_path = os.path.join(tmp_dir, file_name)

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    try:
        response = requests.get(audio_url, stream=True)
        if response.status_code != 200:
            return jsonify({"error": "Failed to download file"}), 500

        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        time.sleep(1)
        return send_file(temp_path, as_attachment=True, download_name=file_name, mimetype="audio/mpeg")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)
