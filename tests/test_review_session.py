"""Review-session continuity and HITL reviewer-action regression tests.

Covers:
- Typed review state contract and session persistence across reruns.
- Approve, edit, and reject flows with same-thread continuity assertions.
- Interrupt panel action exposure and focused review context rendering.
"""

from __future__ import annotations

from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Task 1 tests: typed state + action contract
# ---------------------------------------------------------------------------


def test_interrupt_panel_exposes_reviewer_actions() -> None:
    """Review panel must expose approve, edit, and reject as typed actions."""
    from src.ui.review import ReviewPanelState, ReviewAction

    state = ReviewPanelState(
        thread_id="t-001",
        complaint_summary="Customer charged twice for the same transaction.",
        interrupt_reason="low confidence classification",
        stage_output={"issue_type": "billing", "confidence": 0.55},
        allowed_actions=("approve", "edit", "reject"),
    )

    # All three actions must be exposed and valid ReviewAction values
    assert ReviewAction.APPROVE.value == "approve"
    assert ReviewAction.EDIT.value == "edit"
    assert ReviewAction.REJECT.value == "reject"

    # Panel state must have the thread_id for same-thread routing
    assert state.thread_id == "t-001"
    assert "approve" in state.allowed_actions
    assert "edit" in state.allowed_actions
    assert "reject" in state.allowed_actions

    # Panel state must expose the focused context fields
    assert state.complaint_summary
    assert state.interrupt_reason
    assert state.stage_output is not None


def test_dashboard_state_has_pending_review_field() -> None:
    """DashboardState must carry pending_review and review_banner fields for session continuity."""
    from src.ui.dashboard_state import DashboardState

    state = DashboardState()
    # Must have pending_review for review panel continuity
    assert hasattr(state, "pending_review"), "DashboardState must have pending_review field"
    assert state.pending_review is None  # default: no pending review

    # Must have review_banner for post-action feedback
    assert hasattr(state, "review_banner"), "DashboardState must have review_banner field"
    assert state.review_banner is None  # default: no banner


def test_dashboard_state_set_pending_review_persists() -> None:
    """Setting a pending review on DashboardState must survive the same session object."""
    from src.ui.dashboard_state import DashboardState
    from src.ui.review import ReviewPanelState

    state = DashboardState()
    review_state = ReviewPanelState(
        thread_id="t-002",
        complaint_summary="Mortgage payment not applied.",
        interrupt_reason="high compliance risk",
        stage_output={"route": "human_review"},
        allowed_actions=("approve", "edit", "reject"),
    )

    state.set_pending_review(review_state)
    assert state.pending_review is not None
    assert state.pending_review.thread_id == "t-002"
    assert state.active_thread_id == "t-002"  # active thread updated


def test_dashboard_state_clear_review_removes_pending() -> None:
    """Clearing the review panel on DashboardState must remove pending_review."""
    from src.ui.dashboard_state import DashboardState
    from src.ui.review import ReviewPanelState

    state = DashboardState()
    review_state = ReviewPanelState(
        thread_id="t-003",
        complaint_summary="Credit report error.",
        interrupt_reason="ambiguous classification",
        stage_output={"confidence": 0.45},
        allowed_actions=("approve", "edit", "reject"),
    )
    state.set_pending_review(review_state)
    state.clear_review(banner="Approved — pipeline resumed.")

    assert state.pending_review is None
    assert state.review_banner == "Approved — pipeline resumed."


def test_review_panel_state_from_interrupt_payload() -> None:
    """ReviewPanelState.from_interrupt_payload must map correctly from graph interrupt."""
    from src.ui.review import ReviewPanelState
    from src.graph.state import ReviewInterruptPayload
    from src.schemas.classification import ClassificationResult, IssueType, SeverityLevel

    classification = ClassificationResult(
        product_type="credit_card",
        issue_type=IssueType.BILLING,
        severity=SeverityLevel.MEDIUM,
        compliance_risk="medium",
        confidence=0.52,
    )
    payload = ReviewInterruptPayload(
        thread_id="t-004",
        reason="low confidence",
        confidence=0.52,
        compliance_risk="medium",
        classification=classification,
    )

    panel_state = ReviewPanelState.from_interrupt_payload(
        payload=payload,
        complaint_summary="Card charged twice.",
        stage_output={"confidence": 0.52},
    )

    assert panel_state.thread_id == "t-004"
    assert panel_state.interrupt_reason == "low confidence"
    assert "approve" in panel_state.allowed_actions
    assert panel_state.complaint_summary == "Card charged twice."


def test_apply_reviewer_action_adapter_approve() -> None:
    """apply_reviewer_action_from_ui must dispatch approve and return resume status."""
    from src.ui.review import apply_reviewer_action_from_ui
    from src.graph.state import ReviewDecision

    mock_state = MagicMock()
    mock_state.thread_id = "t-005"

    result = apply_reviewer_action_from_ui(
        routing_state=mock_state,
        action="approve",
        draft_text=None,
    )

    assert result.action == "approve"
    assert result.thread_id == "t-005"
    assert result.resume_status == "resumed"


def test_apply_reviewer_action_adapter_reject() -> None:
    """apply_reviewer_action_from_ui must dispatch reject and return rejected status."""
    from src.ui.review import apply_reviewer_action_from_ui

    mock_state = MagicMock()
    mock_state.thread_id = "t-006"

    result = apply_reviewer_action_from_ui(
        routing_state=mock_state,
        action="reject",
        draft_text=None,
    )

    assert result.action == "reject"
    assert result.thread_id == "t-006"
    assert result.resume_status == "rejected"


# ---------------------------------------------------------------------------
# Task 2 tests: sticky review panel + auto-resume flow
# ---------------------------------------------------------------------------


def test_review_edit_resumes_same_thread() -> None:
    """Edit action must preserve the original thread_id and not restart the pipeline."""
    from src.ui.review import apply_reviewer_action_from_ui, ReviewPanelState
    from src.schemas.classification import ClassificationResult, IssueType, SeverityLevel

    mock_state = MagicMock()
    mock_state.thread_id = "t-007"
    mock_state.classification.model_copy = MagicMock(
        return_value=ClassificationResult(
            product_type="credit_card",
            issue_type=IssueType.BILLING,
            severity=SeverityLevel.MEDIUM,
            compliance_risk="medium",
            confidence=0.90,
        )
    )

    result = apply_reviewer_action_from_ui(
        routing_state=mock_state,
        action="edit",
        draft_text="billing",  # edited classification hint
    )

    # Must preserve the original thread identity
    assert result.thread_id == "t-007", "Edit must not create a new thread"
    assert result.action == "edit"
    assert result.resume_status == "resumed"


def test_review_approve_returns_resume_status() -> None:
    """Approve action must return resume_status='resumed' for status feedback."""
    from src.ui.review import apply_reviewer_action_from_ui

    mock_state = MagicMock()
    mock_state.thread_id = "t-008"

    result = apply_reviewer_action_from_ui(
        routing_state=mock_state,
        action="approve",
        draft_text=None,
    )

    assert result.resume_status == "resumed"
    assert result.error is None


def test_review_action_result_carries_thread_id() -> None:
    """ReviewActionResult must always carry the original thread_id."""
    from src.ui.review import ReviewActionResult

    result = ReviewActionResult(
        action="approve",
        thread_id="t-fixed",
        resume_status="resumed",
    )

    assert result.thread_id == "t-fixed"
    assert result.action == "approve"


# ---------------------------------------------------------------------------
# Task 3 tests: approve/edit/reject regression coverage
# ---------------------------------------------------------------------------


def test_reject_flow_returns_rejected_status_and_thread_id() -> None:
    """Reject must return resume_status='rejected' but preserve the thread_id for audit."""
    from src.ui.review import apply_reviewer_action_from_ui

    mock_state = MagicMock()
    mock_state.thread_id = "t-audit-001"

    result = apply_reviewer_action_from_ui(
        routing_state=mock_state,
        action="reject",
        draft_text=None,
    )

    assert result.action == "reject"
    assert result.thread_id == "t-audit-001"  # thread preserved for audit
    assert result.resume_status == "rejected"


def test_reject_banner_message_is_informative() -> None:
    """After reject, the dashboard banner must describe the rejected state."""
    from src.ui.review import build_post_action_banner

    banner = build_post_action_banner("reject", thread_id="t-rejected")
    assert "reject" in banner.lower() or "rejected" in banner.lower()
    assert "t-rejected" in banner


def test_approve_banner_message_is_informative() -> None:
    """After approve, the dashboard banner must indicate pipeline resumption."""
    from src.ui.review import build_post_action_banner

    banner = build_post_action_banner("approve", thread_id="t-approved")
    assert "approved" in banner.lower() or "resumed" in banner.lower()


def test_edit_banner_message_is_informative() -> None:
    """After edit, the dashboard banner must indicate inline edit and resume."""
    from src.ui.review import build_post_action_banner

    banner = build_post_action_banner("edit", thread_id="t-edited")
    assert "edit" in banner.lower() or "updated" in banner.lower()


def test_review_panel_state_exposes_all_required_context_fields() -> None:
    """ReviewPanelState must expose complaint_summary, interrupt_reason, and stage_output."""
    from src.ui.review import ReviewPanelState

    panel = ReviewPanelState(
        thread_id="t-ctx",
        complaint_summary="Auto loan payment rejected.",
        interrupt_reason="compliance_risk=high",
        stage_output={"route": "human_review", "confidence": 0.45},
        allowed_actions=("approve", "edit", "reject"),
    )

    assert panel.complaint_summary == "Auto loan payment rejected."
    assert panel.interrupt_reason == "compliance_risk=high"
    assert panel.stage_output["confidence"] == 0.45


def test_review_action_result_no_error_on_success() -> None:
    """A successful reviewer action must not carry an error."""
    from src.ui.review import apply_reviewer_action_from_ui

    mock_state = MagicMock()
    mock_state.thread_id = "t-noerr"

    for action in ("approve", "edit", "reject"):
        result = apply_reviewer_action_from_ui(
            routing_state=mock_state,
            action=action,
            draft_text="billing" if action == "edit" else None,
        )
        assert result.error is None, f"Action '{action}' must not produce an error on success"


def test_dashboard_state_review_banner_cleared_on_new_run() -> None:
    """Starting a new pipeline run must clear the review_banner from a prior review."""
    from src.ui.dashboard_state import DashboardState

    state = DashboardState()
    state.review_banner = "Previous: Approved"
    state.clear_for_new_run()

    assert state.review_banner is None
    assert state.pending_review is None
