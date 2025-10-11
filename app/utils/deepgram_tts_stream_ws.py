import asyncio
import logging
import os
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakWebSocketEvents

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

logger = logging.getLogger(__name__)

# Deepgram outputs 48 kHz PCM
DEEPGRAM_SAMPLE_RATE = 48000


async def stream_tts_to_audio_manager_ws(text: str, audio_manager):
    """
    Stream TTS from Deepgram using the official Python SDK WebSocket
    and push PCM to RealtimeAudioOutputManager in real-time.
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

        # Event to signal TTS completion
        tts_done_event = asyncio.Event()

        # --- Event Handlers ---
        def on_open(client, event, **kwargs):
            logger.info(f"Deepgram connection opened: {event}")
            audio_manager.start_streaming()

        def on_audio(client, data, **kwargs):
            # Feed Deepgram PCM directly (48 kHz) to audio manager
            audio_manager.push_stream_chunk(data)

        def on_close(client, event, **kwargs):
            logger.info(f"Deepgram connection closed: {event}")
            audio_manager.stop()
            tts_done_event.set()

        def on_error(client, event, **kwargs):
            logger.error(f"Deepgram TTS error: {event}")
            audio_manager.stop()
            tts_done_event.set()

        # Register event handlers
        dg_connection.on(SpeakWebSocketEvents.Open, on_open)
        dg_connection.on(SpeakWebSocketEvents.AudioData, on_audio)
        dg_connection.on(SpeakWebSocketEvents.Close, on_close)
        dg_connection.on(SpeakWebSocketEvents.Error, on_error)

        # Configure audio options (48 kHz PCM output)
        options = {
            "model": "aura-2-thalia-en",
            "encoding": "linear16",
            "sample_rate": DEEPGRAM_SAMPLE_RATE,
        }

        # Start WebSocket connection
        if dg_connection.start(options) is False:
            logger.error("Failed to start Deepgram TTS connection.")
            audio_manager.stop()
            return

        # Send text to be spoken
        dg_connection.send_text(text)
        dg_connection.flush()

        # Wait until TTS finishes streaming
        await tts_done_event.wait()

        # Finish and clean up
        dg_connection.finish()
        logger.info("TTS stream completed successfully.")

    except Exception as e:
        logger.error(f"Error in Deepgram TTS WebSocket: {e}")
        audio_manager.stop()
