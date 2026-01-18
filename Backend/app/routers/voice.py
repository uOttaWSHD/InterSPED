from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response
import asyncio
import base64
import orjson
import numpy as np
import resampy
from app.services.voice_service import (
    ElevenLabsSTTStream,
    generate_tts,
    SAMPLE_RATE_TARGET,
)
from app.services import session_service
from app.services.solace_service import (
    build_system_context,
    get_turn_instruction,
    send_to_solace,
)
from app.models.interview import StartRequest
import os

router = APIRouter()

TOKEN = os.getenv("ELEVENLABS_API_KEY", "")


@router.get("/api/voice/tts")
async def tts_endpoint(text: str):
    """Proxy TTS requests to ElevenLabs via our service"""
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        b64_audio = await generate_tts(text)
        audio_data = base64.b64decode(b64_audio)
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    sample_rate_src = int(websocket.query_params.get("sampleRate", 44100))
    session_id = websocket.query_params.get("sessionId")

    print(f"Client connected. SRC: {sample_rate_src}Hz, Session: {session_id}")

    if not session_id:
        print("No session ID provided")
        await websocket.close(code=1008, reason="sessionId required")
        return

    try:
        els = await ElevenLabsSTTStream.open_ws(
            {
                "token": TOKEN,
                "model_id": "scribe_v2_realtime",
                "commit_strategy": "vad",
                "vad_silence_threshold_secs": 1.5,
                "vad_threshold": 0.5,
            }
        )
    except Exception as e:
        print(f"Failed to connect to ElevenLabs: {e}")
        await websocket.close(code=1011)
        return

    async def read_from_ws():
        try:
            while True:
                msg = await websocket.receive()
                if "text" in msg:
                    data = msg["text"]
                    audio_bytes = base64.b64decode(data)
                elif "bytes" in msg:
                    audio_bytes = msg["bytes"]
                else:
                    continue

                pcm16 = np.frombuffer(audio_bytes, dtype=np.int16)
                if len(pcm16) == 0:
                    continue

                pcm_float = pcm16.astype(np.float32) / 32767.0
                pcm_16k = resampy.resample(
                    pcm_float, sample_rate_src, SAMPLE_RATE_TARGET
                )
                await els.send_audio(pcm_16k)
        except WebSocketDisconnect:
            pass  # Client disconnected
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
                        await websocket.send_text(
                            orjson.dumps(
                                {"type": "transcript", "text": transcript}
                            ).decode("utf-8")
                        )

                        # Get session and generate AI response
                        session = session_service.get_session(session_id)
                        if not session:
                            print(f"Session {session_id} not found during voice")
                            continue

                        # Check turn limit
                        if session["turn_count"] >= session["max_turns"]:
                            print("Turn limit reached, no AI response")
                            continue

                        # Increment turn
                        turn = session_service.increment_turn(session_id)
                        if turn is None:
                            print(f"Failed to increment turn for session {session_id}")
                            continue

                        company_data = StartRequest(**session["company_data"])

                        # Build the message for Solace
                        system_context = build_system_context(company_data)
                        turn_instruction = get_turn_instruction(turn, company_data)

                        message = f"""[SYSTEM CONTEXT]
{system_context}

[Turn {turn} of 3]
User said: {transcript}

ACKNOWLEDGE what they said, then: {turn_instruction}"""

                        # Send to Solace
                        response_text, new_context_id, error = await send_to_solace(
                            message, context_id=session["context_id"]
                        )

                        if error:
                            print(f"Solace Error: {error}")
                            continue

                        # Update session
                        session_service.update_session(
                            session_id,
                            new_context_id or "",
                            transcript,
                            response_text or "",
                        )

                        if response_text:
                            response_text = response_text.replace(
                                "[INTERVIEW_COMPLETE]", ""
                            ).strip()
                            print(f"AI: {response_text}")

                            # Generate TTS and send
                            b64_audio = await generate_tts(response_text)
                            await websocket.send_text(
                                orjson.dumps(
                                    {
                                        "type": "audio",
                                        "audio": b64_audio,
                                        "text": response_text,
                                    }
                                ).decode("utf-8")
                            )

                elif data.get("message_type") == "partial_transcript":
                    await websocket.send_text(
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
