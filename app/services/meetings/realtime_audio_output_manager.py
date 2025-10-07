import threading
import time
import io
import queue
import numpy as np
from pydub import AudioSegment

SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1      # mono


class RealtimeAudioOutputManager:
    def __init__(self, play_raw_audio_callback, sleep_time_between_chunks_seconds=0.1, output_sample_rate=44100):
        self.play_raw_audio_callback = play_raw_audio_callback
        self.sleep_time_between_chunks_seconds = sleep_time_between_chunks_seconds
        self.SAMPLE_RATE = output_sample_rate

        self.audio_thread = None
        self.stop_audio_thread = False
        self.lock = threading.Lock()

        # NEW: queue for streamed PCM chunks
        self.audio_queue = queue.Queue()
        self.streaming_mode = False

    @staticmethod
    def mp3_to_pcm(mp3_data: bytes, sample_rate: int = 44100, channels: int = 1, sample_width: int = 2) -> bytes:
        buffer = io.BytesIO(mp3_data)
        audio_segment = AudioSegment.from_mp3(buffer)
        audio_segment = audio_segment.set_frame_rate(sample_rate)
        audio_segment = audio_segment.set_channels(channels)
        audio_segment = audio_segment.set_sample_width(sample_width)
        pcm_data = audio_segment.raw_data
        buffer.close()
        return pcm_data

    # =============== Normal (File) Playback ===============

    def _play_audio_chunks_thread(self, audio_data: bytes, chunk_size: int):
        """Plays PCM data that is already fully available (file-based)."""
        for i in range(0, len(audio_data), chunk_size):
            with self.lock:
                if self.stop_audio_thread:
                    break
            chunk = audio_data[i: i + chunk_size]
            self.play_raw_audio_callback(chunk, self.SAMPLE_RATE)
            time.sleep(self.sleep_time_between_chunks_seconds)

    def play_audio(self, audio_data: bytes, chunk_size: int):
        """Play a full PCM buffer (legacy mode)."""
        self.stop()
        self.streaming_mode = False
        self.stop_audio_thread = False
        self.audio_thread = threading.Thread(
            target=self._play_audio_chunks_thread,
            args=(audio_data, chunk_size),
            daemon=True
        )
        self.audio_thread.start()

    # =============== Realtime (Streamed) Playback ===============

    def start_streaming(self):
        """Enable streaming mode (real-time PCM push)."""
        self.stop()
        self.streaming_mode = True
        self.stop_audio_thread = False
        self.audio_thread = threading.Thread(target=self._streaming_playback_loop, daemon=True)
        self.audio_thread.start()

    def push_stream_chunk(self, pcm_chunk: bytes):
        """Push a PCM chunk from an external source (e.g., Deepgram WebSocket)."""
        if self.streaming_mode and not self.stop_audio_thread:
            self.audio_queue.put(pcm_chunk)

    def _streaming_playback_loop(self):
        """Continuously play incoming PCM chunks from the queue."""
        while not self.stop_audio_thread:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                self.play_raw_audio_callback(chunk, self.SAMPLE_RATE)
                time.sleep(self.sleep_time_between_chunks_seconds)
            except queue.Empty:
                continue

    # =============== Stop and Cleanup ===============

    def stop(self):
        with self.lock:
            self.stop_audio_thread = True
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1)
        self.audio_thread = None
        self.streaming_mode = False
        # Clear queue
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

    def cleanup(self):
        self.stop()
