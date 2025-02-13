import os
import logging
import openai
from dotenv import load_dotenv, find_dotenv
from utils.db_util import load_file_into_set, remove_accent, generate_filename_with_datetime
import parameters as param

logger = logging.getLogger(__name__)

_ = load_dotenv(find_dotenv())
client = openai.OpenAI()


def load_black_list():
    return load_file_into_set(param.BLACK_LIST_FILENAME)


def has_black_list_words(black_set, input_string):
    input_set = set([remove_accent(word) for word in input_string.split()])
    intersection = black_set & input_set
    if intersection:
        return [True, ", ".join(intersection)]

    return [False, '']


def load_other_brands():
    return load_file_into_set(param.OTHER_BRANDS_FILENAME)


def has_other_brands(other_brands_set, input_string):
    no_accent_is = set([remove_accent(word) for word in input_string.split()])

    print(",".join(no_accent_is))
    for brand in other_brands_set:
        if brand in no_accent_is:
            return [True, brand]

    return [False, '']


black_list = load_black_list()
other_brands_list = load_other_brands()


def moderation_ok(convidado, recado):
    is_not_ok, error_msg = has_black_list_words(black_list, convidado)
    if is_not_ok:
        return [False, f"O convidado contém palavras não permitidas: {error_msg}"]

    is_not_ok, error_msg = has_black_list_words(black_list, recado)
    if is_not_ok:
        return [False, f"O recado palavras não permitidas: {error_msg}"]

    is_not_ok, error_msg = has_other_brands(other_brands_list, convidado)
    if is_not_ok:
        return [False, f"O convidado contém outras marcas de bebidas: {error_msg}"]

    is_not_ok, error_msg = has_other_brands(other_brands_list, recado)
    if is_not_ok:
        return [False, f"O recado contém outras marcas de bebidas: {error_msg}"]

    prompt = (
        f"Poderia informar se o texto a seguir, destacado entre ###, pode ser aprovado?\n"
        f"Responda apenas S para sim, caso a resposta seja não, informe o porquê da não aprovação\n"
        f"###\n"
        f"{convidado}, {recado}\n"
        f"###"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """
            Você é um censor de textos de um jornal sobre bebidas alcóolicas e precisa avaliar se os 
            textos enviados tem algo com conotação negativa, referências políticas, referências religiosas, 
            palavrões e termos pejorativos. O jornal deve passar sempre uma mensagem divertida e alegre e evitar, 
            a todo custo, algo que possa deixar alguém triste. 
            Referências a bebidas alcóolicas são permitidas, desde que não sejam usadas de forma pejorativa.
            Não pode incentivar o consumo exagerado, compulsivo ou irresponsável de álcool.
            Não pode sugerir que o consumo de bebidas alcoólicas traz sucesso pessoal, 
            profissional, esportivo, social ou sexual."""},
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

    logger.info(prompt)
    logger.info(response)
    result = response.choices[0].message.content
    logger.info(result)

    if result != 'S':
        return [False, result]

    return [True, "OK"]


def generate_lyrics(convidado, opcao, dia_semana, recado, store_location=None):
    logger.info(opcao)

    if opcao == "BAR":
        opcao = "beber cachaça sagatiba no bar"
    elif opcao == "ROLÊ EM CASA":
        opcao = "beber cachaça sagatiba em casa"
    elif opcao == "HAPPY HOUR":
        opcao = "happy hour com cachaça sagatiba"
    elif opcao == "SEXTOU":
        opcao = "sextou com cachaça sagatiba"
    elif opcao == "ANIVERSÁRIO":
        opcao = "aniversário com cachaça sagatiba"
    elif opcao == "FESTA":
        opcao = "festa com cachaça sagatiba"
    elif opcao == "SHOW":
        opcao = "show com cachaça sagatiba"

    prompt = (
        f"Crie a letra de uma música. O convidado é {convidado}, a ocasião é '{opcao}', "
        f"o dia da semana é {dia_semana} e o recado adicional é: '{recado}'. "
        f"A letra deve ser divertida, criativa e com rima."
        "A letra deve conter exatamente uma introdução, um verso e um refrão."
        "A letra não pode incentivar o consumo exagerado, compulsivo ou irresponsável de álcool."
        "A letra não pode sugerir que o consumo de bebidas alcoólicas traz sucesso pessoal, profissional, esportivo, social ou sexual."
    )

    response = client.chat.completions.create(
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

    logger.info(prompt)
    logger.info(response)
    lyrics = response.choices[0].message.content

    if store_location:
        lyrics_filepath = os.path.join(store_location, generate_filename_with_datetime("lyrics", "txt"))
        with open(lyrics_filepath, "w", encoding="utf-8") as f:
            f.write(lyrics)
            f.write('\n')

    return lyrics

