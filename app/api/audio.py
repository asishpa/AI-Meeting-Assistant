from fastapi import APIRouter, WebSocket
import numpy as np
import soundfile as sf
from app.utils.transcription import transcribe_audio

router = APIRouter()

@router.websocket("/audio-stream")
async def audio_stream(ws: WebSocket):
    await ws.accept()
    buffer = bytearray()
    
    try:
        while True:
            data = await ws.receive_bytes()
            buffer.extend(data)

            # Process every ~5 seconds of audio
            if len(buffer) > 16000 * 2 * 5:
                audio_np = np.frombuffer(buffer, dtype=np.int16).astype(np.float32) / 32768.0
                sf.write("temp.wav", audio_np, 16000)
                
                transcript = transcribe_audio("temp.wav")
                print("Transcript:", transcript)
                buffer.clear()
    except Exception as e:
        print("WebSocket closed:", e)
