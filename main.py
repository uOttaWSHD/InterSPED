from __future__ import annotations

import asyncio
import base64
import orjson
import time
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import quote
import os

from dotenv import load_dotenv
import numpy as np
from quart import Quart, websocket as quartws
import aiofiles
from elevenlabs.client import ElevenLabs
from websockets.asyncio.client import connect
import resampy

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection
    from typeshed import HandshakeOpts

load_dotenv()
TOKEN = os.getenv("TOKEN", "")
VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"
SAMPLE_RATE_TARGET = 16000

client = ElevenLabs(api_key=TOKEN)
app = Quart(__name__)


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


async def tts_and_send(text: str):
    print(f"Generating TTS for: {text}")
    audio_iter = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    audio_data = b"".join(audio_iter)
    b64_audio = base64.b64encode(audio_data).decode("utf-8")
    await quartws.send(
        orjson.dumps({"type": "audio", "audio": b64_audio, "text": text}).decode(
            "utf-8"
        )
    )


@app.websocket("/receive")
async def ws_handler():
    args = quartws.args
    sample_rate_src = int(args.get("sampleRate", 44100))

    els = await ElevenLabsSTTStream.open_ws(
        {
            "token": TOKEN,
            "model_id": "scribe_v2_realtime",
            "commit_strategy": "vad",
            "vad_silence_threshold_secs": 1.5,
            "vad_threshold": 0.5,
        }
    )
    print(f"Client connected. SRC: {sample_rate_src}Hz")

    async def read_from_ws():
        try:
            while True:
                msg = await quartws.receive()
                if isinstance(msg, str):
                    audio_bytes = base64.b64decode(msg)
                else:
                    audio_bytes = msg

                pcm16 = np.frombuffer(audio_bytes, dtype=np.int16)
                if len(pcm16) == 0:
                    continue

                pcm_float = pcm16.astype(np.float32) / 32767.0
                pcm_16k = resampy.resample(
                    pcm_float, sample_rate_src, SAMPLE_RATE_TARGET
                )
                await els.send_audio(pcm_16k)
        except Exception as e:
            print(f"WS Read Error: {e}")

    async def receive_from_els():
        try:
            async for msg in els:
                data = orjson.loads(msg)
                if data.get("message_type") == "transcript" and data.get("is_final"):
                    transcript = data.get("text", "").strip()
                    if transcript:
                        print(f"User: {transcript}")
                        await quartws.send(
                            orjson.dumps(
                                {"type": "transcript", "text": transcript}
                            ).decode("utf-8")
                        )
                        response = get_llm_response(transcript)
                        print(f"AI: {response}")
                        await tts_and_send(response)
                elif data.get("message_type") == "partial_transcript":
                    await quartws.send(
                        orjson.dumps(
                            {"type": "partial", "text": data.get("text", "")}
                        ).decode("utf-8")
                    )
        except Exception as e:
            print(f"ELS Receive Error: {e}")

    try:
        await asyncio.gather(read_from_ws(), receive_from_els(), els.wait_for_chunks())
    except Exception as e:
        print(f"Handler Error: {e}")
    finally:
        await els.close()
        print("Disconnected")


@app.route("/")
async def endpoint_home():
    async with aiofiles.open("./index.html", "r") as f:
        return await f.read()


if __name__ == "__main__":
    app.run(port=3000)
