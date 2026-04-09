from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts import evaluate_classifier
from src.evaluation.harness import EvaluationSummary, evaluate_holdout
from src.evaluation.reporting import write_evaluation_artifacts
from src.schemas.classification import (
    ClassificationResult,
    ComplianceRisk,
    IssueType,
    ProductType,
    SeverityLevel,
)


class StubClassifier:
    def __init__(
        self,
        outputs: list[ClassificationResult],
        *,
        fallbacks: list[bool] | None = None,
        attempts: list[int] | None = None,
    ) -> None:
        self._outputs = outputs
        self._fallbacks = fallbacks or [False] * len(outputs)
        self._attempts = attempts or [1] * len(outputs)
        self.calls = 0
        self.used_fallback = False
        self.last_llm_attempts = 0

    def classify(self, payload: str) -> ClassificationResult:
        del payload
        result = self._outputs[self.calls]
        self.used_fallback = self._fallbacks[self.calls]
        self.last_llm_attempts = self._attempts[self.calls]
        self.calls += 1
        return result



def _build_result(
    *,
    product_type: ProductType,
    issue_type: IssueType,
    confidence: float,
) -> ClassificationResult:
    return ClassificationResult(
        product_type=product_type,
        issue_type=issue_type,
        severity=SeverityLevel.MEDIUM,
        compliance_risk=ComplianceRisk.LOW,
        confidence=confidence,
    )



def _write_holdout_dataset(dataset_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                'id': 'row-1',
                'product': 'Credit card',
                'issue': 'Problem with a purchase shown on your statement',
                'narrative': 'My credit card statement shows a duplicate purchase charge.',
                'state': 'CA',
                'date': '2026-04-08',
            },
            {
                'id': 'row-2',
                'product': 'Checking or savings account',
                'issue': 'Problem when making payments',
                'narrative': (
                    'My checking account payment was delayed even though funds were ' 
                    'available.'
                ),
                'state': 'NY',
                'date': '2026-04-09',
            },
        ]
    )
    frame.to_parquet(dataset_path, index=False)



def _run_sample_evaluation(tmp_path: Path) -> EvaluationSummary:
    dataset_path = tmp_path / 'holdout.parquet'
    _write_holdout_dataset(dataset_path)
    classifier = StubClassifier(
        [
            _build_result(
                product_type=ProductType.CREDIT_CARD,
                issue_type=IssueType.BILLING,
                confidence=0.91,
            ),
            _build_result(
                product_type=ProductType.BANK_ACCOUNT,
                issue_type=IssueType.BILLING,
                confidence=0.37,
            ),
        ],
        attempts=[1, 2],
    )
    return evaluate_holdout(dataset_path=dataset_path, classifier=classifier, sample_failures=2)



def _metric(summary: EvaluationSummary, *, label: str, group: str) -> Any:
    metrics = summary.product_breakdown if group == 'product' else summary.issue_breakdown
    return next(metric for metric in metrics if metric.label == label)



def test_holdout_report_computes_macro_f1_and_class_breakdown(tmp_path: Path) -> None:
    summary = _run_sample_evaluation(tmp_path)

    assert summary.record_count == 2
    assert summary.product_macro_f1 == pytest.approx(1.0)
    assert summary.issue_macro_f1 == pytest.approx(0.3333)
    assert summary.macro_f1 == pytest.approx(0.6667)
    assert summary.exact_match_rate == pytest.approx(0.5)
    assert summary.fallback_rate == pytest.approx(0.0)

    billing = _metric(summary, label='BILLING', group='issue')
    payment = _metric(summary, label='PAYMENT', group='issue')
    assert billing.support == 1
    assert billing.predicted == 2
    assert billing.f1 == pytest.approx(0.6667)
    assert payment.support == 1
    assert payment.f1 == pytest.approx(0.0)

    assert [failure.complaint_id for failure in summary.sampled_failures] == ['row-2']



def test_write_evaluation_artifacts_persists_json_and_markdown(tmp_path: Path) -> None:
    summary = _run_sample_evaluation(tmp_path)

    artifacts = write_evaluation_artifacts(summary, output_dir=tmp_path / 'artifacts')
    payload = json.loads(artifacts.json_path.read_text(encoding='utf-8'))
    markdown = artifacts.markdown_path.read_text(encoding='utf-8')

    assert payload['macro_f1'] == pytest.approx(summary.macro_f1)
    assert payload['sampled_failures'][0]['complaint_id'] == 'row-2'
    assert '## Issue Breakdown' in markdown
    assert 'row-2' in markdown



def test_cli_main_writes_artifacts_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset_path = tmp_path / 'holdout.parquet'
    _write_holdout_dataset(dataset_path)
    classifier = StubClassifier(
        [
            _build_result(
                product_type=ProductType.CREDIT_CARD,
                issue_type=IssueType.BILLING,
                confidence=0.91,
            ),
            _build_result(
                product_type=ProductType.BANK_ACCOUNT,
                issue_type=IssueType.BILLING,
                confidence=0.37,
            ),
        ]
    )
    monkeypatch.setattr(
        evaluate_classifier,
        'build_classifier',
        lambda *, live=False: classifier,
    )

    exit_code = evaluate_classifier.main(
        [
            '--dataset',
            str(dataset_path),
            '--output-dir',
            str(tmp_path / 'artifacts'),
            '--sample-failures',
            '1',
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'Holdout evaluation complete' in captured.out
    assert 'Mode: deterministic-fallback' in captured.out
    assert (tmp_path / 'artifacts' / 'holdout-evaluation.json').exists()
    assert (tmp_path / 'artifacts' / 'holdout-evaluation.md').exists()

