"""
Password hashing (bcrypt rounds=12) and policy validation.
"""

from __future__ import annotations

import re

import bcrypt


_ROUNDS = 12

# ── Policy ────────────────────────────────────────────────────────────────────
_POLICY_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)

PASSWORD_POLICY_MESSAGE = (
    "Password must be at least 8 characters and include at least one uppercase letter, "
    "one lowercase letter, one digit, and one special character (!@#$%^&*...)."
)


def validate_password_policy(password: str) -> str:
    """Raise ValueError if the password does not meet the policy."""
    if not _POLICY_RE.match(password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)
    return password


def hash_password(plain: str) -> str:
    """Return bcrypt hash string (UTF-8 safe)."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verification."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False
