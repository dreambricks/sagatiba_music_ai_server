import logging
from time import sleep

from flask import Flask, request, render_template, url_for
from werkzeug.utils import redirect

from utils.musicapi_util import create_music, get_music
from utils.openai_util import moderation_ok, generate_lyrics

import threading

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

    thread = threading.Thread(target=create_music_audio, args=(lyrics,))
    thread.start()

    return render_template("lyrics-generated-test.html", lyrics=lyrics)

def create_music_audio(lyrics):
    print("Creating Music...")
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
                print(f"Audio URL: {audio_url}")
                break
        except:
            pass
    return audio_url


if __name__ == "__main__":
    logger.info("Iniciando aplicação Flask...")
    app.run(host='0.0.0.0', port=5002, debug=True)
