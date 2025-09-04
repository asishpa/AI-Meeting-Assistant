import assemblyai as aai
import os
import logging
from dotenv import load_dotenv
import json

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

def transcribe_file_json(audio_file: str, transcript_file: str) -> dict:
    """
    Transcribe an audio file using AssemblyAI SDK with speaker labels.
    Saves the transcript in JSON format with HH:MM:SS timestamps.
    """
    try:
        logger.info(f"📝 Transcribing audio file: {audio_file}")

        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.universal,
            speaker_labels=True,
            language_detection=True
        )

        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_file)

        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")

        # Build structured JSON transcript using utterances
        json_transcript = []
        for utt in transcript.utterances:
            json_transcript.append({
                "start_time": format_timestamp(utt.start),
                "end_time": format_timestamp(utt.end),
                "text": utt.text,
                "speaker": utt.speaker
            })

        # Save JSON to file
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(json_transcript, f, indent=2)

        logger.info(f"✅ JSON transcript saved to: {transcript_file}")
        return json_transcript

    except Exception as e:
        logger.error(f"❌ Failed to transcribe audio: {e}")
        return {}
