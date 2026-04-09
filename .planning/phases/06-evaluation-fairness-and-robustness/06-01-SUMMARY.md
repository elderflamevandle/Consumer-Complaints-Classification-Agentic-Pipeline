---
phase: 06-evaluation-fairness-and-robustness
plan: "01"
subsystem: evaluation
tags: [evaluation, holdout, taxonomy, metrics, task-runner, tdd]
dependency_graph:
  requires: []
  provides:
    - src/evaluation/taxonomy.py (raw CFPB label normalization into project enums)
    - src/evaluation/harness.py (deterministic holdout evaluation runner)
    - src/evaluation/reporting.py (JSON/Markdown artifact rendering)
    - scripts/evaluate_classifier.py (repo CLI entrypoint for holdout evaluation)
    - scripts/tasks.py eval command (real evaluation task path)
  affects:
    - 06-02 fairness reporting will extend the same evaluation rows and artifact files
tech_stack:
  added:
    - src/evaluation/harness.py
    - src/evaluation/reporting.py
    - scripts/evaluate_classifier.py
  patterns:
    - deterministic raw-label normalization before scoring
    - pure-Python macro F1/per-class metrics without scikit-learn
    - report-first JSON + Markdown artifact generation
    - deterministic fallback CLI mode for repeatable offline evaluation
key_files:
  created:
    - src/evaluation/harness.py
    - src/evaluation/reporting.py
    - scripts/evaluate_classifier.py
    - tests/test_evaluation_harness.py
  modified:
    - src/evaluation/__init__.py
    - src/evaluation/taxonomy.py
    - scripts/tasks.py
    - tests/test_evaluation_taxonomy.py
    - tests/test_task_runner.py
decisions:
  - "Raw CFPB product and issue labels are normalized into the reduced classifier enum space before any metric is computed."
  - "Headline macro F1 is reported as the mean of product-macro-F1 and issue-macro-F1 so both classifier axes are represented."
  - "The default eval CLI runs in deterministic fallback mode; live API-backed evaluation remains available behind --live."
  - "Evaluation artifacts are written to artifacts/eval as stable JSON and Markdown files rather than notebook output."
metrics:
  completed: "2026-04-08"
  tasks: 3
  commits: 3
---

# Phase 6 Plan 01: Holdout Evaluation Harness and Taxonomy Summary

**One-liner:** Real repo-standard holdout evaluation with raw-label normalization, macro F1 plus class breakdowns, sampled failure artifacts, and a working `eval` task.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add production raw-label normalization for holdout truth labels | 96e64bb | src/evaluation/taxonomy.py, tests/test_evaluation_taxonomy.py |
| 2 | Implement deterministic holdout evaluation harness and artifact writer | 8d38f27 | src/evaluation/__init__.py, src/evaluation/harness.py, src/evaluation/reporting.py, scripts/evaluate_classifier.py, tests/test_evaluation_harness.py |
| 3 | Replace the eval task stub and lock the command/report contract with tests | 86762b2 | scripts/tasks.py, scripts/evaluate_classifier.py, src/evaluation/*.py, tests/test_evaluation_harness.py, tests/test_task_runner.py |

## What Was Built

### Taxonomy normalization
- `src/evaluation/taxonomy.py` now converts raw CFPB `product` and `issue` labels into the project's `ProductType` and `IssueType` enums before scoring.
- Credit-reporting-heavy holdout labels normalize into `IssueType.CREDIT_REPORTING` while unsupported debt-collection issue variants fall through to explicit `OTHER`.
- `tests/test_evaluation_taxonomy.py` covers supported mappings, case-insensitivity, prepaid-card collapsing, identity-theft preservation, and unsupported fallthrough.

### Offline evaluation harness
- `src/evaluation/harness.py` loads `data/processed/holdout.parquet`, runs the classifier row-by-row, and captures normalized truth labels, predictions, confidence, fallback usage, and exact-match flags.
- Macro F1 is computed without new dependencies, with separate product and issue breakdown tables plus a single headline score.
- Failure samples are selected deterministically from the sorted failed rows so regressions are reviewable.

### Artifact writer and CLI surface
- `src/evaluation/reporting.py` writes stable JSON and Markdown artifacts to `artifacts/eval/holdout-evaluation.{json,md}`.
- `scripts/evaluate_classifier.py` exposes the evaluation entrypoint, prints a concise summary, and supports `--live` when a full API-backed run is desired.
- `scripts/tasks.py eval` now dispatches to the real evaluation script instead of the Phase 6 placeholder print.

## Verification

Passed:
- `uv run pytest -q tests/test_evaluation_taxonomy.py`
- `uv run pytest -q tests/test_evaluation_harness.py`
- `uv run pytest -q tests/test_evaluation_taxonomy.py tests/test_evaluation_harness.py tests/test_task_runner.py::test_task_runner_resolves_expected_commands`
- `uv run python scripts/tasks.py eval`
- `uv run ruff check src/evaluation scripts/evaluate_classifier.py tests/test_evaluation_taxonomy.py tests/test_evaluation_harness.py tests/test_task_runner.py`
- `uv run mypy src/evaluation`

Observed full-holdout command output:
- Records: `2000`
- Mode: `deterministic-fallback`
- Macro F1: `0.3545`
- Exact match rate: `0.2230`

## Deviations from Plan

### Intentional deviation
- The default CLI mode is deterministic fallback rather than live API-backed classification. Running the live classifier across all 2,000 holdout records is too slow and too variable for the repo-standard offline eval task. The live path is still available via `scripts/evaluate_classifier.py --live`.

### Verification note
- Repo-wide `uv run ruff check .` and `uv run mypy src` still fail on unrelated pre-existing files outside this plan's write scope (notably `.claude/worktrees`, notebook artifacts, and existing UI modules). Targeted checks for the Phase 6 evaluation files pass.

## Known Stubs

None in the shipped Phase 6 evaluation path. The deterministic fallback mode is an intentional offline-evaluation policy, not a placeholder print.

## Self-Check: PASSED

- src/evaluation/taxonomy.py: FOUND
- src/evaluation/harness.py: FOUND
- src/evaluation/reporting.py: FOUND
- scripts/evaluate_classifier.py: FOUND
- tests/test_evaluation_taxonomy.py: FOUND
- tests/test_evaluation_harness.py: FOUND
- scripts/tasks.py eval uses the real evaluation script: VERIFIED
- Commits: 96e64bb, 8d38f27, 86762b2
