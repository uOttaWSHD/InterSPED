from __future__ import annotations

import asyncio
import base64
import orjson
import time
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import quote

from dotenv import load_dotenv
import os

import sounddevice as sd
import soundfile as sf
import numpy as np

from quart import Quart, request, websocket as quartws, jsonify
import aiofiles
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole
from aiortc.rtcrtpreceiver import RemoteStreamTrack

from elevenlabs.client import ElevenLabs
from websockets.asyncio.client import connect

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection
    from sounddevice import CallbackFlags

    from typeshed import HandshakeOpts

load_dotenv()
TOKEN = os.getenv("TOKEN", "")
VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"

SAMPLE_RATE = 16000
CHUNKSIZE = 1024

client = ElevenLabs(api_key=TOKEN)

app = Quart(__name__)

# audio_stream = client.text_to_speech.stream(
#     text="This is a test",
#     voice_id=VOICE_ID,
#     model_id="eleven_multilingual_v2"
# )

# why its bad to do this in frontend
# you'll expose your api key in clientside code

# we're going to stream the audio to the frontend to be played using the browser's builtin tools
# nothing to do with audio_stream for now until the frontend's connected
# just tune a good voice, make it natural

# for user responses we will use speech to text and send the text back to the LLM agent generating the interview
# use websockets

"""
class ElevenLabsStream

async for msg in stream(config):
    - iterator yields websocket messages from elevenlabs
    - note for use: if you encounter a committed transcription, stream that back to the api caller

problem is we have to support both sending a whole complete audio to it, as well as streaming audio to it

async def send(audio): sends a packet of audio to elevenlabs
- okay problem: this audio can wildy vary in format, sampling rate, bit depth
                we have to convert it into a common format


"""

def query(params: dict[str, Any]) -> str:
    def fmt_item(kv):
        k, v = kv
        return f"{quote(k)}={quote(str(v))}"

    return f"?{'&'.join(map(fmt_item, params.items()))}"

async def send_as_json(socket: ClientConnection, obj: Any):
    await socket.send(orjson.dumps(obj).decode("utf-8"))

async def record_chunks(queue: asyncio.Queue):
    loop = asyncio.get_running_loop()

    def callback(indata: np.ndarray[np.dtype[np.float32]], frames: int, time: Any, status: CallbackFlags):
        if status:
            print("STATUS:", status)

        if queue.full():
            chunks = []
            while not queue.empty():
                chunk = queue.get_nowait()

                audio_pcm16 = (chunk * 32767).astype(np.int16)

                chunks.append(audio_pcm16)
            if chunks:
                aud = np.vstack(chunks)
                sf.write('output.wav', aud, SAMPLE_RATE, subtype='PCM_16')

            event.set()
        else:
            # copy because indata is reused by sounddevice
            loop.call_soon_threadsafe(queue.put_nowait, indata.copy())

    event = asyncio.Event()
    # when the audio is being streamed from the frontend we will NOT be using sounddevice to record
    # i'm not sure what the format of that audio data will look like
    # but this code will probably have to change
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=CHUNKSIZE,
        dtype="float32",
        callback=callback,
        device=5
    ):
        await event.wait()  # run forever

def chunk_to_b64(chunk: np.ndarray[np.dtype[np.int16]]) -> str:
    return base64.b64encode(chunk.tobytes()).decode("utf8")

async def open_connection(chunk_queue: asyncio.Queue):
    stop = False

    async def log_messages(socket: ClientConnection):
        nonlocal stop
        while not socket.close_code:
            msg = await socket.recv()
            d = orjson.loads(msg)
            print(msg)
            if d["message_type"] == "partial_transcript" and "stop" in d["text"]:
                stop = True
                return

    params = {
        "model_id": "scribe_v2_realtime",
        "commit_strategy": "vad",
        "vad_silence_threshold_secs": 3,
        "vad_threshold": 0.7
    }

    headers = {
        "xi-api-key": TOKEN,
    }

    async with connect(
        f"wss://api.elevenlabs.io/v1/speech-to-text/realtime" + query(params),
        additional_headers=headers
    ) as socket:
        task = asyncio.create_task(log_messages(socket))
        while not stop:
            chunks = []
            while not chunk_queue.empty():
                chunk = chunk_queue.get_nowait()
                audio_pcm16 = (chunk * 32767).astype(np.int16)
                chunks.append(audio_pcm16)
            if not chunks:
                await asyncio.sleep(1)
                continue

            aud = np.vstack(chunks)

            m = {
                "message_type": "input_audio_chunk",
                "sample_rate": 16000,
                "audio_base_64": chunk_to_b64(aud)
            }

            await send_as_json(socket, m)

        task.exception()

async def test_open_connection(chunk_queue: asyncio.Queue):
    while True:
        chunk = await chunk_queue.get()
        audio_pcm16 = (chunk * 32767).astype(np.int16)
        rms = np.sqrt(np.mean(audio_pcm16**2))
        print(f"Audio level: {rms:.4f}, Queue length: {chunk_queue.qsize()}")

class ElevenLabsSTTStream:
    def __init__(self, socket: ClientConnection):
        self._socket = socket
        self._queue = asyncio.Queue
        self._closed = False

    @classmethod
    async def open_ws(cls, config: HandshakeOpts) -> Self:
        headers = {
            "xi-api-key": config["token"]
        }
        del config["token"]

        socket = await connect(
            f"wss://api.elevenlabs.io/v1/speech-to-text/realtime" + query(config),
            additional_headers=headers
        )

        self = cls(socket)
        return self

    async def wait_for_chunks(self):
        while not self._closed:
            chunks = []
            while not self._queue.empty():
                chunk = self.queue.get_nowait()
                audio_pcm16 = (chunk * 32767).astype(np.int16)
                chunks.append(audio_pcm16)
            if not chunks:
                await asyncio.sleep(1)
                continue

            aud = np.vstack(chunks)

            m = {
                "message_type": "input_audio_chunk",
                "sample_rate": 16000,
                "audio_base_64": chunk_to_b64(aud)
            }

            await self._send_as_json(self._socket, m)

    async def _send_as_json(self, obj: Any):
        await self._socket.send(orjson.dumps(obj).decode("utf-8"))

    async def send(self, data: np.ndarray[np.dtype[np.float32]]):
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(self._queue.put_nowait, data.copy())

    def __aiter__(self):
        return self

    async def __anext__(self) -> Any:
        if self._closed or self._socket.close_code:
            raise StopAsyncIteration

        msg = await self._socket.recv()
        return msg

    async def close(self):
        await self._socket.close()
        self._closed = True

opts = {
    "token": TOKEN,
    "model_id": "scribe_v2_realtime",
    "commit_strategy": "vad",
    "vad_silence_threshold_secs": 3,
    "vad_threshold": 0.7
}

@app.websocket("/receive")
async def ws_handler():
    args = quartws.args
    sample_rate = int(args["sampleRate"])

    els = await ElevenLabsSTTStream.open_ws(opts)
    print("Client connected")

    async def read_from_mic():
        chunks = []
        rn = time.monotonic()
        while True:
            import resampy
            msg = await quartws.receive()
            # Decode Base64 → int16
            audio_bytes = base64.b64decode(msg)
            pcm16 = np.frombuffer(audio_bytes, dtype=np.int16)
            pcm16_16k = resampy.resample(pcm16.astype(float)/32767, sample_rate, 16000)
            pcm16_16k = (pcm16_16k * 32767).astype(np.int16)
            rms = np.sqrt(np.mean(pcm16_16k**2))
            print(f"Audio level: {rms:.4f}")
            chunks.append(pcm16_16k)
            if time.monotonic() - rn >= 1 and chunks:
                aud = np.vstack(chunks)
                m = {
                    "message_type": "input_audio_chunk",
                    "sample_rate": 16000,
                    "audio_base_64": chunk_to_b64(aud)
                }
                await els._socket.send(orjson.dumps(m).decode("utf-8"))

    async def recieve_from_11labs():
        async for msg in els:
            print(msg)
            await quartws.send(msg)

    try:
        await asyncio.gather(
            read_from_mic(),
            recieve_from_11labs()
        )
    except asyncio.CancelledError:
        await els.close()
        print("Client disconnected")

@app.route("/")
async def endpoint_home():
    async with aiofiles.open("./index.html", "r") as f:
        content = await f.read()
    return content

if __name__ == "__main__":
    app.run(port=3000)
