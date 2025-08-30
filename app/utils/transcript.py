import logging

logger = logging.getLogger(__name__)

def transcribe_file(audio_file: str, output_file: str) -> str:
    """
    Dummy transcription (replace with Whisper/OpenAI API later).
    """
    transcript = f"Transcription of {audio_file} ..."
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(transcript)

    logger.info(f"Transcript saved: {output_file}")
    return transcript
