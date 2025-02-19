from pydub import AudioSegment


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