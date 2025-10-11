# utils/deepgram_tts_stream_ws.py

import asyncio
import logging
import os
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakWebSocketEvents, SpeakOptions

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

logger = logging.getLogger(__name__)


async def stream_tts_to_audio_manager_ws(text: str, audio_manager):
    """
    Stream TTS from Deepgram using the official Python SDK WebSocket
    and push PCM to RealtimeAudioOutputManager.

    This method uses Deepgram's real-time TTS WebSocket API via their SDK.
    Requires DEEPGRAM_API_KEY to be set in environment variables.
    """

    if not DEEPGRAM_API_KEY:
        logger.error("Deepgram API key not found in environment variables.")
        audio_manager.stop()
        return

    try:
        # Initialize Deepgram client
        dg_client = DeepgramClient()

        # Create a WebSocket connection for TTS
        dg_connection = dg_client.speak.websocket.v("1")

        # --- Event Handlers ---

        def on_open(self, open, **kwargs):
            logger.info(f"Deepgram connection opened: {open}")
            audio_manager.start_streaming()

        def on_audio(self, data, **kwargs):
            # Received a PCM audio chunk
            audio_manager.push_stream_chunk(data)

        def on_close(self, close, **kwargs):
            logger.info(f"Deepgram connection closed: {close}")
            audio_manager.stop()

        def on_error(self, error, **kwargs):
            logger.error(f"Deepgram TTS error: {error}")
            audio_manager.stop()

        # Register event handlers
        dg_connection.on(SpeakWebSocketEvents.Open, on_open)
        dg_connection.on(SpeakWebSocketEvents.AudioData, on_audio)
        dg_connection.on(SpeakWebSocketEvents.Close, on_close)
        dg_connection.on(SpeakWebSocketEvents.Error, on_error)

        # Configure audio options (48 kHz PCM output)
        options = {
            "model": "aura-2-thalia-en",
            "encoding": "linear16",
            "sample_rate": 48000,
        }


        # Start WebSocket connection
        if dg_connection.start(options) is False:
            logger.error("Failed to start Deepgram TTS connection.")
            audio_manager.stop()
            return

        # Send text to be spoken
        dg_connection.send_text(text)
        dg_connection.flush()

        # Wait until TTS finishes playback
        await asyncio.sleep(2)  # Optional: adjust for your playback duration

        # Finish and clean up
        dg_connection.finish()
        logger.info("TTS stream completed successfully.")

    except Exception as e:
        logger.error(f"Error in Deepgram TTS WebSocket: {e}")
        audio_manager.stop()
