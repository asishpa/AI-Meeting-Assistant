
# app/services/meetings/live_tts.py
import time
from typing import Generator

def tts_generator() -> Generator[bytes, None, None]:
    """
    Example generator that yields audio chunks for live injection.
    Replace `generate_next_chunk()` with your TTS engine.
    """
    import pyttsx3  # optional: offline TTS engine
    import io
    import wave

    engine = pyttsx3.init()
    text_chunks = [
        "Hello everyone, this is the bot speaking.",
        "We will start our discussion shortly.",
        "Feel free to ask questions after the presentation."
    ]

    for text in text_chunks:
        # Generate WAV in memory
        wav_buffer = io.BytesIO()
        engine.save_to_file(text, "temp.wav")
        engine.runAndWait()
        with open("temp.wav", "rb") as f:
            chunk_data = f.read()
        yield chunk_data

        # Optional pause between chunks
        time.sleep(1)
