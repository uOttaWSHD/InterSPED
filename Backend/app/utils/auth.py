import sqlite3
import time
from fastapi import Request, HTTPException, Depends
import os

# Path to the shared SQLite database used by BetterAuth in the Frontend
DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../Frontend/intersped.db")
)


def get_user_from_session(request: Request):
    """
    Verifies the BetterAuth session token from cookies against the SQLite database.
    """
    session_token = request.cookies.get("better-auth.session_token")
    if not session_token:
        # For development/testing, you might want to allow this or check Authorization header
        # raise HTTPException(status_code=401, detail="Not authenticated")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Query session and join with user
        cur.execute(
            """
            SELECT user.* FROM session 
            JOIN user ON session.userId = user.id 
            WHERE session.token = ? AND session.expiresAt > ?
        """,
            (session_token, int(time.time() * 1000)),
        )

        user = cur.fetchone()
        conn.close()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        return dict(user)
    except Exception as e:
        print(f"Auth error: {e}")
        return None
