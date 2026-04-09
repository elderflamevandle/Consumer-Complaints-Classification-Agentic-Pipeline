"""Phase 5 Streamlit control-room shell for FinComplaint AI.

Provides a single operator workspace with:
- A shared editable complaint composer (manual text + golden demo loading)
- Compact stage telemetry cards with model/latency/token data and expanders
- Dedicated audit tab with chronological decision events (timestamp/decision/model)
- Always-visible daily token-budget header widget
- Final customer response and explainer artifacts after a completed run
- Sticky HITL review panel with inline approve, edit, and reject actions
- Auto-resume same-thread continuation after reviewer submission

All pipeline execution flows through the same composer-submit path via the
run_complaint() runtime facade in src/ui/runtime.py.
"""

from __future__ import annotations

import streamlit as st

from src.ui.dashboard_state import DashboardState
from src.ui.demo_cases import load_golden_demos
from src.ui.telemetry import BudgetTelemetry, DashboardSnapshot, StageStatus

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FinComplaint AI - Control Room",
    page_icon=":scales:",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_session_state() -> None:
    """Initialise typed dashboard state in st.session_state if not present."""
    if "dashboard" not in st.session_state:
        st.session_state["dashboard"] = DashboardState()
    if "last_run_snapshot" not in st.session_state:
        st.session_state["last_run_snapshot"] = None


def _get_state() -> DashboardState:
    """Return the typed DashboardState from session state."""
    return st.session_state["dashboard"]  # type: ignore[return-value]


def _get_snapshot() -> DashboardSnapshot | None:
    """Return the last pipeline run snapshot, or None if no run yet."""
    return st.session_state.get("last_run_snapshot")  # type: ignore[return-value]


def _set_snapshot(snapshot: DashboardSnapshot) -> None:
    """Store a completed pipeline run snapshot in session state."""
    st.session_state["last_run_snapshot"] = snapshot


# ---------------------------------------------------------------------------
# Demo loading callback
# ---------------------------------------------------------------------------
def _load_demo_callback(demo_id: str, complaint_text: str) -> None:
    """Callback: load selected golden demo into the shared composer."""
    state = _get_state()
    state.load_demo(demo_id=demo_id, complaint_text=complaint_text)


# ---------------------------------------------------------------------------
# Budget widget
# ---------------------------------------------------------------------------
def _render_budget_widget(budget: BudgetTelemetry | None) -> None:
    """Render compact always-visible daily token-budget header widget.

    Args:
        budget: Current budget telemetry from the runtime facade.
    """
    if budget is None:
        st.caption("Token budget: loading...")
        return

    pct = int(budget.utilization * 100)
    used_k = budget.used_tokens // 1000
    total_k = budget.daily_budget // 1000

    if budget.degrade_non_critical:
        status_label = "DEGRADED"
        color = "red"
    elif budget.warning:
        status_label = "WARNING"
        color = "orange"
    else:
        status_label = "OK"
        color = "green"

    st.markdown(
        f"**Token Budget** &nbsp; "
        f":{color}[{used_k}K / {total_k}K ({pct}%) - {status_label}]"
    )


# ---------------------------------------------------------------------------
# Scenario cards
# ---------------------------------------------------------------------------
def _render_scenario_cards(demos: list) -> None:  # type: ignore[type-arg]
    """Render five golden demo scenario cards alongside the complaint composer.

    Args:
        demos: List of DemoRecord dicts from load_golden_demos().
    """
    st.subheader("Golden Demo Scenarios")
    st.caption("Select a scenario to load it into the complaint composer.")

    cols = st.columns(len(demos))
    for col, demo in zip(cols, demos):
        with col:
            st.markdown(f"**{demo['title']}**")
            st.caption(demo["summary"])
            if st.button("Load", key=f"load_{demo['id']}"):
                _load_demo_callback(demo["id"], demo["complaint_text"])
                st.rerun()


# ---------------------------------------------------------------------------
# Composer form
# ---------------------------------------------------------------------------
def _render_composer(state: DashboardState) -> str:
    """Render the shared editable complaint composer inside an st.form.

    Returns:
        The complaint text string at submission time (from form submit).
    """
    st.subheader("Complaint Composer")

    submitted_text = ""
    with st.form("complaint_form", clear_on_submit=False):
        complaint_input = st.text_area(
            label="Complaint Text",
            value=state.complaint_text,
            height=200,
            placeholder="Paste or type a complaint here, or load a demo scenario above.",
            help="This composer is shared for both manual entry and loaded golden demos.",
        )
        col_submit, col_clear = st.columns([1, 4])
        with col_submit:
            submitted = st.form_submit_button("Run Pipeline", type="primary")
        with col_clear:
            cleared = st.form_submit_button("Clear")

    if submitted and complaint_input.strip():
        state.complaint_text = complaint_input.strip()
        submitted_text = state.complaint_text

    if cleared:
        state.clear_composer()
        st.rerun()

    return submitted_text


# ---------------------------------------------------------------------------
# Sticky HITL review panel
# ---------------------------------------------------------------------------
def _render_review_panel(state: DashboardState) -> None:
    """Render the sticky review panel when a run is paused for human action.

    Displays complaint summary, interrupt reason, and current stage output
    next to inline approve, edit, and reject controls. Submitting an action
    auto-resumes the same thread and shows explicit status feedback.

    Args:
        state: Current DashboardState with pending_review set.
    """
    from src.ui.review import apply_reviewer_action_from_ui, build_post_action_banner

    review = state.pending_review
    if review is None:
        return

    st.divider()
    st.subheader("Human Review Required")
    st.info(
        f"Pipeline paused on thread `{review.thread_id}`. "
        "Review the context below and select an action."
    )

    col_context, col_actions = st.columns([3, 2])

    with col_context:
        st.markdown("**Complaint Summary**")
        st.text(review.complaint_summary)

        st.markdown("**Interrupt Reason**")
        st.text(review.interrupt_reason)

        st.markdown("**Current Stage Output**")
        for key, val in review.stage_output.items():
            st.text(f"{key}: {val}")

    with col_actions:
        st.markdown("**Reviewer Actions**")
        st.caption("Select one action to resume or close the pipeline.")

        # Approve
        if "approve" in review.allowed_actions:
            if st.button("Approve", key="review_approve", type="primary"):
                _dispatch_review_action(state, "approve", draft_text=None)
                st.rerun()

        # Edit with inline text input
        if "edit" in review.allowed_actions:
            draft = st.text_input(
                "Edit (enter updated classification or note):",
                value=review.draft_edit_text or "",
                key="review_edit_draft",
                placeholder="e.g. billing, credit_card, low risk",
            )
            if st.button("Submit Edit", key="review_edit_submit"):
                _dispatch_review_action(state, "edit", draft_text=draft or None)
                st.rerun()

        # Reject
        if "reject" in review.allowed_actions:
            if st.button("Reject", key="review_reject"):
                _dispatch_review_action(state, "reject", draft_text=None)
                st.rerun()


def _dispatch_review_action(
    state: DashboardState,
    action: str,
    draft_text: str | None,
) -> None:
    """Dispatch a reviewer action, update state, and set post-action banner.

    Args:
        state: DashboardState carrying the pending_review context.
        action: One of "approve", "edit", "reject".
        draft_text: Inline edit text for edit actions; None otherwise.
    """
    from src.ui.review import apply_reviewer_action_from_ui, build_post_action_banner
    from unittest.mock import MagicMock

    review = state.pending_review
    if review is None:
        return

    # Build a minimal routing-state proxy for the adapter (UI layer stays simple)
    routing_proxy = MagicMock()
    routing_proxy.thread_id = review.thread_id

    result = apply_reviewer_action_from_ui(
        routing_state=routing_proxy,
        action=action,
        draft_text=draft_text,
    )

    banner = build_post_action_banner(action, thread_id=result.thread_id)
    state.clear_review(banner=banner)


# ---------------------------------------------------------------------------
# Stage telemetry cards
# ---------------------------------------------------------------------------
def _status_badge(status: StageStatus) -> str:
    """Return a color-coded status badge string for a stage card."""
    if status == StageStatus.COMPLETED:
        return ":green[DONE]"
    if status == StageStatus.RUNNING:
        return ":blue[RUNNING]"
    if status == StageStatus.FAILED:
        return ":red[FAILED]"
    if status == StageStatus.SKIPPED:
        return ":gray[SKIPPED]"
    return ":gray[PENDING]"


def _coerce_warning_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


def _collect_snapshot_warnings(snapshot: DashboardSnapshot) -> list[str]:
    warnings: list[str] = []
    for stage in snapshot.stages:
        for warning in _coerce_warning_list(stage.artifacts.get("warnings")):
            warnings.append(f"{stage.stage_name}: {warning}")
    return warnings


def _render_stage_cards(snapshot: DashboardSnapshot) -> None:
    """Render compact stage telemetry cards with expanders for deeper detail.

    Args:
        snapshot: Completed DashboardSnapshot from run_complaint().
    """
    st.subheader("Pipeline Stages")

    for stage in snapshot.stages:
        badge = _status_badge(stage.status)
        header = (
            f"**{stage.stage_name.replace('_', ' ').title()}** "
            f"{badge} &nbsp; "
            f"Model: `{stage.model or 'N/A'}` &nbsp; "
            f"Latency: `{stage.latency_ms}ms` &nbsp; "
            f"Tokens: `{stage.total_tokens}`"
        )
        with st.expander(header, expanded=False):
            stage_warnings = _coerce_warning_list(stage.artifacts.get("warnings"))
            if stage_warnings:
                st.warning("Warnings: " + "; ".join(stage_warnings))
            if stage.error_message:
                st.error(f"Error: {stage.error_message}")
            elif stage.artifacts:
                for key, value in stage.artifacts.items():
                    if key == "warnings":
                        continue
                    st.text(f"{key}: {value}")
            else:
                st.caption("No artifact detail available for this stage.")


# ---------------------------------------------------------------------------
# Audit tab rendering
# ---------------------------------------------------------------------------
def _render_audit_events(snapshot: DashboardSnapshot) -> None:
    """Render chronological audit decision events for the active thread.

    Shows timestamp, node, decision label, model version, and latency in
    a structured table ordered oldest-to-newest.

    Args:
        snapshot: Completed DashboardSnapshot from run_complaint().
    """
    if not snapshot.audit_events:
        st.info("No audit events recorded for this run.")
        return

    st.caption(
        f"Thread: `{snapshot.thread_id}` - {len(snapshot.audit_events)} event(s), "
        "oldest to newest"
    )

    for event in snapshot.audit_events:
        cols = st.columns([3, 2, 3, 2, 1])
        with cols[0]:
            st.text(event.timestamp)
        with cols[1]:
            st.text(event.node)
        with cols[2]:
            st.text(event.decision)
        with cols[3]:
            st.text(event.model_version)
        with cols[4]:
            st.text(f"{event.latency_ms}ms")


# ---------------------------------------------------------------------------
# Final response and explainer rendering
# ---------------------------------------------------------------------------
def _render_final_outputs(snapshot: DashboardSnapshot) -> None:
    """Render the final customer response and explainer artifacts.

    Args:
        snapshot: Completed DashboardSnapshot from run_complaint().
    """
    if snapshot.run_status == "error":
        st.error(f"Pipeline failed: {snapshot.error_message or 'Unknown error'}")
        return

    if snapshot.final_response:
        st.subheader("Customer Response Draft")
        st.text_area(
            "Final Response",
            value=snapshot.final_response,
            height=300,
            disabled=True,
        )
    else:
        st.info("No final response generated.")

    if snapshot.final_explanation:
        st.subheader("Explainer Trace")
        for bullet in snapshot.final_explanation:
            st.markdown(f"- {bullet}")
    else:
        st.caption("Explainer output not available.")


# ---------------------------------------------------------------------------
# Full dashboard result view (tabs layout)
# ---------------------------------------------------------------------------
def _render_results(snapshot: DashboardSnapshot) -> None:
    """Render the full post-run control-room view with tabs.

    Tab 1 - Control Room: Stage cards + final response/explainer
    Tab 2 - Audit Log: Chronological audit decision events
    """
    st.divider()

    snapshot_warnings = _collect_snapshot_warnings(snapshot)
    if snapshot_warnings:
        st.warning("Non-critical warnings: " + " | ".join(snapshot_warnings))

    tab_control, tab_audit = st.tabs(["Control Room", "Audit Log"])

    with tab_control:
        _render_stage_cards(snapshot)
        st.divider()
        _render_final_outputs(snapshot)

    with tab_audit:
        st.subheader("Audit Decision Log")
        st.caption(
            "Chronological pipeline decision events for the active thread, "
            "ordered oldest to newest."
        )
        # Column headers
        cols = st.columns([3, 2, 3, 2, 1])
        headers = ["Timestamp", "Node", "Decision", "Model", "Latency"]
        for col, header in zip(cols, headers):
            with col:
                st.markdown(f"**{header}**")
        st.divider()
        _render_audit_events(snapshot)


# ---------------------------------------------------------------------------
# Pipeline execution callback
# ---------------------------------------------------------------------------
def _run_pipeline(complaint_text: str, state: DashboardState) -> None:
    """Execute the pipeline and store the result in session state.

    This is called from the main render loop when the operator submits a complaint.
    Uses the runtime facade in src/ui/runtime for the shared submit path.
    Clears any prior review state before starting a new run.
    """
    from src.ui.runtime import run_complaint, reset_shared_budget

    # Clear previous review panel and banner for a fresh run
    state.clear_for_new_run()

    with st.spinner("Running complaint pipeline..."):
        try:
            snapshot = run_complaint(complaint_text=complaint_text)
            state.set_active_thread(snapshot.thread_id)
            state.update_snapshot(snapshot.run_status == "completed" and {"run_status": "completed"} or {})
            _set_snapshot(snapshot)
        except Exception as exc:
            st.error(f"Pipeline execution error: {exc}")


# ---------------------------------------------------------------------------
# Main app entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Phase 5 Streamlit control-room shell."""
    _init_session_state()
    state = _get_state()
    demos = load_golden_demos()
    snapshot = _get_snapshot()

    # --- Header with budget widget ---
    col_title, col_budget = st.columns([4, 2])
    with col_title:
        st.title("FinComplaint AI - Control Room")
    with col_budget:
        budget_data = snapshot.budget if snapshot else None
        _render_budget_widget(budget_data)

    st.caption(
        "Classify, investigate, and draft responses for consumer finance complaints. "
        "Load a curated demo or enter a complaint manually below."
    )
    st.divider()

    # --- Post-action review banner (shown after approve/edit/reject) ---
    if state.review_banner:
        st.success(state.review_banner)

    # --- Sticky review panel (shown when pipeline is paused for HITL) ---
    if state.pending_review is not None:
        _render_review_panel(state)

    # --- Scenario cards ---
    _render_scenario_cards(demos)
    st.divider()

    # --- Shared complaint composer ---
    submitted_text = _render_composer(state)

    # --- Execute pipeline when complaint is submitted ---
    if submitted_text:
        _run_pipeline(submitted_text, state)
        snapshot = _get_snapshot()
        st.rerun()

    # --- Show results if a run has completed ---
    if snapshot is not None:
        _render_results(snapshot)


main()
