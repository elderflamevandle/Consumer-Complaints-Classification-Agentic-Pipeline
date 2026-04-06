---
phase: 5
slug: streamlit-hitl-dashboard
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 5 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + Streamlit AppTest + ruff + mypy |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `Run the current task's <automated> verify command from the Per-Task Verification Map` |
| **Full suite command** | `uv run pytest -q && uv run ruff check . && uv run mypy src app` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run the current task's `<automated>` verify command from the Per-Task Verification Map
- **After every plan wave:** Run `uv run pytest -q && uv run ruff check . && uv run mypy src app`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | DATA-03 | unit | `uv run pytest -q tests/test_ui_runtime.py::test_demo_catalog_contains_five_curated_cases` | ? | ? pending |
| 5-01-02 | 01 | 1 | UI-01 | integration | `uv run pytest -q tests/test_streamlit_app.py::test_dashboard_landing_view_shows_composer_and_demo_cards` | ? | ? pending |
| 5-01-03 | 01 | 1 | UI-01 | integration | `uv run pytest -q tests/test_ui_runtime.py tests/test_streamlit_app.py` | ? | ? pending |
| 5-02-01 | 02 | 2 | UI-02 | unit | `uv run pytest -q tests/test_ui_runtime.py::test_pipeline_runtime_returns_stage_telemetry` | ? | ? pending |
| 5-02-02 | 02 | 2 | UI-04,UI-05 | unit | `uv run pytest -q tests/test_ui_runtime.py::test_runtime_snapshot_exposes_budget_audit_and_final_outputs` | ? | ? pending |
| 5-02-03 | 02 | 2 | UI-02,UI-04,UI-05 | integration | `uv run pytest -q tests/test_streamlit_app.py::test_manual_and_demo_inputs_execute_through_shared_submit_path tests/test_streamlit_app.py::test_stage_cards_show_model_latency_and_tokens tests/test_streamlit_app.py::test_stage_cards_use_expanders_for_deeper_detail tests/test_streamlit_app.py::test_audit_tab_renders_timestamp_decision_and_model_fields_in_order tests/test_streamlit_app.py::test_dashboard_shows_budget_widget_and_status_summary tests/test_streamlit_app.py::test_dashboard_renders_final_response_and_explainer_artifacts` | ? | ? pending |
| 5-03-01 | 03 | 3 | UI-03 | integration | `uv run pytest -q tests/test_review_session.py::test_interrupt_panel_exposes_reviewer_actions` | ? | ? pending |
| 5-03-02 | 03 | 3 | UI-03 | integration | `uv run pytest -q tests/test_review_session.py::test_review_edit_resumes_same_thread` | ? | ? pending |
| 5-03-03 | 03 | 3 | UI-03 | integration | `uv run pytest -q tests/test_review_session.py tests/test_streamlit_app.py` | ? | ? pending |

*Status: ? pending - ? green - ? red - ?? flaky*

---

## Wave 0 Requirements

- [x] Existing pytest, Ruff, and mypy infrastructure already covers the phase baseline
- [x] Plan 05-01 Task 1 creates the first runtime tests before later plan tasks depend on them
- [x] Plan 05-01 Task 2 creates initial AppTest landing coverage alongside the Streamlit shell
- [x] Plan 05-03 Task 1 creates review-session tests before later review-panel verify steps depend on them

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Control-room layout remains readable on a laptop-width window during an interrupted review flow | UI-01, UI-03 | Visual density and operator readability are difficult to judge from automated assertions alone | Run the dashboard with one golden demo that triggers review, confirm the composer, stage cards, sticky review panel, and audit/budget surfaces remain understandable without hidden critical controls |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
