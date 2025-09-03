import assemblyai as aai
import os
import logging

logger = logging.getLogger(__name__)
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

def transcribe_file(audio_file: str, transcript_file: str) -> str:
    """
    Transcribe an audio file using AssemblyAI SDK with speaker labels.
    Saves a readable transcript to transcript_file.
    """
    try:
        logger.info(f"📝 Transcribing audio file: {audio_file}")

        # Configure transcription with speaker diarization
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.universal,
            speaker_labels=True,        # Enable speaker diarization
            language_detection=True
        )

        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_file)

        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")

        # Build readable speaker-labeled transcript
        speaker_texts = {}
        for word in transcript.words:
            speaker = f"Speaker {word.speaker}"
            speaker_texts.setdefault(speaker, [])
            speaker_texts[speaker].append(word.text)

        formatted_transcript = ""
        for speaker, words in speaker_texts.items():
            formatted_transcript += f"{speaker}: {' '.join(words)}\n"

        # Save to file
        with open(transcript_file, "w") as f:
            f.write(formatted_transcript)

        logger.info(f"✅ Speaker-labeled transcript saved to: {transcript_file}")
        return formatted_transcript

    except Exception as e:
        logger.error(f"❌ Failed to transcribe audio: {e}")
        return ""
