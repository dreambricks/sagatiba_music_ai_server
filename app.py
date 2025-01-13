import logging
from flask import Flask, request, render_template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/alive', methods=['GET'])
def alive():
    return "alive"

@app.route("/generate-lyrics", methods=["GET", "POST"])
def generate_lyrics():
    if request.method == "POST":

        phone = request.form.get("phone")
        destination = request.form.get("destination")
        invite_options = request.form.getlist("invite")
        weekdays = request.form.getlist("weekday")
        message = request.form.get("message")

        print(f"""
                Dados recebidos:
                
                Phone: {phone}
                Destination: {destination}
                Invite Options: {invite_options}
                Weekdays: {weekdays}
                Message: {message}
                """)

    return render_template("form.html")

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)