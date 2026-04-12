"""
FastAPI dependency injectors for authentication and role-based access control.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jose import JWTError

from ..auth.jwt import decode_access_token
from ..db.mongodb import users_col
from ..models.user import UserDocument, UserPublic, UserRole


# ── Bearer token extraction ───────────────────────────────────────────────────

async def _get_token_from_header(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[len("Bearer "):]


# ── Current user ──────────────────────────────────────────────────────────────

async def get_current_user(
    token: Annotated[str, Depends(_get_token_from_header)],
) -> UserPublic:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    doc = await users_col().find_one({"_id": user_id})
    if not doc:
        raise credentials_exc

    user = UserDocument.from_mongo(doc)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        team_id=user.team_id,
        team_name=user.team_name,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


# ── Role guards ───────────────────────────────────────────────────────────────

def require_role(*roles: UserRole):
    """Factory: returns a dependency that enforces one of the given roles."""
    async def _check(
        current_user: Annotated[UserPublic, Depends(get_current_user)],
    ) -> UserPublic:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _check


require_admin = require_role(UserRole.ADMIN)
require_analyst_or_above = require_role(UserRole.ADMIN, UserRole.ANALYST)
require_customer_or_above = require_role(
    UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER, UserRole.CUSTOMER
)


# ── Type aliases ──────────────────────────────────────────────────────────────

CurrentUser = Annotated[UserPublic, Depends(get_current_user)]
AdminUser = Annotated[UserPublic, Depends(require_admin)]
AnalystUser = Annotated[UserPublic, Depends(require_analyst_or_above)]
AnyAuthUser = Annotated[UserPublic, Depends(require_customer_or_above)]
