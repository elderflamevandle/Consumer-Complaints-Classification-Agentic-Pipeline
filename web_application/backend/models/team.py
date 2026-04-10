"""
Team document model (MongoDB collection: teams).

Teams group analysts by specialty.  Complaints are auto-routed to teams based
on the issue_types list, and analysts only see complaints assigned to their team.
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class TeamDocument(BaseModel):
    """Stored in MongoDB.  Never returned directly — use TeamPublic for API."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    name: str                            # Display name e.g. "Fraud & Security Operations"
    slug: str                            # Unique URL-safe key e.g. "fraud-security"
    description: str = ""
    # Auto-routing: complaints whose issue_type is in this list get team_id set
    issue_types: List[str] = Field(default_factory=list)
    # Informational: which product types this team typically handles
    product_types: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)

    @classmethod
    def from_mongo(cls, data: dict) -> "TeamDocument":
        return cls.model_validate(data)


class TeamPublic(BaseModel):
    """API-safe representation returned to clients."""
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    description: str
    issue_types: List[str]
    product_types: List[str]
    is_active: bool
    member_count: int = 0
    created_at: datetime
    updated_at: datetime
