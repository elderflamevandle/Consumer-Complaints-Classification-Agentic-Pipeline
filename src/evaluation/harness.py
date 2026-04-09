"""Offline holdout evaluation harness for the classifier contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence

from src.agents.classifier import ClassifierAgent
from src.evaluation.taxonomy import normalize
from src.schemas.classification import ClassificationResult, IssueType, ProductType

REQUIRED_COLUMNS = ('id', 'product', 'issue', 'narrative', 'state', 'date')


class SupportsClassify(Protocol):
    used_fallback: bool
    last_llm_attempts: int

    def classify(self, payload: str) -> ClassificationResult:
        ...


@dataclass(frozen=True)
class HoldoutExample:
    complaint_id: str
    raw_product: str
    raw_issue: str
    narrative: str
    state: str
    date: str


@dataclass(frozen=True)
class EvaluationRow:
    complaint_id: str
    raw_product: str
    raw_issue: str
    state: str
    date: str
    narrative_excerpt: str
    truth_product_type: ProductType
    truth_issue_type: IssueType
    predicted_product_type: ProductType
    predicted_issue_type: IssueType
    confidence: float
    used_fallback: bool
    llm_attempts: int
    product_correct: bool
    issue_correct: bool
    exact_match: bool


@dataclass(frozen=True)
class LabelMetrics:
    label: str
    support: int
    predicted: int
    true_positives: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class EvaluationSummary:
    dataset_path: Path
    record_count: int
    macro_f1: float
    product_macro_f1: float
    issue_macro_f1: float
    exact_match_rate: float
    fallback_rate: float
    product_breakdown: tuple[LabelMetrics, ...]
    issue_breakdown: tuple[LabelMetrics, ...]
    sampled_failures: tuple[EvaluationRow, ...]
    rows: tuple[EvaluationRow, ...]
    warnings: tuple[str, ...] = ()



def load_holdout_examples(dataset_path: Path) -> list[HoldoutExample]:
    try:
        import pandas as pd  # type: ignore[import-untyped]
    except Exception as error:
        raise RuntimeError(
            'pandas + pyarrow are required to load the holdout parquet artifact.'
        ) from error

    frame = pd.read_parquet(dataset_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f'Holdout dataset is missing required columns: {missing}')

    examples: list[HoldoutExample] = []
    for record in frame.to_dict(orient='records'):
        examples.append(
            HoldoutExample(
                complaint_id=str(record['id']),
                raw_product=str(record['product'] or ''),
                raw_issue=str(record['issue'] or ''),
                narrative=str(record['narrative'] or ''),
                state=str(record['state'] or ''),
                date=str(record['date'] or ''),
            )
        )

    if not examples:
        raise ValueError('Holdout dataset is empty.')
    return examples



def evaluate_holdout(
    *,
    dataset_path: Path,
    classifier: SupportsClassify | None = None,
    sample_failures: int = 5,
) -> EvaluationSummary:
    examples = load_holdout_examples(dataset_path)
    active_classifier = classifier or ClassifierAgent()

    rows = tuple(_evaluate_example(example, active_classifier) for example in examples)
    product_breakdown, raw_product_macro_f1 = _build_breakdown(
        rows,
        labels=[label.value for label in ProductType],
        truth_getter=lambda row: row.truth_product_type.value,
        prediction_getter=lambda row: row.predicted_product_type.value,
    )
    issue_breakdown, raw_issue_macro_f1 = _build_breakdown(
        rows,
        labels=[label.value for label in IssueType],
        truth_getter=lambda row: row.truth_issue_type.value,
        prediction_getter=lambda row: row.predicted_issue_type.value,
    )

    return EvaluationSummary(
        dataset_path=dataset_path,
        record_count=len(rows),
        macro_f1=_round((raw_product_macro_f1 + raw_issue_macro_f1) / 2),
        product_macro_f1=_round(raw_product_macro_f1),
        issue_macro_f1=_round(raw_issue_macro_f1),
        exact_match_rate=_round(sum(1 for row in rows if row.exact_match) / len(rows)),
        fallback_rate=_round(sum(1 for row in rows if row.used_fallback) / len(rows)),
        product_breakdown=product_breakdown,
        issue_breakdown=issue_breakdown,
        sampled_failures=_sample_failures(rows, sample_failures=max(sample_failures, 0)),
        rows=rows,
    )



def _evaluate_example(example: HoldoutExample, classifier: SupportsClassify) -> EvaluationRow:
    truth = normalize(product=example.raw_product, issue=example.raw_issue)
    prediction = classifier.classify(example.narrative)

    product_correct = prediction.product_type == truth.product_type
    issue_correct = prediction.issue_type == truth.issue_type
    return EvaluationRow(
        complaint_id=example.complaint_id,
        raw_product=example.raw_product,
        raw_issue=example.raw_issue,
        state=example.state,
        date=example.date,
        narrative_excerpt=_excerpt(example.narrative),
        truth_product_type=truth.product_type,
        truth_issue_type=truth.issue_type,
        predicted_product_type=prediction.product_type,
        predicted_issue_type=prediction.issue_type,
        confidence=_round(prediction.confidence),
        used_fallback=getattr(classifier, 'used_fallback', False),
        llm_attempts=getattr(classifier, 'last_llm_attempts', 0),
        product_correct=product_correct,
        issue_correct=issue_correct,
        exact_match=product_correct and issue_correct,
    )



def _build_breakdown(
    rows: Sequence[EvaluationRow],
    *,
    labels: Sequence[str],
    truth_getter: Callable[[EvaluationRow], str],
    prediction_getter: Callable[[EvaluationRow], str],
) -> tuple[tuple[LabelMetrics, ...], float]:
    metrics: list[LabelMetrics] = []
    raw_f1_scores: list[float] = []
    for label in labels:
        support = sum(1 for row in rows if truth_getter(row) == label)
        predicted = sum(1 for row in rows if prediction_getter(row) == label)
        if support == 0 and predicted == 0:
            continue

        true_positives = sum(
            1
            for row in rows
            if truth_getter(row) == label and prediction_getter(row) == label
        )
        false_positives = predicted - true_positives
        false_negatives = support - true_positives
        precision = _safe_divide(true_positives, true_positives + false_positives)
        recall = _safe_divide(true_positives, true_positives + false_negatives)
        if precision == 0.0 and recall == 0.0:
            f1 = 0.0
        else:
            f1 = (2 * precision * recall) / (precision + recall)

        raw_f1_scores.append(f1)
        metrics.append(
            LabelMetrics(
                label=label,
                support=support,
                predicted=predicted,
                true_positives=true_positives,
                precision=_round(precision),
                recall=_round(recall),
                f1=_round(f1),
            )
        )

    raw_macro_f1 = sum(raw_f1_scores) / len(raw_f1_scores) if raw_f1_scores else 0.0
    return tuple(metrics), raw_macro_f1



def _sample_failures(
    rows: Sequence[EvaluationRow],
    *,
    sample_failures: int,
) -> tuple[EvaluationRow, ...]:
    failures = [row for row in rows if not row.exact_match]
    ordered = sorted(failures, key=lambda row: (row.confidence, row.complaint_id))
    return tuple(ordered[:sample_failures])



def _excerpt(text: str, *, limit: int = 160) -> str:
    condensed = ' '.join(text.split())
    if len(condensed) <= limit:
        return condensed
    return f"{condensed[: limit - 3].rstrip()}..."



def _safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator



def _round(value: float) -> float:
    return round(value, 4)

