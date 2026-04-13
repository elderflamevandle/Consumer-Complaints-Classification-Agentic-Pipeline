"""
Refresh token document — token_hash stored, never the raw token.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RefreshTokenDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: str
    token_hash: str           # SHA-256 hex digest of the opaque UUID token
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    expires_at: datetime      # TTL index in MongoDB auto-purges expired docs

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
