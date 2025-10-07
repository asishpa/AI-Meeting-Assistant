import queue
import threading
import time
import numpy as np
import io
from pydub import AudioSegment

SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1      # mono


class RealtimeAudioOutputManager:
    def __init__(self, play_raw_audio_callback, sleep_time_between_chunks_seconds, output_sample_rate=44100):
        self.play_raw_audio_callback = play_raw_audio_callback
        self.sleep_time_between_chunks_seconds = sleep_time_between_chunks_seconds
        self.audio_queue = queue.Queue()
        self.audio_thread = None
        self.stop_audio_thread = False
        self.bytes_per_sample = SAMPLE_WIDTH
        self.SAMPLE_RATE = output_sample_rate

    def _stop_audio_thread(self):
        self.stop_audio_thread = True
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join()

    @staticmethod
    def mp3_to_pcm(mp3_data: bytes, sample_rate: int = 32000, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Convert MP3 audio data to PCM format.
        """
        buffer = io.BytesIO(mp3_data)
        audio_segment = AudioSegment.from_mp3(buffer)
        audio_segment = audio_segment.set_frame_rate(sample_rate)
        audio_segment = audio_segment.set_channels(channels)
        audio_segment = audio_segment.set_sample_width(sample_width)
        pcm_data = audio_segment.raw_data
        buffer.close()
        return pcm_data

    def _play_audio_chunks(self, audio_data: bytes, chunk_size: int):
        for i in range(0, len(audio_data), chunk_size):
            if self.stop_audio_thread:
                break
            chunk = audio_data[i: i + chunk_size]
            self.play_raw_audio_callback(chunk, self.SAMPLE_RATE)
            time.sleep(self.sleep_time_between_chunks_seconds)

    def cleanup(self):
        self.stop_audio_thread = True
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join()
