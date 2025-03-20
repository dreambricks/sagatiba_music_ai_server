from pydub import AudioSegment
import subprocess
import os
import logging

# Configuração do logger
logger = logging.getLogger(__name__)

def fade_out(input_file: str, output_file: str, fade_duration: int = 5000):
    """
    Apply a fade-out effect to the last few seconds of an MP3 file.

    :param input_file: Path to the input MP3 file.
    :param output_file: Path to save the modified MP3 file.
    :param fade_duration: Duration of fade-out in milliseconds (default: 5000ms = 5s).
    """
    # Load the audio file
    audio = AudioSegment.from_mp3(input_file)

    # Apply fade-out at the end
    faded_audio = audio.fade_out(fade_duration)

    # Export the modified audio
    faded_audio.export(output_file, format="mp3")

def apply_watermark_and_metadata(input_audio_path, watermark_path):
    """
    Aplica marca d'água e metadados em um arquivo de áudio usando ffmpeg.
    Retorna o caminho do novo arquivo processado.
    """
    try:
        logger.info(f"[WATERMARK] Iniciando aplicação em {input_audio_path}")

        # Define o novo nome do arquivo
        base, ext = os.path.splitext(input_audio_path)
        output_audio_path = f"{base}_seguenasaga.mp3"

        # Verifica se o arquivo de watermark existe
        if not os.path.exists(watermark_path):
            logger.error(f"[WATERMARK] Arquivo de watermark não encontrado: {watermark_path}")
            raise FileNotFoundError(f"Watermark não encontrada: {watermark_path}")

        # Obter duração do áudio
        cmd_duration = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", input_audio_path
        ]
        duration_output = subprocess.check_output(cmd_duration).decode().strip()
        duration_seconds = float(duration_output)
        fade_duration = 2
        fade_out_start = duration_seconds - fade_duration

        # Comando FFmpeg
        cmd = [
            "ffmpeg", "-i", input_audio_path, "-i", watermark_path,
            "-filter_complex",
            f"[0:a]lowpass=f=7000[audio_clean];"
            f"[1:a]aloop=loop=-1:size=2e+09[a1];"
            f"[audio_clean][a1]amix=inputs=2:duration=first:weights=1 0.05[aout];"
            f"[aout]afade=t=in:ss=0:d={fade_duration},afade=t=out:st={fade_out_start}:d={fade_duration}",
            "-metadata", "title=Segue na Saga",
            "-metadata", "copyright=© 2025 Sagatiba",
            "-metadata", "license=CC BY-NC-ND - Compartilhe, mas não modifique e não use comercialmente. https://creativecommons.org/licenses/by-nc-nd/4.0/",
            "-metadata", "comment=Compartilhe livremente, mas uso comercial é proibido. Saiba mais em: https://seguenasaga.sagatiba.com",
            "-metadata", "encoded_by=https://seguenasaga.sagatiba.com",
            "-metadata", "copyright_flag=1",
            "-b:a", "192k", "-ar", "48000", "-y", output_audio_path
        ]

        subprocess.run(cmd, check=True)
        logger.info(f"[WATERMARK] Marca d'água aplicada: {output_audio_path}")
        return output_audio_path

    except subprocess.CalledProcessError as e:
        logger.error(f"[WATERMARK] Erro FFmpeg: {e.stderr}")
        raise RuntimeError("Erro ao aplicar marca d'água.") from e
    except Exception as e:
        logger.error(f"[WATERMARK] Erro: {str(e)}")
        raise