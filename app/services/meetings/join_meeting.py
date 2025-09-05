import os
import time
import logging
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.schemas.meet import MeetRequest
import threading
import json


logger = logging.getLogger(__name__)

def setup_chrome():
    """
    Setup Chrome with media permissions.
    """
    profile_dir = os.path.join(os.getcwd(), "chrome_profile")
    os.makedirs(profile_dir, exist_ok=True)
    
    chrome_options = Options()
    chrome_options.add_argument(f'--user-data-dir={profile_dir}')
    chrome_options.add_argument('--profile-directory=Default')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications": 1
    })
    chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
    # chrome_options.add_argument('--headless=new')  # Uncomment for headless mode
    
    # Stability options
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)


def start_ffmpeg(output_file="meeting_audio.wav"):
    """Record audio from PulseAudio virtual sink"""
    return subprocess.Popen([
        "ffmpeg",
        "-y",                       # overwrite
        "-f", "pulse",
        "-i", "meet_sink.monitor",  # PulseAudio monitor
        "-ac", "1",
        "-ar", "16000",
        output_file
    ])


def move_chrome_to_sink(sink_name="meet_sink", retries=15, delay=2):
    """
    Keep retrying to find Chrome/Chromium/Meet audio stream and move it to the virtual sink.
    """
    try:
        for attempt in range(retries):
            inputs = subprocess.check_output(["pactl", "list", "sink-inputs"]).decode()
            current_index = None
            found = False

            for line in inputs.splitlines():
                line = line.strip()
                if line.startswith("Sink Input #"):
                    current_index = line.split("#")[1]
                # Match Chrome, Chromium, or WebRTC audio
                if (
                    "application.name = \"Google Chrome\"" in line
                    or "application.name = \"Chromium\"" in line
                    or "application.process.binary = \"chrome\"" in line
                    or "media.name = \"WebRTC Voice\"" in line
                ):
                    if current_index:
                        subprocess.call(["pactl", "move-sink-input", current_index, sink_name])
                        logger.info(f"✅ Moved Chrome/Meet stream {current_index} to {sink_name}")
                        found = True
                        break

            if found:
                return True

            logger.info(f"⏳ No Chrome/Chromium sink-input found yet (attempt {attempt+1}/{retries}), retrying...")
            time.sleep(delay)

        logger.warning("⚠️ Gave up: no Chrome/Meet sink-input appeared")
        return False

    except Exception as e:
        logger.error(f"❌ Failed to move Chrome stream: {e}")
        return False
    
def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS string."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"

def scrape_captions_json_continuous(driver, output_file="captions.json", stop_event=None, interval=0.5, meeting_start_time=None):
    """
    Continuous caption scraper:
    - Writes captions immediately on every poll (no stabilization delay).
    - Each new chunk gets a fresh timestamp.
    """
    captions = []
    next_id = 1

    if meeting_start_time is None:
        meeting_start_time = time.time()

    while not (stop_event and stop_event.is_set()):
        try:
            container = driver.find_element(By.XPATH, "//div[@role='region' and @aria-label='Captions']")
            blocks = container.find_elements(By.XPATH, ".//div[contains(@class,'nMcdL')]")
            current_time = time.time()

            for block in blocks:
                try:
                    speaker = block.find_element(By.CSS_SELECTOR, ".NWpY1d").text.strip()
                except:
                    speaker = ""
                if not speaker:
                    continue

                try:
                    text = block.find_element(By.CSS_SELECTOR, ".VbkSUe").text.strip()
                except:
                    text = ""
                if not text:
                    continue

                elapsed_time = current_time - meeting_start_time

                # If same speaker continues, merge text
                if captions and captions[-1]["speaker"] == speaker:
                    if text not in captions[-1]["text"]:
                        captions[-1]["text"] += " " + text
                        captions[-1]["timestamp_end"] = format_timestamp(elapsed_time)
                else:
                    captions.append({
                        "id": next_id,
                        "speaker": speaker,
                        "text": text,
                        "timestamp_start": format_timestamp(elapsed_time),
                        "timestamp_end": format_timestamp(elapsed_time)
                    })
                    next_id += 1

            # Save continuously
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(captions, f, indent=2)

        except Exception:
            pass

        time.sleep(interval)




def join_and_record_meeting(
    request: MeetRequest,
    record_seconds: int = 60,
    output_file: str = "meeting_audio.wav",
    captions_file: str = "captions.json"
):
    """
    Join Google Meet as guest, disable mic/cam, record audio and captions.
    """
    record_seconds = int(record_seconds)
    logger.info(f"Launching Chrome to join meeting: {request.meet_url}")

    driver = setup_chrome()
    ffmpeg_proc = None
    caption_thread = None
    stop_scraping = threading.Event()

    try:
        driver.get(request.meet_url)
        time.sleep(5)

        # Disable mic
        try:
            mic_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button'][@aria-label[contains(., 'microphone')]]"))
            )
            if mic_button.get_attribute("aria_pressed") != "true":
                mic_button.click()
                logger.info("🎙️ Mic disabled")
        except Exception:
            logger.warning("⚠️ Could not find mic button")

        # Disable cam
        try:
            cam_button = driver.find_element(By.XPATH, "//div[@role='button'][@aria-label[contains(., 'camera')]]")
            if cam_button.get_attribute("aria_pressed") != "true":
                cam_button.click()
                logger.info("📷 Camera disabled")
        except Exception:
            logger.warning("⚠️ Could not find camera button")

        # Enter name
        try:
            name_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Your name']"))
            )
            guest_name = getattr(request, 'guest_name', 'Meeting Bot')
            name_input.clear()
            name_input.send_keys(guest_name)
            logger.info(f"✅ Entered name: {guest_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not enter name: {e}")

        # Click Ask to Join / Join now
        try:
            ask_to_join_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Ask to join']/ancestor::button"))
            )
            ask_to_join_button.click()
            logger.info("✅ Clicked Ask to join")
        except Exception:
            try:
                join_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Join now']/ancestor::button"))
                )
                join_button.click()
                logger.info("✅ Clicked Join now (fallback)")
            except Exception:
                logger.warning("⚠️ Could not find join button")

        # Wait until inside meeting
        try:
            WebDriverWait(driver, 30).until(
                lambda driver: (
                    driver.find_elements(By.XPATH, "//button[@aria-label='Leave call']") or
                    driver.find_elements(By.XPATH, "//*[contains(text(), 'Waiting for') or contains(text(), 'asking to join')]")
                )
            )
            if driver.find_elements(By.XPATH, "//button[@aria-label='Leave call']"):
                logger.info("✅ Successfully joined the meeting")
            else:
                logger.info("⏳ Waiting for host approval")
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Leave call']"))
                )
                logger.info("✅ Host approved - now in meeting")
        except Exception as e:
            logger.error(f"❌ Failed to join meeting: {e}")
            raise

        # Turn on captions
        try:
            captions_button = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'captions')]"))
            )
            if "Turn on captions" in captions_button.get_attribute("aria-label"):
                captions_button.click()
                logger.info("💬 Captions turned ON")
            else:
                logger.info("💬 Captions already ON")
        except Exception:
            logger.warning("⚠️ Could not enable captions")

        # Move Chrome audio to virtual sink
        move_chrome_to_sink("meet_sink")

        start_time = time.time() 
        # Start captions scraping thread
        caption_thread = threading.Thread(
            target=scrape_captions_json,
            args=(driver, captions_file, stop_scraping, 1.5, 1.5, start_time),
            daemon=True
        )
        caption_thread.start()
        logger.info("📝 Started captions scraping")

        # Start FFmpeg
        ffmpeg_proc = start_ffmpeg(output_file)
        logger.info(f"🎤 Recording meeting audio for {record_seconds} seconds...")

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time

            # Meeting ended?
            try:
                leave_button = driver.find_element(By.XPATH, "//button[@aria-label='Leave call']")
                if not leave_button.is_displayed():
                    logger.info("📴 Leave call button disappeared — meeting ended")
                    break
            except:
                logger.info("📴 Leave call button not found — meeting likely ended")
                break

            # Timeout
            if elapsed > record_seconds:
                logger.info("⏳ Max recording time reached — stopping")
                break

            time.sleep(2)

    finally:
        stop_scraping.set()
        if caption_thread:
            caption_thread.join(timeout=5)
        driver.quit()
        logger.info("🔚 Browser closed")

        if ffmpeg_proc:
            try:
                ffmpeg_proc.terminate()
                ffmpeg_proc.wait()
                logger.info(f"🔊 Meeting audio saved to: {output_file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to stop FFmpeg: {e}")

    return output_file, captions_file
