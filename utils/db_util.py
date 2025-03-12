import os
import logging
import requests
import datetime
from werkzeug.utils import secure_filename
import utils.audio_util as audio_util

# Configuração do logger
logger = logging.getLogger(__name__)

NO_ACCENT_PT = {
    '@': 'a', '$': 's', '&': 'e', '1': 'i', '0': 'o', '2': 'z', '5': 's', '3': 'e',
    '4': 'a', '6': 'b', '7': 't', '8': 'b', '9': 'g', 'á': 'a', 'ã': 'a', 'â': 'a',
    'à': 'a', 'é': 'e', 'ê': 'e', 'í': 'i', 'ó': 'o', 'õ': 'o', 'ô': 'o', 'ú': 'u',
    'ç': 'c', 'Á': 'A', 'Ã': 'A', 'Â': 'A', 'À': 'A', 'É': 'E', 'Ê': 'E', 'Í': 'I',
    'Ó': 'O', 'Õ': 'O', 'Ô': 'O', 'Ú': 'U', 'Ç': 'C'
}


# Diretório onde os arquivos de áudio serão armazenados
AUDIO_STORAGE_DIR = "static/mp3/"

def remove_accent(word):
    result = ""
    for i in range(len(word)):
        c = word[i]
        if c in NO_ACCENT_PT:
            result += NO_ACCENT_PT[c]
        else:
            result += c
    return result


def load_file_into_set(file_path):
    try:
        with open(file_path, 'r', encoding="utf8") as file:
            # Strip whitespace and return words as a set for faster lookup
            blacklist = {remove_accent(line.strip()) for line in file if line.strip()}
        return blacklist
    except FileNotFoundError:
        logger.error(f"Error: File not found at '{file_path}'")
        return set()


def add_suffix_to_filepath(filepath: str, suffix: str) -> str:
    """
    Adds a suffix at the end of a file path, before the extension.

    :param filepath: The original file path.
    :param suffix: String that will be added to the file name
    :return: The modified file path with the suffix added before the extension.
    """
    directory, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)
    new_filename = f"{name}{suffix}{ext}"
    return os.path.join(directory, new_filename)


def generate_filename_with_datetime(prefix: str, extension: str) -> str:
    """
    Generates a filename using the given prefix, the current date and time, and the specified extension.

    :param prefix: The prefix for the filename.
    :param extension: The file extension.
    :return: A formatted filename string.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension.strip('.')}"

def store_audio_file(file, id, max_size=1177*1024):
    """Salva o arquivo de áudio recebido no servidor e retorna o caminho do arquivo."""
    try:
        os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)  # Garante que o diretório existe

        # Garante que o nome do arquivo seja seguro
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[-1].lower()

        if ext != ".mp3":
            return None, "Invalid file format. Only MP3 files are allowed."

        # Verifica o tamanho do arquivo
        file.seek(0, os.SEEK_END)
        file_size = file.tell()  # Obtém o tamanho em bytes
        file.seek(0)  # Retorna ao início do arquivo

        if file_size > max_size:
            return None, f"File exceeds size limit of {max_size / 1024:.2f} KB."

        # Define um nome único para o arquivo
        count = 1
        while True:
            file_name = f"sagatiba_{id}_{count}.mp3"
            file_path = os.path.join(AUDIO_STORAGE_DIR, file_name)
            if not os.path.exists(file_path):  # Se o arquivo ainda não existe, usamos esse nome
                break
            count += 1  # Caso contrário, incrementa e tenta novamente

        # Salvar o arquivo no diretório
        file.save(file_path)
        logger.info(f"Audio file saved: {file_path} (Size: {file_size / 1024:.2f} KB)")

        # Aplica fade-out no áudio
        faded_file_path = add_suffix_to_filepath(file_path, "f")
        audio_util.fade_out(file_path, faded_file_path)

        return faded_file_path, None
    except Exception as e:
        logger.error(f"Error saving audio file: {e}")
        return None, "Erro ao processar arquivo de áudio."

def store_audio_url(url, id, max_size=1177*1024):
    """
    Baixa e armazena um arquivo de áudio, garantindo que múltiplos arquivos para o mesmo id não sejam sobrescritos.
    """
    try:
        os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)  # Garante que o diretório existe

        # Define um nome único incrementando `count`
        count = 1
        while True:
            file_name = f"sagatiba_{id}_{count}.mp3"
            file_path = os.path.join(AUDIO_STORAGE_DIR, file_name)
            if not os.path.exists(file_path):  # Se o arquivo ainda não existe, usamos esse nome
                break
            count += 1  # Caso contrário, incrementa e tenta novamente

        # Baixa o arquivo da URL
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download audio from {url} - HTTP {response.status_code}")
            return None, "Failed to download audio file."

        # Salva o arquivo baixado
        file_size = 0
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file_size += len(chunk)
                if chunk:
                    file.write(chunk)
                    if file_size >= max_size:
                        logger.warning(f"File size limit exceeded ({file_size}/{max_size} bytes). Stopping download.")
                        break  # Para o download se atingir o limite de tamanho
            file.flush()  # Garante que todos os dados sejam gravados no disco antes de continuar

        # Aplica fade-out no áudio imediatamente após o salvamento
        faded_file_path = add_suffix_to_filepath(file_path, "f")
        audio_util.fade_out(file_path, faded_file_path)


        logger.info(f"Audio file downloaded and processed: {faded_file_path} (Size: {file_size / 1024:.2f} KB)")
        return faded_file_path, None  # Retorna o caminho do arquivo salvo

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download audio file: {e}")
        return None, str(e)