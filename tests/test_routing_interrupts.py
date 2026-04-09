from __future__ import annotations

from src.graph.interrupts import apply_reviewer_action, get_interrupt_payload
from src.graph.routing import build_routing_state
from src.graph.state import ReviewDecision
from src.intake.pipeline import prepare_intake
from src.schemas.classification import ClassificationResult


def _classification(
    *,
    confidence: float,
    risk: str,
    severity: str = 'MEDIUM',
) -> ClassificationResult:
    return ClassificationResult(
        product_type='CREDIT_CARD',
        issue_type='BILLING',
        severity=severity,
        compliance_risk=risk,
        confidence=confidence,
    )


def test_route_low_confidence_or_high_risk() -> None:
    intake = prepare_intake(raw_text='duplicate charge on my credit card')

    low_confidence = build_routing_state(
        thread_id='thread-1',
        intake=intake,
        classification=_classification(confidence=0.69, risk='LOW'),
    )
    assert low_confidence.route == 'human_review'

    high_risk = build_routing_state(
        thread_id='thread-2',
        intake=intake,
        classification=_classification(confidence=0.92, risk='HIGH'),
    )
    assert high_risk.route == 'human_review'

    safe_path = build_routing_state(
        thread_id='thread-3',
        intake=intake,
        classification=_classification(confidence=0.92, risk='LOW', severity='LOW'),
    )
    assert safe_path.route == 'continue'


def test_reviewer_actions_approve_edit_reject() -> None:
    intake = prepare_intake(raw_text='fraud concern and unauthorized charge')
    base_state = build_routing_state(
        thread_id='thread-42',
        intake=intake,
        classification=_classification(confidence=0.61, risk='HIGH', severity='HIGH'),
    )

    approved = apply_reviewer_action(base_state, ReviewDecision(action='approve'))
    assert approved.review_action == 'approve'
    assert approved.route == 'continue'

    edited_result = _classification(confidence=0.84, risk='MEDIUM')
    edited = apply_reviewer_action(
        base_state,
        ReviewDecision(action='edit', edited_classification=edited_result),
    )
    assert edited.review_action == 'edit'
    assert edited.route == 'continue'
    assert edited.classification.confidence == 0.84

    rejected = apply_reviewer_action(base_state, ReviewDecision(action='reject'))
    assert rejected.review_action == 'reject'
    assert rejected.route == 'rejected'


def test_resume_same_thread_after_review() -> None:
    intake = prepare_intake(raw_text='my account has suspicious activity')
    state = build_routing_state(
        thread_id='thread-99',
        intake=intake,
        classification=_classification(confidence=0.62, risk='HIGH'),
    )

    payload = get_interrupt_payload(state)
    assert payload.thread_id == 'thread-99'

    decision = ReviewDecision(
        action='edit',
        edited_classification=_classification(confidence=0.80, risk='MEDIUM'),
    )
    resumed = apply_reviewer_action(state, decision)

    assert resumed.thread_id == 'thread-99'
    assert resumed.route == 'continue'
    assert resumed.review_required is False
    assert any(event.startswith('thread-99:review_') for event in resumed.events)


def test_ambiguous_intake_review_flow_preserves_same_thread_after_approve() -> None:
    intake = prepare_intake(
        raw_text='contact me about my account issue',
        reviewer_available=True,
    )
    assert intake.review_policy == 'human_review_required'

    state = build_routing_state(
        thread_id='thread-ambiguous',
        intake=intake,
        classification=_classification(confidence=0.65, risk='MEDIUM'),
    )
    assert state.route == 'human_review'

    resumed = apply_reviewer_action(state, ReviewDecision(action='approve'))

    assert resumed.thread_id == 'thread-ambiguous'
    assert resumed.route == 'continue'
    assert resumed.review_action == 'approve'
