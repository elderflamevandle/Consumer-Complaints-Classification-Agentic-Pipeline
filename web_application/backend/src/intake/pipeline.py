"""Pre-LLM intake preparation contract for Phase 2."""

from __future__ import annotations

from src.intake.pii import scrub_pii
from src.intake.receipt_merge import merge_receipt_context
from src.schemas.intake import IntakePreparation, ReviewPolicy

LOW_CONFIDENCE_THRESHOLD = 0.70
EMPTY_COMPLAINT_PLACEHOLDER = 'No complaint details were provided.'
MAX_SCRUBBED_TEXT_CHARS = 4_000
MAX_CLASSIFIER_INPUT_CHARS = 4_500


def _truncate_text(text: str, *, limit: int, suffix: str = ' [TRUNCATED]') -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False

    available = max(limit - len(suffix), 1)
    truncated = f'{text[:available].rstrip()}{suffix}'
    return truncated, True


def prepare_intake(
    *,
    raw_text: str,
    receipt_text: str | None = None,
    reviewer_available: bool = True,
) -> IntakePreparation:
    scrub_result = scrub_pii(raw_text)
    warnings = list(scrub_result.warnings)
    scrubbed_text = scrub_result.scrubbed_text

    if not scrubbed_text:
        scrubbed_text = EMPTY_COMPLAINT_PLACEHOLDER
        warnings.append('empty_complaint_placeholder_applied')

    scrubbed_text, scrubbed_truncated = _truncate_text(
        scrubbed_text,
        limit=MAX_SCRUBBED_TEXT_CHARS,
    )
    if scrubbed_truncated:
        warnings.append('complaint_text_truncated_for_model_safety')

    merged_text, receipt_attached = merge_receipt_context(
        scrubbed_text,
        receipt_text,
    )
    merged_text, classifier_input_truncated = _truncate_text(
        merged_text,
        limit=MAX_CLASSIFIER_INPUT_CHARS,
    )
    if classifier_input_truncated:
        warnings.append('classifier_input_truncated_for_model_safety')

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
        'raw_input_length': str(len(raw_text)),
        'scrubbed_input_length': str(len(scrubbed_text)),
        'classifier_input_length': str(len(merged_text)),
        'empty_input': str(not raw_text.strip()).lower(),
        'scrubbed_text_truncated': str(scrubbed_truncated).lower(),
        'classifier_input_truncated': str(classifier_input_truncated).lower(),
    }

    return IntakePreparation(
        raw_text=raw_text,
        scrubbed_text=scrubbed_text,
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
