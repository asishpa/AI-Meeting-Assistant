import threading
import pyttsx3
import time
import subprocess
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from pydub import AudioSegment

logger = logging.getLogger(__name__)

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
    After `delay_seconds`, unmute mic, generate TTS as WAV, inject into sink, then mute after playback ends.
    """
    def task():
        try:
            # 1. Unmute microphone
            toggle_mic(driver, unmute=True)

            # 2. Generate TTS audio as WAV
            tts_wav = "temp_speech.wav"
            engine = pyttsx3.init()
            engine.save_to_file(text, tts_wav)
            engine.runAndWait()
            logger.info(f"🗣️ Generated TTS WAV: {text}")

            # 3. Play WAV directly into virtual sink
            subprocess.run(["paplay", "--device=" + sink_name, tts_wav], check=True)
            logger.info("🔊 Finished audio injection")

            # 4. Mute mic after playback
            toggle_mic(driver, unmute=False)

        except Exception as e:
            logger.error(f"❌ Failed to speak in meeting: {e}")

    threading.Timer(delay_seconds, task).start()


