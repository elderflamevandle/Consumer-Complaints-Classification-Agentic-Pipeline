"""
Complaint and pipeline-stage document models.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ComplaintStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INTERRUPTED = "interrupted"   # Awaiting human review
    COMPLETE = "complete"
    REJECTED = "rejected"
    FAILED = "failed"


class SeverityLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplianceRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_type: str = "OTHER"
    issue_type: str = "OTHER"
    severity: SeverityLevel = SeverityLevel.LOW
    compliance_risk: ComplianceRisk = ComplianceRisk.LOW
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RemediationStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order: int
    action: str
    policy_reference: str


class PipelineStageDocument(BaseModel):
    """One node execution within a complaint pipeline run."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    complaint_id: str
    node: str          # e.g. "intake", "classifier", "root_cause"
    status: str = "pending"   # pending | running | completed | failed
    model_used: Optional[str] = None
    latency_ms: int = 0
    tokens_used: int = 0
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class ComplaintDocument(BaseModel):
    """Main complaint record stored in MongoDB."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    user_id: str
    complaint_text: str          # Original (may contain PII)
    scrubbed_text: Optional[str] = None   # PII-redacted version
    state_code: str = "CA"
    status: ComplaintStatus = ComplaintStatus.PENDING
    assigned_team: Optional[str] = None

    # Pipeline outputs
    classification: Optional[ClassificationResult] = None
    root_cause: Optional[str] = None
    root_cause_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    remediation_steps: List[RemediationStep] = Field(default_factory=list)
    policy_citations: Optional[Dict[str, Any]] = None
    response_draft: Optional[str] = None
    audit_verdict: Optional[str] = None    # PASS | FAIL | ESCALATE
    explanation: Optional[str] = None

    # Review (HITL)
    review_required: bool = False
    review_action: Optional[str] = None   # approve | edit | reject
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)

    @classmethod
    def from_mongo(cls, data: dict) -> "ComplaintDocument":
        return cls.model_validate(data)
