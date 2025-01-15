import openai
from dotenv import load_dotenv
import os

def moderation_ok(convidado, recado):
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai.api_key = openai_api_key

    prompt = (
        f"Poderia informar se o texto a seguir, destacado entre ###, seria aprovado?\n"
        f"Responda apenas S para sim ou N para não.\n"
        f"###\n"
        f"{convidado} {recado}\n"
        f"###"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um censor de textos de um jornal sobre bebidas alcóolicas e precisa avaliar se os textos enviados tem algo com conotação negativa, referências políticas, referências religiosas, palavrões e termos pejorativos. O jornal deve passar sempre uma mensagem divertida e alegre e evitar, a todo custo, algo que possa deixar alguém triste. Referências a bebidas alcóolicas são permitidas, desde que não sejam usadas de forma pejorativa."},
            {"role": "user", "content": prompt}
        ],
        response_format={
            "type": "text"
        },
        temperature=0,
        max_completion_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    print(prompt)
    print(response)
    result = response.choices[0].message.content
    print(result)

    return result == 'S'


def generate_lyrics(convidado, opcao, dia_semana, recado):
    prompt = (
        f"Crie a letra de uma música. O convidado é {convidado}, a ocasião é '{opcao}', "
        f"o dia da semana é {dia_semana} e o recado adicional é: '{recado}'. "
        f"A letra deve ser divertida, criativa e com rima"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um criador de letras de músicas."},
            {"role": "user", "content": prompt}
        ],
        response_format={
            "type": "text"
        },
        max_completion_tokens=2048,
        temperature=1,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    print(response)
    lyrics = response.choices[0].message.content
    return lyrics

