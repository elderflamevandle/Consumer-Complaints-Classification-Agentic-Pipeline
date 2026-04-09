"""
CSRF protection — double-submit cookie pattern.

Flow:
  1. GET /api/auth/csrf-token  →  sets csrf_token cookie + returns token in body
  2. All state-changing methods (POST/PUT/PATCH/DELETE) must send:
       - Cookie: csrf_token=<token>
       - Header: X-CSRF-Token: <same token>
  3. Middleware compares the two; mismatch → 403.

Exempt paths:
  - GET / HEAD / OPTIONS (safe methods)
  - /health
  - /api/auth/login   (pre-auth; client doesn't have a CSRF token yet)
  - /api/auth/register
  - /api/auth/refresh (refresh uses HTTP-only cookie already; separate cookie)
  - WebSocket upgrade requests
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

_EXEMPT_PATHS = {
    "/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def _tokens_match(a: str, b: str) -> bool:
    """Constant-time comparison."""
    return hmac.compare_digest(
        hashlib.sha256(a.encode()).digest(),
        hashlib.sha256(b.encode()).digest(),
    )


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip safe methods, exempt paths, and WebSocket upgrades
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        if request.url.path in _EXEMPT_PATHS or request.url.path.startswith("/ws"):
            return await call_next(request)

        # Retrieve tokens
        cookie_token = request.cookies.get("csrf_token", "")
        header_token = request.headers.get("X-CSRF-Token", "")

        if not cookie_token or not header_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        if not _tokens_match(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch"},
            )

        return await call_next(request)
