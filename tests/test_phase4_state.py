from __future__ import annotations

from typing import Any

from src.agents.auditor import AuditorAgent
from src.agents.remediator import RemediationResult, RemediationStep
from src.agents.writer import WriterAgent
from src.graph.response_loop import execute_response_loop
from src.graph.routing import build_routing_state
from src.intake.pipeline import prepare_intake
from src.schemas.classification import ClassificationResult
from src.schemas.root_cause import (
    AmbiguityFlag,
    EvidenceCitation,
    RootCauseEvidence,
    RootCauseResult,
)


class ScriptedTransport:
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs
        self.calls = 0

    def __call__(self, **_: Any) -> dict[str, Any]:
        self.calls += 1
        if not self.outputs:
            return {'content': '{}', 'usage': {'total_tokens': 12}}
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return {'content': output, 'usage': {'total_tokens': 12}}


def _classification() -> ClassificationResult:
    return ClassificationResult(
        product_type='CREDIT_CARD',
        issue_type='BILLING',
        severity='LOW',
        compliance_risk='LOW',
        confidence=0.91,
    )


def _diagnosis() -> RootCauseResult:
    return RootCauseResult(
        root_cause='Recurring dispute handling delay',
        ambiguity_flag=AmbiguityFlag.CLEAR,
        evidence=[
            RootCauseEvidence(
                rank=1,
                summary='Prior billing disputes were not resolved on first review.',
                citation=EvidenceCitation(
                    id='R-101',
                    product='credit_card',
                    issue='billing',
                    date='2025-01-14',
                ),
                score=0.91,
            )
        ],
    )


def _remediation() -> RemediationResult:
    return RemediationResult(
        status='ok',
        route='continue',
        action_plan=[
            RemediationStep(
                order=1,
                action='Acknowledge the dispute and confirm the review path.',
                policy_reference='Regulation Z billing error framework',
            ),
            RemediationStep(
                order=2,
                action='Provide the next written status update within the policy window.',
                policy_reference='Regulation Z billing error framework',
            ),
        ],
        policy_citations={
            'sla_window': '15 calendar days',
            'required_actions': ['Acknowledge complaint receipt'],
            'regulatory_basis': 'Regulation Z billing error framework',
        },
    )


def test_response_loop_state_carries_unresolved_issues_across_rewrites() -> None:
    intake = prepare_intake(raw_text='My dispute still has not been resolved.')
    base_state = build_routing_state(
        thread_id='thread-204',
        intake=intake,
        classification=_classification(),
    )
    writer_transport = ScriptedTransport(
        [
            (
                '{"resolution_statement":"Pending.","acknowledgment":"We received your complaint.",'
                '"findings":"We are still looking into the matter.",'
                '"action_steps":["Review the account"],'
                '"timeline_next_steps":"We will provide another update soon.",'
                '"policy_citation_labels":[],"critique_items_addressed":[]}'
            ),
            (
                '{"resolution_statement":"We will review the disputed charges using the '
                'required billing-dispute process.",'
                '"acknowledgment":"We understand the concern described in your complaint.",'
                '"findings":"Current findings point to a delay in dispute handling.",'
                '"action_steps":["Review the disputed transactions","Send the next '
                'written update"],'
                '"timeline_next_steps":"We will follow up within 15 calendar days.",'
                '"policy_citation_labels":["SLA window: 15 calendar days","Regulatory '
                'basis: Regulation Z billing error framework"],'
                '"critique_items_addressed":[]}'
            ),
        ]
    )
    auditor_transport = ScriptedTransport(['not-json', 'not-json'])

    final_state = execute_response_loop(
        base_state,
        diagnosis=_diagnosis(),
        remediation=_remediation(),
        writer=WriterAgent(transport=writer_transport),
        auditor=AuditorAgent(transport=auditor_transport),
    )

    assert final_state.route == 'continue'
    assert final_state.response_loop_status == 'approved'
    assert final_state.rewrite_count == 1
    assert len(final_state.response_cycles) == 2
    assert final_state.response_cycles[0].fail_codes
    assert final_state.latest_response_draft is not None
    assert final_state.latest_response_draft.critique_items_addressed
    assert len(final_state.message_history) == 4


def test_cycle_trace_persists_verdict_codes_and_final_resolution() -> None:
    intake = prepare_intake(raw_text='My card dispute still needs attention.')
    base_state = build_routing_state(
        thread_id='thread-205',
        intake=intake,
        classification=_classification(),
    )
    writer_transport = ScriptedTransport(
        [
            (
                '{"resolution_statement":"Pending.","acknowledgment":"We received your complaint.",'
                '"findings":"We are still looking into the matter.",'
                '"action_steps":["Review the account"],'
                '"timeline_next_steps":"We will provide another update soon.",'
                '"policy_citation_labels":[],"critique_items_addressed":[]}'
            ),
            (
                '{"resolution_statement":"We will review the disputed charges using the '
                'required billing-dispute process.",'
                '"acknowledgment":"We understand the concern described in your complaint.",'
                '"findings":"Current findings point to a delay in dispute handling.",'
                '"action_steps":["Review the disputed transactions","Send the next '
                'written update"],'
                '"timeline_next_steps":"We will follow up within 15 calendar days.",'
                '"policy_citation_labels":["SLA window: 15 calendar days","Regulatory '
                'basis: Regulation Z billing error framework"],'
                '"critique_items_addressed":[]}'
            ),
        ]
    )
    auditor_transport = ScriptedTransport(['not-json', 'not-json'])

    final_state = execute_response_loop(
        base_state,
        diagnosis=_diagnosis(),
        remediation=_remediation(),
        writer=WriterAgent(transport=writer_transport),
        auditor=AuditorAgent(transport=auditor_transport),
    )

    assert final_state.response_cycles[0].verdict == 'FAIL'
    assert 'UNCLEAR_RESOLUTION' in final_state.response_cycles[0].fail_codes
    assert final_state.response_cycles[-1].verdict == 'PASS'
    assert final_state.latest_response_draft is not None
    assert final_state.latest_response_draft.resolution_statement
    assert len(final_state.message_history) <= 6
