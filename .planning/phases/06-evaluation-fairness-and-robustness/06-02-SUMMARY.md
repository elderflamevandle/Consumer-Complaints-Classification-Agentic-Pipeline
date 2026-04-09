---
phase: 06-evaluation-fairness-and-robustness
plan: "02"
subsystem: evaluation
tags: [fairness, evaluation, artifacts, baseline, support-threshold, tdd]
dependency_graph:
  requires: ["06-01"]
  provides:
    - src/evaluation/fairness.py (product-group fairness policy and disparity ratios)
    - fairness sections in holdout JSON and Markdown artifacts
    - CLI fairness summary output in scripts/evaluate_classifier.py
  affects:
    - scripts/tasks.py eval output now reports fairness baseline/comparison counts via the existing artifact path
tech_stack:
  added:
    - src/evaluation/fairness.py
    - tests/test_fairness_report.py
  patterns:
    - canonical raw-product grouping for fairness without changing classifier scoring taxonomy
    - explicit named baseline with minimum-support gating
    - report-first surfacing through existing JSON/Markdown artifacts and CLI output
key_files:
  created:
    - src/evaluation/fairness.py
    - tests/test_fairness_report.py
  modified:
    - src/evaluation/__init__.py
    - src/evaluation/harness.py
    - src/evaluation/reporting.py
    - scripts/evaluate_classifier.py
decisions:
  - "Fairness groups are derived from canonical raw product families, not from the reduced ProductType enum used for scoring."
  - "CREDIT_REPORTING is the explicit baseline group because it has by far the strongest holdout support."
  - "The fairness shortlist is fixed and stable: CREDIT_REPORTING, DEBT_COLLECTION, BANK_ACCOUNT, MORTGAGE, MONEY_TRANSFER, CREDIT_CARD, LOAN."
  - "Groups below the support threshold are skipped with explicit warnings instead of padded into misleading ratio tables."
metrics:
  completed: "2026-04-08"
  tasks: 3
---

# Phase 6 Plan 02: Fairness Computation and Report-First Surfacing Summary

**One-liner:** Deterministic product-group fairness reporting layered into the holdout evaluation artifacts with a named baseline, support-threshold policy, and regression coverage.

## What Was Built

### Fairness policy layer
- `src/evaluation/fairness.py` introduces canonical complaint product groups for fairness reporting: `CREDIT_REPORTING`, `DEBT_COLLECTION`, `BANK_ACCOUNT`, `MORTGAGE`, `MONEY_TRANSFER`, `CREDIT_CARD`, and `LOAN`.
- The report uses `CREDIT_REPORTING` as the explicit baseline group and computes disparity ratios from exact-match performance against that baseline.
- Groups below the configured support floor are captured as `SkippedGroup` entries and emitted as human-readable warnings.

### Evaluation-path integration
- `src/evaluation/harness.py` now attaches a `FairnessReport` to each holdout evaluation run and carries fairness warnings into the summary object.
- `src/evaluation/reporting.py` now serializes fairness into the JSON artifact and renders a dedicated Markdown fairness section with baseline details, support counts, ratio rows, and skipped-group notes.
- `scripts/evaluate_classifier.py` now prints the fairness baseline and comparison count as part of the existing CLI summary instead of introducing any new dashboard view.

### Regression coverage
- `tests/test_fairness_report.py` covers the named baseline policy, underpowered-group skipping, JSON/Markdown fairness rendering, and artifact integration through the evaluation path.
- Existing evaluation tests continue to pass with the fairness extensions layered on top of the Plan 06-01 harness.

## Verification

Passed:
- `uv run pytest -q tests/test_fairness_report.py::test_selected_groups_use_named_baseline_and_skip_underpowered_groups`
- `uv run pytest -q tests/test_evaluation_harness.py tests/test_fairness_report.py`
- `uv run python scripts/tasks.py eval`
- `uv run ruff check src/evaluation scripts/evaluate_classifier.py tests/test_evaluation_taxonomy.py tests/test_evaluation_harness.py tests/test_fairness_report.py tests/test_task_runner.py`
- `uv run mypy src/evaluation`

Observed full-holdout fairness output:
- Baseline group: `CREDIT_REPORTING` (`1340` rows)
- Comparison groups surfaced: `6`
- Holdout artifact path: `artifacts/eval/holdout-evaluation.{json,md}`
- Current deterministic-fallback fairness ratios:
  - `DEBT_COLLECTION`: `0.1924`
  - `BANK_ACCOUNT`: `0.3300`
  - `MORTGAGE`: `0.9758`
  - `MONEY_TRANSFER`: `0.3289`
  - `CREDIT_CARD`: `0.6024`
  - `LOAN`: `0.6211`

## Deviations from Plan

None. Fairness remained report-first and stayed out of the Streamlit dashboard surface.

## Known Stubs

None. The fairness policy, ratio calculation, and artifact surfacing are all exercised through the actual evaluation path.

## Self-Check: PASSED

- src/evaluation/fairness.py: FOUND
- src/evaluation/harness.py fairness field: FOUND
- src/evaluation/reporting.py fairness section: FOUND
- scripts/evaluate_classifier.py fairness summary output: VERIFIED
- tests/test_fairness_report.py: FOUND
