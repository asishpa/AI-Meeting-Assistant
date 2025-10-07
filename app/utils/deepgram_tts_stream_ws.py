# utils/deepgram_tts_stream_ws.py
import asyncio
import websockets
import json
import logging
import os

DEEPGRAM_API_KEY = "YOUR_DEEPGRAM_API_KEY"
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/speak?voice=alloy"

logger = logging.getLogger(__name__)

MIN_CHUNK_SIZE = 10 * 1024  # 10 KB
MAX_CHUNK_SIZE = 50 * 1024  # 50 KB

async def stream_tts_to_audio_manager_ws(text: str, audio_manager):
    """
    Stream TTS from Deepgram WebSocket and push PCM to RealtimeAudioOutputManager.
    Buffers small MP3 chunks to avoid conversion errors.
    Requires Deepgram API key to be set in the DEEPGRAM_API_KEY environment variable.
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        logger.error("Deepgram API key not found in environment variables.")
        audio_manager.stop()
        return
    headers = [("Authorization", f"Token {api_key}")]
    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
    buffer = bytearray()
    
    try:
        async with websockets.connect(DEEPGRAM_WS_URL, extra_headers=headers) as ws:
            # Send TTS request
            await ws.send(json.dumps({"text": text}))

            # Start streaming playback
            audio_manager.start_streaming()

            while True:
                try:
                    data = await ws.recv()
                except websockets.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                    # Process any remaining buffer
                    if buffer:
                        pcm_chunk = audio_manager.mp3_to_pcm(bytes(buffer), sample_rate=audio_manager.SAMPLE_RATE)
                        audio_manager.push_stream_chunk(pcm_chunk)
                    break

                if isinstance(data, str):
                    # Ignore textual messages (Deepgram may send JSON info)
                    continue
                else:
                    # data is bytes (MP3 chunk)
                    buffer.extend(data)
                    
                    # Process buffer if big enough
                    while len(buffer) >= MIN_CHUNK_SIZE:
                        chunk_to_process = buffer[:MAX_CHUNK_SIZE]
                        pcm_chunk = audio_manager.mp3_to_pcm(bytes(chunk_to_process), sample_rate=audio_manager.SAMPLE_RATE)
                        audio_manager.push_stream_chunk(pcm_chunk)
                        buffer = buffer[MAX_CHUNK_SIZE:]  # keep leftover bytes

    except Exception as e:
        logger.error(f"Error in Deepgram TTS WebSocket: {e}")
        audio_manager.stop()
