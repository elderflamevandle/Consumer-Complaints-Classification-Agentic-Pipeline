"""LangGraph multi-agent pipeline for FinComplaint AI.

Architecture:
  START
    -> intake               (PII scrubber)
    -> product_classifier   (Stage-1: identify product)
    -> issue_classifier     (Stage-2: identify issue + severity, conditioned on product)
    -> root_cause           (RAG-based diagnosis)
    -> remediator           (MCP policy grounding)
    -> response_writer      (draft customer response)
    -> response_auditor     (compliance audit + rewrite loop)
         | approved          | needs_rewrite (loop back)
    -> explainer            (audit trail generation)
    -> END

Usage:
    from src.graph.pipeline import build_graph, run_complaint

    graph = build_graph()
    result = run_complaint(graph, complaint_text="I was charged twice...")
"""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.graph.langgraph_state import PipelineState
from src.graph.nodes import (
    explainer_node,
    intake_processor_node,
    issue_classifier_node,
    product_classifier_node,
    remediator_node,
    response_auditor_node,
    response_writer_node,
    root_cause_node,
)


# ---------------------------------------------------------------------------
# Conditional edge function
# ---------------------------------------------------------------------------

def _route_after_auditor(state: PipelineState) -> str:
    """After the auditor: approved -> explainer, needs_rewrite -> writer."""
    if state.get("response_loop_status") == "approved":
        return "explainer"
    return "response_writer"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph() -> Any:
    """Build and compile the FinComplaint AI LangGraph pipeline.

    Returns:
        Compiled LangGraph CompiledGraph ready for .invoke() / .stream().
    """
    workflow = StateGraph(PipelineState)

    # Register nodes
    workflow.add_node("intake_processor", intake_processor_node)
    workflow.add_node("product_classifier", product_classifier_node)
    workflow.add_node("issue_classifier", issue_classifier_node)
    workflow.add_node("root_cause", root_cause_node)
    workflow.add_node("remediator", remediator_node)
    workflow.add_node("response_writer", response_writer_node)
    workflow.add_node("response_auditor", response_auditor_node)
    workflow.add_node("explainer", explainer_node)

    # Linear edges
    workflow.add_edge(START, "intake_processor")
    workflow.add_edge("intake_processor", "product_classifier")
    workflow.add_edge("product_classifier", "issue_classifier")
    workflow.add_edge("issue_classifier", "root_cause")
    workflow.add_edge("root_cause", "remediator")
    workflow.add_edge("remediator", "response_writer")
    workflow.add_edge("response_writer", "response_auditor")

    # Writer/auditor rewrite loop
    workflow.add_conditional_edges(
        "response_auditor",
        _route_after_auditor,
        {
            "explainer": "explainer",
            "response_writer": "response_writer",
        },
    )

    workflow.add_edge("explainer", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

def run_complaint(
    graph: Any,
    complaint_text: str,
    *,
    thread_id: str | None = None,
    state_code: str = "XX",
    config: dict[str, Any] | None = None,
) -> PipelineState:
    """Run the full pipeline for a single complaint.

    Args:
        graph:          Compiled LangGraph graph from build_graph().
        complaint_text: Raw consumer complaint text.
        thread_id:      Optional thread ID for tracking.
        state_code:     US state code for MCP policy lookup (e.g. 'NY').
        config:         Additional LangGraph config (e.g. recursion_limit).

    Returns:
        Final PipelineState after all nodes complete.
    """
    tid = thread_id or str(uuid.uuid4())
    initial_state: PipelineState = {
        "thread_id": tid,
        "raw_complaint": complaint_text,
        "state_code": state_code,
        "rewrite_count": 0,
        "events": [],
        "stage_telemetry": [],
        "unresolved_issues": [],
    }

    run_config: dict[str, Any] = {"configurable": {"thread_id": tid}}
    if config:
        run_config.update(config)

    return graph.invoke(initial_state, config=run_config)


# ---------------------------------------------------------------------------
# Module-level singleton graph (used by UI runtime)
# ---------------------------------------------------------------------------

_GRAPH: Any | None = None


def get_graph() -> Any:
    """Return the module-level compiled graph, building it on first call."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH
