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
            logger.info("Mic unmuted")
        elif not unmute and not is_muted:
            mic_button.click()
            logger.info("Mic muted")
        else:
            logger.info("Mic already in desired state")

        return True
    except Exception as e:
        logger.error(f"Could not toggle mic: {e}")
        return False


def speak_in_meeting(driver, text: str, delay_seconds: int = 10, sink_name="meet_sink"):
    """
    After `delay_seconds`, unmute mic, generate TTS as WAV (48kHz mono),
    inject into sink, then mute after playback ends.
    """
    def task():
        try:
            # 1. Unmute microphone
            toggle_mic(driver, unmute=True)

            # 2. Generate raw TTS WAV (default pyttsx3 output, e.g. 22050 Hz)
            tts_wav = "temp_speech.wav"
            fixed_wav = "temp_speech_fixed.wav"

            engine = pyttsx3.init()
            engine.save_to_file(text, tts_wav)
            engine.runAndWait()
            logger.info(f"Generated TTS WAV at default rate: {tts_wav}")

            # 3. Resample to 48kHz mono for Google Meet
            audio = AudioSegment.from_wav(tts_wav)
            audio = audio.set_frame_rate(48000).set_channels(1)
            audio.export(fixed_wav, format="wav")
            logger.info(f"Resampled to 48kHz mono: {fixed_wav}")

            # 4. Play WAV directly into virtual sink
            subprocess.run(["paplay", "--device=" + sink_name, fixed_wav], check=True)
            logger.info("Finished audio injection")

            # 5. Mute mic after playback
            toggle_mic(driver, unmute=False)

        except Exception as e:
            logger.error(f"Failed to speak in meeting: {e}")

    threading.Timer(delay_seconds, task).start()
