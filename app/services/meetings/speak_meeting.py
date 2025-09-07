import threading
import pyttsx3
import time
import subprocess
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def speak_in_meeting(driver, text: str, delay_seconds: int = 10, sink_name="meet_sink"):
    """
    After `delay_seconds`, unmute the mic, generate TTS, inject into sink, mute again.
    """
    def task():
        try:
            # 1. Unmute microphone
            mic_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button'][@aria-label[contains(., 'microphone')]]"))
            )
            if mic_button.get_attribute("aria_pressed") == "false":  # muted
                mic_button.click()
                logger.info("🎙️ Mic unmuted")

            # 2. Generate TTS audio
            tts_file = "temp_speech.wav"
            engine = pyttsx3.init()
            engine.save_to_file(text, tts_file)
            engine.runAndWait()
            logger.info(f"🗣️ Generated TTS audio: {text}")

            # 3. Inject into virtual sink (so Meet hears it)
            subprocess.call(["paplay", "--device=" + sink_name, tts_file])
            logger.info("🔊 Audio injected into meeting")

            # 4. Mute again
            time.sleep(1)
            if mic_button.get_attribute("aria_pressed") == "true":
                mic_button.click()
                logger.info("🔇 M   ic muted again")

        except Exception as e:
            logger.error(f"❌ Failed to speak in meeting: {e}")

    # Run in background after delay
    threading.Timer(delay_seconds, task).start()
