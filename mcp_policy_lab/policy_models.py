from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class PolicyRequest:
    issue_type: str
    state_code: str
    complaint_text: str = ""


@dataclass(slots=True)
class PolicyEvidence:
    title: str
    url: str
    excerpt: str = ""


@dataclass(slots=True)
class PolicyResult:
    status: str
    source: str
    issue_type: str
    state_code: str
    sla_window: str
    required_actions: list[str]
    regulatory_basis: str
    confidence: float
    evidence: list[PolicyEvidence] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    retrieved_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PolicyProvider:
    name: str = "provider"

    def resolve(self, request: PolicyRequest) -> PolicyResult | None:
        raise NotImplementedError

