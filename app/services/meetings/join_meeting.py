import os
import time
import logging
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service  # ADD THIS IMPORT
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.schemas.meet import MeetRequest

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
    chrome_options.add_argument('--alsa-output-device=meet_sink')
    chrome_options.add_argument('--autoplay-policy=no-user-gesture-required')
    # chrome_options.add_argument('--headless=new')  # Commented out for testing
    
    # Add these additional arguments for better stability
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')

    # Set up the service (this was missing!)
    service = Service("/usr/bin/chromedriver")
    
    # Return driver with service configuration
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

def join_and_record_meeting(
    request: MeetRequest,
    record_seconds: int = 60,
    output_file: str = "meeting_audio.wav"
):
    """
    Join Google Meet as guest, disable mic/cam, and record audio.
    """
    record_seconds = int(record_seconds)
    logger.info(f"Launching Chrome to join meeting: {request.meet_url}")

    driver = setup_chrome()
    ffmpeg_proc = None
    
    try:
        driver.get(request.meet_url)
        time.sleep(5)

        # --- Disable mic & camera if toggle buttons exist ---
        try:
            mic_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button'][@aria-label[contains(., 'microphone')]]"))
            )
            if mic_button.get_attribute("aria_pressed") != "true":
                mic_button.click()
                logger.info("🎙️ Mic disabled")
        except Exception:
            logger.warning("⚠️ Could not find mic button")

        try:
            cam_button = driver.find_element(By.XPATH, "//div[@role='button'][@aria-label[contains(., 'camera')]]")
            if cam_button.get_attribute("aria_pressed") != "true":
                cam_button.click()
                logger.info("📷 Camera disabled")
        except Exception:
            logger.warning("⚠️ Could not find camera button")

        # --- Enter name in the text field ---
        try:
            name_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Your name']"))
            )
            guest_name = getattr(request, 'guest_name', 'Meeting Bot')  # Use provided name or default
            name_input.clear()
            name_input.send_keys(guest_name)
            logger.info(f"✅ Entered name: {guest_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not enter name: {e}")

        # --- Click "Ask to join" button ---
        try:
            ask_to_join_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Ask to join']/ancestor::button"))
            )
            ask_to_join_button.click()
            logger.info("✅ Clicked Ask to join")
        except Exception as e:
            logger.warning(f"⚠️ Could not click 'Ask to join' button: {e}")
            # Fallback: try to find "Join now" button if "Ask to join" fails
            try:
                join_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Join now']/ancestor::button"))
                )
                join_button.click()
                logger.info("✅ Clicked Join now (fallback)")
            except Exception:
                logger.warning("⚠️ Could not find either 'Ask to join' or 'Join now' button")

        # --- Wait until inside meeting or for host approval ---
        try:
            # First wait for either successful join or waiting for approval
            WebDriverWait(driver, 30).until(
                lambda driver: (
                    driver.find_elements(By.XPATH, "//button[@aria-label='Leave call']") or  # Successfully joined
                    driver.find_elements(By.XPATH, "//*[contains(text(), 'Waiting for') or contains(text(), 'asking to join')]")  # Waiting for approval
                )
            )
            
            # Check if we're in the meeting or waiting
            if driver.find_elements(By.XPATH, "//button[@aria-label='Leave call']"):
                logger.info("✅ Successfully joined the meeting")
            else:
                logger.info("⏳ Waiting for host approval to join the meeting")
                # Wait a bit longer for host approval
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Leave call']"))
                )
                logger.info("✅ Host approved - now in the meeting")
                
        except Exception as e:
            logger.error(f"❌ Failed to join meeting: {e}")
            raise

        # --- Start FFmpeg only after joining ---
        ffmpeg_proc = start_ffmpeg(output_file)
        logger.info(f"🎤 Recording meeting audio for {record_seconds} seconds...")
        time.sleep(record_seconds)

    finally:
        driver.quit()
        logger.info("🔚 Browser closed")

        if ffmpeg_proc:
            try:
                ffmpeg_proc.terminate()
                ffmpeg_proc.wait()
                logger.info(f"🔊 Meeting audio saved to: {output_file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to stop FFmpeg: {e}")

    return output_file
