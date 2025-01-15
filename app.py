import logging
from flask import Flask, request, render_template

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
            # Gerando letras
            lyrics = generate_lyrics(destination, invite_options, weekdays, message)
            logger.info(f"Letras geradas: {lyrics}")
            return render_template("lyrics-generated-test.html", message=lyrics)
        else:
            # Mensagem para conteúdo não permitido
            formatted_lyrics = """
Seu texto contém referências pejorativas, políticas ou religiosas.
Por favor, envie outro texto sem essas referências.
           """
            logger.warning("Texto bloqueado por violar as regras de moderação.")
            return render_template("lyrics-generated-test.html", message=formatted_lyrics)

    logger.info("Renderizando formulário para geração de letras.")
    return render_template("form-generate-lyrics-test.html")


if __name__ == "__main__":
    logger.info("Iniciando aplicação Flask...")
    app.run(host='0.0.0.0', port=5002, debug=True)
