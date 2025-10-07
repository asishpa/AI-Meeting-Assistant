import numpy as np
import threading
from .realtime_audio_output_manager import RealtimeAudioOutputManager
from app.utils.gemini_ai_client import query_gemini_search
import asyncio
from app.utils.deepgram_tts_stream_ws import stream_tts_to_audio_manager_ws
class MeetBot:
    def __init__(self, driver, sample_rate=44100):
        self.driver = driver
        self.SAMPLE_RATE = sample_rate
        self.audio_manager = RealtimeAudioOutputManager(
            play_raw_audio_callback=self.send_raw_audio,
            sleep_time_between_chunks_seconds=0.1,
            output_sample_rate=self.SAMPLE_RATE
        )
        self.bot_playing = False
        self.lock = threading.Lock()
        self.awaiting_query = False  # Indicates bot is waiting for user question after "Hello meeting assistant"

    def send_raw_audio(self, chunk_bytes, sample_rate):
        pcm_array = np.frombuffer(chunk_bytes, dtype=np.int16).tolist()
        self.driver.execute_script(
            "window.botOutputManager.playPCMAudio(arguments[0], arguments[1], 1)",
            pcm_array,
            sample_rate
        )

    def play_mp3_file(self, filepath):
        with open(filepath, "rb") as f:
            mp3_data = f.read()
        pcm_data = self.audio_manager.mp3_to_pcm(mp3_data, sample_rate=self.SAMPLE_RATE)
        with self.lock:
            self.bot_playing = True
        self.audio_manager.play_audio(pcm_data, chunk_size=self.SAMPLE_RATE * 2)

    def stop_mp3(self):
        with self.lock:
            if self.bot_playing:
                self.audio_manager.stop()
                self.bot_playing = False

    def stop(self):
        self.stop_mp3()
        self.audio_manager.cleanup()

    # --------------------------
    # New: Deepgram streaming + AI logic
    # --------------------------

    def stream_tts_response(self, text: str):
        """Stream Deepgram TTS response in real-time."""
        if not text:
            return
        with self.lock:
            self.bot_playing = True
        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
            loop.run_until_complete(stream_tts_to_audio_manager_ws(text, self.audio_manager))
            with self.lock:
                self.bot_playing = False

        threading.Thread(target=runner, daemon=True).start()

    def handle_caption(self, caption_text: str):
        """Main logic for trigger + AI interaction."""
        if not caption_text:
            return
        text_lower = caption_text.lower().strip()

        # Trigger phrase: wake up the bot
        if "hello meeting assistant" in text_lower:
            if not self.bot_playing:
                response = "Yes, tell me. I’m listening."
                threading.Thread(target=self.stream_tts_response, args=(response,), daemon=True).start()
                self.awaiting_query = True
            return

        # Follow-up query (user asks a question)
        if self.awaiting_query and not self.bot_playing:
            self.awaiting_query = False
            user_question = caption_text.strip()

            ai_result = query_gemini_search(user_question)
            if ai_result["success"]:
                ai_response = ai_result["answer"]
            else:
                ai_response = "I'm sorry, I couldn't fetch an answer right now."

            threading.Thread(target=self.stream_tts_response, args=(ai_response,), daemon=True).start()

