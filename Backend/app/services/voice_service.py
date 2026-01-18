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
        self._first_chunk_sent = False
        self._first_message: dict[str, Any] | None = None

    @classmethod
    async def open_ws(cls, config: dict[str, Any]) -> Self:
        token = config.pop("token")

        # Debug: Show partial key to verify it's loading
        print(f"DEBUG: API Key starts with: {token[:10]}... ends with: ...{token[-4:]}")

        # Build the URL with query parameters
        query_string = query(config)
        url = f"wss://api.elevenlabs.io/v1/speech-to-text/realtime{query_string}"

        print(f"DEBUG: Connecting to ElevenLabs STT: {url[:80]}...")

        # Pass API key in headers - this is the server-side auth method
        headers = {"xi-api-key": token}

        socket = await connect(
            url,
            additional_headers=headers,
            # Increase ping interval to keep connection alive
            ping_interval=20,
            ping_timeout=20,
        )

        # Wait for and log the first message (should be session_started or auth_error)
        first_msg = await socket.recv()
        first_data = orjson.loads(first_msg)
        print(f"DEBUG: First message from ElevenLabs: {first_data}")

        if first_data.get("message_type") == "auth_error":
            raise Exception(
                f"ElevenLabs auth error: {first_data.get('error', 'Unknown auth error')}"
            )

        instance = cls(socket)
        instance._first_message = first_data  # Store for later use
        return instance

    async def wait_for_chunks(self):
        """Continuously send audio chunks from the queue to ElevenLabs"""
        chunks_sent = 0
        print("DEBUG: wait_for_chunks started")

        # PRIME THE CONNECTION: Send 250ms of silence immediately to prevent early timeout
        # and ensure the session is active.
        try:
            silence_prime = np.zeros(4000, dtype=np.int16)  # 250ms at 16kHz
            m_prime = {
                "message_type": "input_audio_chunk",
                "audio_base_64": chunk_to_b64(silence_prime),
                "commit": False,
                "sample_rate": SAMPLE_RATE_TARGET,
            }
            await self._socket.send(orjson.dumps(m_prime).decode("utf-8"))
            print("DEBUG: Sent priming silence to ElevenLabs")
        except Exception as e:
            print(f"DEBUG: Failed to prime connection: {e}")

        while not self._closed and not self._socket.close_code:
            try:
                # Use wait_for with a generous timeout (2s) to implement Keep-Alive Heartbeat
                # This ensures we don't block forever if the user is silent, preventing ELs timeout.
                try:
                    chunk = await asyncio.wait_for(self._queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    # HEARTBEAT: Send 100ms of silence to keep connection alive during user silence
                    silence = np.zeros(1600, dtype=np.int16)
                    m = {
                        "message_type": "input_audio_chunk",
                        "audio_base_64": chunk_to_b64(silence),
                        "commit": False,
                        "sample_rate": SAMPLE_RATE_TARGET,
                    }
                    await self._socket.send(orjson.dumps(m).decode("utf-8"))
                    continue

                if isinstance(chunk, str):
                    if chunk == "COMMIT":
                        # Only send commit if we have actually sent audio (or primed).
                        # Since we primed, we are safe to send commit.
                        print(
                            "DEBUG: Sending explicit COMMIT to ElevenLabs (with silence)"
                        )
                        # Send 100ms of silence
                        silence = np.zeros(1600, dtype=np.int16)
                        m = {
                            "message_type": "input_audio_chunk",
                            "audio_base_64": chunk_to_b64(silence),
                            "commit": True,
                            "sample_rate": SAMPLE_RATE_TARGET,
                        }
                        await self._socket.send(orjson.dumps(m).decode("utf-8"))
                    continue

                # Normal Audio Chunk
                # Convert float32 [-1, 1] to int16
                audio_pcm16 = (chunk * 32767).astype(np.int16)

                m = {
                    "message_type": "input_audio_chunk",
                    "audio_base_64": chunk_to_b64(audio_pcm16),
                    "commit": False,
                    "sample_rate": SAMPLE_RATE_TARGET,
                }

                await self._socket.send(orjson.dumps(m).decode("utf-8"))
                chunks_sent += 1

                # Log every 50 chunks (approx 5s)
                if chunks_sent % 50 == 0:
                    print(f"DEBUG: Sent {chunks_sent} chunks to ElevenLabs")

            except Exception as e:
                if not self._closed:
                    print(f"DEBUG: Error sending audio chunk to ElevenLabs: {e}")
                    import traceback

                    traceback.print_exc()
                if self._socket.close_code:
                    print(
                        f"DEBUG: ElevenLabs socket closed with code {self._socket.close_code}"
                    )
                    break

        print(
            f"DEBUG: wait_for_chunks exited. Sent {chunks_sent} total chunks. closed={self._closed}, close_code={self._socket.close_code}"
        )

    async def send_audio(self, pcm_data: np.ndarray):
        """Queue audio data to be sent to ElevenLabs"""
        if not self._closed:
            await self._queue.put(pcm_data)

    async def send_commit(self):
        """Queue a commit signal to be sent to ElevenLabs"""
        if not self._closed:
            await self._queue.put("COMMIT")

    def __aiter__(self):
        return self

    async def __anext__(self) -> Any:
        if self._closed or self._socket.close_code:
            raise StopAsyncIteration
        try:
            return await self._socket.recv()
        except Exception:
            raise StopAsyncIteration

    async def close(self):
        self._closed = True
        try:
            await self._socket.close()
        except Exception:
            pass


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
