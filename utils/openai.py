import openai

def clean_response(input_text):
    forbidden_words = ["palavrão1", "palavrão2", "expressão de baixo calão"]

    if any(word in input_text.lower() for word in forbidden_words):
        return "PROIBIDO"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Este é um sistema seguro e educativo."},
                {"role": "user", "content": input_text}]
    )  

    if any(word in response['choices'][0]['message']['content'].lower() for word in forbidden_words):
        return "PROIBIDO"
    else:
        return "OK"

user_input = "Exemplo de entrada com palavrão1"
print(clean_response(user_input))
