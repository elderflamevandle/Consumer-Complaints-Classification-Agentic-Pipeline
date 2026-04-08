"""Phase 5 Streamlit control-room shell for FinComplaint AI.

Provides a single operator workspace with a shared editable complaint composer
and golden demo scenario cards. Free-text manual entry and curated demo loading
use the same composer and the same pipeline submission path.
"""

from __future__ import annotations

import streamlit as st

from src.ui.dashboard_state import DashboardState
from src.ui.demo_cases import load_golden_demos

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


def _get_state() -> DashboardState:
    """Return the typed DashboardState from session state."""
    return st.session_state["dashboard"]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Demo loading callback
# ---------------------------------------------------------------------------
def _load_demo_callback(demo_id: str, complaint_text: str) -> None:
    """Callback: load selected golden demo into the shared composer."""
    state = _get_state()
    state.load_demo(demo_id=demo_id, complaint_text=complaint_text)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def _render_header() -> None:
    """Render the control-room page title and short description."""
    st.title("FinComplaint AI - Control Room")
    st.caption(
        "Classify, investigate, and draft responses for consumer finance complaints. "
        "Load a curated demo or enter a complaint manually below."
    )


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


def _render_pipeline_placeholder(thread_text: str) -> None:
    """Render a placeholder banner when a pipeline run is triggered."""
    st.divider()
    st.info(
        f"Pipeline run requested for complaint: \"{thread_text[:80]}{'...' if len(thread_text) > 80 else ''}\"\n\n"
        "Stage cards and audit trace will appear here as the pipeline executes. "
        "(Full pipeline integration arrives in Phase 5 Plan 02.)"
    )


# ---------------------------------------------------------------------------
# Main app entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Phase 5 Streamlit control-room shell."""
    _init_session_state()
    state = _get_state()
    demos = load_golden_demos()

    _render_header()
    st.divider()

    # Side-by-side layout: scenario cards (left/top) and composer (right/below)
    _render_scenario_cards(demos)
    st.divider()

    submitted_text = _render_composer(state)

    if submitted_text:
        _render_pipeline_placeholder(submitted_text)


main()
