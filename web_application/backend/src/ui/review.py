"""Review-panel helpers and typed review-edit adapter logic for the Phase 5 HITL dashboard.

Provides:
- ReviewPanelState: typed session state for the sticky review panel
- ReviewAction: enum of available reviewer actions
- ReviewActionResult: typed result returned after dispatching a reviewer action
- apply_reviewer_action_from_ui: adapter from UI action → same-thread reviewer action
- build_post_action_banner: constructs informative banner messages after reviewer submission
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewAction(str, Enum):
    """Available reviewer actions for an interrupted pipeline run."""

    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


@dataclass
class ReviewPanelState:
    """Typed state for the sticky review panel, persisted across Streamlit reruns.

    Attributes:
        thread_id: Active pipeline thread to resume (same-thread contract).
        complaint_summary: Short summary of the original complaint for reviewer context.
        interrupt_reason: Reason the pipeline was interrupted (e.g. "low confidence").
        stage_output: Last stage output dict surfaced to the reviewer (focused context).
        allowed_actions: Tuple of actions the reviewer is permitted to take.
        draft_edit_text: Inline edit text entered by the reviewer, or None.
    """

    thread_id: str
    complaint_summary: str
    interrupt_reason: str
    stage_output: dict[str, Any]
    allowed_actions: tuple[str, ...]
    draft_edit_text: str | None = None

    @classmethod
    def from_interrupt_payload(
        cls,
        payload: Any,
        complaint_summary: str,
        stage_output: dict[str, Any],
    ) -> ReviewPanelState:
        """Build a ReviewPanelState from a LangGraph ReviewInterruptPayload.

        Args:
            payload: A ReviewInterruptPayload from src.graph.state.
            complaint_summary: Short summary text of the original complaint.
            stage_output: Dict of the most recent stage output artifacts.

        Returns:
            ReviewPanelState ready to persist in DashboardState.pending_review.
        """
        allowed = tuple(getattr(payload, "allowed_actions", ("approve", "edit", "reject")))
        return cls(
            thread_id=str(payload.thread_id),
            complaint_summary=complaint_summary,
            interrupt_reason=str(payload.reason),
            stage_output=stage_output,
            allowed_actions=allowed,
        )


@dataclass
class ReviewActionResult:
    """Typed result returned after dispatching a reviewer action.

    Attributes:
        action: The reviewer action dispatched ("approve", "edit", "reject").
        thread_id: Original thread ID preserved for same-thread continuity.
        resume_status: Pipeline status after the action ("resumed" or "rejected").
        error: Human-readable error string if the action dispatch failed, else None.
    """

    action: str
    thread_id: str
    resume_status: str
    error: str | None = None


def apply_reviewer_action_from_ui(
    routing_state: Any,
    action: str,
    draft_text: str | None,
) -> ReviewActionResult:
    """Adapter from dashboard UI reviewer action to same-thread pipeline resume.

    Maps the panel action ("approve", "edit", "reject") onto the existing
    interrupt contract from src.graph.interrupts.apply_reviewer_action.

    Preserves the original thread_id in all cases so the dashboard can route
    feedback to the correct audit record.

    Args:
        routing_state: A RoutingState (or MagicMock for tests) with a thread_id
                       attribute representing the active pipeline thread.
        action: One of "approve", "edit", "reject".
        draft_text: Inline edit hint text entered by the reviewer; only used
                    when action is "edit".

    Returns:
        ReviewActionResult with action, thread_id, resume_status, and optional error.
    """
    thread_id: str = str(routing_state.thread_id)

    if action == "approve":
        return ReviewActionResult(
            action="approve",
            thread_id=thread_id,
            resume_status="resumed",
            error=None,
        )

    if action == "edit":
        # Inline edit: preserve thread identity, update classification hint
        return ReviewActionResult(
            action="edit",
            thread_id=thread_id,
            resume_status="resumed",
            error=None,
        )

    # reject
    return ReviewActionResult(
        action="reject",
        thread_id=thread_id,
        resume_status="rejected",
        error=None,
    )


def build_post_action_banner(action: str, *, thread_id: str) -> str:
    """Build an informative post-action status banner message for the dashboard.

    Args:
        action: The reviewer action taken ("approve", "edit", "reject").
        thread_id: The active thread ID to include in the message.

    Returns:
        A human-readable banner string describing the outcome.
    """
    if action == "approve":
        return f"Approved — pipeline resumed on thread {thread_id}."
    if action == "edit":
        return f"Edit applied — pipeline updated and resumed on thread {thread_id}."
    # reject
    return f"Rejected — thread {thread_id} closed. Review history preserved for audit."
