"""Deterministic routing policy for low-confidence or high-risk classifications."""

from __future__ import annotations

from src.graph.state import ReviewInterruptPayload, RoutingState
from src.schemas.classification import ClassificationResult, ComplianceRisk, SeverityLevel
from src.schemas.intake import IntakePreparation

HUMAN_REVIEW_THRESHOLD = 0.70


def _interrupt_reason(classification: ClassificationResult) -> str:
    reasons: list[str] = []
    if classification.confidence < HUMAN_REVIEW_THRESHOLD:
        reasons.append('confidence_below_threshold')
    if classification.compliance_risk == ComplianceRisk.HIGH:
        reasons.append('high_compliance_risk')
    if classification.severity == SeverityLevel.CRITICAL:
        reasons.append('critical_severity')
    return ','.join(reasons) if reasons else 'none'


def should_route_to_human_review(classification: ClassificationResult) -> bool:
    return (
        classification.confidence < HUMAN_REVIEW_THRESHOLD
        or classification.compliance_risk == ComplianceRisk.HIGH
        or classification.severity == SeverityLevel.CRITICAL
    )


def build_routing_state(
    *,
    thread_id: str,
    intake: IntakePreparation,
    classification: ClassificationResult,
) -> RoutingState:
    review_required = should_route_to_human_review(classification)
    if review_required:
        payload = ReviewInterruptPayload(
            thread_id=thread_id,
            reason=_interrupt_reason(classification),
            confidence=classification.confidence,
            compliance_risk=classification.compliance_risk.value,
            classification=classification,
        )
        return RoutingState(
            thread_id=thread_id,
            intake=intake,
            classification=classification,
            route='human_review',
            review_required=True,
            interrupt_payload=payload,
            events=[f'{thread_id}:route_human_review'],
        )

    return RoutingState(
        thread_id=thread_id,
        intake=intake,
        classification=classification,
        route='continue',
        review_required=False,
        events=[f'{thread_id}:route_continue'],
    )