from fastapi import APIRouter, HTTPException, Query
import time
from app.models.interview import (
    StartRequest,
    StartResponse,
    RespondRequest,
    RespondResponse,
    SummaryRequest,
    SummaryResponse,
    StatusResponse,
    CompanyOverview,
    InterviewInsights,
)
from app.services.solace_service import (
    build_system_context,
    get_turn_instruction,
    send_to_solace,
)
from app.services import session_service

router = APIRouter()


@router.post("/start", response_model=StartResponse)
async def start_interview(company_data: StartRequest):
    """Start a new interview session with company context"""
    session_id = f"session_{int(time.time() * 1000)}"

    # Get company name for the greeting
    company_name = "the company"
    if company_data.company_overview and company_data.company_overview.name:
        company_name = company_data.company_overview.name

    # Build the initial message with company context
    system_context = build_system_context(company_data)

    message = f"""[SYSTEM CONTEXT]
{system_context}

[START INTERVIEW - Introduce yourself as John from {company_name} and ask about their background]"""

    # Send to Solace
    response_text, context_id, error = await send_to_solace(message)

    if error:
        raise HTTPException(status_code=500, detail=error)

    if not response_text:
        # Fallback opening
        response_text = f"Hello, my name is John and I'm a senior engineer at {company_name}. Thanks for joining me today. Can you start by telling me a little about your background and experience?"

    # Store session with company data for later turns
    session_service.create_session(
        session_id=session_id,
        context_id=context_id or "",
        company_data=company_data.model_dump(),
        response_text=response_text,
    )

    return StartResponse(
        session_id=session_id, response=response_text, turn=0, interview_complete=False
    )


@router.post("/respond", response_model=RespondResponse)
async def respond_to_interview(data: RespondRequest):
    """Send a response to the interviewer"""
    session_id = data.session_id
    user_input = data.text.strip()

    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail="Invalid session_id. Start a new interview first."
        )

    if not user_input:
        raise HTTPException(status_code=400, detail="text is required")

    # Check if interview is already complete
    if session["turn_count"] >= session["max_turns"]:
        raise HTTPException(
            status_code=400,
            detail="Interview is complete. Call /api/interview/summary to get feedback.",
        )

    # Increment turn count
    turn = session_service.increment_turn(session_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Rebuild company data from session
    company_data = StartRequest(**session["company_data"])

    # Build the message with company context
    system_context = build_system_context(company_data)
    turn_instruction = get_turn_instruction(turn, company_data)

    message = f"""[SYSTEM CONTEXT]
{system_context}

[Turn {turn} of 3]
User said: {user_input}

ACKNOWLEDGE what they said, then: {turn_instruction}"""

    # Send to Solace
    response_text, new_context_id, error = await send_to_solace(
        message, context_id=session["context_id"]
    )

    if error:
        raise HTTPException(status_code=500, detail=error)

    # Update session
    session["context_id"] = new_context_id

    # Remove [INTERVIEW_COMPLETE] marker if present
    if response_text:
        response_text = response_text.replace("[INTERVIEW_COMPLETE]", "").strip()

    # Update transcript
    session["transcript"] += (
        f"\n\nCandidate: {user_input}\n\nInterviewer: {response_text}"
    )

    interview_complete = turn >= session["max_turns"]

    return RespondResponse(
        session_id=session_id,
        response=response_text or "(No response received)",
        turn=turn,
        interview_complete=interview_complete,
    )


@router.post("/summary", response_model=SummaryResponse)
async def get_interview_summary(data: SummaryRequest):
    """Get summary of the interview"""
    session_id = data.session_id

    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    transcript = session["transcript"]

    # Build summary request with full transcript
    message = f"""Here is the complete interview transcript. Please provide accurate feedback based on what actually happened:

--- TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Based on this transcript, give a brief spoken summary. Be honest about the candidate's actual performance."""

    # Send to SummaryAgent
    response_text, _, error = await send_to_solace(
        message, context_id=session["context_id"], agent_name="SummaryAgent"
    )

    if error:
        raise HTTPException(status_code=500, detail=error)

    # Clean up session
    session_service.delete_session(session_id)

    return SummaryResponse(
        summary=response_text or "Could not generate summary", transcript=transcript
    )


@router.get("/status", response_model=StatusResponse)
async def get_status(session_id: str = Query(..., description="The session ID")):
    """Get status of a session"""
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    return StatusResponse(
        session_id=session_id,
        turn=session["turn_count"],
        max_turns=session["max_turns"],
        interview_complete=session["turn_count"] >= session["max_turns"],
    )
