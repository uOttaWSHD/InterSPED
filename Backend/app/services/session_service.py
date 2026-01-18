from typing import Dict, Any, Optional, List
import time
from app.utils.key_manager import get_key

# Global sessions storage
sessions: Dict[str, Any] = {}


def create_session(
    session_id: str,
    context_id: str,
    company_data: dict,
    response_text: str,
    max_turns: int = 15,
):
    # Deterministically assign keys for this session
    elevenlabs_key = get_key("ELEVENLABS_API_KEY", session_id)
    llm_key = get_key("LLM_SERVICE_API_KEY", session_id) or get_key(
        "GROQ_API_KEY", session_id
    )

    sessions[session_id] = {
        "context_id": context_id,
        "turn_count": 0,
        "transcript": f"Interviewer: {response_text}",
        "max_turns": max_turns,
        "company_data": company_data,
        "last_interaction": time.time(),
        "assigned_keys": {"elevenlabs": elevenlabs_key, "llm": llm_key},
    }
    return sessions[session_id]


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    session = sessions.get(session_id)
    if session:
        session["last_interaction"] = time.time()
    return session


def update_session(
    session_id: str, context_id: str, user_input: str, response_text: str
):
    session = sessions.get(session_id)
    if session:
        session["context_id"] = context_id
        session["transcript"] += (
            f"\n\nCandidate: {user_input}\n\nInterviewer: {response_text}"
        )
        session["last_interaction"] = time.time()
        return session
    return None


def increment_turn(session_id: str):
    session = sessions.get(session_id)
    if session:
        session["turn_count"] += 1
        session["last_interaction"] = time.time()
        return session["turn_count"]
    return None


def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]


def cleanup_old_sessions(max_age_seconds: int = 3600):
    now = time.time()
    to_delete = [
        sid
        for sid, s in sessions.items()
        if now - s["last_interaction"] > max_age_seconds
    ]
    for sid in to_delete:
        del sessions[sid]
