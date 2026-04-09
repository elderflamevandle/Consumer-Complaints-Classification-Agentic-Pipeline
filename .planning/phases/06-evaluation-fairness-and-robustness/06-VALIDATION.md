---
phase: 6
slug: evaluation-fairness-and-robustness
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
---

# Phase 6 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + Ruff + mypy |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `Run the current task's <automated> verify command from the Per-Task Verification Map` |
| **Full suite command** | `uv run pytest -q && uv run ruff check . && uv run mypy src` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run the current task's `<automated>` verify command from the Per-Task Verification Map
- **After every plan wave:** Run `uv run pytest -q && uv run ruff check . && uv run mypy src`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | EVAL-01 | unit | `uv run pytest -q tests/test_evaluation_taxonomy.py` | planned | pending |
| 6-01-02 | 01 | 1 | EVAL-01 | integration | `uv run pytest -q tests/test_evaluation_harness.py::test_holdout_report_computes_macro_f1_and_class_breakdown` | planned | pending |
| 6-01-03 | 01 | 1 | EVAL-01 | integration | `uv run pytest -q tests/test_evaluation_taxonomy.py tests/test_evaluation_harness.py tests/test_task_runner.py::test_task_runner_resolves_expected_commands` | planned | pending |
| 6-02-01 | 02 | 2 | EVAL-02 | unit | `uv run pytest -q tests/test_fairness_report.py::test_selected_groups_use_named_baseline_and_skip_underpowered_groups` | planned | pending |
| 6-02-02 | 02 | 2 | EVAL-02 | integration | `uv run pytest -q tests/test_fairness_report.py::test_fairness_report_includes_ratios_support_and_warnings` | planned | pending |
| 6-02-03 | 02 | 2 | EVAL-02 | integration | `uv run pytest -q tests/test_evaluation_harness.py tests/test_fairness_report.py` | planned | pending |
| 6-03-01 | 03 | 2 | FLOW-04 | unit | `uv run pytest -q tests/test_phase6_reliability.py::test_prepare_intake_handles_empty_and_very_long_inputs_without_crash` | planned | pending |
| 6-03-02 | 03 | 2 | FLOW-04 | integration | `uv run pytest -q tests/test_phase6_reliability.py::test_runtime_surfaces_non_critical_fallback_warning_without_failing_run` | planned | pending |
| 6-03-03 | 03 | 2 | FLOW-04, OPS-02 | integration | `uv run pytest -q tests/test_phase6_reliability.py tests/test_llm_client.py tests/test_routing_interrupts.py` | planned | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] Existing pytest, Ruff, and mypy infrastructure already covers the repo baseline.
- [x] Plan 06-01 Task 1 creates taxonomy-mapping tests before the harness depends on normalized labels.
- [x] Plan 06-02 Task 1 creates fairness-report tests before fairness output is wired into the evaluation artifacts.
- [x] Plan 06-03 Task 1 creates dedicated reliability tests before warning surfacing and regression expansion depend on them.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Evaluation markdown report is readable and the sampled failure examples are useful to a reviewer | EVAL-01, EVAL-02 | Numeric assertions can validate structure, but not whether the report is understandable in a demo or teammate review context | Run `uv run python scripts/tasks.py eval`, open the generated Markdown artifact, and confirm the macro F1 summary, class breakdown, fairness section, and failure examples read clearly and match the JSON artifact |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all planned new verification files
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
