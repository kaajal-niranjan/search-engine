"""Server-side browser sessions for reliable refresh persistence.

The browser cookie stores only a URL-safe session id. Session details
(email, activity timestamps) live in a local JSON store so cookie values
never contain characters that browsers / CookieManager mangle.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config import (
    SESSION_COOKIE_MAX_AGE_SECONDS,
    SESSION_COOKIE_NAME,
    SESSION_IDLE_TIMEOUT_SECONDS,
    SESSIONS_STORE_PATH,
)

COOKIE_NAME = SESSION_COOKIE_NAME
IDLE_TIMEOUT_SECONDS = SESSION_IDLE_TIMEOUT_SECONDS
COOKIE_MAX_AGE_SECONDS = SESSION_COOKIE_MAX_AGE_SECONDS

_lock = threading.Lock()


@dataclass(frozen=True)
class SessionData:
    session_id: str
    email: str
    last_activity: float
    issued_at: float

    @property
    def idle_seconds(self) -> float:
        return max(0.0, time.time() - self.last_activity)

    @property
    def is_idle_expired(self) -> bool:
        return self.idle_seconds >= IDLE_TIMEOUT_SECONDS

    @property
    def is_hard_expired(self) -> bool:
        return (time.time() - self.issued_at) >= COOKIE_MAX_AGE_SECONDS


def _read_store(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_store(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _row_to_session(session_id: str, row: dict) -> Optional[SessionData]:
    try:
        email = str(row["email"]).strip().lower()
        last_activity = float(row["last_activity"])
        issued_at = float(row["issued_at"])
    except (KeyError, TypeError, ValueError):
        return None
    if not email or "@" not in email:
        return None
    return SessionData(
        session_id=session_id,
        email=email,
        last_activity=last_activity,
        issued_at=issued_at,
    )


def create_session(email: str, path: Path = SESSIONS_STORE_PATH) -> SessionData:
    """Create a new server-side session and return it (cookie stores session_id only)."""
    normalized = email.strip().lower()
    now = time.time()
    session_id = secrets.token_urlsafe(32)
    row = {
        "email": normalized,
        "last_activity": now,
        "issued_at": now,
    }
    with _lock:
        data = _read_store(path)
        data[session_id] = row
        _write_store(data, path)
    return SessionData(
        session_id=session_id,
        email=normalized,
        last_activity=now,
        issued_at=now,
    )


def get_session(
    session_id: Optional[str],
    path: Path = SESSIONS_STORE_PATH,
) -> Optional[SessionData]:
    if not session_id or not isinstance(session_id, str):
        return None
    sid = session_id.strip()
    if not sid:
        return None
    with _lock:
        data = _read_store(path)
        row = data.get(sid)
        if not isinstance(row, dict):
            return None
        return _row_to_session(sid, row)


def touch_session(
    session_id: Optional[str],
    path: Path = SESSIONS_STORE_PATH,
) -> Optional[SessionData]:
    """Update last_activity; returns None if missing / hard-expired."""
    if not session_id:
        return None
    sid = session_id.strip()
    now = time.time()
    with _lock:
        data = _read_store(path)
        row = data.get(sid)
        if not isinstance(row, dict):
            return None
        session = _row_to_session(sid, row)
        if session is None or session.is_hard_expired:
            data.pop(sid, None)
            _write_store(data, path)
            return None
        row["last_activity"] = now
        data[sid] = row
        _write_store(data, path)
        return SessionData(
            session_id=sid,
            email=session.email,
            last_activity=now,
            issued_at=session.issued_at,
        )


def delete_session(
    session_id: Optional[str],
    path: Path = SESSIONS_STORE_PATH,
) -> None:
    if not session_id:
        return
    sid = session_id.strip()
    with _lock:
        data = _read_store(path)
        if sid in data:
            data.pop(sid, None)
            _write_store(data, path)


def validate_session_for_restore(
    session_id: Optional[str],
    path: Path = SESSIONS_STORE_PATH,
) -> Optional[SessionData]:
    """
    Restore across browser refresh.

    Only the hard lifetime cap applies here. The 1-minute inactivity logout is
    enforced by the browser idle watchdog while the dashboard is open — applying
    idle expiry on refresh would boot active users who only viewed the page
    without triggering Streamlit widget reruns.
    """
    session = get_session(session_id, path=path)
    if session is None:
        return None
    if session.is_hard_expired:
        delete_session(session_id, path=path)
        return None
    return session


# Backwards-compatible helpers used by older call sites / docs
def create_session_token(email: str, **_: object) -> str:
    return create_session(email).session_id


def parse_session_token(token: Optional[str]) -> Optional[SessionData]:
    return get_session(token)


def validate_session_token(token: Optional[str]) -> Optional[SessionData]:
    return validate_session_for_restore(token)


def touch_session_token(token: Optional[str]) -> Optional[str]:
    session = touch_session(token)
    return session.session_id if session else None
