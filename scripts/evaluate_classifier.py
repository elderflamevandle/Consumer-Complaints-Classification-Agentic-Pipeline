"""Run the Phase 6 holdout evaluation and persist review artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence

from src.agents.classifier import ClassifierAgent
from src.evaluation.harness import EvaluationSummary, SupportsClassify, evaluate_holdout
from src.evaluation.reporting import DEFAULT_OUTPUT_DIR, ArtifactPaths, write_evaluation_artifacts

DEFAULT_DATASET_PATH = Path('data/processed/holdout.parquet')


class DeterministicFallbackTransport:
    def __call__(self, **_: object) -> dict[str, object]:
        return {'content': 'not-json', 'usage': {'total_tokens': 0}}



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
    parser.add_argument(
        '--live',
        action='store_true',
        help='Use the live classifier transport instead of deterministic fallback mode',
    )
    return parser



def build_classifier(*, live: bool = False) -> SupportsClassify:
    if live:
        return ClassifierAgent()
    return ClassifierAgent(transport=DeterministicFallbackTransport())



def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    sample_failures: int = 5,
    live: bool = False,
    classifier: SupportsClassify | None = None,
) -> tuple[EvaluationSummary, ArtifactPaths]:
    active_classifier = classifier or build_classifier(live=live)
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
        live=args.live,
    )
    print('Holdout evaluation complete')
    print(f'Mode: {"live" if args.live else "deterministic-fallback"}')
    print(f'Records: {summary.record_count}')
    print(f'Macro F1: {summary.macro_f1:.4f}')
    print(f'Exact match rate: {summary.exact_match_rate:.4f}')
    print(f'JSON: {artifacts.json_path.as_posix()}')
    print(f'Markdown: {artifacts.markdown_path.as_posix()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
