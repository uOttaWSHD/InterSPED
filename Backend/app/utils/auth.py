import libsql_client
import time
from fastapi import Request, HTTPException
import os

# Initialize Turso client
url = os.environ.get("TURSO_DATABASE_URL", "file:intersped.db")
auth_token = os.environ.get("TURSO_AUTH_TOKEN")

# Create a sync client for use in the dependency
client = libsql_client.create_client_sync(url=url, auth_token=auth_token)


def get_user_from_session(request: Request):
    """
    Verifies the BetterAuth session token from cookies against the Turso/libSQL database.
    """
    session_token = request.cookies.get("better-auth.session_token")
    if not session_token:
        return None

    try:
        # Query session and join with user
        # Note: libsql_client returns ResultSet with rows that can be accessed by index or column name
        result = client.execute(
            """
            SELECT user.* FROM session 
            JOIN user ON session.userId = user.id 
            WHERE session.token = ? AND session.expiresAt > ?
            """,
            (session_token, int(time.time() * 1000)),
        )

        if not result.rows:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        # Convert row to dict. result.columns contains column names.
        row = result.rows[0]
        user_dict = {col: row[i] for i, col in enumerate(result.columns)}

        return user_dict
    except Exception as e:
        print(f"Auth error: {e}")
        return None
