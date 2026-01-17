from __future__ import annotations

import asyncio
import base64
import orjson
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import sounddevice as sd
import soundfile as sf
import numpy as np

from elevenlabs.client import ElevenLabs
from websockets.asyncio.client import connect

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection
    from sounddevice import CallbackFlags

VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"
TOKEN = "sk_81e6f0ed55fb3c01bdbd72c980e12c027cd1ac798c9a4d39"

SAMPLE_RATE = 16000
# SAMPLE_RATE = 48000
CHUNKSIZE = 1024

client = ElevenLabs(api_key=TOKEN)

audio_stream = client.text_to_speech.stream(
    text="This is a test",
    voice_id=VOICE_ID,
    model_id="eleven_multilingual_v2"
)

# why its bad to do this in frontend
# you'll expose your api key in clientside code

# we're going to stream the audio to the frontend to be played using the browser's builtin tools
# nothing to do with audio_stream for now until the frontend's connected
# just tune a good voice, make it natural

# for user responses we will use speech to text and send the text back to the LLM agent generating the interview
# use websockets

def query(params: dict[str, Any]) -> str:
    def fmt_item(kv):
        k, v = kv
        return f"{quote(k)}={quote(str(v))}"

    return f"?{'&'.join(map(fmt_item, params.items()))}"

async def send_as_json(socket: ClientConnection, obj: Any):
    await socket.send(orjson.dumps(obj))

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
        while not socket.close_code:
            msg = await socket.recv()
            d = orjson.loads(msg)
            if d["message_type"] == "partial_transcript" and "stop" in d["text"]:
                stop = True
                return

    params = {
        "model_id": "scribe_v2_realtime",
    }

    headers = {
        "xi-api-key": TOKEN,
    }

    async with connect(
        f"wss://api.elevenlabs.io/v1/speech-to-text/realtime" + query(params),
        additional_headers=headers
    ) as socket:
        task = asyncio.create_task(log_messages(socket))
        count = 10
        while not stop:
            chunk = await chunk_queue.get()

            audio_pcm16 = (chunk * 32767).astype(np.int16)

            m = {
                "message_type": "input_audio_chunk",
                "sample_rate": 16000,
                "commit": count == 0,
                "audio_base_64": chunk_to_b64(audio_pcm16)
            }

            await send_as_json(socket, m)
            count += 1
            if count > 1000:
                count = 0

        task.exception()

async def test_open_connection(chunk_queue: asyncio.Queue):
    while True:
        chunk = await chunk_queue.get()
        audio_pcm16 = (chunk * 32767).astype(np.int16)
        rms = np.sqrt(np.mean(audio_pcm16**2))
        print(f"Audio level: {rms:.4f}, Queue length: {chunk_queue.qsize()}")


async def hello():
    audio_chunks = asyncio.Queue()

    await asyncio.gather(
        record_chunks(audio_chunks),
        open_connection(audio_chunks),
    )


if __name__ == "__main__":
    asyncio.run(hello())
