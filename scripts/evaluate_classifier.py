"""Run the Phase 6 holdout evaluation and persist review artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence

from src.agents.classifier import ClassifierAgent
from src.evaluation.harness import EvaluationSummary, SupportsClassify, evaluate_holdout
from src.evaluation.reporting import ArtifactPaths, DEFAULT_OUTPUT_DIR, write_evaluation_artifacts

DEFAULT_DATASET_PATH = Path('data/processed/holdout.parquet')



def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Run the holdout classifier evaluation.')
    parser.add_argument('--dataset', default=str(DEFAULT_DATASET_PATH), help='Holdout parquet path')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR), help='Artifact output dir')
    parser.add_argument(
        '--sample-failures',
        default=5,
        type=int,
        help='Number of deterministic failure examples to include in the report',
    )
    return parser



def build_classifier() -> SupportsClassify:
    return ClassifierAgent()



def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    sample_failures: int = 5,
    classifier: SupportsClassify | None = None,
) -> tuple[EvaluationSummary, ArtifactPaths]:
    active_classifier = classifier or build_classifier()
    summary = evaluate_holdout(
        dataset_path=dataset_path,
        classifier=active_classifier,
        sample_failures=sample_failures,
    )
    artifacts = write_evaluation_artifacts(summary, output_dir=output_dir)
    return summary, artifacts



def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary, artifacts = run_evaluation(
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output_dir),
        sample_failures=args.sample_failures,
    )
    print('Holdout evaluation complete')
    print(f'Records: {summary.record_count}')
    print(f'Macro F1: {summary.macro_f1:.4f}')
    print(f'Exact match rate: {summary.exact_match_rate:.4f}')
    print(f'JSON: {artifacts.json_path.as_posix()}')
    print(f'Markdown: {artifacts.markdown_path.as_posix()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
