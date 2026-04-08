---
phase: "05"
plan: "02"
subsystem: ui
tags: [streamlit, telemetry, audit, budget, runtime-facade, tdd]
dependency_graph:
  requires:
    - "05-01"
    - "src/llm/client.py (LLMResponse.total_tokens)"
    - "src/tools/audit_logger.py (fetch_events, log_node_outcome)"
    - "src/llm/rate_limiter.py (TokenBudgetTracker.snapshot)"
    - "All pipeline agents (classifier, root_cause, remediator, writer, auditor, explainer)"
  provides:
    - "src/ui/telemetry.py: typed telemetry contracts (StageTelemetry, DashboardSnapshot, BudgetTelemetry, AuditEventSnapshot)"
    - "src/ui/runtime.py: UI-safe complaint runtime facade"
    - "app/streamlit_app.py: compact stage cards, audit tab, budget widget, final response rendering"
  affects:
    - "Phase 5 Plan 03 (human review controls)"
    - "Any future plan consuming DashboardSnapshot"
tech_stack:
  added:
    - "src/ui/telemetry.py (dataclasses, enum)"
    - "src/ui/runtime.py (facade over all pipeline agents)"
  patterns:
    - "TDD red-green for all three tasks"
    - "Module-level shared budget tracker with injectable reset for tests"
    - "Agent stage timing via time.monotonic() with latency_ms capture"
    - "Injected transport + in-memory SQLite for testable runtime calls"
    - "st.tabs for control-room / audit-log split layout"
    - "st.expander per stage card for compact-by-default with deeper artifact detail"
key_files:
  created:
    - src/ui/telemetry.py
    - src/ui/runtime.py
  modified:
    - app/streamlit_app.py
    - tests/test_ui_runtime.py
    - tests/test_streamlit_app.py
decisions:
  - "Stage telemetry uses dataclasses rather than Pydantic for zero-dependency UI layer (no Pydantic in Streamlit render path)"
  - "Runtime facade uses module-level shared TokenBudgetTracker so budget accumulates across runs per session"
  - "Remediator failure is non-fatal in the facade — downstream stages receive a stub RemediationResult so the run continues"
  - "st.tabs separates Control Room (cards + response) from Audit Log to avoid cluttering main workspace"
  - "Agent model metadata read via last_model attribute post-call rather than instrumenting each client call"
metrics:
  duration: "7 min"
  completed: "2026-04-08"
  tasks_completed: 3
  files_changed: 5
  tests_added: 22
---

# Phase 5 Plan 02: Runtime Telemetry, Audit Tab, and Budget Widget Summary

**One-liner:** Typed stage telemetry contracts plus a UI-safe runtime facade powering compact stage cards, chronological audit tab, always-visible budget widget, and final response/explainer rendering in the Streamlit control room.

## What Was Built

### Task 1: Typed stage telemetry contracts (`src/ui/telemetry.py`, `src/llm/client.py`)
- `StageStatus` enum covering PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
- `StageTelemetry` dataclass with stage_name, status, model, latency_ms, total_tokens, artifacts, error_message
- `BudgetTelemetry` dataclass mapping TokenBudgetTracker.snapshot() to UI-consumable fields
- `AuditEventSnapshot` dataclass with thread_id, node, timestamp, decision, model_version, latency_ms
- `DashboardSnapshot` dataclass composing stages, budget, audit_events, final_response, final_explanation, run_status
- Helper `budget_telemetry_from_snapshot()` and `audit_event_from_dict()` converters
- LLMResponse.total_tokens confirmed already present in src/llm/client.py (no change needed)

### Task 2: Dashboard runtime facade (`src/ui/runtime.py`)
- `run_complaint()` executes all seven pipeline stages: intake, classifier, root_cause, remediator, writer, auditor, explainer
- Per-stage timing captures latency_ms via time.monotonic()
- Audit events written to SQLite via AuditLogger with thread-scoped fetch
- `fetch_budget_snapshot()` returns current BudgetTelemetry for header widget
- `fetch_audit_events()` loads chronological events by thread_id
- Injectable transport and db_connect_fn for test isolation
- Module-level shared budget tracker with reset_shared_budget() for test cleanup
- Remediator failure non-fatal: stub RemediationResult allows downstream stages to continue

### Task 3: Streamlit control room update (`app/streamlit_app.py`)
- Budget header widget always visible in top-right showing used/total tokens, warning/degrade state
- Stage telemetry cards use st.expander — compact by default, artifacts visible on expand
- st.tabs splits Control Room (stage cards + response) from Audit Log tab
- Audit Log tab renders timestamp, node, decision, model, latency in columnar layout (oldest-to-newest)
- Final customer response rendered in read-only text area after completed runs
- Explainer bullets listed under Explainer Trace section
- Both manual complaint text and loaded demos execute through the same complaint_form submit path

## Requirements Satisfied

- **UI-02**: Stage cards show model, latency, token usage for each pipeline node
- **UI-04**: Dedicated Audit Log tab backed by SQLite events with timestamp/decision/model fields
- **UI-05**: Always-visible daily budget widget with warning and degrade state indicators

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all telemetry values are captured from real pipeline execution. The runtime facade
wires real agent invocations; test isolation uses mock transports, not placeholder data.

## Self-Check: PASSED

- `src/ui/telemetry.py` exists and contains `latency_ms`
- `src/ui/runtime.py` exists with `run_complaint()` function (577 lines >= 120 minimum)
- `app/streamlit_app.py` contains `st.tabs` for the audit tab
- `tests/test_ui_runtime.py` is 383 lines >= 80 minimum
- `tests/test_streamlit_app.py` is 404 lines >= 110 minimum
- All 36 tests in `tests/test_ui_runtime.py tests/test_streamlit_app.py` pass
- Commits: 8fc75a5 (Task 1), 3982db1 (Task 2), 4ae2fec (Task 3)
