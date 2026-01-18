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

# Debug: Log if token is loaded
if TOKEN:
    print(f"[voice.py] ElevenLabs API Key loaded: {TOKEN[:10]}...{TOKEN[-4:]}")
else:
    print("[voice.py] WARNING: ELEVENLABS_API_KEY not found in environment!")


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
        # ElevenLabs Scribe STT parameters
        # Based on official docs: vad_silence_threshold_secs (float), model_id is optional
        els = await ElevenLabsSTTStream.open_ws(
            {
                "token": TOKEN,
                "audio_format": "pcm_16000",  # Tell ElevenLabs we're sending 16kHz PCM
                "commit_strategy": "vad",
                "vad_silence_threshold_secs": 1.2,  # INCREASED from 1.0 to 1.2 for less cutting off
                "vad_threshold": 0.35,  # INCREASED from 0.3 to 0.35 to ignore background noise
                "min_speech_duration_ms": 150,  # INCREASED from 100 to 150 to ignore short bursts
                "min_silence_duration_ms": 400,  # INCREASED from 300 to 400 for better segmentation
            }
        )
        print("DEBUG: ElevenLabs STT connection opened successfully")
    except Exception as e:
        print(f"Failed to connect to ElevenLabs: {e}")
        import traceback

        traceback.print_exc()
        await websocket.close(code=1011)
        return

    audio_chunk_count = 0  # Debug counter
    last_transcript = None  # Deduplication
    is_completed = False  # Track if interview is complete

    # State management for handling interruptions
    current_processing_task: asyncio.Task | None = None
    interrupt_event = asyncio.Event()

    async def read_from_ws():
        nonlocal audio_chunk_count
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

                audio_chunk_count += 1
                # Log first few chunks, then every 100th
                if audio_chunk_count <= 5 or audio_chunk_count % 100 == 0:
                    # Calculate RMS energy for debugging
                    rms = np.sqrt(np.mean(pcm16.astype(np.float32) ** 2))
                    print(
                        f"DEBUG: Audio chunk #{audio_chunk_count}, samples: {len(pcm16)}, RMS: {rms:.1f}"
                    )

                pcm_float = pcm16.astype(np.float32) / 32767.0

                # Only resample if needed
                if sample_rate_src != SAMPLE_RATE_TARGET:
                    pcm_16k = resampy.resample(
                        pcm_float, sample_rate_src, SAMPLE_RATE_TARGET
                    )
                else:
                    pcm_16k = pcm_float

                await els.send_audio(pcm_16k)
        except WebSocketDisconnect:
            print("DEBUG: Browser WebSocket disconnected")
        except Exception as e:
            print(f"WS Read Error: {e}")

    async def process_user_turn(
        transcript: str, turn: int, company_data: StartRequest, session_id: str
    ):
        """
        Process a single turn: Send to Solace, Generate TTS, Send to User.
        This runs in a cancellable task to support interruption.
        """
        try:
            # Check for interruption before starting heavy work
            if interrupt_event.is_set():
                print(
                    f"DEBUG: Task cancelled before Solace call for: '{transcript[:20]}...'"
                )
                return

            system_context = build_system_context(company_data)
            turn_instruction = get_turn_instruction(turn, company_data)

            # Need to get session to access context_id
            session = session_service.get_session(session_id)
            context_id = session.get("context_id") if session else None

            message = f"""[SYSTEM CONTEXT]
{system_context}

[Turn {turn}]
User said: {transcript}

ACKNOWLEDGE what they said briefly, then: {turn_instruction}"""

            print(f"Sending message to Solace for turn {turn}...")

            # Send to Solace (This is the long-running "thinking" part)
            response_text, new_context_id, error = await send_to_solace(
                message, context_id=context_id
            )

            # Check for interruption again after "thinking"
            if interrupt_event.is_set():
                print(
                    f"DEBUG: Task cancelled after Solace response for: '{transcript[:20]}...'"
                )
                return

            if error:
                print(f"Solace Error: {error}")
                response_text = (
                    "I'm sorry, I'm having trouble connecting to my brain right now."
                )

            if not response_text:
                response_text = "I see. Tell me more."

            # Update session state
            session_service.update_session(
                session_id,
                new_context_id or context_id or "",
                transcript,
                response_text,
            )

            # Cleanup response text
            response_text = response_text.replace("[INTERVIEW_COMPLETE]", "").strip()
            print(f"AI: {response_text}")

            # Generate TTS
            try:
                b64_audio = await generate_tts(response_text)

                # Check for interruption before sending audio
                if interrupt_event.is_set():
                    print(
                        f"DEBUG: Task cancelled before sending audio for: '{transcript[:20]}...'"
                    )
                    return

                await websocket.send_text(
                    orjson.dumps(
                        {
                            "type": "audio",
                            "audio": b64_audio,
                            "text": response_text,
                        }
                    ).decode("utf-8")
                )
            except Exception as e:
                print(f"TTS Error: {e}")
                # Fallback to text
                if not interrupt_event.is_set():
                    await websocket.send_text(
                        orjson.dumps(
                            {
                                "type": "text",
                                "text": response_text,
                            }
                        ).decode("utf-8")
                    )

        except asyncio.CancelledError:
            print(f"DEBUG: Processing task cancelled for: '{transcript[:20]}...'")
            raise
        except Exception as e:
            print(f"Error in process_user_turn: {e}")

    async def receive_from_els():
        nonlocal last_transcript, is_completed, current_processing_task
        try:
            async for msg in els:
                data = orjson.loads(msg)
                msg_type = data.get("message_type")
                # print(f"ELS DEBUG: received {msg_type}")

                # Handle session_started message
                if msg_type == "session_started":
                    print(
                        f"ELS: Session started with config: {data.get('config', {}).get('model_id')}"
                    )
                    continue

                # Handle committed_transcript (final transcript with VAD)
                if msg_type == "committed_transcript":
                    transcript = data.get("text", "").strip()
                    if transcript:
                        # Deduplication
                        if transcript == last_transcript:
                            print(
                                f"DEBUG: Skipping duplicate transcript: '{transcript[:20]}...'"
                            )
                            continue

                        # INTERRUPTION LOGIC:
                        # If we receive a new committed transcript, it means the user has finished a new sentence.
                        # If the AI was currently processing a previous sentence (thinking) or speaking,
                        # we want to STOP that and focus on the new input.

                        if (
                            current_processing_task
                            and not current_processing_task.done()
                        ):
                            print(
                                f"DEBUG: Interrupting previous task for new input: '{transcript[:20]}...'"
                            )
                            # 1. Cancel the backend processing task
                            current_processing_task.cancel()
                            interrupt_event.set()

                            # 2. Send interrupt signal to Frontend to stop audio playback immediately
                            await websocket.send_text(
                                orjson.dumps({"type": "interrupt"}).decode("utf-8")
                            )

                            # Wait briefly for cancellation to propagate
                            try:
                                await current_processing_task
                            except asyncio.CancelledError:
                                pass

                            # Reset event for new task
                            interrupt_event.clear()

                        last_transcript = transcript
                        print(f"User (New Input): {transcript}")

                        # Echo back to user
                        await websocket.send_text(
                            orjson.dumps(
                                {"type": "transcript", "text": transcript}
                            ).decode("utf-8")
                        )

                        # Get session
                        session = session_service.get_session(session_id)
                        if not session:
                            print(f"Session {session_id} not found")
                            continue

                        # Check turn limit
                        if session["turn_count"] >= session["max_turns"]:
                            if not is_completed:
                                print("Turn limit reached")
                                is_completed = True
                                # Send completion message
                                try:
                                    end_text = "The interview is now complete. Thank you for your time."
                                    b64_audio = await generate_tts(end_text)
                                    await websocket.send_text(
                                        orjson.dumps(
                                            {
                                                "type": "audio",
                                                "audio": b64_audio,
                                                "text": end_text,
                                            }
                                        ).decode("utf-8")
                                    )
                                except Exception as e:
                                    print(f"Failed to send completion audio: {e}")
                            continue

                        # Increment turn
                        turn = session_service.increment_turn(session_id)
                        if turn is None:
                            continue

                        company_data = StartRequest(**session["company_data"])

                        # Start new processing task
                        interrupt_event.clear()
                        current_processing_task = asyncio.create_task(
                            process_user_turn(
                                transcript, turn, company_data, session_id
                            )
                        )

                # We can also detect "partial_transcript" to trigger interruptions EARLIER
                # e.g., if user starts speaking (partial text appears), we can lower volume or pause AI.
                elif msg_type == "partial_transcript":
                    text = data.get("text", "")
                    if text:
                        # Send partial to frontend
                        await websocket.send_text(
                            orjson.dumps({"type": "partial", "text": text}).decode(
                                "utf-8"
                            )
                        )

                        # OPTIONAL: Aggressive interruption on partials?
                        # For now, let's stick to committed transcripts to avoid false positives.

        except Exception as e:
            print(f"ELS Receive Error: {e}")
            import traceback

            traceback.print_exc()

    try:
        await asyncio.gather(read_from_ws(), receive_from_els(), els.wait_for_chunks())
    except Exception as e:
        print(f"Handler Error: {e}")
    finally:
        await els.close()
        print("Disconnected")
