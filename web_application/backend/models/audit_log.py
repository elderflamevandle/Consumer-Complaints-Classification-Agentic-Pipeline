"""
Audit log document — append-only.  NEVER update or delete audit records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuditAction(StrEnum):
    # Auth
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    USER_LOGOUT = "USER_LOGOUT"
    USER_LOCKED = "USER_LOCKED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"

    # Users
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_TEAM_ASSIGNED = "USER_TEAM_ASSIGNED"

    # Teams
    TEAM_CREATED = "TEAM_CREATED"
    TEAM_UPDATED = "TEAM_UPDATED"
    TEAM_DEACTIVATED = "TEAM_DEACTIVATED"

    # Complaints
    COMPLAINT_CREATED = "COMPLAINT_CREATED"
    COMPLAINT_STATUS_CHANGED = "COMPLAINT_STATUS_CHANGED"
    COMPLAINT_ASSIGNED = "COMPLAINT_ASSIGNED"
    COMPLAINT_REVIEWED = "COMPLAINT_REVIEWED"
    COMPLAINT_DELETED = "COMPLAINT_DELETED"

    # Pipeline
    PIPELINE_STARTED = "PIPELINE_STARTED"
    PIPELINE_STAGE_COMPLETED = "PIPELINE_STAGE_COMPLETED"
    PIPELINE_INTERRUPTED = "PIPELINE_INTERRUPTED"
    PIPELINE_COMPLETED = "PIPELINE_COMPLETED"
    PIPELINE_FAILED = "PIPELINE_FAILED"


class AuditLogDocument(BaseModel):
    """Immutable audit record.  Insert only."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: Optional[str] = None       # None for system events
    action: AuditAction
    entity_type: Optional[str] = None   # "complaint" | "user" | "pipeline"
    entity_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
