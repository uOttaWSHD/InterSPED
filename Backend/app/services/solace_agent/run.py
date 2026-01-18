#!/usr/bin/env python3
"""
FastAPI for Interview Simulator
Interacts with Solace Agent Mesh to conduct mock interviews
Starts SAM automatically on startup
"""

import sys
import os
import json
import time
import httpx
import subprocess
import asyncio
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.solace_service import (
    start_sam,
    stop_sam,
    wait_for_sam_ready,
    start_sam_with_rotation,
    send_to_solace as shared_send_to_solace,
    build_system_context,
    get_turn_instruction,
)

# Configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
AGENT_NAME = "OrchestratorAgent"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Session storage (in production, use Redis or a database)
sessions: dict = {}


# Pydantic models for incoming company data
class CodingProblem(BaseModel):
    title: str = ""
    difficulty: str = "medium"
    problem_statement: str = ""
    example_input: str = ""
    example_output: str = ""
    constraints: list[str] = []
    leetcode_number: int = 0
    leetcode_url: str = ""
    topics: list[str] = []
    approach_hints: list[str] = []
    optimal_time_complexity: str = ""
    optimal_space_complexity: str = ""
    frequency: str = "common"
    company_specific_notes: str = ""


class CommonQuestion(BaseModel):
    question: str = ""
    category: str = "behavioral"
    difficulty: str = "medium"
    tips: str = ""
    sample_answer: str = ""
    key_points_to_cover: list[str] = []
    follow_up_questions: list[str] = []
    red_flags: list[str] = []
    company_specific_context: str = ""


class SystemDesignQuestion(BaseModel):
    question: str = ""
    scope: str = ""
    key_components: list[str] = []
    evaluation_criteria: list[str] = []
    common_approaches: list[str] = []
    follow_up_topics: list[str] = []
    time_allocation: str = ""


class MockScenario(BaseModel):
    scenario_title: str = ""
    stage: str = ""
    duration: str = ""
    opening: str = ""
    questions_sequence: list[str] = []
    expected_flow: str = ""
    closing: str = ""
    time_for_candidate_questions: bool = True
    good_questions_to_ask: list[str] = []


class InterviewStage(BaseModel):
    stage_name: str = ""
    description: str = ""
    duration: str = ""
    format: str = ""
    interviewers: str = ""
    focus_areas: list[str] = []
    sample_questions: list[str] = []
    success_criteria: list[str] = []
    preparation_strategy: str = ""


class InterviewProcess(BaseModel):
    stages: list[InterviewStage] = []
    total_duration: str = ""
    preparation_tips: list[str] = []


class TechnicalRequirements(BaseModel):
    programming_languages: list[str] = []
    frameworks_tools: list[str] = []
    concepts: str = ""
    experience_level: str = ""
    must_have_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    domain_knowledge: list[str] = []


class InterviewInsights(BaseModel):
    common_questions: list[CommonQuestion] = []
    coding_problems: list[CodingProblem] = []
    system_design_questions: list[SystemDesignQuestion] = []
    mock_scenarios: list[MockScenario] = []
    interview_process: Optional[InterviewProcess] = None
    technical_requirements: Optional[TechnicalRequirements] = None
    what_they_look_for: list[str] = []
    red_flags_to_avoid: list[str] = []
    salary_range: str = ""
    company_values_in_interviews: list[str] = []


class CompanyOverview(BaseModel):
    name: str = ""
    industry: str = ""
    size: str = ""
    headquarters: str = ""
    mission: str = ""
    culture: str = ""
    recent_news: list[str] = []


class StartRequest(BaseModel):
    success: bool = True
    company_overview: Optional[CompanyOverview] = None
    interview_insights: Optional[InterviewInsights] = None
    sources: list[str] = []
    session_id: str = ""
    metadata: dict = {}


# Response models
class RespondRequest(BaseModel):
    session_id: str
    text: str


class SummaryRequest(BaseModel):
    session_id: str


class StartResponse(BaseModel):
    session_id: str
    response: str
    turn: int
    interview_complete: bool


class RespondResponse(BaseModel):
    session_id: str
    response: str
    turn: int
    interview_complete: bool


class SummaryResponse(BaseModel):
    summary: str
    transcript: str


class StatusResponse(BaseModel):
    session_id: str
    turn: int
    max_turns: int
    interview_complete: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage SAM lifecycle with FastAPI"""
    # Startup
    await start_sam_with_rotation()
    yield
    # Shutdown
    stop_sam()


app = FastAPI(title="Interview Simulator API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/interview/start", response_model=StartResponse)
async def start_interview(company_data: StartRequest):
    """Start a new interview session with company context"""
    session_id = f"session_{int(time.time() * 1000)}"
    print(company_data)
    # Get company name for the greeting
    company_name = "the company"
    if company_data.company_overview and company_data.company_overview.name:
        company_name = company_data.company_overview.name

    # Build the initial message with company context
    system_context = build_system_context(company_data)

    message = f"""[SYSTEM CONTEXT]
{system_context}

[START INTERVIEW - Introduce yourself as Rachel from {company_name} and ask about their background]"""

    # Send to Solace
    response_text, context_id, error = await shared_send_to_solace(
        message, session_id=session_id
    )

    if error:
        raise HTTPException(status_code=500, detail=error)

    if not response_text:
        # Fallback opening
        response_text = f"Hello, my name is Rachel and I'm a senior engineer at {company_name}. Thanks for joining me today. Can you start by telling me a little about your background and experience?"

    # Store session with company data for later turns
    sessions[session_id] = {
        "context_id": context_id,
        "turn_count": 0,
        "transcript": f"Interviewer: {response_text}",
        "max_turns": 3,
        "company_data": company_data.model_dump(),  # Store for use in respond
    }

    return StartResponse(
        session_id=session_id, response=response_text, turn=0, interview_complete=False
    )


@app.post("/api/interview/respond", response_model=RespondResponse)
async def respond_to_interview(data: RespondRequest):
    """Send a response to the interviewer"""
    session_id = data.session_id
    user_input = data.text.strip()

    if session_id not in sessions:
        raise HTTPException(
            status_code=404, detail="Invalid session_id. Start a new interview first."
        )

    if not user_input:
        raise HTTPException(status_code=400, detail="text is required")

    session = sessions[session_id]

    # Check if interview is already complete
    if session["turn_count"] >= session["max_turns"]:
        raise HTTPException(
            status_code=400,
            detail="Interview is complete. Call /api/interview/summary to get feedback.",
        )

    # Increment turn count
    session["turn_count"] += 1
    turn = session["turn_count"]

    # Rebuild company data from session
    company_data = StartRequest(**session["company_data"])

    # Build the message with company context
    system_context = build_system_context(company_data)
    turn_instruction = get_turn_instruction(turn, company_data)

    message = f"""[SYSTEM CONTEXT]
{system_context}

[Turn {turn} of 3]
User said: {user_input}

INSTRUCTIONS:
- If the user answered the question: ACKNOWLEDGE what they said, then {turn_instruction}
- If the user asked a question or needs clarification: ANSWER them clearly. Do NOT move to the next stage yet.
- Keep response concise."""

    # Send to Solace
    response_text, new_context_id, error = await shared_send_to_solace(
        message, context_id=session["context_id"], session_id=session_id
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


@app.post("/api/interview/summary", response_model=SummaryResponse)
async def get_interview_summary(data: SummaryRequest):
    """Get summary of the interview"""
    session_id = data.session_id

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    session = sessions[session_id]
    transcript = session["transcript"]

    # Build summary request with full transcript
    message = f"""Here is the complete interview transcript. Please provide accurate feedback based on what actually happened:

--- TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Based on this transcript, give a brief spoken summary. Be honest about the candidate's actual performance."""

    # Send to SummaryAgent
    response_text, _, error = await shared_send_to_solace(
        message,
        context_id=session["context_id"],
        agent_name="SummaryAgent",
        session_id=session_id,
    )

    if error:
        raise HTTPException(status_code=500, detail=error)

    # Clean up session
    del sessions[session_id]

    return SummaryResponse(
        summary=response_text or "Could not generate summary", transcript=transcript
    )


@app.get("/api/interview/status", response_model=StatusResponse)
async def get_status(session_id: str = Query(..., description="The session ID")):
    """Get status of a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    session = sessions[session_id]

    return StatusResponse(
        session_id=session_id,
        turn=session["turn_count"],
        max_turns=session["max_turns"],
        interview_complete=session["turn_count"] >= session["max_turns"],
    )


@app.get("/health")
async def health_check_endpoint():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
