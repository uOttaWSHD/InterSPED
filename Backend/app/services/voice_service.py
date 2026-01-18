from __future__ import annotations

import asyncio
import base64
import orjson
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import quote
import os
import numpy as np
from elevenlabs.client import ElevenLabs
from websockets.asyncio.client import connect

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

# We assume env vars are loaded by main app
TOKEN = os.getenv(
    "ELEVENLABS_API_KEY", ""
)  # changed to explicit name, but original used TOKEN
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "UgBBYS2sOqTuMpoF3BR0")
SAMPLE_RATE_TARGET = 16000

client = ElevenLabs(api_key=TOKEN)


def query(params: dict[str, Any]) -> str:
    def fmt_item(kv):
        k, v = kv
        return f"{quote(k)}={quote(str(v))}"

    return f"?{'&'.join(map(fmt_item, params.items()))}"


def chunk_to_b64(chunk: np.ndarray) -> str:
    return base64.b64encode(chunk.tobytes()).decode("utf8")


class ElevenLabsSTTStream:
    def __init__(self, socket: ClientConnection):
        self._socket = socket
        self._queue = asyncio.Queue()
        self._closed = False

    @classmethod
    async def open_ws(cls, config: dict[str, Any]) -> Self:
        token = config.pop("token")
        headers = {"xi-api-key": token}
        socket = await connect(
            f"wss://api.elevenlabs.io/v1/speech-to-text/realtime" + query(config),
            additional_headers=headers,
        )
        return cls(socket)

    async def wait_for_chunks(self):
        while not self._closed:
            chunks = []
            while not self._queue.empty():
                chunk = await self._queue.get()
                # Assuming chunk is already float32 resampled to 16k
                audio_pcm16 = (chunk * 32767).astype(np.int16)
                chunks.append(audio_pcm16)

            if not chunks:
                await asyncio.sleep(0.05)
                continue

            aud = np.concatenate(chunks)
            m = {
                "message_type": "input_audio_chunk",
                "sample_rate": SAMPLE_RATE_TARGET,
                "audio_base_64": chunk_to_b64(aud),
            }
            await self._socket.send(orjson.dumps(m).decode("utf-8"))

    async def send_audio(self, pcm_data: np.ndarray):
        await self._queue.put(pcm_data)

    def __aiter__(self):
        return self

    async def __anext__(self) -> Any:
        if self._closed or self._socket.close_code:
            raise StopAsyncIteration
        return await self._socket.recv()

    async def close(self):
        self._closed = True
        await self._socket.close()


def get_llm_response(text: str) -> str:
    responses = {
        "hello": "Hello! I'm your AI interviewer today. Shall we begin?",
        "hi": "Hi there! Ready for your interview?",
        "start": "Great! Let's start with your background. Tell me about yourself.",
        "tell me about yourself": "That's interesting. What are your greatest strengths?",
        "strengths": "Very impressive. And what would you say is your greatest weakness?",
        "weakness": "Honesty is important. How do you handle stressful situations?",
    }
    lowered = text.lower()
    for k, v in responses.items():
        if k in lowered:
            return v
    return f"I see. You mentioned '{text}'. Can you elaborate on how that's relevant to this role?"


async def generate_tts(text: str) -> str:
    """Generates TTS audio and returns base64 string"""
    print(f"DEBUG: Generating TTS for: {text}")
    try:
        # Run in thread pool to avoid blocking async loop
        audio_iter = await asyncio.to_thread(
            client.text_to_speech.convert,
            text=text,
            voice_id=VOICE_ID,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        audio_data = b"".join(audio_iter)
        print(f"DEBUG: TTS Generated successfully, length: {len(audio_data)} bytes")
        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        return b64_audio
    except Exception as e:
        print(f"DEBUG: TTS Generation Failed: {e}")
        raise e
