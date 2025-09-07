import threading
import time
import subprocess
import logging
import os
from elevenlabs import ElevenLabs
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# Initialize ElevenLabs client
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def toggle_mic(driver, unmute=True):
    """Unmute or mute mic (idempotent)."""
    try:
        mic_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(@aria-label, 'microphone')]"
            ))
        )

        is_muted = mic_button.get_attribute("data-is-muted") == "true"

        if unmute and is_muted:
            mic_button.click()
            logger.info("🎙️ Mic unmuted")
        elif not unmute and not is_muted:
            mic_button.click()
            logger.info("🔇 Mic muted")
        else:
            logger.info("ℹ️ Mic already in desired state")

        return True
    except Exception as e:
        logger.error(f"❌ Could not toggle mic: {e}")
        return False


def speak_in_meeting(driver, text: str, delay_seconds: int = 10, sink_name="meet_sink"):
    """
    After `delay_seconds`, unmute mic, generate TTS with ElevenLabs, inject into sink, then mute after playback.
    """
    def task():
        try:
            # 1. Unmute microphone
            toggle_mic(driver, unmute=True)

            # 2. Generate TTS audio using ElevenLabs
            tts_file = "temp_speech.wav"
            audio = client.text_to_speech.convert(
                voice_id="Rachel",   # <-- change voice if you want
                model_id="eleven_multilingual_v2",
                output_format="wav",
                text=text
            )
            with open(tts_file, "wb") as f:
                f.write(audio)
            logger.info(f"🗣️ Generated TTS with ElevenLabs: {text}")

            # 3. Inject into virtual sink and WAIT until finished
            subprocess.run(["paplay", "--device=" + sink_name, tts_file], check=True)
            logger.info("🔊 Finished audio injection")

            # 4. Mute mic AFTER playback fully done
            toggle_mic(driver, unmute=False)

        except Exception as e:
            logger.error(f"❌ Failed to speak in meeting: {e}")

    # Run in background after delay
    threading.Timer(delay_seconds, task).start()
