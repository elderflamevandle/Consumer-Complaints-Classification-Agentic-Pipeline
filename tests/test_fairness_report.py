from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.evaluation.fairness import DEFAULT_BASELINE_GROUP, build_fairness_report
from src.evaluation.harness import EvaluationRow, evaluate_holdout
from src.evaluation.reporting import write_evaluation_artifacts
from src.schemas.classification import (
    ClassificationResult,
    ComplianceRisk,
    IssueType,
    ProductType,
    SeverityLevel,
)


class StubClassifier:
    def __init__(self, outputs: list[ClassificationResult]) -> None:
        self._outputs = outputs
        self.calls = 0
        self.used_fallback = False
        self.last_llm_attempts = 1

    def classify(self, payload: str) -> ClassificationResult:
        del payload
        result = self._outputs[self.calls]
        self.calls += 1
        return result



def _build_result(*, exact_match: bool) -> ClassificationResult:
    issue_type = IssueType.BILLING if exact_match else IssueType.OTHER
    return ClassificationResult(
        product_type=ProductType.OTHER,
        issue_type=issue_type,
        severity=SeverityLevel.MEDIUM,
        compliance_risk=ComplianceRisk.LOW,
        confidence=0.55,
    )



def _make_row(*, complaint_id: str, raw_product: str, exact_match: bool) -> EvaluationRow:
    predicted_issue = IssueType.BILLING if exact_match else IssueType.OTHER
    return EvaluationRow(
        complaint_id=complaint_id,
        raw_product=raw_product,
        raw_issue='synthetic issue',
        state='NY',
        date='2026-04-08',
        narrative_excerpt='synthetic narrative',
        truth_product_type=ProductType.OTHER,
        truth_issue_type=IssueType.BILLING,
        predicted_product_type=ProductType.OTHER,
        predicted_issue_type=predicted_issue,
        confidence=0.55,
        used_fallback=False,
        llm_attempts=1,
        product_correct=True,
        issue_correct=exact_match,
        exact_match=exact_match,
    )



def _write_fairness_dataset(dataset_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                'id': 'row-1',
                'product': 'Credit reporting or other personal consumer reports',
                'issue': 'Incorrect information on your report',
                'narrative': 'A credit report item is still incorrect after dispute.',
                'state': 'CA',
                'date': '2026-04-08',
            },
            {
                'id': 'row-2',
                'product': (
                    'Credit reporting, credit repair services, or other personal '
                    'consumer reports'
                ),
                'issue': 'Improper use of your report',
                'narrative': 'My report was accessed without authorization.',
                'state': 'CA',
                'date': '2026-04-08',
            },
            {
                'id': 'row-3',
                'product': 'Credit reporting',
                'issue': 'Incorrect information on credit report',
                'narrative': 'The same credit report issue keeps reappearing.',
                'state': 'CA',
                'date': '2026-04-08',
            },
            {
                'id': 'row-4',
                'product': 'Checking or savings account',
                'issue': 'Problem when making payments',
                'narrative': 'My bank payment posted late.',
                'state': 'NY',
                'date': '2026-04-09',
            },
            {
                'id': 'row-5',
                'product': 'Bank account or service',
                'issue': 'Managing an account',
                'narrative': 'The account portal is missing transactions.',
                'state': 'NY',
                'date': '2026-04-09',
            },
            {
                'id': 'row-6',
                'product': 'Student loan',
                'issue': 'Problem when making payments',
                'narrative': 'The loan payment history is wrong.',
                'state': 'TX',
                'date': '2026-04-10',
            },
        ]
    )
    frame.to_parquet(dataset_path, index=False)



def _load_sample_rows() -> tuple[EvaluationRow, ...]:
    return (
        _make_row(
            complaint_id='row-1',
            raw_product='Credit reporting or other personal consumer reports',
            exact_match=True,
        ),
        _make_row(
            complaint_id='row-2',
            raw_product=(
                'Credit reporting, credit repair services, or other personal '
                'consumer reports'
            ),
            exact_match=False,
        ),
        _make_row(complaint_id='row-3', raw_product='Credit reporting', exact_match=True),
        _make_row(
            complaint_id='row-4',
            raw_product='Checking or savings account',
            exact_match=True,
        ),
        _make_row(complaint_id='row-5', raw_product='Bank account or service', exact_match=False),
        _make_row(complaint_id='row-6', raw_product='Student loan', exact_match=True),
    )



def test_selected_groups_use_named_baseline_and_skip_underpowered_groups() -> None:
    report = build_fairness_report(_load_sample_rows(), min_support=2)

    assert report.baseline_group == DEFAULT_BASELINE_GROUP
    assert report.baseline_support == 3
    assert report.baseline_exact_match_rate == pytest.approx(0.6667)
    assert [comparison.group for comparison in report.comparisons] == ['BANK_ACCOUNT']
    assert report.comparisons[0].support == 2
    assert report.comparisons[0].disparity_ratio == pytest.approx(0.75)
    assert [group.group for group in report.skipped_groups] == ['LOAN']
    assert report.warnings == ('Skipped LOAN: support 1 < min_support 2.',)



def test_fairness_report_includes_ratios_support_and_warnings(tmp_path: Path) -> None:
    dataset_path = tmp_path / 'holdout.parquet'
    _write_fairness_dataset(dataset_path)
    classifier = StubClassifier(
        [
            _build_result(exact_match=True),
            _build_result(exact_match=False),
            _build_result(exact_match=True),
            _build_result(exact_match=True),
            _build_result(exact_match=False),
            _build_result(exact_match=True),
        ]
    )

    summary = evaluate_holdout(
        dataset_path=dataset_path,
        classifier=classifier,
        sample_failures=2,
        fairness_min_support=2,
    )
    artifacts = write_evaluation_artifacts(summary, output_dir=tmp_path / 'artifacts')
    payload = json.loads(artifacts.json_path.read_text(encoding='utf-8'))
    markdown = artifacts.markdown_path.read_text(encoding='utf-8')

    fairness = payload['fairness']
    assert isinstance(fairness, dict)
    assert fairness['baseline_group'] == 'CREDIT_REPORTING'
    assert fairness['comparisons'][0]['group'] == 'BANK_ACCOUNT'
    assert fairness['comparisons'][0]['support'] == 2
    assert fairness['skipped_groups'][0]['group'] == 'LOAN'
    assert fairness['warnings'] == ['Skipped LOAN: support 1 < min_support 2.']
    assert '## Fairness' in markdown
    assert 'CREDIT_REPORTING' in markdown
    assert 'Skipped LOAN: support 1 < min_support 2' in markdown

