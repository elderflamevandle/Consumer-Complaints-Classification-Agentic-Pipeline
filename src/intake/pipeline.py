"""Pre-LLM intake preparation contract for Phase 2."""

from __future__ import annotations

from src.intake.pii import scrub_pii
from src.intake.receipt_merge import merge_receipt_context
from src.schemas.intake import IntakePreparation, ReviewPolicy

LOW_CONFIDENCE_THRESHOLD = 0.70


def prepare_intake(
    *,
    raw_text: str,
    receipt_text: str | None = None,
    reviewer_available: bool = True,
) -> IntakePreparation:
    scrub_result = scrub_pii(raw_text)
    merged_text, receipt_attached = merge_receipt_context(
        scrub_result.scrubbed_text,
        receipt_text,
    )

    warnings = list(scrub_result.warnings)
    route_to_human_review = False
    high_risk_warning = False
    review_policy: ReviewPolicy = 'auto'

    if scrub_result.scrub_confidence < LOW_CONFIDENCE_THRESHOLD:
        if reviewer_available:
            route_to_human_review = True
            review_policy = 'human_review_required'
            warnings.append('low_scrub_confidence_requires_human_review')
        else:
            high_risk_warning = True
            review_policy = 'warning_continue'
            warnings.append('low_scrub_confidence_reviewer_unavailable_warning_continue')

    trace = {
        'scrubber': 'typed-token-v1',
        'receipt_merge': 'append-receipt-context',
        'classifier_input_source': 'scrubbed_text_plus_optional_receipt',
    }

    return IntakePreparation(
        raw_text=raw_text,
        scrubbed_text=scrub_result.scrubbed_text,
        classifier_input_text=merged_text,
        scrub_confidence=scrub_result.scrub_confidence,
        reviewer_available=reviewer_available,
        route_to_human_review=route_to_human_review,
        high_risk_warning=high_risk_warning,
        review_policy=review_policy,
        receipt_attached=receipt_attached,
        warnings=warnings,
        trace=trace,
    )