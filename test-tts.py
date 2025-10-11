import os
import sounddevice as sd
import numpy as np
import time
import queue
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakWebSocketEvents

# Load .env file
load_dotenv()

TTS_TEXT = "Hello, this is a text to speech example using Deepgram."
audio_queue = queue.Queue()

def main():
    try:
        deepgram = DeepgramClient()
        dg_connection = deepgram.speak.websocket.v("1")

        connection_closed = False

        def on_open(client, event, **kwargs):
            print(f"Connection opened: {event}")

        def on_binary_data(client, data, **kwargs):
            array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_queue.put(array)

        def on_close(client, event, **kwargs):
            nonlocal connection_closed
            print(f"Connection closed: {event}")
            connection_closed = True

        dg_connection.on(SpeakWebSocketEvents.Open, on_open)
        dg_connection.on(SpeakWebSocketEvents.AudioData, on_binary_data)
        dg_connection.on(SpeakWebSocketEvents.Close, on_close)

        options = {
            "model": "aura-2-thalia-en",
            "encoding": "linear16",
            "sample_rate": 48000,
        }

        if dg_connection.start(options) is False:
            print("Failed to start connection")
            return

        dg_connection.send_text(TTS_TEXT)
        dg_connection.flush()

        print("Playing TTS audio...")

        with sd.OutputStream(samplerate=48000, channels=1, dtype='float32') as stream:
            while not connection_closed or not audio_queue.empty():
                try:
                    chunk = audio_queue.get(timeout=0.5)
                    stream.write(chunk)
                except queue.Empty:
                    continue

        dg_connection.finish()
        print("TTS stream completed")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
