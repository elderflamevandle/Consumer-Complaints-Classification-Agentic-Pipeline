from __future__ import annotations

from typing import Any

from src.agents.remediator import RemediatorAgent
from src.schemas.classification import ClassificationResult
from src.schemas.root_cause import (
    AmbiguityFlag,
    EvidenceCitation,
    RootCauseEvidence,
    RootCauseResult,
)
from src.tools.mcp_policy_client import MCPPolicyClient


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


class ScriptedRunner:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[str] = []

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool = payload.get('tool')
        self.calls.append(str(tool))
        return self.response


def _classification() -> ClassificationResult:
    return ClassificationResult(
        product_type='CREDIT_CARD',
        issue_type='BILLING',
        severity='HIGH',
        compliance_risk='HIGH',
        confidence=0.82,
    )


def _diagnosis() -> RootCauseResult:
    return RootCauseResult(
        root_cause='Recurring dispute intake and escalation delays',
        ambiguity_flag=AmbiguityFlag.CLEAR,
        evidence=[
            RootCauseEvidence(
                rank=1,
                summary='Repeated billing disputes delayed',
                citation=EvidenceCitation(
                    id='C-101',
                    product='credit_card',
                    issue='billing',
                    date='2025-01-10',
                ),
                score=0.91,
            )
        ],
    )


def _policy_response() -> dict[str, Any]:
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


def test_mcp_tool_is_called_before_action_plan() -> None:
    runner = ScriptedRunner(_policy_response())
    mcp_client = MCPPolicyClient(request_runner=runner)
    transport = ScriptedTransport(
        ['{"action_plan":["Acknowledge complaint","Validate billing records"]}']
    )
    agent = RemediatorAgent(transport=transport, mcp_client=mcp_client)

    result = agent.propose_action(
        complaint_text='I keep getting duplicate card charges.',
        classification=_classification(),
        diagnosis=_diagnosis(),
        state_code='CA',
    )

    assert result.status == 'ok'
    assert runner.calls == ['get_sla_requirements']
    assert agent.call_order == ['mcp', 'llm']
    assert transport.calls == 1


def test_policy_unavailable_routes_human_review() -> None:
    runner = ScriptedRunner({'status': 'error', 'error': 'mcp_unavailable'})
    mcp_client = MCPPolicyClient(request_runner=runner)
    transport = ScriptedTransport(
        ['{"action_plan":["This should never be used because policy fails"]}']
    )
    agent = RemediatorAgent(transport=transport, mcp_client=mcp_client)

    result = agent.propose_action(
        complaint_text='Fraud claim with urgent timeline concerns.',
        classification=_classification(),
        diagnosis=_diagnosis(),
        state_code='CA',
    )

    assert result.status == 'POLICY_UNAVAILABLE'
    assert result.route == 'human_review'
    assert result.action_plan == []
    assert transport.calls == 0
    assert agent.call_order == ['mcp']


def test_remediation_cites_required_mcp_fields() -> None:
    runner = ScriptedRunner(_policy_response())
    mcp_client = MCPPolicyClient(request_runner=runner)
    transport = ScriptedTransport(
        [
            (
                '{"action_plan":['
                '"Confirm account security protections",'
                '"Issue provisional credit if criteria met",'
                '"Send written timeline and escalation path"'
                ']}'
            )
        ]
    )
    agent = RemediatorAgent(transport=transport, mcp_client=mcp_client)

    result = agent.propose_action(
        complaint_text='Unauthorized transactions keep appearing after prior report.',
        classification=_classification(),
        diagnosis=_diagnosis(),
        state_code='CA',
    )

    assert result.status == 'ok'
    assert result.route == 'continue'
    assert [step.order for step in result.action_plan] == [1, 2, 3]
    assert result.policy_citations['sla_window'] == '15 calendar days'
    assert isinstance(result.policy_citations['required_actions'], list)
    assert result.policy_citations['regulatory_basis'] == 'Regulation Z billing error framework'

