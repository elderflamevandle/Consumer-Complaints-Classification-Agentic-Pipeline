"""Evaluation helpers for offline quality reporting."""

from src.evaluation.harness import (
    EvaluationRow,
    EvaluationSummary,
    HoldoutExample,
    LabelMetrics,
    SupportsClassify,
    evaluate_holdout,
    load_holdout_examples,
)
from src.evaluation.reporting import (
    DEFAULT_OUTPUT_DIR,
    ArtifactPaths,
    evaluation_to_dict,
    render_markdown_report,
    write_evaluation_artifacts,
)
from src.evaluation.taxonomy import NormalizedTruth, normalize, normalize_issue, normalize_product

__all__ = [
    'ArtifactPaths',
    'DEFAULT_OUTPUT_DIR',
    'EvaluationRow',
    'EvaluationSummary',
    'HoldoutExample',
    'LabelMetrics',
    'NormalizedTruth',
    'SupportsClassify',
    'evaluate_holdout',
    'evaluation_to_dict',
    'load_holdout_examples',
    'normalize',
    'normalize_issue',
    'normalize_product',
    'render_markdown_report',
    'write_evaluation_artifacts',
]
