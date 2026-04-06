from __future__ import annotations

from typing import Any

from src.agents.explainer import ExplainerAgent
from src.agents.remediator import RemediationResult, RemediationStep
from src.schemas.auditor import AuditReasonCode, AuditVerdict, ResponseAuditResult
from src.schemas.classification import ClassificationResult
from src.schemas.response import ResponseDraft
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
            )
        ],
        policy_citations={
            'sla_window': '15 calendar days',
            'required_actions': ['Acknowledge complaint receipt'],
            'regulatory_basis': 'Regulation Z billing error framework',
        },
    )


def _response() -> ResponseDraft:
    return ResponseDraft(
        resolution_statement=(
            'We will review the disputed charges using the required '
            'billing-dispute process.'
        ),
        acknowledgment='We understand the concern described in your complaint.',
        findings='Current findings point to a delay in dispute handling.',
        action_steps=[
            'Review the disputed transactions.',
            'Send the next written update.',
        ],
        timeline_next_steps='We will follow up within 15 calendar days.',
        policy_citation_labels=[
            'SLA window: 15 calendar days',
            'Regulatory basis: Regulation Z billing error framework',
        ],
        critique_items_addressed=[],
    )


def _audit() -> ResponseAuditResult:
    return ResponseAuditResult(
        verdict=AuditVerdict.PASS,
        reason_codes=[],
        critique_summary=(
            'Response satisfies structure, policy-grounding, and customer-safe '
            'tone checks.'
        ),
        must_fix_items=[],
        rewrite_recommended=False,
    )


def test_explainer_outputs_stage_chain_bullets() -> None:
    agent = ExplainerAgent(transport=ScriptedTransport(['not-json']))

    result = agent.summarize_chain(
        classification=_classification(),
        diagnosis=_diagnosis(),
        remediation=_remediation(),
        final_response=_response(),
        audit_verdict=_audit(),
    )

    stages = [bullet.stage for bullet in result.bullets]
    assert 5 <= len(result.bullets) <= 7
    assert stages == ['classification', 'diagnosis', 'remediation', 'response', 'audit']


def test_explainer_uses_final_artifacts_not_raw_input() -> None:
    agent = ExplainerAgent(transport=ScriptedTransport(['not-json']))
    result = agent.summarize_chain(
        classification=_classification(),
        diagnosis=_diagnosis(),
        remediation=_remediation(),
        final_response=_response(),
        audit_verdict=ResponseAuditResult(
            verdict=AuditVerdict.FAIL,
            reason_codes=[AuditReasonCode.UNCLEAR_RESOLUTION],
            critique_summary='Clarify the resolution path in the findings block.',
            must_fix_items=['State the resolution path clearly in the findings block.'],
            rewrite_recommended=True,
        ),
        raw_input='Please contact me at alice@example.com about this billing issue.',
    )

    rendered = result.render_text().lower()
    assert 'alice@example.com' not in rendered
    assert 'classification' in rendered
    assert 'audit' in rendered
