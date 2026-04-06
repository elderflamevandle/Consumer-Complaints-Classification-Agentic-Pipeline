"""Graph state models for routing and human-review interrupts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.auditor import ResponseAuditResult
from src.schemas.classification import ClassificationResult
from src.schemas.explainer import ExplanationResult
from src.schemas.intake import IntakePreparation
from src.schemas.response import ResponseDraft

ReviewerAction = Literal['approve', 'edit', 'reject']
RouteDecision = Literal['continue', 'human_review', 'rejected']
ResponseLoopStatus = Literal['not_started', 'needs_rewrite', 'approved', 'escalated']


class ReviewDecision(BaseModel):
    action: ReviewerAction
    reviewer_notes: str | None = None
    edited_classification: ClassificationResult | None = None


class ReviewInterruptPayload(BaseModel):
    thread_id: str
    reason: str
    confidence: float
    compliance_risk: str
    allowed_actions: tuple[str, str, str] = ('approve', 'edit', 'reject')
    classification: ClassificationResult


class ResponseCycleTrace(BaseModel):
    cycle_number: int = Field(ge=1)
    verdict: str
    fail_codes: list[str] = Field(default_factory=list)
    critique_summary: str


class RoutingState(BaseModel):
    thread_id: str
    intake: IntakePreparation
    classification: ClassificationResult
    route: RouteDecision
    review_required: bool
    interrupt_payload: ReviewInterruptPayload | None = None
    review_action: ReviewerAction | None = None
    events: list[str] = Field(default_factory=list)
    last_logged_nodes: list[str] = Field(default_factory=list)
    message_history: list[str] = Field(default_factory=list)
    latest_response_draft: ResponseDraft | None = None
    unresolved_issues: list[str] = Field(default_factory=list)
    rewrite_count: int = Field(default=0, ge=0)
    response_cycles: list[ResponseCycleTrace] = Field(default_factory=list)
    response_loop_status: ResponseLoopStatus = 'not_started'
    final_audit: ResponseAuditResult | None = None
    final_explanation: ExplanationResult | None = None
