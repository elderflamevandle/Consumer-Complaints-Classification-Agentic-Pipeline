"""
Auth router — register, login, logout, token refresh, current user.

Security model:
  • Access token:  JWT, 15 min, returned in JSON body
  • Refresh token: opaque UUID, 7 days, HTTP-only Secure SameSite=Strict cookie
  • Refresh tokens stored as SHA-256 hash in MongoDB + Redis blocklist on revocation
  • 5 failed logins → 30-min account lockout tracked in Redis
  • Generic error message (does not reveal whether email exists)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..auth.dependencies import CurrentUser
from ..auth.jwt import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    JWTError,
)
from ..auth.password import (
    PASSWORD_POLICY_MESSAGE,
    hash_password,
    validate_password_policy,
    verify_password,
)
from ..config import settings
from ..db.mongodb import refresh_tokens_col, users_col
from ..db.redis_client import (
    clear_login_attempts,
    get_login_attempts,
    increment_login_attempts,
    is_account_locked,
    is_refresh_token_revoked,
    revoke_refresh_token,
    set_account_locked,
)
from ..models.audit_log import AuditAction, AuditLogDocument
from ..models.refresh_token import RefreshTokenDocument
from ..models.user import UserDocument, UserPublic, UserRole
from ..db.mongodb import audit_logs_col

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_GENERIC_AUTH_ERROR = "Invalid credentials"

# ── Request / Response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def _policy(cls, v: str) -> str:
        return validate_password_policy(v)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = settings.jwt_access_token_expire_minutes * 60
    user: UserPublic


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = settings.jwt_access_token_expire_minutes * 60


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.jwt_refresh_token_expire_days * 86_400,
        path="/api/auth/refresh",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh")


async def _write_audit(
    action: AuditAction,
    *,
    user_id: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    doc = AuditLogDocument(
        user_id=user_id,
        action=action,
        entity_type="user",
        entity_id=entity_id or user_id,
        details=details or {},
        ip_address=ip,
        user_agent=user_agent,
    )
    await audit_logs_col().insert_one(doc.to_mongo())


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, response: Response):
    # Check duplicate email
    existing = await users_col().find_one({"email": body.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = UserDocument(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.ANALYST,
    )
    await users_col().insert_one(user.to_mongo())

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(refresh_token)

    rt_doc = RefreshTokenDocument(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(tz=timezone.utc)
        + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    await refresh_tokens_col().insert_one(rt_doc.to_mongo())
    _set_refresh_cookie(response, refresh_token)

    await _write_audit(
        AuditAction.USER_REGISTERED,
        user_id=user.id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    logger.info("User registered — id=%s", user.id)

    public = UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
    return TokenResponse(access_token=access_token, user=public)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"

    # Check IP-level login-attempt count (brute-force guard)
    attempts = await get_login_attempts(ip)
    if attempts >= settings.max_failed_login_attempts:
        await _write_audit(
            AuditAction.USER_LOGIN_FAILED,
            details={"reason": "ip_locked", "ip": ip},
            ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_GENERIC_AUTH_ERROR,
        )

    doc = await users_col().find_one({"email": body.email})

    # Always run password verify (timing-safe even if user not found)
    dummy_hash = "$2b$12$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    stored_hash = doc["password_hash"] if doc else dummy_hash
    password_ok = verify_password(body.password, stored_hash)

    if not doc or not password_ok:
        await increment_login_attempts(ip)
        if doc:
            # Increment per-user counter; lock if threshold reached
            new_count = (doc.get("failed_login_count") or 0) + 1
            update: dict = {"failed_login_count": new_count, "updated_at": datetime.now(tz=timezone.utc)}
            if new_count >= settings.max_failed_login_attempts:
                await set_account_locked(str(doc["_id"]))
                update["locked_until"] = datetime.now(tz=timezone.utc) + timedelta(
                    minutes=settings.account_lockout_minutes
                )
                await _write_audit(
                    AuditAction.USER_LOCKED,
                    user_id=str(doc["_id"]),
                    details={"reason": "too_many_failures"},
                    ip=ip,
                )
            await users_col().update_one({"_id": doc["_id"]}, {"$set": update})

        await _write_audit(
            AuditAction.USER_LOGIN_FAILED,
            user_id=str(doc["_id"]) if doc else None,
            details={"ip": ip},
            ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_GENERIC_AUTH_ERROR,
        )

    user = UserDocument.from_mongo(doc)

    # Check account lock (Redis TTL gate)
    if await is_account_locked(user.id):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=_GENERIC_AUTH_ERROR,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_GENERIC_AUTH_ERROR,
        )

    # Successful login — reset counters
    await clear_login_attempts(ip)
    await users_col().update_one(
        {"_id": user.id},
        {"$set": {"failed_login_count": 0, "last_login_at": datetime.now(tz=timezone.utc), "updated_at": datetime.now(tz=timezone.utc)}},
    )

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = generate_refresh_token()
    rt_doc = RefreshTokenDocument(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(tz=timezone.utc)
        + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    await refresh_tokens_col().insert_one(rt_doc.to_mongo())
    _set_refresh_cookie(response, refresh_token)

    await _write_audit(
        AuditAction.USER_LOGIN,
        user_id=user.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    logger.info("User logged in — id=%s", user.id)

    public = UserPublic(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )
    return TokenResponse(access_token=access_token, user=public)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    token_hash = hash_refresh_token(refresh_token)

    # Check Redis blocklist first (fast path)
    if await is_refresh_token_revoked(token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # Look up in MongoDB
    rt_doc = await refresh_tokens_col().find_one({"token_hash": token_hash, "is_revoked": False})
    if not rt_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Check expiry
    expires_at: datetime = rt_doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user_id = rt_doc["user_id"]
    doc = await users_col().find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user = UserDocument.from_mongo(doc)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Rotate: revoke old, issue new
    ttl = int((expires_at - datetime.now(tz=timezone.utc)).total_seconds())
    await revoke_refresh_token(token_hash, max(ttl, 1))
    await refresh_tokens_col().update_one(
        {"_id": rt_doc["_id"]}, {"$set": {"is_revoked": True}}
    )

    new_refresh = generate_refresh_token()
    new_hash = hash_refresh_token(new_refresh)
    new_rt_doc = RefreshTokenDocument(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=datetime.now(tz=timezone.utc)
        + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    await refresh_tokens_col().insert_one(new_rt_doc.to_mongo())
    _set_refresh_cookie(response, new_refresh)

    new_access = create_access_token(subject=user.id, role=user.role)

    await _write_audit(
        AuditAction.TOKEN_REFRESHED,
        user_id=user.id,
        ip=request.client.host if request.client else None,
    )
    return RefreshResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        await refresh_tokens_col().update_one(
            {"token_hash": token_hash}, {"$set": {"is_revoked": True}}
        )
        await revoke_refresh_token(token_hash, settings.jwt_refresh_token_expire_days * 86_400)

    _clear_refresh_cookie(response)
    await _write_audit(
        AuditAction.USER_LOGOUT,
        user_id=current_user.id,
        ip=request.client.host if request.client else None,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: CurrentUser) -> UserPublic:
    return current_user
