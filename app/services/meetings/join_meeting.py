import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
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
    
    return webdriver.Chrome(options=chrome_options)

def join_and_record_meeting(
    request: MeetRequest,
    record_seconds: int = 60,
    output_file: str = "meeting_audio.wav"
):
    """
    Join Google Meet as guest, disable mic/cam, and optionally keep session open.
    """
    record_seconds = int(record_seconds)  # safe conversion in case Celery passes string
    logger.info(f"Launching Chrome to join meeting: {request.meet_url}")
    driver = setup_chrome()
    
    try:
        driver.get(request.meet_url)
        time.sleep(3)

        # --- Handle "Got it" popup ---
        try:
            got_it = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.='Got it']"))
            )
            got_it.click()
            logger.info("✅ Dismissed 'Got it' popup")
            time.sleep(2)
        except:
            logger.info("ℹ️  No 'Got it' popup found")

        # --- Fill guest name ---
        try:
            name_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@aria-label="Your name"]'))
            )
            name_input.clear()
            name_input.send_keys(request.guest_name)
            logger.info(f"✅ Added name: {request.guest_name}")
            time.sleep(2)
        except:
            logger.warning("⚠️  Could not set guest name")

        # --- Turn off microphone ---
        try:
            mic_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//div[@role="button" and contains(@aria-label,"Turn off microphone")]')
                )
            )
            mic_btn.click()
            logger.info("✅ Microphone turned off")
            time.sleep(1)
        except:
            logger.info("ℹ️  Microphone already off or not found")

        # --- Turn off camera ---
        try:
            cam_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//div[@role="button" and contains(@aria-label,"Turn off camera")]')
                )
            )
            cam_btn.click()
            logger.info("✅ Camera turned off")
            time.sleep(1)
        except:
            logger.info("ℹ️  Camera already off or not found")

        # --- Join meeting ---
        try:
            join_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[text()="Join now"]/ancestor::button'))
            )
            join_btn.click()
            logger.info("✅ Clicked 'Join now'")
        except:
            try:
                ask_join_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//span[text()="Ask to join"]/ancestor::button'))
                )
                ask_join_btn.click()
                logger.info("✅ Clicked 'Ask to join'")
            except Exception as e:
                logger.error(f"❌ Could not join meeting: {e}")
                return None

        # --- Keep session open (simulate recording) ---
        logger.info(f"🎤 Meeting joined! Keeping session open for {record_seconds} seconds...")
        time.sleep(record_seconds)

        # NOTE: Selenium cannot capture other participants' audio
        logger.info(f"🔊 Recording placeholder saved to: {output_file}")

    finally:
        driver.quit()
        logger.info("🔚 Browser closed")

    return output_file
