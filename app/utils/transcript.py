import assemblyai as aai
import os
import logging
import json

logger = logging.getLogger(__name__)

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

def transcribe_file_json(audio_file: str, transcript_file: str) -> dict:
    """
    Transcribe an audio file using AssemblyAI SDK with speaker labels.
    Saves the transcript in JSON format to transcript_file.
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

        # Build structured JSON transcript preserving word order
        json_transcript = []
        for word in transcript.words:
            json_transcript.append({
                "start_time": word.start,
                "end_time": word.end,
                "text": word.text,
                "speaker": word.speaker
            })

        # Save JSON to file
        with open(transcript_file, "w") as f:
            json.dump(json_transcript, f, indent=2)

        logger.info(f"✅ JSON transcript saved to: {transcript_file}")
        return json_transcript

    except Exception as e:
        logger.error(f"❌ Failed to transcribe audio: {e}")
        return {}
