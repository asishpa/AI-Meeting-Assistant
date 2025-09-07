import threading
import pyttsx3
import time
import subprocess
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

def setup_virtual_sink(sink_name="meet_sink"):
    """
    Ensure virtual sink exists and set its monitor as the default mic.
    """
    try:
        # Check if sink exists
        sinks = subprocess.check_output(["pactl", "list", "short", "sinks"]).decode()
        if sink_name not in sinks:
            subprocess.call([
                "pactl", "load-module", "module-null-sink",
                f"sink_name={sink_name}"
            ])
            logger.info(f"✅ Created virtual sink: {sink_name}")
        else:
            logger.info(f"ℹ️ Virtual sink {sink_name} already exists")

        # Set monitor as default source (mic)
        subprocess.call([
            "pactl", "set-default-source", f"{sink_name}.monitor"
        ])
        logger.info(f"🎙️ Set default mic to {sink_name}.monitor")

    except Exception as e:
        logger.error(f"❌ Failed to set up virtual sink: {e}")


def speak_in_meeting(driver, text: str, delay_seconds: int = 10, sink_name="meet_sink"):
    """
    After `delay_seconds`, unmute the mic, generate TTS, inject into sink, mute again.
    """
    def task():
        try:
            # 0. Make sure sink is ready
            setup_virtual_sink(sink_name)

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
                logger.info("🔇 Mic muted again")

        except Exception as e:
            logger.error(f"❌ Failed to speak in meeting: {e}")

    # Run in background after delay
    threading.Timer(delay_seconds, task).start()
