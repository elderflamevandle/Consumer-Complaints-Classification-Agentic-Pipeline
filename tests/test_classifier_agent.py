from __future__ import annotations

from typing import Any

from src.agents.classifier import ClassifierAgent
from src.schemas.classification import ClassificationResult, ProductType


class ScriptedTransport:
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs
        self.calls = 0

    def __call__(self, **_: Any) -> dict[str, Any]:
        self.calls += 1
        if not self.outputs:
            return {'content': '{}', 'usage': {'total_tokens': 20}}

        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return {'content': output, 'usage': {'total_tokens': 20}}


def test_classifier_strict_schema() -> None:
    transport = ScriptedTransport(
        [
            (
                '{"product_type":"credit card","issue_type":"billing",'
                '"severity":"medium","compliance_risk":"low","confidence":0.83}'
            )
        ]
    )
    agent = ClassifierAgent(transport=transport)

    result = agent.classify('Card billing issue with duplicate charge')

    assert isinstance(result, ClassificationResult)
    assert result.product_type == ProductType.CREDIT_CARD
    assert result.issue_type.value == 'BILLING'
    assert 0.0 <= result.confidence <= 1.0


def test_invalid_json_repair_retry_then_fallback() -> None:
    transport = ScriptedTransport(
        [
            'not-json',
            '{"product_type":"invalid","issue_type":"invalid"}',
            '{"product_type":"invalid","issue_type":"invalid"}',
        ]
    )
    agent = ClassifierAgent(transport=transport, repair_retries=2)

    result = agent.classify('Fraud alert for credit card and unauthorized charges')

    assert transport.calls == 3
    assert agent.used_fallback is True
    assert result.product_type == ProductType.CREDIT_CARD
    assert result.issue_type.value == 'FRAUD'


def test_missing_confidence_keyword_heuristic() -> None:
    transport = ScriptedTransport(
        [
            '{"product_type":"CREDIT_CARD","issue_type":"FRAUD","severity":"HIGH","compliance_risk":"HIGH"}',
            '{"product_type":"CREDIT_CARD","issue_type":"FRAUD","severity":"HIGH","compliance_risk":"HIGH"}',
            '{"product_type":"CREDIT_CARD","issue_type":"FRAUD","severity":"HIGH","compliance_risk":"HIGH"}',
        ]
    )
    agent = ClassifierAgent(transport=transport, repair_retries=2)

    result = agent.classify('Fraud and identity theft on my credit card account')

    assert agent.used_fallback is True
    assert 0.5 <= result.confidence <= 0.95
    assert result.compliance_risk.value == 'HIGH'