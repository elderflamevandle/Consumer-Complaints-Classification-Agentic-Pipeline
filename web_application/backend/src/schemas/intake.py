"""Schemas for intake preprocessing and routing hints."""

from typing import Literal

from pydantic import BaseModel, Field

ReviewPolicy = Literal['auto', 'human_review_required', 'warning_continue']


class ScrubResult(BaseModel):
    raw_text: str
    scrubbed_text: str
    scrub_confidence: float = Field(ge=0.0, le=1.0)
    redaction_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class IntakePreparation(BaseModel):
    raw_text: str
    scrubbed_text: str
    classifier_input_text: str
    scrub_confidence: float = Field(ge=0.0, le=1.0)
    reviewer_available: bool
    route_to_human_review: bool
    high_risk_warning: bool
    review_policy: ReviewPolicy
    receipt_attached: bool
    warnings: list[str] = Field(default_factory=list)
    trace: dict[str, str] = Field(default_factory=dict)

    def classifier_payload(self) -> dict[str, str]:
        """LLM-facing payload intentionally excludes raw intake text."""
        return {'complaint_text': self.classifier_input_text}