# join_and_record_meeting.py
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
from app.schemas.meet import MeetRequest,MeetingMetadataDetails

import threading
from typing import Dict, List, Any
from datetime import datetime
from app.schemas.transcript import TranscriptUtterance
from .meet_bot import MeetBot  # <-- Import your MeetBot class

logger = logging.getLogger(__name__)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
def setup_chrome():
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
    # chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        js_file_path = os.path.join(PROJECT_ROOT, "js", "botOutputManager.js")
        if not os.path.exists(js_file_path):
            raise FileNotFoundError(f"botOutputManager.js not found at {js_file_path}")

        with open(js_file_path, "r", encoding="utf-8") as f:
            bot_manager_code = f.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": bot_manager_code})
        logger.info(" botOutputManager.js preloaded into Chrome (auto-inject every page).")
    except Exception as e:
        logger.error(f" Failed to inject botOutputManager.js: {e}")
    
    return driver

def start_ffmpeg(output_file="meeting_audio.wav"):
    return subprocess.Popen([
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", "meet_sink.monitor",
        "-ac", "1",
        "-ar", "16000",
        output_file
    ])

def move_chrome_to_sink(sink_name="meet_sink", retries=15, delay=2):
    for attempt in range(retries):
        inputs = subprocess.check_output(["pactl", "list", "sink-inputs"]).decode()
        current_index = None
        found = False
        for line in inputs.splitlines():
            line = line.strip()
            if line.startswith("Sink Input #"):
                current_index = line.split("#")[1]
            if ("application.name = \"Google Chrome\"" in line or
                "application.name = \"Chromium\"" in line or
                "application.process.binary = \"chrome\"" in line or
                "media.name = \"WebRTC Voice\"" in line):
                if current_index:
                    subprocess.call(["pactl", "move-sink-input", current_index, sink_name])
                    logger.info(f" Moved Chrome/Meet stream {current_index} to {sink_name}")
                    found = True
                    break
        if found:
            return True
        time.sleep(delay)
    logger.warning(" No Chrome/Meet sink-input appeared")
    return False

def format_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

def scrape_captions_json(
    driver,
    stop_event=None,
    interval=1.5,
    stable_time=1.5,
    start_time=None,
    shared_list=None,
    bot=None,
    mp3_file_path=None
):
    finalized_captions = [] if shared_list is None else shared_list
    active_captions = {}
    last_finalized_text = {}
    start_time = start_time or time.time()
    TRIGGER_PHRASE = "hello meeting assistant"

    while not (stop_event and stop_event.is_set()):
        try:
            container = driver.find_element(By.XPATH, "//div[@role='region' and @aria-label='Captions']")
            blocks = container.find_elements(By.XPATH, ".//div[contains(@class,'nMcdL')]")
            current_time = time.time()

            merged_blocks = []
            current_speaker, current_text = None, ""
            for block in blocks:
                try:
                    speaker = block.find_element(By.CSS_SELECTOR, ".NWpY1d").text.strip()
                    text = block.find_element(By.CSS_SELECTOR, ".VbkSUe").text.strip()
                except:
                    continue
                if not speaker or not text:
                    continue
                if speaker == current_speaker:
                    current_text += " " + text
                else:
                    if current_speaker:
                        merged_blocks.append({"speaker": current_speaker, "text": current_text.strip()})
                    current_speaker, current_text = speaker, text
            if current_speaker:
                merged_blocks.append({"speaker": current_speaker, "text": current_text.strip()})

            for merged_block in merged_blocks:
                speaker, text = merged_block["speaker"], merged_block["text"]
                if speaker not in active_captions:
                    active_captions[speaker] = {"text": text, "last_seen": current_time, "finalized": False}
                else:
                    # Caption changed -> speaker is still talking
                    if active_captions[speaker]["text"] != text:
                        active_captions[speaker]["text"] = text
                        active_captions[speaker]["last_seen"] = current_time
                        active_captions[speaker]["finalized"] = False

                        #  Someone started talking again while bot is speaking → stop bot
                        if bot and getattr(bot, "bot_playing", False):
                            bot.stop_mp3()

                    # Caption stable for enough time -> finalize it
                    else:
                        if not active_captions[speaker]["finalized"] and current_time - active_captions[speaker]["last_seen"] > stable_time:
                            prev_text = last_finalized_text.get(speaker, "")
                            new_text = (
                                text[len(prev_text):].lstrip(". ").strip()
                                if prev_text and text.startswith(prev_text)
                                else text
                            )
                            if new_text:
                                elapsed = current_time - start_time
                                finalized_captions.append({
                                    "speaker": speaker,
                                    "text": new_text,
                                    "timestamp": format_timestamp(elapsed)
                                })
                                last_finalized_text[speaker] = text

                                if TRIGGER_PHRASE in new_text.lower() and bot and mp3_file_path:
                                    if not bot.bot_playing:  # prevent overlap
                                        bot.play_mp3_file(mp3_file_path)

                            active_captions[speaker]["finalized"] = True

        except Exception as e:
            # Optional debug: logger.warning(f"Caption scraping error: {e}")
            logger.info(f" Caption scrape err: {e}")
        time.sleep(interval)

    return finalized_captions


def join_and_record_meeting(request: MeetRequest, record_seconds: int = 60, output_file: str = "meeting_audio.wav"):
    record_seconds = int(record_seconds)
    driver = setup_chrome()
    ffmpeg_proc, caption_thread = None, None
    stop_scraping = threading.Event()
    shared_captions = []
    joined = False
    MP3_FILE = os.path.join(PROJECT_ROOT, "audio", "hello.mp3")
    bot = MeetBot(driver)

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
        except: pass

        # Disable camera
        try:
            cam_button = driver.find_element(By.XPATH, "//div[@role='button'][@aria-label[contains(., 'camera')]]")
            if cam_button.get_attribute("aria_pressed") != "true":
                cam_button.click()
        except: pass

        # Enter name
        try:
            name_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Your name']"))
            )
            name_input.clear()
            name_input.send_keys(getattr(request, 'guest_name', 'Meeting Bot'))
        except: pass

        # Click Join
        try:
            WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Ask to join']/ancestor::button"))
            ).click()
        except:
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Join now']/ancestor::button"))
                ).click()
            except: pass

        # Wait until inside meeting
        try:
            WebDriverWait(driver, 30).until(
                lambda d: d.find_elements(By.XPATH, "//button[@aria-label='Leave call']")
            )
            joined = True
        except: return None, []

        if joined:
            # Turn on captions
            try:
                captions_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'captions')]"))
                )
                if "Turn on captions" in captions_button.get_attribute("aria-label"):
                    captions_button.click()
            except: pass

            # Move Chrome audio to virtual sink
            move_chrome_to_sink("meet_sink")

            start_time = time.time()
            caption_thread = threading.Thread(
                target=scrape_captions_json,
                args=(driver, stop_scraping, 1.5, 1.5, start_time, shared_captions, bot, MP3_FILE),
                daemon=True
            )
            caption_thread.start()

            ffmpeg_proc = start_ffmpeg(output_file)

            # Recording loop
            while time.time() - start_time < record_seconds:
                try:
                    leave_button = driver.find_element(By.XPATH, "//button[@aria-label='Leave call']")
                    if not leave_button.is_displayed():
                        break
                except: break
                time.sleep(2)

    finally:
        stop_scraping.set()
        if caption_thread:
            caption_thread.join(timeout=5)
        driver.quit()
        bot.stop()
        if ffmpeg_proc:
            ffmpeg_proc.terminate()
            ffmpeg_proc.wait()

    return output_file if joined else None, shared_captions if joined else []
def parse_timestamp_to_seconds(timestamp: str) -> float:
    """Convert HH:MM:SS or MM:SS timestamp to seconds."""
    parts = timestamp.split(':')
    if len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:  # MM:SS
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    else:
        return 0

def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

# def build_speaker_mapping(captions_file: str) -> Dict[str, str]:
#     """
#     Build a mapping from speaker labels (A, B, C, etc.) to actual names from captions.
#     Uses the order of first appearance to assign speaker labels.
#     """
#     try:
#         with open(captions_file, 'r', encoding='utf-8') as f:
#             captions = json.load(f)
        
#         # Track unique speakers in order of appearance
#         speaker_order = []
#         seen_speakers = set()
        
#         for caption in captions:
#             speaker = caption.get('speaker', '').strip()
#             if speaker and speaker not in seen_speakers:
#                 speaker_order.append(speaker)
#                 seen_speakers.add(speaker)
        
#         # Create mapping: A -> first speaker, B -> second speaker, etc.
#         speaker_mapping = {}
#         for i, actual_name in enumerate(speaker_order):
#             label = chr(ord('A') + i)  # A, B, C, D, etc.
#             speaker_mapping[label] = actual_name
        
#         logger.info(f" Speaker mapping created: {speaker_mapping}")
#         return speaker_mapping
        
#     except Exception as e:
#         logger.error(f" Failed to build speaker mapping: {e}")
#         return {}

def merge_transcript_with_captions(
    transcript: List[TranscriptUtterance], 
    captions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    merged = []
    for idx, (t, c) in enumerate(zip(transcript, captions), start=1):
        merged_segment = {
            "id": idx,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "speaker_label": t.speaker or "Unknown",
            "speaker_name": c.get("speaker", "Unknown"),
            "text": t.text.strip(),
            "duration_seconds": (
                parse_timestamp_to_seconds(t.end_time) -
                parse_timestamp_to_seconds(t.start_time)
            )
        }
        merged.append(merged_segment)

    final_output = {
        "metadata": {
            "total_segments": len(merged),
            "generated_at": datetime.now().isoformat()
        },
        "transcript": merged
    }

    return final_output

def generate_summary_stats(merged_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate summary statistics from the merged transcript."""
    try:

        transcript = merged_data.get('transcript', [])
        speaker_mapping = merged_data.get('metadata', {}).get('speaker_mapping', {})

        # Calculate speaker statistics
        speaker_stats = {}
        total_duration = 0
        
        for segment in transcript:
            speaker = segment.get('speaker_name', 'Unknown')
            duration = segment.get('duration_seconds', 0)
            text_length = len(segment.get('text', ''))
            
            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    'segments': 0,
                    'total_duration': 0,
                    'total_words': 0,
                    'total_characters': 0
                }
            
            speaker_stats[speaker]['segments'] += 1
            speaker_stats[speaker]['total_duration'] += duration
            speaker_stats[speaker]['total_words'] += len(segment.get('text', '').split())
            speaker_stats[speaker]['total_characters'] += text_length
            total_duration += duration
        
        # Calculate percentages
        for speaker in speaker_stats:
            speaker_stats[speaker]['percentage_of_time'] = round(
                (speaker_stats[speaker]['total_duration'] / total_duration * 100) if total_duration > 0 else 0, 2
            )
            speaker_stats[speaker]['avg_segment_duration'] = round(
                speaker_stats[speaker]['total_duration'] / speaker_stats[speaker]['segments'], 2
            ) if speaker_stats[speaker]['segments'] > 0 else 0
        
        summary = {
            "total_duration_seconds": round(total_duration, 2),
            "total_duration_formatted": seconds_to_timestamp(total_duration),
            "total_segments": len(transcript),
            "unique_speakers": len(speaker_stats),
            "speaker_statistics": speaker_stats
        }
        
        logger.info(f" Summary statistics generated")
        return summary
        
    except Exception as e:
        logger.error(f" Failed to generate summary: {e}")
        return {}

# Example usage function
def process_meeting_transcript( transcript: List[Dict[str, Any]], captions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Complete workflow to process meeting transcript:
    1. Transcript already passed into function
    2. Merge with captions data
    3. Generate summary statistics
    """
    
    try:
        
        # Step 2: Merge transcript with captions
        logger.info(" Merging transcript with captions...")
        merged_data = merge_transcript_with_captions(transcript, captions)

        if merged_data:
            # Step 3: Generate summary
            logger.info(" Generating summary statistics...")
            summary = generate_summary_stats(merged_data)

            if summary:
                merged_data['metadata']['summary'] = summary
                return {
                    "merged_transcript": merged_data,
                    "summary": summary
                }
            else:
                logger.error(" Summary generation failed")
                return {"error": "Summary generation failed"}
                
            
    except Exception as e:
        logger.error(f" Processing failed: {e}")
        return {"success": False, "error": str(e)}
