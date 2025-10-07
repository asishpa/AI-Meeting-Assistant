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
        self.audio_manager._play_audio_chunks(pcm_data, chunk_size=self.SAMPLE_RATE * 2)

    def stop(self):
        self.audio_manager.cleanup()
