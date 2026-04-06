from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.auditor import AuditorAgent
from src.agents.remediator import RemediationResult, RemediationStep
from src.agents.writer import WriterAgent
from src.graph.response_loop import execute_response_loop
from src.graph.routing import build_routing_state
from src.intake.pipeline import prepare_intake
from src.schemas.auditor import AuditReasonCode, AuditVerdict
from src.schemas.classification import ClassificationResult
from src.schemas.response import ResponseDraft
from src.schemas.root_cause import (
    AmbiguityFlag,
    EvidenceCitation,
    RootCauseEvidence,
    RootCauseResult,
)
from src.tools.audit_logger import AuditLogger


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
        confidence=0.92,
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
            )
        ],
        policy_citations={
            'sla_window': '15 calendar days',
            'required_actions': ['Acknowledge complaint receipt'],
            'regulatory_basis': 'Regulation Z billing error framework',
        },
    )


def test_auditor_returns_reason_coded_fail() -> None:
    agent = AuditorAgent(transport=ScriptedTransport(['not-json']))
    draft = ResponseDraft(
        resolution_statement='Pending.',
        acknowledgment='This is our fault and we guarantee a refund.',
        findings='We definitely caused this issue.',
        action_steps=['Close the case immediately.'],
        timeline_next_steps='You will definitely hear back tomorrow.',
        policy_citation_labels=[],
        critique_items_addressed=[],
    )

    result = agent.review_response(
        draft=draft,
        remediation=_remediation(),
    )

    assert result.verdict == AuditVerdict.FAIL
    assert AuditReasonCode.MISSING_POLICY_CITATION in result.reason_codes
    assert AuditReasonCode.OVERCOMMITMENT in result.reason_codes
    assert AuditReasonCode.UNCLEAR_RESOLUTION in result.reason_codes
    assert result.rewrite_recommended is True


def test_fail_routes_back_to_writer_until_retry_cap() -> None:
    intake = prepare_intake(raw_text='My card dispute is still unresolved after multiple updates.')
    base_state = build_routing_state(
        thread_id='thread-104',
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
                '{"resolution_statement":"Pending.","acknowledgment":"We received your complaint.",'
                '"findings":"We are still looking into the matter.",'
                '"action_steps":["Review the account"],'
                '"timeline_next_steps":"We will provide another update soon.",'
                '"policy_citation_labels":[],"critique_items_addressed":[]}'
            ),
            (
                '{"resolution_statement":"Pending.","acknowledgment":"We received your complaint.",'
                '"findings":"We are still looking into the matter.",'
                '"action_steps":["Review the account"],'
                '"timeline_next_steps":"We will provide another update soon.",'
                '"policy_citation_labels":[],"critique_items_addressed":[]}'
            ),
        ]
    )
    auditor_transport = ScriptedTransport(['not-json', 'not-json', 'not-json'])

    final_state = execute_response_loop(
        base_state,
        diagnosis=_diagnosis(),
        remediation=_remediation(),
        writer=WriterAgent(transport=writer_transport),
        auditor=AuditorAgent(transport=auditor_transport),
    )

    assert final_state.route == 'human_review'
    assert final_state.review_required is True
    assert final_state.response_loop_status == 'escalated'
    assert final_state.rewrite_count == 2
    assert len(final_state.response_cycles) == 3
    assert final_state.unresolved_issues
    assert any(event.startswith('thread-104:response_rewrite_') for event in final_state.events)


def test_pass_routes_continue_and_logs_writer_auditor_events(tmp_path: Path) -> None:
    logger = AuditLogger(db_path=tmp_path / 'audit.db')
    intake = prepare_intake(raw_text='Duplicate credit card charge and no written update.')
    base_state = build_routing_state(
        thread_id='thread-105',
        intake=intake,
        classification=_classification(),
        audit_logger=logger,
    )
    writer_transport = ScriptedTransport(
        [
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
            )
        ]
    )
    auditor_transport = ScriptedTransport(
        [
            (
                '{"verdict":"PASS","reason_codes":[],"critique_summary":"Response meets '
                'review standards.",'
                '"must_fix_items":[],"rewrite_recommended":false}'
            )
        ]
    )

    final_state = execute_response_loop(
        base_state,
        diagnosis=_diagnosis(),
        remediation=_remediation(),
        writer=WriterAgent(transport=writer_transport, audit_logger=logger),
        auditor=AuditorAgent(transport=auditor_transport, audit_logger=logger),
    )

    assert final_state.route == 'continue'
    assert final_state.review_required is False
    assert final_state.final_audit is not None
    assert final_state.final_audit.verdict == AuditVerdict.PASS

    events = logger.fetch_events(thread_id='thread-105')
    nodes = [event['node'] for event in events]
    assert 'writer' in nodes
    assert 'auditor' in nodes
