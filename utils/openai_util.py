import openai
from dotenv import load_dotenv
import os

def clean_response(input_text):
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai.api_key = openai_api_key

    messages = [
        {"role": "system", "content": "Este é um sistema educativo. Por favor, evite conteúdo ofensivo e inapropriado."},
        {"role": "user", "content": input_text}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300
    )

    generated_text = response.choices[0].message["content"]

    eval_messages = [
        {"role": "system", "content": "Avalie se a resposta anterior contém linguagem ofensiva, inapropriada ou com assuntos relacionados à política ou religião."},
        {"role": "user", "content": generated_text}
    ]

    eval_response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=eval_messages,
        max_tokens=300
    )

    eval_content = eval_response.choices[0].message["content"].lower()
    if "não" in eval_content or "nenhuma" in eval_content:
        return "OK"
    else:
        return "PROIBIDO"

user_input = "Exemplo de entrada em que catolicismo é ruim"
print(clean_response(user_input))
