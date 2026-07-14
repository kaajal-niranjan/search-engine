"""Email/password authentication with local credential store (D1).

Users register first; credentials are stored locally as salted PBKDF2 digests
(salt:hash). Plaintext passwords are never stored or shown in the UI.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
from pathlib import Path

from src.config import USERS_STORE_PATH

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ITERATIONS = 100_000
_MIN_PASSWORD_LENGTH = 6

# Thread-safe file I/O for multi-session Streamlit use
_lock = threading.Lock()

# Seed accounts written once when the local store is first created.
_SEED_USERS: dict[str, str] = {
    "admin@valere.io": (
        "b686b9a968e82c79ae31abe16cb444a4:"
        "3b7e2b2742c668ad87b7b78f37fd37cf182ac4dcaffee29dedfcfe12db9ab3f4"
    ),
    "demo@valere.io": (
        "4f651dfef2462230a0a8d138384a118e:"
        "90a5e79425c8e9c741450cf2ac106eeefa91e2c8cce9d8249159d5d699782863"
    ),
    "user@example.com": (
        "398f4073284f27ddebdce94448f29597:"
        "33a9152dee8af32cef05bca84331e35f7d37c7a6714cedb6c88d68c7205aacc0"
    ),
}


def _derive_hash(password: str, salt: str) -> str:
    """Derive a one-way password digest using PBKDF2-HMAC-SHA256."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return digest.hex()


def hash_password(password: str, salt: str | None = None) -> str:
    """Create a salted password digest for storage."""
    salt_value = salt or secrets.token_hex(16)
    return f"{salt_value}:{_derive_hash(password, salt_value)}"


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email.strip()))


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _read_store(path: Path) -> dict[str, str]:
    """Read credential map from disk (caller must hold _lock)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_SEED_USERS, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return dict(_SEED_USERS)

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    return {_normalize_email(str(k)): str(v) for k, v in raw.items()}


def _write_store(users: dict[str, str], path: Path) -> None:
    """Write credential map to disk (caller must hold _lock)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(users, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_users(path: Path = USERS_STORE_PATH) -> dict[str, str]:
    """Load email → salt:hash map from the local credential store."""
    with _lock:
        return _read_store(path)


def user_exists(email: str, path: Path = USERS_STORE_PATH) -> bool:
    """Return True if the email is already registered."""
    return _normalize_email(email) in load_users(path)


def register_user(
    email: str,
    password: str,
    path: Path = USERS_STORE_PATH,
) -> tuple[bool, str]:
    """
    Register a new user in the local credential store.

    Returns (success, message). On success the password is stored as a
    salted PBKDF2 digest only.
    """
    normalized = _normalize_email(email)

    if not normalized:
        return False, "Email is required."
    if not is_valid_email(normalized):
        return False, "Please enter a valid email address."
    if not password:
        return False, "Password is required."
    if len(password) < _MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {_MIN_PASSWORD_LENGTH} characters."

    with _lock:
        users = _read_store(path)
        if normalized in users:
            return False, "An account with this email already exists."

        users[normalized] = hash_password(password)
        _write_store(users, path)

    return True, "Account created successfully. You can sign in now."


def verify_credentials(
    email: str,
    password: str,
    path: Path = USERS_STORE_PATH,
) -> bool:
    """
    Verify login by hashing the entered password and comparing digests.

    Passwords are not decrypted. One-way hashing is used so stored credentials
    cannot be reversed back to the original password.
    """
    normalized = _normalize_email(email)
    stored = load_users(path).get(normalized)
    if not stored or ":" not in stored:
        return False

    salt, expected_hash = stored.split(":", 1)
    actual_hash = _derive_hash(password, salt)
    return secrets.compare_digest(actual_hash, expected_hash)


# Legacy alias: in-memory-style access for older docs/snippets.
# Prefer load_users() / register_user() / verify_credentials().
USERS: dict[str, str] = _SEED_USERS
