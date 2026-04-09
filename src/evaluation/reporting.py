"""Artifact rendering for Phase 6 holdout evaluation reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.evaluation.harness import EvaluationRow, EvaluationSummary, LabelMetrics

DEFAULT_OUTPUT_DIR = Path('artifacts/eval')
JSON_ARTIFACT_NAME = 'holdout-evaluation.json'
MARKDOWN_ARTIFACT_NAME = 'holdout-evaluation.md'


@dataclass(frozen=True)
class ArtifactPaths:
    json_path: Path
    markdown_path: Path



def evaluation_to_dict(summary: EvaluationSummary) -> dict[str, object]:
    return {
        'artifact_version': 1,
        'dataset_path': str(summary.dataset_path),
        'record_count': summary.record_count,
        'macro_f1': summary.macro_f1,
        'product_macro_f1': summary.product_macro_f1,
        'issue_macro_f1': summary.issue_macro_f1,
        'exact_match_rate': summary.exact_match_rate,
        'fallback_rate': summary.fallback_rate,
        'warnings': list(summary.warnings),
        'product_breakdown': [_metric_to_dict(metric) for metric in summary.product_breakdown],
        'issue_breakdown': [_metric_to_dict(metric) for metric in summary.issue_breakdown],
        'sampled_failures': [_failure_to_dict(row) for row in summary.sampled_failures],
    }



def render_markdown_report(summary: EvaluationSummary) -> str:
    lines = [
        '# Holdout Evaluation',
        '',
        f'Dataset: `{summary.dataset_path.as_posix()}`',
        '',
        '## Summary',
        '',
        '| Metric | Value |',
        '| --- | ---: |',
        f'| Records | {summary.record_count} |',
        f'| Macro F1 | {summary.macro_f1:.4f} |',
        f'| Product Macro F1 | {summary.product_macro_f1:.4f} |',
        f'| Issue Macro F1 | {summary.issue_macro_f1:.4f} |',
        f'| Exact Match Rate | {summary.exact_match_rate:.4f} |',
        f'| Fallback Rate | {summary.fallback_rate:.4f} |',
        '',
    ]

    if summary.warnings:
        lines.extend(['## Warnings', ''])
        for warning in summary.warnings:
            lines.append(f'- {warning}')
        lines.append('')

    _append_breakdown(lines, title='Product Breakdown', metrics=summary.product_breakdown)
    _append_breakdown(lines, title='Issue Breakdown', metrics=summary.issue_breakdown)

    lines.extend(['## Sampled Failures', ''])
    if not summary.sampled_failures:
        lines.append('No failures sampled.')
        lines.append('')
        return '\n'.join(lines)

    for row in summary.sampled_failures:
        lines.extend(
            [
                f"### {row.complaint_id}",
                f"- Truth: `{row.truth_product_type.value}` / `{row.truth_issue_type.value}`",
                (
                    '- Prediction: '
                    f"`{row.predicted_product_type.value}` / `{row.predicted_issue_type.value}`"
                ),
                f'- Confidence: {row.confidence:.4f}',
                f"- Fallback Used: {'yes' if row.used_fallback else 'no'}",
                f'- State/Date: {row.state or "N/A"} / {row.date or "N/A"}',
                f'- Excerpt: {row.narrative_excerpt}',
                '',
            ]
        )
    return '\n'.join(lines)



def write_evaluation_artifacts(
    summary: EvaluationSummary,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ArtifactPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / JSON_ARTIFACT_NAME
    markdown_path = output_dir / MARKDOWN_ARTIFACT_NAME
    json_path.write_text(
        json.dumps(evaluation_to_dict(summary), indent=2, sort_keys=True),
        encoding='utf-8',
    )
    markdown_path.write_text(render_markdown_report(summary), encoding='utf-8')
    return ArtifactPaths(json_path=json_path, markdown_path=markdown_path)



def _append_breakdown(
    lines: list[str],
    *,
    title: str,
    metrics: tuple[LabelMetrics, ...],
) -> None:
    lines.extend([f'## {title}', ''])
    if not metrics:
        lines.extend(['No observed labels.', ''])
        return

    lines.extend(
        [
            '| Label | Support | Predicted | Precision | Recall | F1 |',
            '| --- | ---: | ---: | ---: | ---: | ---: |',
        ]
    )
    for metric in metrics:
        lines.append(
            '| '
            f'{metric.label} | {metric.support} | {metric.predicted} | '
            f'{metric.precision:.4f} | {metric.recall:.4f} | {metric.f1:.4f} |'
        )
    lines.append('')



def _metric_to_dict(metric: LabelMetrics) -> dict[str, object]:
    return {
        'label': metric.label,
        'support': metric.support,
        'predicted': metric.predicted,
        'true_positives': metric.true_positives,
        'precision': metric.precision,
        'recall': metric.recall,
        'f1': metric.f1,
    }



def _failure_to_dict(row: EvaluationRow) -> dict[str, object]:
    return {
        'complaint_id': row.complaint_id,
        'raw_product': row.raw_product,
        'raw_issue': row.raw_issue,
        'state': row.state,
        'date': row.date,
        'narrative_excerpt': row.narrative_excerpt,
        'truth_product_type': row.truth_product_type.value,
        'truth_issue_type': row.truth_issue_type.value,
        'predicted_product_type': row.predicted_product_type.value,
        'predicted_issue_type': row.predicted_issue_type.value,
        'confidence': row.confidence,
        'used_fallback': row.used_fallback,
        'llm_attempts': row.llm_attempts,
        'product_correct': row.product_correct,
        'issue_correct': row.issue_correct,
        'exact_match': row.exact_match,
    }
