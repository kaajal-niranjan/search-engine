"""Email/password authentication with salted one-way password hashing."""

from __future__ import annotations

import hashlib
import re
import secrets

# Passwords are stored as salted PBKDF2 digests (salt:hash).
# Plaintext passwords are never stored in code or shown in the UI.
USERS: dict[str, str] = {
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

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ITERATIONS = 100_000


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


def verify_credentials(email: str, password: str) -> bool:
    """
    Verify login by hashing the entered password and comparing digests.

    Passwords are not decrypted. One-way hashing is used so stored credentials
    cannot be reversed back to the original password.
    """
    normalized = email.strip().lower()
    stored = USERS.get(normalized)
    if not stored or ":" not in stored:
        return False

    salt, expected_hash = stored.split(":", 1)
    actual_hash = _derive_hash(password, salt)
    return secrets.compare_digest(actual_hash, expected_hash)
