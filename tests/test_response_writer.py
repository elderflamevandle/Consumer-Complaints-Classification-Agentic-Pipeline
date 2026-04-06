from __future__ import annotations

from typing import Any

from src.agents.remediator import RemediationResult, RemediationStep
from src.agents.writer import WriterAgent
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
        severity='HIGH',
        compliance_risk='HIGH',
        confidence=0.88,
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
                action=(
                    'Validate the disputed transaction details and issue the next '
                    'written update.'
                ),
                policy_reference='Regulation Z billing error framework',
            ),
        ],
        policy_citations={
            'sla_window': '15 calendar days',
            'required_actions': [
                'Acknowledge complaint receipt',
                'Validate disputed transaction details',
            ],
            'regulatory_basis': 'Regulation Z billing error framework',
        },
    )


def test_writer_generates_four_block_response() -> None:
    transport = ScriptedTransport(
        [
            (
                '{"resolution_statement":"We will review the disputed charges under the '
                'required complaint process.",'
                '"acknowledgment":"We understand the concern described in your complaint.",'
                '"findings":"Current findings point to a delay in dispute handling.",'
                '"action_steps":["Confirm the disputed transactions in writing","Share '
                'the next review update"],'
                '"timeline_next_steps":"We will provide the next update within 15 calendar days.",'
                '"policy_citation_labels":["Regulatory basis: Regulation Z billing '
                'error framework"],'
                '"critique_items_addressed":[]}'
            )
        ]
    )
    agent = WriterAgent(transport=transport)

    result = agent.compose_response(
        complaint_text='My card was charged twice and the dispute has stalled.',
        classification=_classification(),
        diagnosis=_diagnosis(),
        remediation=_remediation(),
    )

    rendered = result.render_text()
    assert result.resolution_statement
    assert rendered.count('Acknowledgment:') == 1
    assert rendered.count('Findings:') == 1
    assert rendered.count('Action Steps:') == 1
    assert rendered.count('Timeline / Next Steps:') == 1
    assert '1. Confirm the disputed transactions in writing' in rendered


def test_writer_includes_resolution_statement_and_policy_labels() -> None:
    transport = ScriptedTransport(
        [
            (
                '{"resolution_statement":"We will review the account and follow the '
                'required billing-dispute steps.",'
                '"acknowledgment":"We appreciate the opportunity to review your concern.",'
                '"findings":"Current findings point to a repeat dispute-handling delay.",'
                '"action_steps":["Review the account activity","Send the next written update"],'
                '"timeline_next_steps":"We will follow up within the required review window.",'
                '"policy_citation_labels":[],"critique_items_addressed":[]}'
            )
        ]
    )
    agent = WriterAgent(transport=transport)

    result = agent.compose_response(
        complaint_text='I reported duplicate charges and still need an answer.',
        classification=_classification(),
        diagnosis=_diagnosis(),
        remediation=_remediation(),
    )

    rendered = result.render_text()
    assert result.resolution_statement in rendered
    assert 'Policy Labels:' in rendered
    assert 'SLA window: 15 calendar days' in rendered
    assert 'Regulatory basis: Regulation Z billing error framework' in rendered


def test_writer_blocks_overcommitment_language() -> None:
    transport = ScriptedTransport(
        [
            (
                '{"resolution_statement":"We guarantee this will be fixed immediately.",'
                '"acknowledgment":"This is our fault and we are liable for the issue.",'
                '"findings":"We promise the outcome will definitely be in your favor.",'
                '"action_steps":["We guarantee a refund today"],'
                '"timeline_next_steps":"You will definitely receive a final answer tomorrow.",'
                '"policy_citation_labels":[],"critique_items_addressed":[]}'
            )
        ]
    )
    agent = WriterAgent(transport=transport)

    result = agent.compose_response(
        complaint_text='My bank said the dispute would be resolved but I have no update.',
        classification=_classification(),
        diagnosis=_diagnosis(),
        remediation=_remediation(),
    )

    rendered = result.render_text().lower()
    assert 'guarantee' not in rendered
    assert 'liable' not in rendered
    assert 'our fault' not in rendered
    assert 'definitely' not in rendered
    assert agent.guardrail_triggered is True
