from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.remediator import RemediatorAgent
from src.agents.root_cause import RootCauseAgent
from src.graph.interrupts import apply_reviewer_action
from src.graph.routing import build_routing_state
from src.graph.state import ReviewDecision
from src.intake.pipeline import prepare_intake
from src.schemas.classification import ClassificationResult
from src.tools.audit_logger import AuditLogger
from src.tools.mcp_policy_client import MCPPolicyClient
from src.tools.vector_search import RetrievedCase


class ScriptedTransport:
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs
        self.calls = 0

    def __call__(self, **_: Any) -> dict[str, Any]:
        self.calls += 1
        if not self.outputs:
            return {'content': '{}', 'usage': {'total_tokens': 10}}
        output = self.outputs.pop(0)
        return {'content': output, 'usage': {'total_tokens': 10}}


def _classification() -> ClassificationResult:
    return ClassificationResult(
        product_type='CREDIT_CARD',
        issue_type='BILLING',
        severity='HIGH',
        compliance_risk='HIGH',
        confidence=0.61,
    )


def _mcp_response(_: dict[str, Any]) -> dict[str, Any]:
    return {
        'status': 'ok',
        'result': {
            'issue_type': 'BILLING',
            'state_code': 'CA',
            'sla_window': '15 calendar days',
            'required_actions': [
                'Acknowledge complaint receipt',
                'Validate disputed transaction details',
            ],
            'regulatory_basis': 'Regulation Z billing error framework',
        },
    }


def test_phase3_nodes_emit_thread_consistent_events(tmp_path: Path) -> None:
    logger = AuditLogger(db_path=tmp_path / 'audit.db')
    intake = prepare_intake(
        raw_text='Alice reported duplicate charge. Contact alice@example.com or 555-123-4567.',
        reviewer_available=True,
    )

    classification = _classification()
    routed = build_routing_state(
        thread_id='thread-77',
        intake=intake,
        classification=classification,
        audit_logger=logger,
    )
    resumed = apply_reviewer_action(
        routed,
        ReviewDecision(action='approve'),
        audit_logger=logger,
    )
    assert resumed.route == 'continue'

    retrieved = [
        RetrievedCase(
            id='C-404',
            product='credit_card',
            issue='billing',
            date='2025-01-20',
            state='CA',
            narrative='Duplicate transaction dispute not resolved quickly',
            score=0.88,
        )
    ]
    root_transport = ScriptedTransport(
        [
            (
                '{"root_cause":"Recurring dispute handling delay",'
                '"ambiguity_flag":"CLEAR",'
                '"evidence":[{"rank":1,"summary":"Repeat billing disputes",'
                '"score":0.88,'
                '"citation":{"id":"C-404","product":"credit_card","issue":"billing","date":"2025-01-20"}}]}'
            )
        ]
    )
    root_agent = RootCauseAgent(
        transport=root_transport,
        retriever=lambda **_: retrieved,
        audit_logger=logger,
    )
    diagnosis = root_agent.diagnose(intake.scrubbed_text, thread_id='thread-77')

    rem_transport = ScriptedTransport(
        ['{"action_plan":["Confirm dispute evidence","Issue provisional credit"]}']
    )
    remediator = RemediatorAgent(
        transport=rem_transport,
        mcp_client=MCPPolicyClient(request_runner=_mcp_response),
        audit_logger=logger,
    )
    rem_result = remediator.propose_action(
        complaint_text=intake.scrubbed_text,
        classification=classification,
        diagnosis=diagnosis,
        state_code='CA',
        thread_id='thread-77',
    )
    assert rem_result.status == 'ok'

    events = logger.fetch_events(thread_id='thread-77')
    assert len(events) >= 4
    assert all(event['thread_id'] == 'thread-77' for event in events)

    nodes = [event['node'] for event in events]
    assert 'routing' in nodes
    assert 'review_interrupt' in nodes
    assert 'root_cause' in nodes
    assert 'remediator' in nodes

    combined = ' '.join(event['scrubbed_text'] for event in events).lower()
    assert 'alice@example.com' not in combined
    assert '555-123-4567' not in combined

