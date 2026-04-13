"""
Input sanitisation middleware.

- Strips HTML/JS from all string fields in JSON request bodies using bleach.
- Rejects requests with duplicate query parameters (HTTP parameter pollution).
- Applied before route handlers see the data.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import bleach
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# bleach defaults: strips all tags and dangerous attributes
_ALLOWED_TAGS: list[str] = []
_ALLOWED_ATTRS: dict = {}


def _sanitize_value(v: Any) -> Any:
    """Recursively sanitize string values in a JSON-decoded structure."""
    if isinstance(v, str):
        return bleach.clean(v, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v


class SanitizeMiddleware(BaseHTTPMiddleware):
    """
    Sanitize JSON body strings + block HTTP parameter pollution.
    We patch the request body in-place so route handlers see clean data.
    """

    _SKIP_CONTENT_TYPES = {"multipart/form-data", "application/x-www-form-urlencoded"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # ── HTTP Parameter Pollution guard ──────────────────────────────────
        seen: set[str] = set()
        for key in request.query_params.keys():
            if key in seen:
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Duplicate query parameter: {key}"},
                )
            seen.add(key)

        # ── JSON body sanitisation ──────────────────────────────────────────
        # NOTE: We use request._body (the cache that request.body() returns on
        # repeated calls) rather than patching _receive.  Patching _receive
        # confuses Starlette's BaseHTTPMiddleware ASGI state machine and
        # produces "Unexpected message received: http.request" errors.
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type and request.method in {"POST", "PUT", "PATCH"}:
            try:
                raw = await request.body()        # populates request._body cache
                if raw:
                    payload = json.loads(raw)
                    clean_payload = _sanitize_value(payload)
                    clean_bytes = json.dumps(clean_payload).encode()
                    # Overwrite the cache — all subsequent request.body() calls
                    # (including FastAPI's JSON parser) will see clean data.
                    request._body = clean_bytes   # type: ignore[attr-defined]
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Let FastAPI's own validator return 422

        return await call_next(request)
