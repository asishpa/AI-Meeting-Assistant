
import assemblyai as aai
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import json
from app.schemas.transcript import TranscriptUtterance
from app.core.errors import TranscriptionError
from deepgram import DeepgramClient

logger = logging.getLogger(__name__)


load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

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
def transcribe_file_json_deepgram(audio_file: str) -> List[TranscriptUtterance]:
    try:
        logger.info(f"Transcribing audio file with Deepgram v3: {audio_file}")
        
        if not DEEPGRAM_API_KEY:
            raise TranscriptionError("Deepgram API key is missing", status_code=500)

        # Initialize Deepgram v3 client
        dg_client = DeepgramClient(api_key=DEEPGRAM_API_KEY)

        with open(audio_file, "rb") as f:
            source = {"buffer": f.read(), "mimetype": "audio/wav"}
            
            options = {
                "punctuate": True,
                "diarize": True,
                "utterances": True,
                "detect_language": True,
                "model": "nova-2",  # Specify model for better results
                "smart_format": True,  # Enhanced formatting

            }
            response = dg_client.listen.prerecorded.v("1").transcribe_file(source, options)
            logger.error(f"Deepgram raw response: {response}")


        # Check if response has the expected structure
        if not hasattr(response, 'results') or not response.results:
            raise TranscriptionError("Invalid response from Deepgram", status_code=500)

        # Access utterances from the response
        if not hasattr(response.results, 'utterances') or not response.results.utterances:
            raise TranscriptionError("No utterances found in Deepgram response", status_code=500)

        dg_utterances = response.results.utterances

        # Convert to list of dicts for merge_utterances function
        utterance_dicts = []
        for utt in dg_utterances:
            utterance_dicts.append({
                "start": utt.start,
                "end": utt.end,
                "transcript": utt.transcript,
                "speaker": getattr(utt, 'speaker', 0)  # Some versions might not have speaker
            })

        # Merge consecutive utterances with same speaker
        utterances = merge_utterances(utterance_dicts)

        return utterances

    except TranscriptionError:
        raise
    except Exception as e:
        logger.error(f"Failed to transcribe with Deepgram v3: {e}")
        raise TranscriptionError(message=str(e), status_code=500)


def transcribe_file_json_aai(audio_file: str) -> List[TranscriptUtterance]:
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
    
def merge_utterances(utterances: List[dict]) -> List[TranscriptUtterance]:
    """
    Merge consecutive Deepgram utterances if the speaker is the same.
    """
    merged: List[TranscriptUtterance] = []

    for utt in utterances:
        start = int(utt["start"] * 1000)
        end = int(utt["end"] * 1000)
        speaker = f"spk_{utt.get('speaker', 0)}"
        text = utt["transcript"]

        if merged and merged[-1].speaker == speaker:
            # Extend the last utterance
            merged[-1].end_time = format_timestamp(end)
            merged[-1].text += " " + text.strip()
        else:
            # Start a new utterance
            merged.append(
                TranscriptUtterance(
                    start_time=format_timestamp(start),
                    end_time=format_timestamp(end),
                    text=text.strip(),
                    speaker=speaker,
                )
            )

    return merged
