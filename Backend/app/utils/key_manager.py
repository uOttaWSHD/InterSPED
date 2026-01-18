import os
import json
import hashlib
from typing import List, Optional


def parse_keys(env_name: str) -> List[str]:
    """
    Parses an environment variable which is now strictly comma-separated.
    """
    val = os.environ.get(env_name, "")
    if not val:
        return []

    val = val.strip()

    # Strictly comma-separated as per new format
    if "," in val:
        return [k.strip() for k in val.split(",") if k.strip()]

    return [val]


def get_key_count(env_name: str) -> int:
    """
    Returns the number of available keys for the given environment variable.
    """
    return len(parse_keys(env_name))


def get_key(env_name: str, session_id: Optional[str] = None, attempt: int = 0) -> str:
    """
    Gets a key for a specific session_id using a deterministic hash.
    If no session_id is provided, returns the key at the given attempt index.
    The 'attempt' parameter allows cycling through keys if one fails.
    """
    keys = parse_keys(env_name)
    if not keys:
        return ""

    if not session_id:
        return keys[attempt % len(keys)]

    # Use deterministic hash of session_id to pick a key, then offset by attempt
    hash_val = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
    index = (hash_val + attempt) % len(keys)
    return keys[index]
