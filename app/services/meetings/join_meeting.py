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
from typing import Dict, List, Any
from datetime import datetime
from app.services.meetings.live_audio import inject_live_audio_to_meet
from app.services.meetings.live_tts import tts_generator


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

def scrape_captions_json(driver, output_file="captions.json", stop_event=None, interval=1.5, stable_time=1.5, start_time=None):
    """
    Robust Google Meet captions scraper.

    Features:
    - Handles multiple speakers.
    - Only finalizes text when it stabilizes.
    - Avoids repeated text if a speaker continues speaking later.
    - Saves only new appended text.
    - Ignores captions with empty speaker.
    - Merges consecutive blocks from the same speaker.
    """
    finalized_captions = []
    active_captions = {}         # Current text per speaker
    last_finalized_text = {}     # Last finalized text per speaker
    if start_time is None:
        start_time = time.time()  # fallback   # Relative timestamp base

    while not (stop_event and stop_event.is_set()):
        try:
            container = driver.find_element(By.XPATH, "//div[@role='region' and @aria-label='Captions']")
            blocks = container.find_elements(By.XPATH, ".//div[contains(@class,'nMcdL')]")
            current_time = time.time()
            updated = False
            
            # Process blocks to merge consecutive same-speaker blocks
            merged_blocks = []
            current_speaker = None
            current_text = ""
            
            for block in blocks:
                try:
                    speaker = block.find_element(By.CSS_SELECTOR, ".NWpY1d").text.strip()
                except:
                    speaker = ""

                # Skip empty speaker blocks
                if not speaker:
                    continue

                try:
                    text = block.find_element(By.CSS_SELECTOR, ".VbkSUe").text.strip()
                except:
                    text = ""
                if not text:
                    continue
                
                # Merge consecutive blocks from same speaker
                if speaker == current_speaker:
                    # Same speaker - merge text
                    current_text += " " + text
                else:
                    # Different speaker - save previous merged block if exists
                    if current_speaker:
                        merged_blocks.append({
                            "speaker": current_speaker,
                            "text": current_text.strip()
                        })
                    
                    # Start new merged block
                    current_speaker = speaker
                    current_text = text
            
            # Don't forget the last merged block
            if current_speaker:
                merged_blocks.append({
                    "speaker": current_speaker,
                    "text": current_text.strip()
                })

            # Process merged blocks
            for merged_block in merged_blocks:
                speaker = merged_block["speaker"]
                text = merged_block["text"]

                # Initialize if new speaker
                if speaker not in active_captions:
                    active_captions[speaker] = {"text": text, "last_seen": current_time, "finalized": False}
                else:
                    # Text changed → reset timer
                    if active_captions[speaker]["text"] != text:
                        active_captions[speaker]["text"] = text
                        active_captions[speaker]["last_seen"] = current_time
                        active_captions[speaker]["finalized"] = False
                    else:
                        # Text stable → finalize if enough time passed
                        if not active_captions[speaker]["finalized"] and current_time - active_captions[speaker]["last_seen"] > stable_time:
                            prev_text = last_finalized_text.get(speaker, "")
                            new_text = text

                            # Remove repeated prefix
                            if prev_text and new_text.startswith(prev_text):
                                new_text = new_text[len(prev_text):].lstrip(". ").strip()

                            if new_text:  # Only finalize non-empty new text
                                elapsed = current_time - start_time
                                finalized_captions.append({
                                    "speaker": speaker,
                                    "text": new_text,
                                    "timestamp": format_timestamp(elapsed)
                                })
                                last_finalized_text[speaker] = text
                                updated = True

                            active_captions[speaker]["finalized"] = True

            # Write to JSON only if updated
            if updated:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(finalized_captions, f, indent=2)

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
                tts_audio_path = "bot_speech.wav"  # your pre-recorded TTS file
                inject_audio_to_meet(driver, tts_audio_path)
                
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
        # --- Launch live audio injector after 30 seconds ---
        #if tts_generator:
        #    def delayed_injection():
        #        time.sleep(30)
        #        logger.info("⏳ 30s elapsed — injecting live bot audio now")
        #        inject_live_audio_to_meet(driver, tts_generator)

        #    threading.Thread(target=delayed_injection, daemon=True).start()

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

def build_speaker_mapping(captions_file: str) -> Dict[str, str]:
    """
    Build a mapping from speaker labels (A, B, C, etc.) to actual names from captions.
    Uses the order of first appearance to assign speaker labels.
    """
    try:
        with open(captions_file, 'r', encoding='utf-8') as f:
            captions = json.load(f)
        
        # Track unique speakers in order of appearance
        speaker_order = []
        seen_speakers = set()
        
        for caption in captions:
            speaker = caption.get('speaker', '').strip()
            if speaker and speaker not in seen_speakers:
                speaker_order.append(speaker)
                seen_speakers.add(speaker)
        
        # Create mapping: A -> first speaker, B -> second speaker, etc.
        speaker_mapping = {}
        for i, actual_name in enumerate(speaker_order):
            label = chr(ord('A') + i)  # A, B, C, D, etc.
            speaker_mapping[label] = actual_name
        
        logger.info(f"📝 Speaker mapping created: {speaker_mapping}")
        return speaker_mapping
        
    except Exception as e:
        logger.error(f"❌ Failed to build speaker mapping: {e}")
        return {}

def merge_transcript_with_captions(transcript_file, captions_file, output_file):
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    with open(captions_file, 'r', encoding='utf-8') as f:
        captions = json.load(f)

    merged_transcript = []
    for i, (t, c) in enumerate(zip(transcript, captions), 1):
        merged_segment = {
            "id": i,
            "start_time": t.get("start_time", "00:00"),
            "end_time": t.get("end_time", "00:00"),
            "speaker_label": t.get("speaker", "Unknown"),
            "speaker_name": c.get("speaker", "Unknown"),
            "text": t.get("text", "").strip(),
            "duration_seconds": parse_timestamp_to_seconds(t.get("end_time", "00:00")) -
                               parse_timestamp_to_seconds(t.get("start_time", "00:00"))
        }
        merged_transcript.append(merged_segment)

    final_output = {
        "metadata": {
            "total_segments": len(merged_transcript),
            "generated_at": datetime.now().isoformat(),
            "source_files": {"transcript": transcript_file, "captions": captions_file}
        },
        "transcript": merged_transcript
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    return merged_transcript

def generate_summary_stats(merged_file: str) -> Dict[str, Any]:
    """Generate summary statistics from the merged transcript."""
    try:
        with open(merged_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        transcript = data.get('transcript', [])
        speaker_mapping = data.get('metadata', {}).get('speaker_mapping', {})
        
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
        
        logger.info(f"📈 Summary statistics generated")
        return summary
        
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {e}")
        return {}

# Example usage function
def process_meeting_transcript(audio_file: str, captions_file: str, output_dir: str = "."):
    """
    Complete workflow to process meeting transcript:
    1. Transcribe audio (assumes transcribe_file_json is available)
    2. Merge with captions data
    3. Generate summary statistics
    """
    import os
    
    # File paths
    transcript_file = os.path.join(output_dir, "meeting_transcript.json")
    merged_file = os.path.join(output_dir, "merged_transcript.json")
    summary_file = os.path.join(output_dir, "transcript_summary.json")
    
    try:
        # Step 1: Transcribe audio (assuming transcribe_file_json function exists)
        logger.info("🎵 Starting audio transcription...")
        #transcript_data = transcribe_file_json(audio_file, transcript_file)
        
        # Step 2: Merge transcript with captions
        logger.info("🔗 Merging transcript with captions...")
        merged_data = merge_transcript_with_captions(transcript_file, captions_file, merged_file)
        
        if merged_data:
            # Step 3: Generate summary
            logger.info("📊 Generating summary statistics...")
            summary = generate_summary_stats(merged_file)
            
            if summary:
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ Summary saved to: {summary_file}")
            
            return {
                "transcript_file": transcript_file,
                "merged_file": merged_file,
                "summary_file": summary_file,
                "success": True
            }
        else:
            logger.error("❌ Merge failed")
            return {"success": False}
            
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        return {"success": False, "error": str(e)}
def inject_audio_to_meet(driver, audio_file_path: str):
    """
    Inject audio into Google Meet automatically by finding the active RTCPeerConnection.
    Assumes audio_file_path is a WAV or PCM file.
    """
    import base64
    import os

    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    # Convert audio file to base64
    with open(audio_file_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")

    js_code = f"""
    (async () => {{
        // 1. Find active RTCPeerConnection(s)
        let pcs = [];
        for (const key in window) {{
            try {{
                if (window[key] instanceof RTCPeerConnection) pcs.push(window[key]);
            }} catch (e) {{}}
        }}
        if (pcs.length === 0) {{
            console.warn("⚠️ No RTCPeerConnection found!");
            return;
        }}
        const pc = pcs[0];
        window.botPC = pc;  // optional reference

        // 2. Decode base64 audio
        const audioData = Uint8Array.from(atob("{audio_base64}"), c => c.charCodeAt(0));
        const audioContext = new AudioContext({{ sampleRate: 48000 }});
        const audioBuffer = await audioContext.decodeAudioData(audioData.buffer);

        // 3. Create MediaStreamTrackGenerator
        const generator = new MediaStreamTrackGenerator({{ kind: "audio" }});
        const writer = generator.writable.getWriter();
        const channelData = audioBuffer.getChannelData(0);
        const frameSize = 1024;
        const sampleRate = audioBuffer.sampleRate;

        for (let i = 0; i < channelData.length; i += frameSize) {{
            const frameArray = new Float32Array(frameSize);
            frameArray.set(channelData.subarray(i, i + frameSize));
            await writer.write(new AudioData({{
                timestamp: (i / sampleRate) * 1000000,
                data: frameArray,
                format: "f32",
                numberOfChannels: 1,
                sampleRate
            }}));
        }}
        writer.close();

        // 4. Add track to Meet
        pc.addTrack(generator);
        console.log("✅ Bot audio track added to Meet");
    }})();
    """

    driver.execute_script(js_code)
    print("🔊 Injected bot audio into Meet")
