"""Graph state models for routing and human-review interrupts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.classification import ClassificationResult
from src.schemas.intake import IntakePreparation

ReviewerAction = Literal['approve', 'edit', 'reject']
RouteDecision = Literal['continue', 'human_review', 'rejected']


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
