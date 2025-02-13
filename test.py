import logging

import os
import requests

#import log_config

import utils.musicapi_util as musicapi
from utils.openai_util import moderation_ok, generate_lyrics
from utils.twilio_util import send_whatsapp_message
import time
import re
import utils.audio_util as audio_util
import utils.db_util as db_util

logger = logging.getLogger(__name__)


def test_create_persona():
    musicapi.create_persona()


def test_upload_song(song_filename=None):
    if song_filename:
        logger.info(f"uploading song {song_filename}")
    else:
        logger.info("uploading song")
    result = musicapi.upload_song(song_filename)
    logger.info(result)


def store_audio(url, prefix=None, max_size=1177 * 1024):
    tmp_dir = 'static/mp3/'
    task_id = get_task_id_from_url(url)
    file_name = f"sagatiba_{prefix}_{task_id}.mp3" if prefix else f"sagatiba_{task_id}.mp3"
    temp_path = os.path.join(tmp_dir, file_name)

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return None # jsonify({"error": "Failed to download file"}), 500

        file_size = 0
        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file_size += len(chunk)
                if chunk:
                    file.write(chunk)
                    if file_size >= max_size:
                        break

        time.sleep(1)
        return temp_path

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None # jsonify({"error": str(e)}), 500


def store_audio_and_fade_out(url, task_id, max_size=1177*1024):
    filepath = store_audio(url, task_id, max_size)

    if filepath is None:
        return None

    faded_filepath = db_util.add_suffix_to_filepath(filepath, "f")
    audio_util.fade_out(filepath, faded_filepath)

    return faded_filepath


def get_task_id_from_url(url):
    """
    Extracts the task_id from a given URL.

    Supported formats:
    - 'https://audiopipe.suno.ai/?item_id=<task_id>'
    - 'https://cdn1.suno.ai/<task_id>.mp3'
    """
    pattern = re.compile(r'([a-f0-9-]{36})')  # Matches UUID-like patterns
    match = pattern.search(url)
    return match.group(1) if match else None


def links_to_curl(urls, prefix=None):
    for url in urls:
        id = None
        try:
            id = get_task_id_from_url(url)
            if prefix:
                id = f"{prefix}_{id}"
            print(f"curl -o sagatiba_{id}.mp3 {url}")
        except:
            pass


def test_create_song(continue_clip_id="5ba1800f-b498-45d1-a0d6-aa0deac46144", continue_at=21, lyric_id=2, model="sonic-v4", tags=None, song_cut=None, my_lyrics=None):
    global global_tags, global_model

    global_model = model

    if tags:
        global_tags = tags

    song_cuts = {
        "morango_03.mp3": {"clip_id": "667dd19f-f7a4-4871-88db-751412ae1448", "continue_at": 25},
        "vai_la_01.mp3": {"clip_id": "98b55f7a-98cf-46d3-8940-ca8361a99827", "continue_at": 29},
        "vai_la_02.mp3": {"clip_id": "6e8c6613-a9b1-4d39-9260-61abd5829333", "continue_at": 24},
        "suno_grave_01.mp3": {"clip_id": "c7d53c56-4a06-4fab-b881-4464abfea30a", "continue_at": 29},
        "grave_03.mp3": {"clip_id": "bca0948a-5172-48e2-b286-dabafeaa5162", "continue_at": 24},
        "grave_01.mp3": {"clip_id": "c7d53c56-4a06-4fab-b881-4464abfea30a", "continue_at": 26},
        "grave_10e.mp3": {"clip_id": "362685c4-c238-4df8-9b77-94b6a9f46403", "continue_at": 30},
        "grave_09e.mp3": {"clip_id": "81b68397-a480-4114-bb6b-73ae40a3c395", "continue_at": 30},
        "02_MARAISA_MORANGO_COM_CHOCOLATE.mp3": {"clip_id": "381d55db-63aa-49bf-b1cc-162124edb59f", "continue_at": 18},
        "AMORES_DA_MINHA_VIDA_corte1.mp3": {"clip_id": "78dcd27e-62a1-4d35-ab93-514ee691cf2d", "continue_at": 24},
        "AMORES_DA_MINHA_VIDA_corte2.mp3": {"clip_id": "ed0b2428-f58d-4351-a495-d785a723455a", "continue_at": 36},
        "CONTINUA_corte1.mp3": {"clip_id": "2132b8f8-48b5-4630-851f-ccd96f94b54f", "continue_at": 30},
        "CONTINUA_corte2.mp3": {"clip_id": "8a09b096-d55e-4352-ac83-46ea89e1300c", "continue_at": 32},
        "CUIDA_BEM_DELA_corte1.mp3": {"clip_id": "c6171c9d-b680-44f7-9e2c-dc88b0941668", "continue_at": 23},
        "CUIDA_BEM_DELA_corte2.mp3": {"clip_id": "c2d1aefc-0920-4c5b-acb5-ff9e50938973", "continue_at": 23},
        "ESCONDIDINHO_corte1.mp3": {"clip_id": "104e514c-1bc6-474a-a523-970f8a21f98b", "continue_at": 21},
        "ESCONDIDINHO_corte2.mp3": {"clip_id": "b3b87462-5fd8-4d71-b24c-171e43f00761", "continue_at": 23},
        "MEDO_BOBO_corte1.mp3": {"clip_id": "437688ac-977e-49c8-8616-9658ec103a3b", "continue_at": 42},
        "MORANGO_CHOCOLATE_corte1.mp3": {"clip_id": "c326db99-8f4b-42fd-93ba-3a771d15f14e", "continue_at": 33},
        "QUAL_A_GRACA_corte1.mp3": {"clip_id": "9ab462e2-015c-48d5-b856-47c2729148dc", "continue_at": 22},
        "VAI_LA_corte1.mp3": {"clip_id": "bd78cdfd-6d47-457a-8659-829558b2b480", "continue_at": 18},
        "VAI_LA_corte2.mp3": {"clip_id": "391fbbea-35d7-432a-a7d3-a76b971803dd", "continue_at": 17}
    }

    if song_cut:
        try:
            continue_clip_id = song_cuts[song_cut]["clip_id"]
            continue_at = song_cuts[song_cut]["continue_at"]
        except:
            logger.info(f"can't find song cut '{song_cut}'")
            #song_cut = None
            #return

    task_id = '19cc9ebd-f1a2-4346-8211-c86a17697a1a'
    title = "Sagatiba"
    lyrics1 = """
[Intro]
E aí, galera. Bora seguir na saga? 
Essa música é pra quem faz acontecer. 
Pra quem é da equipe. 
E sabe seguir na saga. 

[Verse1]
Então bora? 
Bora levar Sagatiba pra cada esquina. 
Pra cada mesa de bar. 
Pra cada conversa gostosa. 

[Chorus]
Pra quem tá na rua. 
Pra quem tá na loja. 
Os donos do show. 
Pra quem tá na rua. 
Pra quem tá na loja. 
Os donos do show. 

[Verse2]
Essa música é pra quem faz sucesso. 
Pra quem faz Sagatiba brilhar. 
Pra quem tem Sagatiba no coração. 
E coloca Sagatiba no copo. 

[Chorus]
Pra quem tá na rua. 
Pra quem tá na loja. 
Os donos do show.
Pra quem tá na rua. 
Pra quem tá na loja. 
Os donos do show. 
"""

    lyrics2 = """
(Verso 1)  
É sexta-feira, chegou o dia,  
José na roda, que alegria!  
Cachaça Sagatiba na mão,  
Vamos brindar, é pura diversão!

(Refrão)  
Sextou, sextou, a festa começou,  
Cento e cinquenta, é o que gastou,  
Rindo e dançando, o povo animado,  
Com José do lado, tudo é celebrado!

(Verso 2)  
Balde de gelo e a mesa cheia,  
Quem não se alegra, não está na ideia,  
Pitadas de limão, o brinde certo,  
Com essa galera, só risada, só afeto!

(Refrão)  
Sextou, sextou, a festa começou,  
Cento e cinquenta, é o que gastou,  
Rindo e dançando, o povo animado,  
Com José do lado, tudo é celebrado!

(Ponte)  
A noite é longa, a música toca,  
Sagatiba aumenta a nossa loucura,  
Os corpos se mexem, a energia é boa,  
Em cada gole, a amizade flutua!

(Refrão)  
Sextou, sextou, a festa começou,  
Cento e cinquenta, é o que gastou,  
Rindo e dançando, o povo animado,  
Com José do lado, tudo é celebrado!

(Outro)  
E quando o sol raiar, a gente vai lembrar,  
Dessas risadas que não vão acabar,  
Sexta-feira, nossa tradição,  
Um brinde a José, ao amor e à união!  
Sextou, sextou, é pura diversão!
    """

    lyrics3 = """
(Verso 1)  
É domingo, o sol raiou,  
José chegou, a festa começou.  
Um sorriso no rosto, e um copo na mão,  
Cachaça Sagatiba é a nossa canção.  

(Refrão)  
Vem pra cá, vem dançar,  
Com Maiara e Maraísa, vamos contagiar!  
Churrasco na brasa, amizade a brilhar,  
Cachaça na veia, deixa a gente sonhar.  

(Verso 2)  
As carnes na grelha, o cheiro no ar,  
Mas a verdadeira festa é saber brindar.  
E entre uma risada e outra, vamos aproveitar,  
A vida é curta pra não celebrar!  

(Refrão)  
Vem pra cá, vem dançar,  
Com Maiara e Maraísa, vamos contagiar!  
Churrasco na brasa, amizade a brilhar,  
Cachaça na veia, deixa a gente sonhar.  

(Ponte)  
Tô levando a vida no embalo da canção,  
Com os amigos ao lado, é pura diversão.  
A cada gole, um sonho a mais,  
É domingo, e a festa nunca é demais!  

(Refrão)  
Vem pra cá, vem dançar,  
Com Maiara e Maraísa, vamos contagiar!  
Churrasco na brasa, amizade a brilhar,  
Cachaça na veia, deixa a gente sonhar.  

(Final)  
E quando a noite chegar, não vamos parar,  
A saga do domingo vai continuar.  
Com José e a galera, todos a cantar,  
Cachaça e risadas, vamos eternizar!  

(Encerramento)  
Então levanta o copo, faz esse brinde soar,  
Porque aqui é alegria, jamais vai faltar!  
Com Maiara e Maraísa, vamos festejar,  
Domingo de cachaça, não podemos parar!      
    """

    lyrics_list = [lyrics1, lyrics2, lyrics3]

    if my_lyrics:
        lyrics = my_lyrics
    else:
        lyrics = lyrics_list[lyric_id]

    logger.info("Creating Music")
    task_id = musicapi.create_music1(lyrics)
    #task_id = musicapi.create_music3(lyrics, continue_clip_id, continue_at)
    logger.info(f"Music created with task_id: {task_id}")
    for t in range(200):
        print(f"Waiting... [{t}]")
        for i in range(10):
            print(f"{i} ", end='')
            time.sleep(1)
        print("")
        try:
            audio_urls = musicapi.get_music(task_id, return_both_urls=True)
            if audio_urls:
                logger.info(f"{song_cut}:{continue_at} | {global_model} | '{global_tags}'")
                logger.info(audio_urls)
                prefix = song_cut.split('.')[0] if song_cut else None
                links_to_curl(audio_urls, prefix=prefix)

                for audio_url in audio_urls:
                    print(f"downloading: {audio_url}")
                    store_audio(audio_url, prefix=prefix)
                break
        except:
            pass

    #logger.info(f"download the music from: {audio_url}")


def upload_cuts():
    song_cuts = [
        'AMORES_DA_MINHA_VIDA_corte1.mp3',
        'AMORES_DA_MINHA_VIDA_corte2.mp3',
        'A_CULPA_E_NOSSA_corte1.mp3',
        'BENGALA_E_CROCHE_corte1.mp3',
        'BENGALA_E_CROCHE_corte2.mp3',
        'CONTINUA_corte1.mp3',
        'CONTINUA_corte2.mp3',
        'CUIDA_BEM_DELA_corte1.mp3',
        'CUIDA_BEM_DELA_corte2.mp3',
        'ESCONDIDINHO_corte1.mp3',
        'ESCONDIDINHO_corte2.mp3',
        'MEDO_BOBO_corte1.mp3',
        'MORANGO_CHOCOLATE_corte1.mp3',
        'NARCISISTA_corte1.mp3',
        'NARCISISTA_corte2.mp3',
        'NEM_TCHUM_corte1.mp3',
        'QUAL_A_GRACA_corte1.mp3',
        'TODO_MUNDO_MENOS_VOCE_corte1.mp3',
        'TODO_MUNDO_MENOS_VOCE_corte2.mp3',
        'VAI_LA_corte1.mp3',
        'VAI_LA_corte2.mp3',
    ]

    for song_cut in song_cuts:
        test_upload_song(f"trechos/{song_cut}")

    #AMORES_DA_MINHA_VIDA_corte1.mp3 clip_id: 266861a5-cac6-4ea8-b5e1-e16c15fc622c
    #AMORES_DA_MINHA_VIDA_corte2.mp3 clip_id: ed0b2428-f58d-4351-a495-d785a723455a
    #CONTINUA_corte1.mp3             clip_id: 2132b8f8-48b5-4630-851f-ccd96f94b54f
    #CONTINUA_corte2.mp3             clip_id: 8a09b096-d55e-4352-ac83-46ea89e1300c
    #CUIDA_BEM_DELA_corte1.mp3       clip_id: c6171c9d-b680-44f7-9e2c-dc88b0941668
    #CUIDA_BEM_DELA_corte2.mp3       clip_id: c2d1aefc-0920-4c5b-acb5-ff9e50938973
    #ESCONDIDINHO_corte1.mp3         clip_id: 104e514c-1bc6-474a-a523-970f8a21f98b
    #ESCONDIDINHO_corte2.mp3         clip_id: b3b87462-5fd8-4d71-b24c-171e43f00761
    #MEDO_BOBO_corte1.mp3            clip_id: 437688ac-977e-49c8-8616-9658ec103a3b
    #MORANGO_CHOCOLATE_corte1.mp3    clip_id: c326db99-8f4b-42fd-93ba-3a771d15f14e
    #QUAL_A_GRACA_corte1.mp3         clip_id: 9ab462e2-015c-48d5-b856-47c2729148dc
    #VAI_LA_corte1.mp3               clip_id: bd78cdfd-6d47-457a-8659-829558b2b480
    #VAI_LA_corte2.mp3               clip_id: 391fbbea-35d7-432a-a7d3-a76b971803dd


def test_moderation(destination, message):
    return print(moderation_ok(destination, message))


def test_generate_lyrics(destination, invite_options, weekdays, message):
    is_ok, error_msg = moderation_ok(destination, message)

    if is_ok:
        lyrics = generate_lyrics(destination, invite_options, weekdays, message)
        logger.info(f"Letras geradas: {lyrics}")
        return lyrics
    else:
        logger.warning(f"Texto bloqueado por violar as regras de moderação: {error_msg}")
        return None


def test_lyrics_generation():
    destination = "José"
    invite_options = "beber em casa"
    weekdays = "Domingo"
    message = "amarelo"

    lyrics = test_generate_lyrics(destination, invite_options, weekdays, message)
    logger.warning(lyrics)
    return lyrics


def test_music_generation(song_cut=None, tags=None, lyrics=None):
    if not song_cut:
        song_cut = "02_MARAISA_MORANGO_COM_CHOCOLATE.mp3"
    if not tags:
        tags = "sertanejo, female, back vocals, 30 seconds long"

    if not lyrics:
        lyrics = """
        **Introdução:**  
        No domingo de sol, a festa começou,  
        Chamei José pra beber, e a alegria chegou.  
        Com a Sagatiba na mesa, não tem tempo ruim,  
        A torcida é animada, vamos juntos até o fim!

        **Verso:**  
        A bola rola solta, e a barraca tá montada,  
        Nas risadas e dribles, a galera já é pesada.  
        Cachaça na cuca, e na grama a gente briga,  
        Entre um gol e outro, a amizade é a liga!

        **Refrão:**  
        Bebe cachaça, José, cachaça sem parar,  
        A gente joga futebol, até o dia clarear.  
        Vai ser drible e festa, até o sol raiar,  
        Domingo em casa é pura diversão, vem pra cá!
            """

    print(f"tags: {tags}")
    ###lyrics = test_lyrics_generation()
    if lyrics:
        test_create_song(song_cut=song_cut, my_lyrics=lyrics, model="sonic-v4", tags=tags)


def test_send_whatsapp_message():
    message = "Hola, que tal? Vamos beber una cerveza?"
    destination_number = "whatsapp:+5511984283885" # Dudu
    #destination_number = "whatsapp:+5511915956535" # Kiko
    send_whatsapp_message(message, destination_number)


def test_manual_get_music(task_id):
    audio_urls = musicapi.get_music2(task_id)
    if audio_urls:
        logger.info(audio_urls)
        links_to_curl(audio_urls)

        for audio_url in audio_urls:
            print(f"downloading: {audio_url}")
            store_audio(audio_url)
    else:
        logger.info("No music found")


def test_manual_music_generation(lyrics):
    logger.info("test manual music generation")
    task_id = musicapi.create_music4(lyrics)

    logger.info("waiting for links...")
    test_manual_get_music(task_id)


def test_fade_out():
    input_mp3 = "static/mp3/sagatiba_5f9556aa-7a4a-497a-9a18-af3eb903b6ff.mp3"
    output_mp3 = "static/mp3/sagatiba_fade_out.mp3"
    audio_util.fade_out(input_mp3, output_mp3)


if __name__ == "__main__":
    lyrics2 = """
    **Introdução:**  
    No domingo de sol, a festa começou,  
    Chamei José pra beber, e a alegria chegou.  
    Com a Sagatiba na mesa, não tem tempo ruim,  
    A torcida é animada, vamos juntos até o fim!

    **Verso:**  
    A bola rola solta, e a barraca tá montada,  
    Nas risadas e dribles, a galera já é pesada.  
    Cachaça na cuca, e na grama a gente briga,  
    Entre um gol e outro, a amizade é a liga!

    **Refrão:**  
    Bebe cachaça, José, cachaça sem parar,  
    A gente joga futebol, até o dia clarear.  
    Vai ser drible e festa, até o sol raiar,  
    Domingo em casa é pura diversão, vem pra cá!
        """
    lyrics = """
    [Intro]
    E aí, galera. Bora seguir na saga? 
    Essa música é pra quem faz acontecer. 
    Pra quem é da equipe. 
    E sabe seguir na saga. 

    [Verse1]
    Então bora? 
    Bora levar Sagatiba pra cada esquina. 
    Pra cada mesa de bar. 
    Pra cada conversa gostosa. 

    [Chorus]
    Pra quem tá na rua. 
    Pra quem tá na loja. 
    Os donos do show. 
    Pra quem tá na rua. 
    Pra quem tá na loja. 
    Os donos do show. 

    [Verse2]
    Essa música é pra quem faz sucesso. 
    Pra quem faz Sagatiba brilhar. 
    Pra quem tem Sagatiba no coração. 
    E coloca Sagatiba no copo. 

    [Chorus]
    Pra quem tá na rua. 
    Pra quem tá na loja. 
    Os donos do show.
    Pra quem tá na rua. 
    Pra quem tá na loja. 
    Os donos do show. 
    """

    #test_fade_out()
    #test_create_song(lyric_id=1)

    #test_manual_get_music("967b4f04-b52e-41a2-b458-f5e9435adc8f")

    #test_manual_music_generation(lyrics2)
    #test_music_generation(song_cut="vai_la_02.mp3")#, tags="female voices only, sertanejo, back vocals, 30 seconds long")
    #test_music_generation(song_cut="grave_01.mp3", lyrics=lyrics, tags="sertanejo, country, back vocals, strong female voice, joyfully, uplifting")
    #test_upload_song("trechos/vai_la_02.mp3")
    #test_upload_song()# "trechos/02_MARAISA_MORANGO_COM_CHOCOLATE.mp3")
    #test_send_whatsapp_message()
    #test_lyrics_generation()
    #test_moderation(destination="pedro", message="guarda sol amarelo")
    #musicapi.create_persona()
    #musicapi.create_music2(lyrics)
    #musicapi.get_music("9b152bb8-7cee-4257-9763-f17fe837f982", True)
    #upload_cuts()
    #test_upload_song()

    #test_create_song(song_cut="02_MARAISA_MORANGO_COM_CHOCOLATE.mp3", lyric_id=2, model="sonic-v4",
    #                 tags="sertanejo, female, back vocals, 30 seconds long")
    # test_create_song(song_cut="AMORES_DA_MINHA_VIDA_corte1.mp3", lyric_id=2, model="sonic-v3-5", tags="sertanejo, country, female, back vocals, 1 minute length")
