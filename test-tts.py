import pyttsx3

def text_to_speech(text, voice_id=None, rate=150, volume=1.0):
    # Initialize the TTS engine
    engine = pyttsx3.init()

    # Set voice if provided (male/female depending on your system voices)
    if voice_id is not None:
        voices = engine.getProperty("voices")
        if 0 <= voice_id < len(voices):
            engine.setProperty("voice", voices[voice_id].id)

    # Set speaking rate
    engine.setProperty("rate", rate)

    # Set volume (0.0 to 1.0)
    engine.setProperty("volume", volume)

    # Speak the text
    engine.say(text)
    engine.runAndWait()

if __name__ == "__main__":
    sample_text = "Hello! This is a text to speech demo using Python."
    text_to_speech(sample_text, voice_id=0)  # Try 0 or 1 for different voices
