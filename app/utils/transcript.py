
import assemblyai as aai
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import json
from app.schemas.transcript import TranscriptUtterance
from app.core.errors import TranscriptionError


logger = logging.getLogger(__name__)


load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

def format_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS string."""
    seconds = ms // 1000
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"


def transcribe_file_json(audio_file: str) -> List[TranscriptUtterance]:
    """
    Transcribe an audio file using AssemblyAI SDK with speaker labels.
    Returns a list of TranscriptUtterance models with HH:MM:SS timestamps.
    Raises TranscriptionError on failure.
    """
    try:
        logger.info(f" Transcribing audio file: {audio_file}")

        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.universal,
            speaker_labels=True,
            language_detection=True
        )

        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_file)

        if transcript.status == "error":
            raise TranscriptionError(message=f"Transcription failed: {transcript.error}")

        # Build structured transcript using utterances and Pydantic schema
        utterances = [
            TranscriptUtterance(
                start_time=format_timestamp(utt.start),
                end_time=format_timestamp(utt.end),
                text=utt.text,
                speaker=utt.speaker
            )
            for utt in transcript.utterances
        ]

        return utterances

    except TranscriptionError:
        raise
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        raise TranscriptionError(message=str(e), status_code=500)
