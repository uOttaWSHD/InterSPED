from typing import Dict, Any, Optional
import time

# Global sessions storage
sessions: Dict[str, Any] = {}


def create_session(
    session_id: str,
    context_id: str,
    company_data: dict,
    response_text: str,
    max_turns: int = 3,
):
    sessions[session_id] = {
        "context_id": context_id,
        "turn_count": 0,
        "transcript": f"Interviewer: {response_text}",
        "max_turns": max_turns,
        "company_data": company_data,
        "last_interaction": time.time(),
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
