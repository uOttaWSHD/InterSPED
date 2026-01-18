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

from app.utils.key_manager import get_key

router = APIRouter()

# Debug: Log if keys are available
available_keys = get_key("ELEVENLABS_API_KEY")
if available_keys:
    print(f"[voice.py] ElevenLabs API keys found")
else:
    print("[voice.py] WARNING: ELEVENLABS_API_KEY not found in environment!")


@router.get("/api/voice/tts")
async def tts_endpoint(text: str):
    """Proxy TTS requests to ElevenLabs via our service"""
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        b64_audio = await generate_tts(
            text
        )  # No session id for generic TTS endpoint usually, or we can use a dummy
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
        # Based on official docs: commit_strategy="manual" ensures we only commit when the user mutes
        session_token = get_key("ELEVENLABS_API_KEY", session_id)
        els = await ElevenLabsSTTStream.open_ws(
            {
                "token": session_token,
                "audio_format": "pcm_16000",
                "commit_strategy": "manual",
                # "vad_silence_threshold_secs": 2.0,  <-- Disabled to remove "waiting for silence"
                # "vad_threshold": 0.4,
                # "min_speech_duration_ms": 250,
                # "min_silence_duration_ms": 500,
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

    # Buffers for "Mic State" logic
    buffered_transcript = ""  # Stores completed sentences while mic is still on
    current_partial = ""  # Stores the current incomplete sentence

    # State management for handling interruptions
    current_processing_task: asyncio.Task | None = None
    interrupt_event = asyncio.Event()

    # Synchronization for manual commit
    # transcript_committed_event = asyncio.Event()  <-- Removing this blocking event

    # Flag to track if we are waiting for a commit to complete
    is_waiting_for_commit = False

    async def handle_final_transcript(transcript: str):
        nonlocal \
            last_transcript, \
            is_completed, \
            current_processing_task, \
            is_waiting_for_commit

        # Reset commit flag since we are handling it
        is_waiting_for_commit = False

        clean_text = transcript.strip()
        if not clean_text:
            return

        # Deduplication: Prevent technical double-sends, but allow repeats in new context
        if clean_text == last_transcript:
            print(f"DEBUG: Skipping duplicate transcript: '{clean_text[:20]}...'")
            return

        last_transcript = clean_text
        print(f"User (Final Input): {clean_text}")

        # Echo back to user
        await websocket.send_text(
            orjson.dumps({"type": "transcript", "text": clean_text}).decode("utf-8")
        )

        # Get session
        session = session_service.get_session(session_id)
        if not session:
            print(f"Session {session_id} not found")
            return

        # Check turn limit
        if session["turn_count"] >= session["max_turns"]:
            if not is_completed:
                is_completed = True
                try:
                    end_text = "The interview is now complete. Thank you for your time."
                    b64_audio = await generate_tts(end_text, session_id=session_id)

                    await websocket.send_text(
                        orjson.dumps(
                            {
                                "type": "audio",
                                "audio": b64_audio,
                                "text": end_text,
                            }
                        ).decode("utf-8")
                    )
                except Exception:
                    pass
            return

        # Increment turn
        turn = session_service.increment_turn(session_id)
        if turn is None:
            return

        company_data = StartRequest(**session["company_data"])

        # Start new processing task
        interrupt_event.clear()
        current_processing_task = asyncio.create_task(
            process_user_turn(clean_text, turn, company_data, session_id)
        )

    async def read_from_ws():
        nonlocal \
            audio_chunk_count, \
            current_partial, \
            buffered_transcript, \
            is_waiting_for_commit
        try:
            while True:
                msg = await websocket.receive()

                # Check for commit signal
                if "text" in msg:
                    try:
                        text_data = msg["text"]
                        # Try to parse as JSON first (for control messages)
                        if text_data.startswith("{"):
                            try:
                                json_msg = orjson.loads(text_data)
                                if json_msg.get("type") == "commit":
                                    print(
                                        "DEBUG: Received manual commit signal (Mic Muted)"
                                    )

                                    # Set the flag to indicate we expect a final transcript shortly
                                    is_waiting_for_commit = True

                                    # Tell ElevenLabs to commit immediately (this now sends silence+commit)
                                    await els.send_commit()

                                    # We do NOT wait here. We rely on receive_from_els to trigger handle_final_transcript
                                    print(
                                        "DEBUG: Commit sent. Waiting for async response..."
                                    )
                                    continue
                            except Exception as e:
                                print(f"JSON Parse Error: {e}")

                    except Exception:
                        pass

                    # If not JSON, assume base64 audio
                    data = msg["text"]
                    audio_bytes = base64.b64decode(data)

                elif "bytes" in msg:
                    audio_bytes = msg["bytes"]
                else:
                    continue

                pcm16 = np.frombuffer(audio_bytes, dtype=np.int16)
                if len(pcm16) == 0:
                    continue

                # INTERRUPTION LOGIC:
                # If the user sends audio (speaks) while the AI is processing/speaking, cancel the AI.
                if (
                    current_processing_task
                    and not current_processing_task.done()
                    and not interrupt_event.is_set()
                ):
                    print("DEBUG: Interruption detected! User started speaking.")
                    interrupt_event.set()
                    current_processing_task.cancel()

                    # Notify frontend to stop playback
                    try:
                        await websocket.send_text(
                            orjson.dumps({"type": "interrupt"}).decode("utf-8")
                        )
                    except Exception as e:
                        print(f"Failed to send interrupt signal: {e}")

                audio_chunk_count += 1
                if audio_chunk_count <= 5 or audio_chunk_count % 100 == 0:
                    rms = np.sqrt(np.mean(pcm16.astype(np.float32) ** 2))
                    print(
                        f"DEBUG: Audio chunk #{audio_chunk_count}, samples: {len(pcm16)}, RMS: {rms:.1f}"
                    )

                pcm_float = pcm16.astype(np.float32) / 32767.0
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

    # ... process_user_turn defined below ...

    async def process_user_turn(
        transcript: str, turn: int, company_data: StartRequest, session_id: str
    ):
        nonlocal last_transcript
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

            # Get recent history (last 2000 chars to fit in context)
            full_history = session.get("transcript", "") if session else ""
            recent_history = (
                full_history[-2000:] if len(full_history) > 2000 else full_history
            )

            message = f"""[SYSTEM CONTEXT]
{system_context}

[CONVERSATION HISTORY]
...
{recent_history}

[Turn {turn}]
User said: {transcript}

[CURRENT PHASE & GOAL]
{turn_instruction}

[RESPONSE GUIDELINES]
1. PRIORITIZE the user's immediate input (questions, checks, or concerns).
2. CHECK HISTORY: Did the user answer the LAST question asked by the Interviewer?
   - IF NO: Acknowledge their input, then GENTLY steer them back to the unanswered question. Do NOT jump to the [CURRENT PHASE & GOAL] yet.
   - IF YES (or if it was just small talk): Proceed to [CURRENT PHASE & GOAL].
3. Keep it conversational and professional.
"""

            print(f"Sending message to Solace for turn {turn}...")

            # Send to Solace (This is the long-running "thinking" part)
            response_text, new_context_id, error = await send_to_solace(
                message, context_id=context_id, session_id=session_id
            )

            # Check for interruption again after "thinking"
            if interrupt_event.is_set():
                print(
                    f"DEBUG: Task cancelled after Solace response for: '{transcript[:20]}...'"
                )
                return

            if error:
                print(f"❌ [Voice Turn] Solace Error: {error}")
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

            # Reset deduplication state so user can repeat themselves in the next turn
            last_transcript = None

            # Generate TTS
            try:
                b64_audio = await generate_tts(response_text, session_id=session_id)

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
        except Exception:
            print(f"❌ Error in process_user_turn:")
            import traceback

            traceback.print_exc()

            # Inform user of error
            try:
                error_msg = "I'm having trouble connecting to my brain right now. Please try again."
                await websocket.send_text(
                    orjson.dumps({"type": "text", "text": error_msg}).decode("utf-8")
                )
            except:
                pass

    async def receive_from_els():
        nonlocal current_partial, buffered_transcript
        try:
            async for msg in els:
                data = orjson.loads(msg)
                msg_type = data.get("message_type")

                # Handle session_started message
                if msg_type == "session_started":
                    print(
                        f"ELS: Session started with config: {data.get('config', {}).get('model_id')}"
                    )
                    continue

                    # Handle committed_transcript
                if msg_type == "committed_transcript":
                    transcript = data.get("text", "").strip()
                    if transcript:
                        print(f"DEBUG: Buffering committed text: '{transcript}'")
                        if buffered_transcript:
                            buffered_transcript += " " + transcript
                        else:
                            buffered_transcript = transcript
                        current_partial = ""  # Reset partial as it is now committed

                        # Send updated COMBINED partial to frontend
                        combined_text = buffered_transcript
                        await websocket.send_text(
                            orjson.dumps(
                                {"type": "partial", "text": combined_text}
                            ).decode("utf-8")
                        )

                        # CRITICAL: If we were waiting for a commit (User Muted), process immediately
                        if is_waiting_for_commit:
                            print(
                                f"DEBUG: Commit completed by event. Final text: {buffered_transcript}"
                            )
                            await handle_final_transcript(buffered_transcript)
                            # Reset buffers
                            buffered_transcript = ""
                            current_partial = ""

                # Handle partial_transcript
                elif msg_type == "partial_transcript":
                    text = data.get("text", "")
                    if text:
                        current_partial = text

                        # Send updated COMBINED partial to frontend
                        # Combine buffered (previous sentences) + current partial (current sentence)
                        combined_text = (
                            f"{buffered_transcript} {current_partial}".strip()
                        )

                        await websocket.send_text(
                            orjson.dumps(
                                {"type": "partial", "text": combined_text}
                            ).decode("utf-8")
                        )

        except Exception as e:
            print(f"ELS Receive Error: {e}")

            import traceback

            traceback.print_exc()

    try:
        # Run tasks. If wait_for_chunks exits (e.g. connection closed), we want to know.
        # But we also want to keep reading from the client if possible?
        # No, if ELs closes, we can't do anything useful.

        chunk_task = asyncio.create_task(els.wait_for_chunks())
        read_task = asyncio.create_task(read_from_ws())
        recv_task = asyncio.create_task(receive_from_els())

        done, pending = await asyncio.wait(
            [chunk_task, read_task, recv_task], return_when=asyncio.FIRST_COMPLETED
        )

        print(f"DEBUG: Main loop finished. Done tasks: {[t.get_name() for t in done]}")

        # If wait_for_chunks finished, it means ELs closed.
        if chunk_task in done:
            print("DEBUG: wait_for_chunks exited early. Cancelling other tasks.")

        # Cancel any pending tasks to ensure clean shutdown
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        print(f"Handler Error: {e}")
    finally:
        await els.close()
        print("Disconnected")
