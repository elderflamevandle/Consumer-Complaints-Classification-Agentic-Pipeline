---
phase: "05"
plan: "01"
subsystem: ui
tags: [streamlit, hitl, dashboard, demo-catalog, session-state, apptestD]
dependency_graph:
  requires: []
  provides:
    - src/ui/dashboard_state.py (DashboardState typed session contract)
    - src/ui/demo_cases.py (golden demo catalog loader)
    - data/golden_demos.json (five curated demo scenarios)
    - app/streamlit_app.py (Streamlit control-room shell)
  affects:
    - Phase 5 Plan 02 (pipeline runner and stage card rendering)
    - Phase 5 Plan 03 (human-review controls and audit tab)
tech_stack:
  added:
    - streamlit>=1.35.0 (UI framework for control-room shell)
  patterns:
    - Typed dataclass session state (DashboardState) with shared composer contract
    - Scenario-card layout with load-into-composer pattern (no separate run path)
    - AppTest regression coverage using streamlit.testing.v1
key_files:
  created:
    - src/ui/__init__.py
    - src/ui/dashboard_state.py
    - src/ui/demo_cases.py
    - data/golden_demos.json
    - app/streamlit_app.py
    - tests/test_ui_runtime.py
    - tests/test_streamlit_app.py
  modified:
    - pyproject.toml (added streamlit dependency)
    - scripts/tasks.py (added dashboard task command)
decisions:
  - "Used DashboardState dataclass (not TypedDict) to support mutation methods like load_demo() and clear_composer() while keeping the session contract typed and testable."
  - "Demo Load buttons keyed as load_{demo_id} so AppTest can locate them by key for deterministic test assertions."
  - "Form submit buttons appear in at.button (not at.form_submit_button) in Streamlit AppTest v1.35+ - documented in test comments."
metrics:
  duration: "6 min"
  completed: "2026-04-08"
  tasks: 3
  files: 9
---

# Phase 5 Plan 01: Control-Room Shell and Golden Demo Catalog Summary

**One-liner:** Streamlit control-room shell with shared editable complaint composer and five curated golden demos loaded via scenario cards into the same submission path.

## What Was Built

The Phase 5 operator surface is established: a single-page Streamlit dashboard (app/streamlit_app.py) where operators can either type a complaint manually or click one of five golden demo scenario cards to load pre-curated text into the same shared text_area composer. Both paths submit through the same `st.form`.

The supporting modules are:
- `src/ui/dashboard_state.py` - `DashboardState` dataclass with `complaint_text`, `selected_demo`, `active_thread_id`, and `last_snapshot` fields. Provides `load_demo()`, `clear_composer()`, `set_active_thread()`, and `update_snapshot()` methods for later pipeline integration.
- `src/ui/demo_cases.py` - `load_golden_demos()` and `get_demo_by_id()` loading from `data/golden_demos.json`, with full validation of required fields.
- `data/golden_demos.json` - Five curated consumer finance complaint scenarios: unauthorized credit card charge, mortgage payment misapplied, student loan servicer transfer error, overdraft fee cascade, and auto insurance wrongful denial.

A `dashboard` task command was added to `scripts/tasks.py` so operators can launch with `uv run python scripts/tasks.py dashboard`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add typed dashboard state and curated golden demo catalog | b94ebf1 | src/ui/__init__.py, src/ui/dashboard_state.py, src/ui/demo_cases.py, data/golden_demos.json, tests/test_ui_runtime.py |
| 2 | Build Streamlit control-room shell with shared editable composer | 4ee060a | pyproject.toml, scripts/tasks.py, app/streamlit_app.py, tests/test_streamlit_app.py |
| 3 | Add AppTest coverage for landing view and demo loading path | eca4e22 | tests/test_ui_runtime.py, tests/test_streamlit_app.py |

## Test Results

All 21 tests pass:
- 11 tests in `tests/test_ui_runtime.py` (catalog contract, DashboardState behavior, demo realism)
- 10 tests in `tests/test_streamlit_app.py` (AppTest landing view, demo loading, composer editability, no-browser exercise)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AppTest exception check used `is None` instead of falsy check**
- **Found during:** Task 2 (GREEN phase verification)
- **Issue:** `at.exception` returns an `ElementList()` (falsy when empty) not `None`. Tests using `assert at.exception is None` failed even with a healthy app.
- **Fix:** Changed all exception assertions to `assert not at.exception` with explanatory comments.
- **Files modified:** tests/test_streamlit_app.py
- **Commit:** 4ee060a

**2. [Rule 1 - Bug] `form_submit_button` attribute does not exist in AppTest v1.35+**
- **Found during:** Task 2 (GREEN phase verification)
- **Issue:** The test assumed `at.form_submit_button` existed. In Streamlit AppTest, form submit buttons are included in `at.button`.
- **Fix:** Changed test to assert `len(at.button) >= 6` (5 demo load + at least 1 form submit).
- **Files modified:** tests/test_streamlit_app.py
- **Commit:** 4ee060a

## Known Stubs

None - the control-room shell renders real data from `data/golden_demos.json`. Pipeline integration (stage cards, audit trace) is intentionally deferred to Phase 5 Plan 02 per the roadmap and is shown as a placeholder info banner after submission.

## Self-Check: PASSED

All created files confirmed present on disk. All task commits (b94ebf1, 4ee060a, eca4e22) confirmed in git log.
