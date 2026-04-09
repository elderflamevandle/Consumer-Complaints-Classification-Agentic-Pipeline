"""
JWT utilities — RS256 when keys are configured, HS256 fallback for local dev.
Access tokens expire in 15 min.  Refresh tokens are opaque UUIDs (not JWT).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from ..config import settings

# ── Token creation ─────────────────────────────────────────────────────────

def _signing_key() -> str:
    return settings.jwt_private_key if settings.use_rs256 else settings.jwt_secret_key


def _verify_key() -> str:
    return settings.jwt_public_key if settings.use_rs256 else settings.jwt_secret_key


def _algorithm() -> str:
    return "RS256" if settings.use_rs256 else "HS256"


def create_access_token(
    subject: str,
    role: str,
    extra: Dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(tz=timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,           # user_id
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _signing_key(), algorithm=_algorithm())


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate an access token.
    Raises jose.JWTError on invalid/expired tokens.
    """
    return jwt.decode(token, _verify_key(), algorithms=[_algorithm()])


# ── Refresh token (opaque UUID) ───────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Return a cryptographically random opaque refresh token."""
    return str(uuid.uuid4())


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest — stored in DB instead of the raw token."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Convenience re-export ─────────────────────────────────────────────────────

__all__ = [
    "create_access_token",
    "decode_access_token",
    "generate_refresh_token",
    "hash_refresh_token",
    "JWTError",
]
