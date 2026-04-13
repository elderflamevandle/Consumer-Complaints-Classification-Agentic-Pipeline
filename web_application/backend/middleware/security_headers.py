"""
Security headers middleware — injected on every response.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Legacy XSS filter (for old browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Deny framing completely
        response.headers["X-Frame-Options"] = "DENY"

        # HSTS (only meaningful in production over HTTPS)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Content Security Policy — tightened; adjust if you add CDN assets
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "   # shadcn needs inline styles
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Remove server fingerprinting headers
        # MutableHeaders doesn't support .pop(); use del with existence check
        for _hdr in ("server", "x-powered-by"):
            if _hdr in response.headers:
                del response.headers[_hdr]

        return response
