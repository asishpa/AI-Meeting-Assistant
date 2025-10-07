import numpy as np
from .realtime_audio_output_manager import RealtimeAudioOutputManager

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
