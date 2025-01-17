import logging
from datetime import datetime
import random

from flask import Flask, request, render_template, url_for, jsonify, send_file, redirect
from flask_cors import CORS

from utils.musicapi_util import create_music, get_music
from utils.openai_util import moderation_ok, generate_lyrics
import os
import requests
import time

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
CORS(app)


@app.route('/alive', methods=['GET'])
def alive():
    logger.info("Endpoint /alive acessado.")
    return "alive"


@app.route("/", methods=["GET", "POST"])
def generate_lyrics_page():
    if request.method == "POST":
        destination = request.form.get("destination")
        invite_options = request.form.get("invite_options")
        weekdays = request.form.get("weekdays")
        message = request.form.get("message")

        # Logando os dados recebidos no formulário
        logger.info(f"Formulário recebido: destination={destination}, invite_options={invite_options}, "
                    f"weekdays={weekdays}, message={message}")

        if moderation_ok(destination, message):

            lyrics = generate_lyrics(destination, invite_options, weekdays, message)
            logger.info(f"Letras geradas: {lyrics}")
            return redirect(url_for('lyrics_page', lyrics=lyrics))
        else:
            # Mensagem para conteúdo não permitido
            blocked_message = """
Seu texto contém referências pejorativas, políticas ou religiosas.
Por favor, envie outro texto sem essas referências.
           """
            logger.warning("Texto bloqueado por violar as regras de moderação.")
            return render_template("lyrics-generated-test.html", lyrics=blocked_message)

    logger.info("Renderizando formulário para geração de letras.")
    return render_template("form-generate-lyrics-test.html")


@app.route("/lyrics_page", methods=["GET", "POST"])
def lyrics_page():
    lyrics = request.args.get('lyrics')
    return render_template("lyrics-generated-test.html", lyrics=lyrics)


@app.route("/generate_task_id")
def generate_task_id():
    lyrics = request.args.get("lyrics")
    task_id = create_music(lyrics)
    print(task_id)
    return task_id


@app.route("/create_music_audio")
def create_music_audio():
    task_id = request.args.get('task_id')
    audio_url = get_music(task_id)
    if audio_url:
        return audio_url
    else:
        return "Aguardando geracao do audio", 500


@app.route("/download_audio", methods=["GET"])
def download_audio():
    audio_url = request.args.get('audio_url')
    if not audio_url:
        return {"error": "No audio_url provided"}, 400

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
            return {"error": "Failed to download file"}, 500

        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        time.sleep(1)

        return send_file(temp_path, as_attachment=True, download_name=file_name, mimetype="audio/mpeg")

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    logger.info("Iniciando aplicação Flask...")
    app.run(host='0.0.0.0', port=5002, debug=True)
