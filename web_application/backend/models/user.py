"""
User document model (MongoDB collection: users).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class UserDocument(BaseModel):
    """Stored in MongoDB — never returned directly to clients."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    email: EmailStr
    password_hash: str
    full_name: str
    role: UserRole = UserRole.ANALYST
    # Team membership — set by admin; None means unassigned
    team_id: Optional[str] = None
    team_name: Optional[str] = None   # Denormalised for cheap reads
    is_active: bool = True
    failed_login_count: int = 0
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_mongo(self) -> dict:
        d = self.model_dump(by_alias=True)
        return d

    @classmethod
    def from_mongo(cls, data: dict) -> "UserDocument":
        return cls.model_validate(data)


class UserPublic(BaseModel):
    """Safe representation returned to API clients — no password_hash."""
    model_config = ConfigDict(extra="forbid")

    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
