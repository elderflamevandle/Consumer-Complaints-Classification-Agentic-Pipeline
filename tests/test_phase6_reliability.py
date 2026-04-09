from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from src.agents.remediator import RemediationResult, RemediationStep
from src.intake.pipeline import (
    EMPTY_COMPLAINT_PLACEHOLDER,
    MAX_CLASSIFIER_INPUT_CHARS,
    MAX_SCRUBBED_TEXT_CHARS,
    prepare_intake,
)
from src.schemas.auditor import ResponseAuditResult
from src.schemas.classification import ClassificationResult
from src.schemas.explainer import ExplanationBullet, ExplanationResult
from src.schemas.response import ResponseDraft
from src.schemas.root_cause import AmbiguityFlag, EvidenceCitation, RootCauseEvidence, RootCauseResult
from src.ui.telemetry import StageStatus


def test_prepare_intake_handles_empty_and_very_long_inputs_without_crash() -> None:
    empty = prepare_intake(raw_text='', reviewer_available=True)

    assert empty.scrubbed_text == EMPTY_COMPLAINT_PLACEHOLDER
    assert empty.classifier_input_text == EMPTY_COMPLAINT_PLACEHOLDER
    assert empty.route_to_human_review is True
    assert empty.review_policy == 'human_review_required'
    assert 'empty_input' in empty.warnings
    assert 'empty_complaint_placeholder_applied' in empty.warnings

    very_long = prepare_intake(
        raw_text='duplicate charge and unexplained fee ' * 700,
        receipt_text='merchant ledger row ' * 200,
        reviewer_available=True,
    )

    assert len(very_long.scrubbed_text) <= MAX_SCRUBBED_TEXT_CHARS
    assert len(very_long.classifier_input_text) <= MAX_CLASSIFIER_INPUT_CHARS
    assert 'complaint_text_truncated_for_model_safety' in very_long.warnings
    assert 'classifier_input_truncated_for_model_safety' in very_long.warnings
    assert very_long.trace['scrubbed_text_truncated'] == 'true'
    assert very_long.trace['classifier_input_truncated'] == 'true'


class _FakeClassifierAgent:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.used_fallback = False

    def classify(self, _intake: Any) -> ClassificationResult:
        return ClassificationResult(
            product_type='CREDIT_CARD',
            issue_type='BILLING',
            severity='MEDIUM',
            compliance_risk='MEDIUM',
            confidence=0.86,
        )


class _FakeRootCauseAgent:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.used_fallback = True
        self.last_model = 'heuristic-fallback'

    def diagnose(self, _complaint_text: str, *, thread_id: str | None = None) -> RootCauseResult:
        del thread_id
        return RootCauseResult(
            root_cause='Fallback evidence indicates a duplicate billing pattern.',
            evidence=[
                RootCauseEvidence(
                    rank=1,
                    summary='Similar duplicate billing complaint found.',
                    citation=EvidenceCitation(
                        id='case-1',
                        product='CREDIT_CARD',
                        issue='BILLING',
                        date='2026-04-08',
                    ),
                    score=0.7,
                )
            ],
            ambiguity_flag=AmbiguityFlag.AMBIGUOUS,
        )


class _FakeRemediatorAgent:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.last_model = 'remediator-test'

    def propose_action(self, **_kwargs: Any) -> RemediationResult:
        return RemediationResult(
            status='ok',
            route='continue',
            action_plan=[
                RemediationStep(
                    order=1,
                    action='Review the disputed transaction and confirm the duplicate charge.',
                    policy_reference='Reg E',
                )
            ],
            policy_citations={
                'sla_window': '10 business days',
                'regulatory_basis': 'Reg E',
            },
        )


class _FakeWriterAgent:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.used_fallback = False
        self.last_model = 'writer-test'

    def compose_response(self, **_kwargs: Any) -> ResponseDraft:
        return ResponseDraft(
            resolution_statement='We will review the duplicate charge concern.',
            acknowledgment='We understand the billing concern you reported.',
            findings='Current findings indicate a duplicate charge pattern that needs review.',
            action_steps=['Review the transaction history and disputed amount.'],
            timeline_next_steps='We will follow up within 10 business days.',
            policy_citation_labels=['Reg E'],
            critique_items_addressed=[],
        )


class _FakeAuditorAgent:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.used_fallback = False
        self.last_model = 'auditor-test'

    def review_response(self, **_kwargs: Any) -> ResponseAuditResult:
        return ResponseAuditResult(
            verdict='PASS',
            reason_codes=[],
            critique_summary='Draft passes audit checks.',
            must_fix_items=[],
            rewrite_recommended=False,
        )


class _FakeExplainerAgent:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.used_fallback = False
        self.last_model = 'explainer-test'

    def summarize_chain(self, **_kwargs: Any) -> ExplanationResult:
        return ExplanationResult(
            bullets=[
                ExplanationBullet(stage='classification', summary='Classified as billing.', citations=[]),
                ExplanationBullet(stage='diagnosis', summary='Fallback diagnosis used.', citations=['case-1']),
                ExplanationBullet(stage='remediation', summary='Proposed a policy-grounded review.', citations=['Reg E']),
                ExplanationBullet(stage='response', summary='Drafted customer response.', citations=[]),
                ExplanationBullet(stage='audit', summary='Audit passed.', citations=[]),
            ]
        )


class _FakeAuditLogger:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.events: list[dict[str, object]] = []

    def log_node_outcome(
        self,
        *,
        thread_id: str,
        node: str,
        model: str,
        latency_ms: int,
        decision: str,
        scrubbed_text: str,
    ) -> bool:
        self.events.append(
            {
                'thread_id': thread_id,
                'node': node,
                'timestamp': '2026-04-08T10:00:00Z',
                'decision': decision,
                'model': model,
                'latency_ms': latency_ms,
                'scrubbed_text': scrubbed_text,
            }
        )
        return True

    def fetch_events(self, *, thread_id: str) -> list[dict[str, object]]:
        return [event for event in self.events if event['thread_id'] == thread_id]


def test_runtime_surfaces_non_critical_fallback_warning_without_failing_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.ui import runtime as runtime_module

    monkeypatch.setattr(runtime_module, 'ClassifierAgent', _FakeClassifierAgent)
    monkeypatch.setattr(runtime_module, 'RootCauseAgent', _FakeRootCauseAgent)
    monkeypatch.setattr(runtime_module, 'RemediatorAgent', _FakeRemediatorAgent)
    monkeypatch.setattr(runtime_module, 'WriterAgent', _FakeWriterAgent)
    monkeypatch.setattr(runtime_module, 'AuditorAgent', _FakeAuditorAgent)
    monkeypatch.setattr(runtime_module, 'ExplainerAgent', _FakeExplainerAgent)
    monkeypatch.setattr(runtime_module, 'AuditLogger', _FakeAuditLogger)

    snapshot = runtime_module.run_complaint(
        complaint_text='My card was charged twice for the same purchase.',
        db_connect_fn=lambda _path: sqlite3.connect(':memory:'),
    )

    assert snapshot.run_status == 'completed'
    root_cause_stage = next(stage for stage in snapshot.stages if stage.stage_name == 'root_cause')
    assert root_cause_stage.status == StageStatus.COMPLETED
    assert root_cause_stage.model == 'heuristic-fallback'
    assert root_cause_stage.artifacts['warnings'] == ['root_cause_used_fallback']
    assert snapshot.error_message is None
