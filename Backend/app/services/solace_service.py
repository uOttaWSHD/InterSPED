import os
import subprocess
import signal
import time
import httpx
import asyncio
import json
from typing import Optional, Tuple
from app.models.interview import (
    StartRequest,
    CompanyOverview,
    InterviewInsights,
    TechnicalRequirements,
)

# Configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
AGENT_NAME = "OrchestratorAgent"
# Path to the solace-agent directory where configs are located
SOLACE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "solace_agent")
)

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

    print(f"🚀 Starting Solace Agent Mesh from {SOLACE_AGENT_DIR}...")

    command = ["sam", "run", "configs/"]

    try:
        sam_process = subprocess.Popen(
            command,
            cwd=SOLACE_AGENT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,  # Create new process group for clean shutdown
        )
    except FileNotFoundError:
        print("Command 'sam' not found. Trying 'uv run sam'...")
        command = ["uv", "run", "sam", "run", "configs/"]
        sam_process = subprocess.Popen(
            command,
            cwd=SOLACE_AGENT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
        )

    return sam_process


def stop_sam():
    """Stop SAM subprocess"""
    global sam_process

    if sam_process:
        print("🛑 Stopping Solace Agent Mesh...")
        try:
            os.killpg(os.getpgid(sam_process.pid), signal.SIGTERM)
            sam_process.wait(timeout=10)
        except Exception as e:
            print(f"Error stopping SAM: {e}")
            try:
                os.killpg(os.getpgid(sam_process.pid), signal.SIGKILL)
            except Exception:
                pass
        sam_process = None


def build_system_context(company_data: StartRequest) -> str:
    """Build dynamic system prompt from company data"""
    overview = company_data.company_overview or CompanyOverview()
    insights = company_data.interview_insights or InterviewInsights()
    tech_reqs = insights.technical_requirements or TechnicalRequirements()

    company_name = overview.name or "the company"
    industry = overview.industry or "technology"

    # Build tech stack string
    tech_stack = (
        ", ".join(tech_reqs.programming_languages or [])
        if tech_reqs.programming_languages
        else "various technologies"
    )
    frameworks = (
        ", ".join(tech_reqs.frameworks_tools or [])
        if tech_reqs.frameworks_tools
        else "standard tools"
    )

    # Build focus areas
    focus_areas = (
        ", ".join(insights.what_they_look_for or [])
        if insights.what_they_look_for
        else "technical skills, problem-solving"
    )

    # Coding Problems
    coding_problems_str = ""
    if insights.coding_problems:
        coding_problems_str = "\n".join(
            [
                f"- {p.title} (Difficulty: {p.difficulty}): {p.problem_statement}\n  Optimal Complexity: {p.optimal_time_complexity}, {p.optimal_space_complexity}"
                for p in insights.coding_problems
                if p
            ]
        )

    # System Design
    system_design_str = ""
    if insights.system_design_questions:
        system_design_str = "\n".join(
            [
                f"- {q.question}: Focus on {', '.join(q.key_components or []) if q.key_components else 'general components'}"
                for q in insights.system_design_questions
                if q
            ]
        )

    # Behavioral
    behavioral_str = ""
    if insights.common_questions:
        behavioral_str = "\n".join(
            [
                f"- {q.question} (Category: {q.category})"
                for q in insights.common_questions
                if q
            ]
        )

    # Build context string
    context = f"""[COMPANY PROFILE]
Name: {company_name}
Industry: {industry}
Size: {overview.size}
Headquarters: {overview.headquarters}
Mission: {overview.mission}
Culture: {overview.culture or "Professional"}

[TECHNICAL REQUIREMENTS]
Experience Level: {tech_reqs.experience_level}
Programming Languages: {tech_stack}
Frameworks/Tools: {frameworks}
Concepts: {tech_reqs.concepts}
Must-have Skills: {", ".join(tech_reqs.must_have_skills or []) if tech_reqs.must_have_skills else "N/A"}

[INTERVIEW STRATEGY]
Focus Areas: {focus_areas}
What they look for: {", ".join(insights.what_they_look_for or []) if insights.what_they_look_for else "N/A"}
Red Flags: {", ".join(insights.red_flags_to_avoid or []) if insights.red_flags_to_avoid else "N/A"}
Company Values: {", ".join(insights.company_values_in_interviews or []) if insights.company_values_in_interviews else "N/A"}


[POTENTIAL QUESTIONS]
Coding:
{coding_problems_str or "General algorithmic questions"}

System Design:
{system_design_str or "Scalability and architecture"}

Behavioral:
{behavioral_str or "Situational and experience-based"}

[INSTRUCTIONS]
You are John, a senior interviewer at {company_name}. 
Use the above data to tailor your questions. If the candidate mentions {tech_stack}, dive deeper.
Probe for the red flags mentioned.
Stay in character. Be conversational but firm."""

    return context


def get_turn_instruction(turn: int, company_data: StartRequest) -> str:
    """Get instruction for specific turn based on company data"""
    insights = company_data.interview_insights or InterviewInsights()

    # Try to get actual questions from the data
    behavioral_q = (
        insights.common_questions[0].question if insights.common_questions else None
    )
    system_design_q = (
        insights.system_design_questions[0].question
        if insights.system_design_questions
        else None
    )
    coding_q = (
        f"a coding question about {insights.coding_problems[0].title}"
        if insights.coding_problems
        else None
    )

    instructions = {
        1: f"ASK about: {behavioral_q or 'their experience with a challenging project'}. MAX 2 sentences.",
        2: f"ASK about: {system_design_q or 'how they would design a scalable system'}. MAX 2 sentences.",
        3: "SAY GOODBYE. Thank them for their time and say you'll be in touch. MAX 2 sentences.",
    }
    return instructions.get(turn, "SAY GOODBYE.")


async def send_to_solace(
    message: str, context_id: Optional[str] = None, agent_name: str = AGENT_NAME
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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
                "parts": [{"kind": "text", "text": message}],
            }
        },
    }

    if context_id:
        payload["params"]["contextId"] = context_id

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Submit the message and get task ID
        try:
            submit_response = await client.post(
                f"{GATEWAY_URL}/api/v1/message:stream",
                json=payload,
                headers={"Content-Type": "application/json"},
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
                headers={"Accept": "text/event-stream"},
            ) as sse_response:
                full_text = ""
                async for line in sse_response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    json_data = line[5:].strip()  # Remove "data:" prefix
                    try:
                        event_data = json.loads(json_data)
                        state = (
                            event_data.get("result", {}).get("status", {}).get("state")
                        )

                        if state == "completed":
                            parts = (
                                event_data.get("result", {})
                                .get("status", {})
                                .get("message", {})
                                .get("parts", [])
                            )
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
