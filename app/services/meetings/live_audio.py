import base64
import struct
import json
import time
import numpy as np
from selenium.webdriver.remote.webdriver import WebDriver

def inject_live_audio_to_meet(
    driver: WebDriver,
    audio_source,
    chunk_size: int = 1024,
    sample_rate: int = 48000,
    delay_between_chunks: float = 0.01
):
    """
    Inject live audio into Google Meet.

    Parameters:
    - driver: Selenium WebDriver instance (Meet page)
    - audio_source: 
        - str -> path to WAV file (mono)
        - generator -> yields float32 np.array chunks in range [-1, 1]
    - chunk_size: number of samples per chunk
    - sample_rate: audio sample rate
    - delay_between_chunks: time to wait between chunks (seconds)
    """

    # --- Helper: WAV file -> generator of chunks ---
    def wav_file_generator(file_path):
        import wave
        with wave.open(file_path, "rb") as wf:
            assert wf.getnchannels() == 1, "Only mono audio supported"
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i+chunk_size]
        return

    # Determine source type
    if isinstance(audio_source, str):
        chunk_generator = wav_file_generator(audio_source)
    else:
        chunk_generator = audio_source  # already a generator

    # --- Convert chunks to base64 strings for JS ---
    js_chunks = []
    timestamp = 0
    for chunk in chunk_generator:
        if len(chunk) == 0:
            continue
        # pad last chunk if needed
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        bytes_chunk = struct.pack(f"{len(chunk)}f", *chunk)
        b64_chunk = base64.b64encode(bytes_chunk).decode("utf-8")
        js_chunks.append({"data": b64_chunk, "timestamp": timestamp})
        timestamp += len(chunk) / sample_rate

    js_chunks_str = json.dumps(js_chunks)

    # --- JS code to inject streaming audio ---
    js_code = f"""
    (async (chunks, sampleRate) => {{
        let pc = null;
        for (const key in window) {{
            try {{
                if (window[key] instanceof RTCPeerConnection) {{
                    pc = window[key];
                    break;
                }}
            }} catch(e) {{}}
        }}
        if (!pc) {{
            console.warn("⚠️ No RTCPeerConnection found!");
            return;
        }}

        const generator = new MediaStreamTrackGenerator({{ kind: "audio" }});
        const writer = generator.writable.getWriter();
        pc.addTrack(generator);

        for (const chunkObj of chunks) {{
            const chunkData = Uint8Array.from(atob(chunkObj.data), c => c.charCodeAt(0));
            const floatArray = new Float32Array(chunkData.buffer);
            await writer.write(new AudioData({{
                timestamp: chunkObj.timestamp * 1000000,
                data: floatArray,
                format: "f32",
                numberOfChannels: 1,
                sampleRate
            }}));
            await new Promise(r => setTimeout(r, {int(delay_between_chunks*1000)}));
        }}
        writer.close();
        console.log("✅ Live bot audio finished");
    }})({js_chunks_str}, {sample_rate});
    """

    driver.execute_script(js_code)
    print("🔊 Streaming bot audio injected into Meet")
