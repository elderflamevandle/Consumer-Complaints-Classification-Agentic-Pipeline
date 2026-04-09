from __future__ import annotations

from src.intake.pipeline import (
    EMPTY_COMPLAINT_PLACEHOLDER,
    LOW_CONFIDENCE_THRESHOLD,
    MAX_CLASSIFIER_INPUT_CHARS,
    MAX_SCRUBBED_TEXT_CHARS,
    prepare_intake,
)


def test_pii_scrub_before_llm() -> None:
    raw_text = 'My name is John Doe. Call me at 555-123-4567 or john@example.com.'

    prepared = prepare_intake(raw_text=raw_text, reviewer_available=True)
    payload = prepared.classifier_payload()

    assert payload['complaint_text'] == prepared.classifier_input_text
    assert raw_text != payload['complaint_text']
    assert '[PHONE]' in prepared.scrubbed_text
    assert '[EMAIL]' in prepared.scrubbed_text
    assert '555-123-4567' not in payload['complaint_text']
    assert 'john@example.com' not in payload['complaint_text'].lower()


def test_receipt_merge_contract() -> None:
    prepared = prepare_intake(
        raw_text='Card charged twice at local merchant.',
        receipt_text='Merchant: ACME Store   Amount: $45.32',
        reviewer_available=True,
    )

    assert prepared.receipt_attached is True
    assert '[RECEIPT_CONTEXT]' in prepared.classifier_input_text
    assert prepared.classifier_input_text.endswith('Merchant: ACME Store Amount: $45.32')


def test_low_confidence_scrub_routes_or_warns() -> None:
    ambiguous_text = 'my name is x and contact me about account issues'

    with_reviewer = prepare_intake(
        raw_text=ambiguous_text,
        reviewer_available=True,
    )
    assert with_reviewer.scrub_confidence < LOW_CONFIDENCE_THRESHOLD
    assert with_reviewer.route_to_human_review is True
    assert with_reviewer.review_policy == 'human_review_required'
    assert with_reviewer.high_risk_warning is False

    without_reviewer = prepare_intake(
        raw_text=ambiguous_text,
        reviewer_available=False,
    )
    assert without_reviewer.scrub_confidence < LOW_CONFIDENCE_THRESHOLD
    assert without_reviewer.route_to_human_review is False
    assert without_reviewer.review_policy == 'warning_continue'
    assert without_reviewer.high_risk_warning is True
    assert 'low_scrub_confidence_reviewer_unavailable_warning_continue' in without_reviewer.warnings


def test_empty_input_uses_placeholder_and_review_policy() -> None:
    prepared = prepare_intake(raw_text='', reviewer_available=True)

    assert prepared.scrubbed_text == EMPTY_COMPLAINT_PLACEHOLDER
    assert prepared.classifier_input_text == EMPTY_COMPLAINT_PLACEHOLDER
    assert prepared.route_to_human_review is True
    assert prepared.review_policy == 'human_review_required'
    assert 'empty_input' in prepared.warnings
    assert 'empty_complaint_placeholder_applied' in prepared.warnings
    assert prepared.trace['empty_input'] == 'true'


def test_long_input_is_truncated_before_downstream_stages() -> None:
    prepared = prepare_intake(
        raw_text='billing issue ' * 600,
        receipt_text='merchant details ' * 150,
        reviewer_available=True,
    )

    assert len(prepared.scrubbed_text) <= MAX_SCRUBBED_TEXT_CHARS
    assert len(prepared.classifier_input_text) <= MAX_CLASSIFIER_INPUT_CHARS
    assert 'complaint_text_truncated_for_model_safety' in prepared.warnings
    assert 'classifier_input_truncated_for_model_safety' in prepared.warnings
    assert prepared.trace['scrubbed_text_truncated'] == 'true'
    assert prepared.trace['classifier_input_truncated'] == 'true'
