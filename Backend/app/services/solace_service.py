import os
import subprocess
import signal
import time
import httpx
import asyncio
import json
import sys
import traceback
from typing import Optional, Tuple, List
from app.models.interview import (
    StartRequest,
    CompanyOverview,
    InterviewInsights,
    TechnicalRequirements,
)

from app.utils.key_manager import get_key, get_key_count, parse_keys

# Configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
AGENT_NAME = "OrchestratorAgent"
SOLACE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "solace_agent")
)

# Global process reference
sam_process: Optional[subprocess.Popen] = None


async def wait_for_sam_ready(timeout: int = 60) -> bool:
    """Wait for SAM gateway to be ready"""
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{GATEWAY_URL}/health", timeout=2.0)
                if response.status_code == 200:
                    print("✅ SAM Gateway is healthy")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False


def stop_sam():
    """Stop SAM subprocess"""
    global sam_process
    if sam_process:
        print("🛑 Stopping Solace Agent Mesh...")
        try:
            os.killpg(os.getpgid(sam_process.pid), signal.SIGTERM)
            sam_process.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(sam_process.pid), signal.SIGKILL)
            except Exception:
                pass
        sam_process = None


def start_sam(api_key: Optional[str] = None):
    """Start SAM as a subprocess with correct environment"""
    global sam_process

    # Don't start if already running, unless we are forcing a restart (e.g. for key rotation)
    if sam_process and sam_process.poll() is None:
        return sam_process

    print(f"🚀 Starting Solace Agent Mesh...")

    env = os.environ.copy()

    # Ensure we use the verified working Cerebras config by default
    # but allow override via api_key for rotation
    effective_key = api_key
    if not effective_key:
        raw_keys = env.get("LLM_SERVICE_API_KEY", "")
        if raw_keys:
            effective_key = raw_keys.split(",")[0].strip()

    if effective_key:
        env["LLM_SERVICE_API_KEY"] = effective_key
        if effective_key.startswith("gsk_"):
            env["LLM_SERVICE_ENDPOINT"] = "https://api.groq.com/openai/v1"
            env["LLM_SERVICE_PLANNING_MODEL_NAME"] = "llama-3.3-70b-versatile"
            env["LLM_SERVICE_GENERAL_MODEL_NAME"] = "llama-3.1-8b-instant"
        elif effective_key.startswith("csk-"):
            env["LLM_SERVICE_ENDPOINT"] = "https://api.cerebras.ai/v1"
            env["LLM_SERVICE_PLANNING_MODEL_NAME"] = "llama3.3-70b"
            env["LLM_SERVICE_GENERAL_MODEL_NAME"] = "llama3.3-70b"

    # Set other required vars if missing
    env.setdefault("NAMESPACE", "sam/")
    env.setdefault("SOLACE_DEV_MODE", "true")
    env.setdefault("GATEWAY_URL", "http://localhost:8000")
    env.setdefault("FASTAPI_PORT", "8000")

    try:
        # Launch SAM in the background, inheriting stdout/stderr for visibility
        sam_process = subprocess.Popen(
            ["uv", "run", "sam", "run", "configs/"],
            cwd=SOLACE_AGENT_DIR,
            stdout=sys.stdout,
            stderr=sys.stderr,
            preexec_fn=os.setsid,
            env=env,
        )
    except Exception as e:
        print(f"❌ Failed to start SAM: {e}")
        traceback.print_exc()

    return sam_process


async def start_sam_with_rotation():
    """Starts SAM only if it is not already running"""
    if await wait_for_sam_ready(timeout=2):
        print("✅ SAM is already running and ready")
        return True

    start_sam()
    return await wait_for_sam_ready(timeout=45)


async def send_to_solace(
    message: str,
    context_id: Optional[str] = None,
    agent_name: str = AGENT_NAME,
    session_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Send message to SAM. If it fails and rotation is enabled, try the next key."""

    # Try once with current running SAM
    result_text, new_ctx_id, error = await _send_to_solace_internal(
        message, context_id, agent_name
    )

    # If it failed and rotation is NOT disabled, try rotating
    if error and os.environ.get("DISABLE_KEY_ROTATION") != "true":
        print(f"⚠️ SAM request failed: {error}. Attempting key rotation...")
        keys = []
        for env_name in ["LLM_SERVICE_API_KEY", "LLM_API_KEY", "GROQ_API_KEY"]:
            for k in parse_keys(env_name):
                if k not in keys:
                    keys.append(k)

        # Try up to 5 unique keys
        for i in range(1, min(len(keys), 5)):
            print(f"🔄 Rotating to key index {i}...")
            stop_sam()
            start_sam(keys[i])
            if await wait_for_sam_ready(timeout=30):
                await asyncio.sleep(2)  # Grace period
                result_text, new_ctx_id, error = await _send_to_solace_internal(
                    message, context_id, agent_name
                )
                if not error:
                    return result_text, new_ctx_id, None
            else:
                print(f"❌ SAM failed to start with key {i}")

    return result_text, new_ctx_id, error


async def _send_to_solace_internal(
    message: str, context_id: Optional[str] = None, agent_name: str = AGENT_NAME
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Internal client logic to talk to SAM Gateway"""
    request_id = int(time.time() * 1000)
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/stream",
        "params": {
            "message": {
                "messageId": f"msg_{request_id}",
                "kind": "message",
                "role": "user",
                "metadata": {"agent_name": agent_name},
                "parts": [{"kind": "text", "text": message}],
            }
        },
    }
    if context_id:
        payload["params"]["contextId"] = context_id

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{GATEWAY_URL}/api/v1/message:stream", json=payload
            )
            if resp.status_code != 200:
                return (
                    None,
                    context_id,
                    f"Gateway Error {resp.status_code}: {resp.text[:100]}",
                )

            task_id = resp.json().get("result", {}).get("id")
            new_ctx_id = resp.json().get("result", {}).get("contextId", context_id)
            if not task_id:
                return None, new_ctx_id, "No task ID"

            # SSE Subscribe
            full_text = ""
            async with client.stream(
                "GET", f"{GATEWAY_URL}/api/v1/sse/subscribe/{task_id}"
            ) as sse:
                async for line in sse.aiter_lines():
                    if line.startswith("data:"):
                        event = json.loads(line[5:])
                        res = event.get("result", {})

                        # Bulletproof parsing of SAM SSE stream
                        def extract_text(obj):
                            if not isinstance(obj, dict):
                                return None
                            # Case 1: direct message.parts (final message)
                            msg = obj.get("message")
                            if isinstance(msg, dict):
                                parts = msg.get("parts", [])
                                for p in parts:
                                    if p.get("kind") == "text" and p.get("text"):
                                        return p["text"]
                            # Case 2: status.message.parts (incremental)
                            status = obj.get("status")
                            if isinstance(status, dict):
                                msg = status.get("message")
                                if isinstance(msg, dict):
                                    parts = msg.get("parts", [])
                                    for p in parts:
                                        if p.get("kind") == "text" and p.get("text"):
                                            return p["text"]
                            return None

                        t = extract_text(res)
                        if t and len(t) > len(full_text):
                            full_text = t

                        status = res.get("status")
                        if isinstance(status, dict):
                            state = status.get("state")
                            if state == "completed":
                                break
                            if state == "failed":
                                return (
                                    None,
                                    new_ctx_id,
                                    f"Task failed: {status.get('error')}",
                                )

            return full_text, new_ctx_id, None
    except Exception as e:
        return None, context_id, f"Request Exception: {str(e)}"


def build_system_context(company_data: StartRequest) -> str:
    """Build system prompt"""
    c = company_data.company_overview or CompanyOverview()
    i = company_data.interview_insights or InterviewInsights()
    t = i.technical_requirements or TechnicalRequirements()

    return f"""[COMPANY] {c.name} ({c.industry})
[TECH] {", ".join(t.programming_languages or [])}
[FOCUS] {", ".join(i.what_they_look_for or [])}
You are John, a senior interviewer. Stay in character. Be concise."""


def get_turn_instruction(turn: int, company_data: StartRequest) -> str:
    if turn <= 3:
        return "PHASE: BEHAVIORAL. Ask about their background."
    if turn <= 10:
        return "PHASE: TECHNICAL. Ask a coding question."
    return "PHASE: CLOSING. Wrap up."
