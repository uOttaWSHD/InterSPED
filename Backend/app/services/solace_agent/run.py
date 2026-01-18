#!/usr/bin/env python3
"""
FastAPI for Interview Simulator
Interacts with Solace Agent Mesh to conduct mock interviews
Starts SAM automatically on startup
"""

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

# Configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
AGENT_NAME = "OrchestratorAgent"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# SAM process reference
sam_process: Optional[subprocess.Popen] = None


async def wait_for_sam_ready(timeout: int = 60) -> bool:
    """Wait for SAM gateway to be ready"""
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{GATEWAY_URL}/health", timeout=2.0)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False


def start_sam():
    """Start SAM as a subprocess"""
    global sam_process
    
    print("🚀 Starting Solace Agent Mesh...")
    
    # Start SAM using uv run
    sam_process = subprocess.Popen(
        ["uv", "run", "sam", "run", "configs/"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid  # Create new process group for clean shutdown
    )
    
    return sam_process


def stop_sam():
    """Stop SAM subprocess"""
    global sam_process
    
    if sam_process:
        print("🛑 Stopping Solace Agent Mesh...")
        try:
            # Kill the entire process group
            os.killpg(os.getpgid(sam_process.pid), signal.SIGTERM)
            sam_process.wait(timeout=10)
        except Exception as e:
            print(f"Error stopping SAM: {e}")
            try:
                os.killpg(os.getpgid(sam_process.pid), signal.SIGKILL)
            except Exception:
                pass
        sam_process = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage SAM lifecycle with FastAPI"""
    # Startup
    start_sam()
    
    print("⏳ Waiting for SAM gateway to be ready...")
    if await wait_for_sam_ready():
        print("✅ SAM gateway is ready!")
    else:
        print("⚠️  SAM gateway may not be fully ready, continuing anyway...")
    
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

# Configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
AGENT_NAME = "OrchestratorAgent"

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


def build_system_context(company_data: StartRequest) -> str:
    """Build dynamic system prompt from company data"""
    overview = company_data.company_overview or CompanyOverview()
    insights = company_data.interview_insights or InterviewInsights()
    tech_reqs = insights.technical_requirements or TechnicalRequirements()
    
    company_name = overview.name or "the company"
    industry = overview.industry or "technology"
    
    # Build tech stack string
    tech_stack = ", ".join(tech_reqs.programming_languages[:5]) if tech_reqs.programming_languages else "various technologies"
    frameworks = ", ".join(tech_reqs.frameworks_tools[:5]) if tech_reqs.frameworks_tools else ""
    
    # Build focus areas from what they look for
    focus_areas = ", ".join(insights.what_they_look_for[:5]) if insights.what_they_look_for else "technical skills, problem-solving"
    
    # Get sample questions to guide the interview
    behavioral_qs = [q.question for q in insights.common_questions[:2]] if insights.common_questions else []
    system_design_qs = [q.question for q in insights.system_design_questions[:2]] if insights.system_design_questions else []
    coding_problems = [f"{p.title}: {p.problem_statement[:100]}" for p in insights.coding_problems[:2]] if insights.coding_problems else []
    
    # Build context string
    context = f"""Company: {company_name}
Industry: {industry}
Culture: {overview.culture or 'Professional and innovative'}
Tech Stack: {tech_stack}
Frameworks/Tools: {frameworks}
Focus Areas: {focus_areas}
Experience Level: {tech_reqs.experience_level or 'varies'}

Company Values: {', '.join(insights.company_values_in_interviews[:3]) if insights.company_values_in_interviews else 'excellence, teamwork, innovation'}

Sample Behavioral Questions to Draw From:
{chr(10).join(f'- {q}' for q in behavioral_qs) if behavioral_qs else '- Tell me about yourself'}

Sample System Design Topics:
{chr(10).join(f'- {q}' for q in system_design_qs) if system_design_qs else '- Design a scalable system'}

Sample Coding Topics:
{chr(10).join(f'- {p}' for p in coding_problems) if coding_problems else '- Data structures and algorithms'}

Red Flags to Probe For:
{', '.join(insights.red_flags_to_avoid[:3]) if insights.red_flags_to_avoid else 'lack of preparation, poor communication'}

You are John, a senior engineer interviewing a candidate for a role at {company_name}. Be natural and conversational."""
    
    return context


def get_turn_instruction(turn: int, company_data: StartRequest) -> str:
    """Get instruction for specific turn based on company data"""
    insights = company_data.interview_insights or InterviewInsights()
    
    # Try to get actual questions from the data
    behavioral_q = insights.common_questions[0].question if insights.common_questions else None
    system_design_q = insights.system_design_questions[0].question if insights.system_design_questions else None
    coding_q = f"a coding question about {insights.coding_problems[0].title}" if insights.coding_problems else None
    
    instructions = {
        1: f"ASK about: {behavioral_q or 'their experience with a challenging project'}. MAX 2 sentences.",
        2: f"ASK about: {system_design_q or 'how they would design a scalable system'}. MAX 2 sentences.",
        3: "SAY GOODBYE. Thank them for their time and say you'll be in touch. MAX 2 sentences."
    }
    return instructions.get(turn, "SAY GOODBYE.")


async def send_to_solace(message: str, context_id: Optional[str] = None, agent_name: str = AGENT_NAME) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Send message to Solace Agent Mesh and get response"""
    request_id = int(time.time() * 1000)
    msg_id = f"msg_{request_id}"
    
    # Build payload
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/stream",
        "params": {
            "message": {
                "messageId": msg_id,
                "kind": "message",
                "role": "user",
                "metadata": {"agent_name": agent_name},
                "parts": [{"kind": "text", "text": message}]
            }
        }
    }
    
    if context_id:
        payload["params"]["contextId"] = context_id
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Submit the message and get task ID
        try:
            submit_response = await client.post(
                f"{GATEWAY_URL}/api/v1/message:stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            submit_data = submit_response.json()
        except Exception as e:
            return None, context_id, f"Error submitting message: {e}"
        
        task_id = submit_data.get("result", {}).get("id")
        new_context_id = submit_data.get("result", {}).get("contextId", context_id)
        
        if not task_id:
            return None, new_context_id, "Could not get task ID"
        
        # Step 2: Subscribe to SSE events for this task
        try:
            async with client.stream(
                "GET",
                f"{GATEWAY_URL}/api/v1/sse/subscribe/{task_id}",
                headers={"Accept": "text/event-stream"}
            ) as sse_response:
                full_text = ""
                async for line in sse_response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    
                    json_data = line[5:].strip()  # Remove "data:" prefix
                    try:
                        event_data = json.loads(json_data)
                        state = event_data.get("result", {}).get("status", {}).get("state")
                        
                        if state == "completed":
                            parts = event_data.get("result", {}).get("status", {}).get("message", {}).get("parts", [])
                            for part in parts:
                                if part.get("kind") == "text":
                                    full_text = part.get("text", "")
                                    break
                            break
                    except json.JSONDecodeError:
                        continue
                
                return full_text, new_context_id, None
            
        except Exception as e:
            return None, new_context_id, f"Error reading SSE stream: {e}"


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

[START INTERVIEW - Introduce yourself as John from {company_name} and ask about their background]"""
    
    # Send to Solace
    response_text, context_id, error = await send_to_solace(message)
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    if not response_text:
        # Fallback opening
        response_text = f"Hello, my name is John and I'm a senior engineer at {company_name}. Thanks for joining me today. Can you start by telling me a little about your background and experience?"
    
    # Store session with company data for later turns
    sessions[session_id] = {
        "context_id": context_id,
        "turn_count": 0,
        "transcript": f"Interviewer: {response_text}",
        "max_turns": 3,
        "company_data": company_data.model_dump()  # Store for use in respond
    }
    
    return StartResponse(
        session_id=session_id,
        response=response_text,
        turn=0,
        interview_complete=False
    )


@app.post("/api/interview/respond", response_model=RespondResponse)
async def respond_to_interview(data: RespondRequest):
    """Send a response to the interviewer"""
    session_id = data.session_id
    user_input = data.text.strip()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Invalid session_id. Start a new interview first.")
    
    if not user_input:
        raise HTTPException(status_code=400, detail="text is required")
    
    session = sessions[session_id]
    
    # Check if interview is already complete
    if session["turn_count"] >= session["max_turns"]:
        raise HTTPException(
            status_code=400, 
            detail="Interview is complete. Call /api/interview/summary to get feedback."
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

ACKNOWLEDGE what they said, then: {turn_instruction}"""
    
    # Send to Solace
    response_text, new_context_id, error = await send_to_solace(
        message, 
        context_id=session["context_id"]
    )
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Update session
    session["context_id"] = new_context_id
    
    # Remove [INTERVIEW_COMPLETE] marker if present
    if response_text:
        response_text = response_text.replace("[INTERVIEW_COMPLETE]", "").strip()
    
    # Update transcript
    session["transcript"] += f"\n\nCandidate: {user_input}\n\nInterviewer: {response_text}"
    
    interview_complete = turn >= session["max_turns"]
    
    return RespondResponse(
        session_id=session_id,
        response=response_text or "(No response received)",
        turn=turn,
        interview_complete=interview_complete
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
    response_text, _, error = await send_to_solace(
        message,
        context_id=session["context_id"],
        agent_name="SummaryAgent"
    )
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Clean up session
    del sessions[session_id]
    
    return SummaryResponse(
        summary=response_text or "Could not generate summary",
        transcript=transcript
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
        interview_complete=session["turn_count"] >= session["max_turns"]
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
