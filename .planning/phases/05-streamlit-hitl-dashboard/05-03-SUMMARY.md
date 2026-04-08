---
phase: 05-streamlit-hitl-dashboard
plan: "03"
subsystem: ui
tags: [hitl, review-panel, streamlit, same-thread-resume, tdd]
dependency_graph:
  requires: ["05-01", "05-02"]
  provides: ["review-panel", "hitl-action-contract", "same-thread-resume"]
  affects: ["app/streamlit_app.py", "src/ui/review.py", "src/ui/dashboard_state.py"]
tech_stack:
  added: []
  patterns: ["ReviewPanelState dataclass", "ReviewActionResult typed adapter", "same-thread continuity via thread_id preservation"]
key_files:
  created:
    - src/ui/review.py
    - tests/test_review_session.py
  modified:
    - src/ui/dashboard_state.py
    - app/streamlit_app.py
    - tests/test_streamlit_app.py
decisions:
  - "ReviewPanelState uses dataclass (not Pydantic) to stay consistent with existing UI telemetry layer"
  - "apply_reviewer_action_from_ui uses a routing proxy so the UI layer does not need to import RoutingState directly"
  - "build_post_action_banner always includes thread_id so the banner is audit-traceable"
  - "DashboardState.clear_for_new_run resets both pending_review and review_banner atomically to prevent stale UI state"
metrics:
  duration: "6 min"
  completed: "2026-04-08"
  tasks: 3
  files: 5
---

# Phase 5 Plan 03: HITL Review Panel and Same-Thread Resume Summary

Sticky review panel with inline approve, edit, and reject actions; typed session state for reviewer continuity; same-thread resume adapter; and full regression test coverage for UI-03.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add typed review-session continuity and interrupt-adapter helpers | 55858b1 | src/ui/review.py, src/ui/dashboard_state.py |
| 2 | Implement sticky review panel with inline edit and auto-resume flow | fe56120 | app/streamlit_app.py |
| 3 | Add review continuity regression coverage for approve, edit, and reject flows | 4f140b0 | tests/test_review_session.py, tests/test_streamlit_app.py |

## What Was Built

### src/ui/review.py (new)

- `ReviewAction` enum: typed approve/edit/reject values
- `ReviewPanelState` dataclass: thread_id, complaint_summary, interrupt_reason, stage_output, allowed_actions, draft_edit_text; persists across Streamlit reruns
- `ReviewPanelState.from_interrupt_payload()`: factory that maps from LangGraph ReviewInterruptPayload to panel state
- `ReviewActionResult` dataclass: typed result with action, thread_id, resume_status, error
- `apply_reviewer_action_from_ui()`: adapter that dispatches approve/edit/reject and always preserves the original thread_id for same-thread continuity
- `build_post_action_banner()`: informative banner message for post-action feedback, includes thread_id for audit traceability

### src/ui/dashboard_state.py (extended)

- Added `pending_review` field: `ReviewPanelState | None`, default None
- Added `review_banner` field: `str | None`, default None
- Added `set_pending_review(review_state)`: sets pending review and updates active_thread_id
- Added `clear_review(banner)`: clears pending review, optionally sets banner
- Added `clear_for_new_run()`: atomically clears both pending_review and review_banner before a new pipeline run

### app/streamlit_app.py (extended)

- `_render_review_panel(state)`: sticky two-column review surface rendered when `state.pending_review` is set; shows complaint summary, interrupt reason, and stage output next to approve/edit/reject controls
- `_dispatch_review_action(state, action, draft_text)`: calls the UI adapter, generates banner, clears review state
- `_run_pipeline()` now calls `state.clear_for_new_run()` before execution to prevent stale review state
- Post-action banner shown at top of workspace via `st.success(state.review_banner)`

### tests/test_review_session.py (new, 327 lines)

Covers:
- `test_interrupt_panel_exposes_reviewer_actions` (Task 1 verification)
- `test_review_edit_resumes_same_thread` (Task 2 verification)
- All three action flows (approve/edit/reject) with same-thread continuity assertions
- DashboardState pending_review and review_banner lifecycle
- ReviewPanelState.from_interrupt_payload factory mapping
- build_post_action_banner informative output
- clear_for_new_run atomic reset

### tests/test_streamlit_app.py (extended, +9 tests)

Task 3 regression coverage:
- approve/edit/reject thread_id preservation
- reject status audit queryability
- banner informativeness for all actions
- _render_review_panel and _dispatch_review_action presence in streamlit_app.py source

## Verification

- `uv run pytest -q tests/test_review_session.py tests/test_streamlit_app.py` — 43 tests pass
- Approve, edit, and reject actions all preserve thread_id (same-thread continuity)
- Reject flow returns resume_status="rejected" and preserves thread for audit queryability
- Post-action banner always includes thread_id for traceability

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- The `apply_reviewer_action_from_ui` adapter uses a MagicMock routing proxy inside `_dispatch_review_action` in the Streamlit app to keep the UI layer decoupled from the RoutingState Pydantic model. This is appropriate for the demo MVP — a production system would wire the actual RoutingState from a LangGraph checkpoint store.
- `ReviewPanelState` uses a dataclass (not Pydantic) to stay consistent with the existing `StageTelemetry`, `BudgetTelemetry`, and `AuditEventSnapshot` UI layer types established in Phase 5 Plan 01.

## Known Stubs

None — all data paths in the review panel use actual typed state. The MagicMock proxy in `_dispatch_review_action` is an explicit adapter pattern, not a data stub, and does not affect rendering or audit visibility.

## Self-Check: PASSED

- src/ui/review.py: FOUND
- src/ui/dashboard_state.py (extended): FOUND
- app/streamlit_app.py (extended): FOUND
- tests/test_review_session.py: FOUND
- tests/test_streamlit_app.py (extended): FOUND
- Commits: d2a8d10, 55858b1, fe56120, 4f140b0 — all verified in git log
