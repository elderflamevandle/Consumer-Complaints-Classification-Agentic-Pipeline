---
phase: 06-evaluation-fairness-and-robustness
plan: "03"
subsystem: reliability
tags: [reliability, hardening, intake, runtime, streamlit, fallback, tdd]
dependency_graph:
  requires: ["06-01"]
  provides:
    - deterministic intake edge-case contract
    - visible non-critical fallback warnings in runtime and UI telemetry
    - targeted regression coverage for same-thread review continuity
  affects:
    - app/streamlit_app.py
    - src/intake/pipeline.py
    - src/ui/runtime.py
tech_stack:
  added:
    - tests/test_phase6_reliability.py
  patterns:
    - deterministic empty-input placeholder and truncation warnings
    - runtime stage warning propagation without introducing a new pause mode
    - same-thread ambiguous-review regression coverage
key_files:
  created:
    - tests/test_phase6_reliability.py
  modified:
    - src/agents/root_cause.py
    - src/intake/pipeline.py
    - src/ui/runtime.py
    - app/streamlit_app.py
    - tests/test_intake_pipeline.py
    - tests/test_llm_client.py
    - tests/test_root_cause_agent.py
    - tests/test_routing_interrupts.py
    - tests/test_streamlit_app.py
    - tests/test_ui_runtime.py
decisions:
  - "Empty complaints now use a deterministic placeholder while preserving the existing human-review routing policy."
  - "Intake truncates scrubbed complaint text and classifier input separately, with explicit warnings and trace lengths for operator visibility."
  - "Non-critical fallback behavior stays visible through existing stage artifacts and Streamlit result surfaces instead of introducing a new pause mode."
  - "RootCauseAgent now exposes last_model like the other runtime agents so warning telemetry and type checks share a consistent contract."
metrics:
  completed: "2026-04-08"
  tasks: 3
  commits: 1
---

# Phase 6 Plan 03: Reliability Hardening and Warning Visibility Summary

**One-liner:** Hardened intake and runtime edges for empty, ambiguous, and very long complaints; surfaced non-critical fallback warnings through the existing control-room views; and locked the behavior down with targeted regressions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Formalize empty, ambiguous, and long-input intake handling | 2b6634e | src/intake/pipeline.py, tests/test_intake_pipeline.py, tests/test_phase6_reliability.py |
| 2 | Surface non-critical fallback and degraded-path warnings through existing runtime/UI patterns | 2b6634e | src/ui/runtime.py, app/streamlit_app.py, tests/test_ui_runtime.py, tests/test_streamlit_app.py, tests/test_phase6_reliability.py |
| 3 | Extend targeted reliability regressions for fallback behavior and same-thread review continuity | 2b6634e | src/agents/root_cause.py, tests/test_llm_client.py, tests/test_root_cause_agent.py, tests/test_routing_interrupts.py |

## What Was Built

### Intake hardening
- `src/intake/pipeline.py` now applies a deterministic placeholder when the scrubbed complaint is empty and preserves the existing `human_review_required` routing behavior for that path.
- Scrubbed complaint text and classifier input are truncated independently with explicit warnings (`complaint_text_truncated_for_model_safety`, `classifier_input_truncated_for_model_safety`) plus trace metadata for raw, scrubbed, and classifier input lengths.
- `tests/test_intake_pipeline.py` and `tests/test_phase6_reliability.py` lock the empty-input and long-input contracts so the pipeline stays non-crashing at the intake boundary.

### Runtime and dashboard warning visibility
- `src/ui/runtime.py` now enriches stage artifacts with warning lists for intake, classifier, root-cause, remediator, writer, auditor, and explainer fallback or degraded paths.
- `app/streamlit_app.py` reuses the existing stage expanders and results view to surface stage-level warnings and an aggregated `Non-critical warnings` summary without adding a new offline or paused mode.
- Successful degraded runs remain successful: warnings are visible to the operator but do not convert a recoverable run into a failure state.

### Targeted reliability coverage
- `tests/test_phase6_reliability.py` adds end-to-end regression coverage for empty/very long intake and visible fallback warning propagation.
- `tests/test_llm_client.py` extends the degrade-policy contract so critical calls do not degrade when the budget threshold is exceeded.
- `tests/test_routing_interrupts.py` verifies ambiguous intake still resumes the same thread after reviewer approval, and `tests/test_root_cause_agent.py` locks the `last_model` contract now used by runtime telemetry.

## Verification

Passed:
- `uv run pytest -q tests/test_phase6_reliability.py tests/test_llm_client.py tests/test_routing_interrupts.py tests/test_intake_pipeline.py tests/test_ui_runtime.py tests/test_streamlit_app.py tests/test_root_cause_agent.py`
- `uv run mypy src/intake/pipeline.py src/ui/runtime.py src/agents/root_cause.py`

Verified behaviors:
- Empty complaints route deterministically to human review with a placeholder payload instead of crashing.
- Very long complaints are truncated before downstream stages while preserving explicit warnings and trace lengths.
- Non-critical fallback behavior stays visible in runtime telemetry and the Streamlit results view without breaking successful runs.
- Ambiguous review-routing still preserves same-thread continuity after approval.

## Deviations from Plan

### [Rule 1 - Bug] Runtime metadata contract fix
- Found during: Task 3
- Issue: `RootCauseAgent` did not expose `last_model`, even though `src/ui/runtime.py` already treated it as part of the runtime agent contract.
- Fix: Added `last_model` tracking to `src/agents/root_cause.py` and regression assertions in `tests/test_root_cause_agent.py`.
- Verification: Included in the targeted pytest suite and `uv run mypy src/intake/pipeline.py src/ui/runtime.py src/agents/root_cause.py`.
- Commit: 2b6634e

### Execution note
- The implementation landed in one code commit because `tests/test_phase6_reliability.py` spans both intake hardening and runtime warning visibility. The behavior is still verified task-by-task through the targeted Phase 6 suite above.

## Known Stubs

None. The hardening path and warning visibility use production runtime code and are exercised by the shipped regression suite.

## Self-Check: PASSED

- src/intake/pipeline.py: FOUND
- src/ui/runtime.py: FOUND
- app/streamlit_app.py: FOUND
- tests/test_phase6_reliability.py: FOUND
- tests/test_llm_client.py: FOUND
- tests/test_routing_interrupts.py: FOUND
- tests/test_root_cause_agent.py: FOUND
- Commit: 2b6634e