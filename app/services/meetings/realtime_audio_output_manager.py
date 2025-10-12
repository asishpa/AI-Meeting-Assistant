import threading
import time
import io
import queue
import numpy as np
from pydub import AudioSegment
import logging

# ----------------- Logging Setup -----------------
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

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

        logger.debug(f"AudioOutputManager initialized with sample rate {self.SAMPLE_RATE}")

    @staticmethod
    def mp3_to_pcm(mp3_data: bytes, sample_rate: int = 44100, channels: int = 1, sample_width: int = 2) -> bytes:
        logger.debug(f"Converting MP3 to PCM: sample_rate={sample_rate}, channels={channels}, sample_width={sample_width}")
        buffer = io.BytesIO(mp3_data)
        audio_segment = AudioSegment.from_mp3(buffer)
        audio_segment = audio_segment.set_frame_rate(sample_rate)
        audio_segment = audio_segment.set_channels(channels)
        audio_segment = audio_segment.set_sample_width(sample_width)
        pcm_data = audio_segment.raw_data
        buffer.close()
        logger.debug(f"MP3 converted to PCM: {len(pcm_data)} bytes")
        return pcm_data

    # =============== Normal (File) Playback ===============

    def _play_audio_chunks_thread(self, audio_data: bytes, chunk_size: int):
        logger.debug(f"Starting file playback thread: {len(audio_data)} bytes, chunk_size={chunk_size}")
        for i in range(0, len(audio_data), chunk_size):
            with self.lock:
                if self.stop_audio_thread:
                    logger.debug("Stop signal received in file playback thread")
                    break
            chunk = audio_data[i: i + chunk_size]
            logger.debug(f"Playing chunk {i} to {i+len(chunk)} ({len(chunk)} bytes)")
            self.play_raw_audio_callback(chunk, self.SAMPLE_RATE)
            time.sleep(self.sleep_time_between_chunks_seconds)
        logger.debug("File playback thread finished")

    def play_audio(self, audio_data: bytes, chunk_size: int):
        logger.debug("play_audio called")
        self.stop()
        self.streaming_mode = False
        self.stop_audio_thread = False
        self.audio_thread = threading.Thread(
            target=self._play_audio_chunks_thread,
            args=(audio_data, chunk_size),
            daemon=True
        )
        self.audio_thread.start()
        logger.debug("Audio thread started for file playback")

    # =============== Realtime (Streamed) Playback ===============

    def start_streaming(self):
        logger.debug("Starting streaming mode")
        self.stop()
        self.streaming_mode = True
        self.stop_audio_thread = False
        self.audio_thread = threading.Thread(target=self._streaming_playback_loop, daemon=True)
        self.audio_thread.start()
        logger.debug("Streaming playback thread started")

    def push_stream_chunk(self, pcm_chunk: bytes):
        if self.streaming_mode and not self.stop_audio_thread:
            self.audio_queue.put(pcm_chunk)
            logger.debug(f"Pushed chunk to queue: {len(pcm_chunk)} bytes, queue size now {self.audio_queue.qsize()}")

    def _streaming_playback_loop(self):
        logger.debug("Streaming playback loop started")
        while not self.stop_audio_thread:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                duration_sec = len(chunk) / (self.SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)
                logger.debug(f"Dequeued chunk: {len(chunk)} bytes, duration {duration_sec:.3f}s, queue size {self.audio_queue.qsize()}")
                self.play_raw_audio_callback(chunk, self.SAMPLE_RATE)
                time.sleep(duration_sec)
            except queue.Empty:
                continue
        logger.debug("Streaming playback loop exited")

    # =============== Stop and Cleanup ===============

    def stop(self):
        with self.lock:
            self.stop_audio_thread = True
        if self.audio_thread and self.audio_thread.is_alive():
            logger.debug("Joining audio thread on stop()")
            self.audio_thread.join(timeout=1)
        self.audio_thread = None
        self.streaming_mode = False
        # Clear queue
        with self.audio_queue.mutex:
            queue_len = len(self.audio_queue.queue)
            self.audio_queue.queue.clear()
            if queue_len > 0:
                logger.debug(f"Cleared {queue_len} chunks from audio queue")
        logger.debug("AudioOutputManager stopped")

    def cleanup(self):
        logger.debug("Cleanup called")
        self.stop()
