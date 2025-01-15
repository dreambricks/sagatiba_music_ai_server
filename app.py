import logging
from flask import Flask, request, render_template

from utils.openai_util import moderation_ok, generate_lyrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/alive', methods=['GET'])
def alive():
    return "alive"


@app.route("/", methods=["GET", "POST"])
def generate_lyrics_page():
    if request.method == "POST":

        # phone = request.form.get("phone")
        destination = request.form.get("destination")
        invite_options = request.form.get("invite_options")
        weekdays = request.form.get("weekdays")
        message = request.form.get("message")

        if moderation_ok(destination, message):
            lyrics = generate_lyrics(destination, invite_options, weekdays, message)
            return render_template("lyrics-generated-test.html", message=lyrics)
        else:
            formated_lyrics = """
Seu texto contém referências pejorativas, políticas ou religiosas.
Por favor, envie outro texto sem essas referências.
           """
            return render_template("lyrics-generated-test.html", message=formated_lyrics)

    return render_template("form-generate-lyrics-test.html")


if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)
