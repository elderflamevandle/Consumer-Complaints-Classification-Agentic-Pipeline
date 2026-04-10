"""
FinComplaint AI — FastAPI application factory.

Startup order:
  1. Connect MongoDB (Motor)
  2. Connect Redis (aioredis)
  3. Register middleware (security headers → CSRF → sanitize → CORS)
  4. Mount routers (auth, complaints, admin)
  5. Expose /health + /api/auth/csrf-token

All middleware is applied in reverse-registration order by Starlette, so the
outermost wrapper (security headers) runs first on every response.
"""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .auth.router import router as auth_router
from .config import settings
from .db.mongodb import connect_db, close_db
from .db.redis_client import connect_redis, close_redis
from .middleware.csrf import CSRFMiddleware
from .middleware.sanitize import SanitizeMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .routers.admin import router as admin_router
from .routers.complaints import router as complaints_router
from .routers.teams import router as teams_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter (slowapi) ────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FinComplaint AI backend (env=%s)", settings.app_env)
    await connect_db()
    try:
        await connect_redis()
    except Exception as exc:
        logger.warning("Redis unavailable — rate-limiting and lockout will be degraded: %s", exc)
    yield
    await close_db()
    try:
        await close_redis()
    except Exception:
        pass
    logger.info("FinComplaint AI backend shut down")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Production-grade complaint triage — REST + WebSocket API",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Attach rate limiter ───────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Middleware stack (applied bottom-up — last-added = outermost) ─────────
    # 1. Input sanitisation + param-pollution guard (innermost)
    app.add_middleware(SanitizeMiddleware)

    # 2. CSRF (double-submit cookie)
    app.add_middleware(CSRFMiddleware)

    # 3. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-CSRF-Token"],
    )

    # 4. Security headers (outermost — runs on every response)
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth_router, prefix="/api")
    app.include_router(complaints_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(teams_router, prefix="/api")

    # ── Utility endpoints ─────────────────────────────────────────────────────

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "env": settings.app_env}

    @app.get("/api/auth/csrf-token", tags=["auth"])
    async def get_csrf_token(request: Request):
        """
        Issue a fresh CSRF token.
        Sets a non-HttpOnly cookie and returns the same value in the body.
        The frontend must include X-CSRF-Token: <value> on all mutating requests.
        """
        token = secrets.token_hex(32)
        response = JSONResponse(content={"csrf_token": token})
        response.set_cookie(
            key="csrf_token",
            value=token,
            httponly=False,          # JS must be able to read this one
            secure=settings.is_production,
            samesite="strict",
            max_age=3600,
        )
        return response

    # ── Global error handler ──────────────────────────────────────────────────

    @app.exception_handler(Exception)
    async def _global_exc(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
