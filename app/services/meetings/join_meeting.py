import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.schemas.meet import MeetRequest
import subprocess

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
    chrome_options.add_argument('--headless=new')

    
    return webdriver.Chrome(options=chrome_options)

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

    # --- Start FFmpeg recording BEFORE launching Chrome ---
    ffmpeg_proc = start_ffmpeg(output_file)

    driver = setup_chrome()
    
    try:
        driver.get(request.meet_url)
        time.sleep(3)

        # ... all your Selenium steps (popups, guest name, mic/cam off, join meeting) ...

        logger.info(f"🎤 Meeting joined! Keeping session open for {record_seconds} seconds...")
        time.sleep(record_seconds)

    finally:
        driver.quit()
        logger.info("🔚 Browser closed")
        
        # --- Stop FFmpeg recording ---
        ffmpeg_proc.terminate()
        ffmpeg_proc.wait()
        logger.info(f"🔊 Meeting audio saved to: {output_file}")

    return output_file
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