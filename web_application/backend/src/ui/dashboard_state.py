"""Typed dashboard session state for the Phase 5 Streamlit control-room shell.

Provides the shared complaint-source contract between the composer, demo loading,
and pipeline runner so all operators enter through the same submission path.

Also provides the pending-review and review-banner contract for sticky review
panel continuity across Streamlit reruns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.ui.review import ReviewPanelState


@dataclass
class DashboardState:
    """Typed representation of the Streamlit session state for the control-room shell.

    Attributes:
        complaint_text: Current text in the shared editable complaint composer.
        selected_demo: Stable ID of the currently loaded golden demo, or None for manual entry.
        active_thread_id: LangGraph thread ID for the currently running or last-run pipeline.
        last_snapshot: Most recent pipeline state snapshot dict for rendering stage cards.
        pending_review: Active ReviewPanelState when pipeline is paused for HITL action.
        review_banner: Post-action status banner text shown after reviewer submission.
    """

    complaint_text: str = ""
    selected_demo: str | None = None
    active_thread_id: str | None = None
    last_snapshot: dict[str, Any] | None = field(default=None)
    pending_review: Any | None = field(default=None)  # ReviewPanelState | None
    review_banner: str | None = None

    def load_demo(self, demo_id: str, complaint_text: str) -> None:
        """Load a golden demo into the shared composer.

        Args:
            demo_id: Stable identifier for the golden demo scenario.
            complaint_text: Pre-filled complaint text from the demo record.
        """
        self.selected_demo = demo_id
        self.complaint_text = complaint_text

    def clear_composer(self) -> None:
        """Reset the composer to blank manual-entry mode."""
        self.complaint_text = ""
        self.selected_demo = None

    def set_active_thread(self, thread_id: str) -> None:
        """Record the active pipeline thread ID after submission."""
        self.active_thread_id = thread_id

    def update_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Update the last pipeline state snapshot for stage-card rendering."""
        self.last_snapshot = snapshot

    def set_pending_review(self, review_state: Any) -> None:
        """Set a pending review panel state for HITL action.

        Also updates active_thread_id to the review state's thread so that
        same-thread resume routing remains consistent.

        Args:
            review_state: A ReviewPanelState describing the current interrupt.
        """
        self.pending_review = review_state
        if review_state is not None and hasattr(review_state, "thread_id"):
            self.active_thread_id = review_state.thread_id

    def clear_review(self, banner: str | None = None) -> None:
        """Clear the pending review panel and optionally set a post-action banner.

        Args:
            banner: Optional informative message to show after reviewer submits an action.
        """
        self.pending_review = None
        self.review_banner = banner

    def clear_for_new_run(self) -> None:
        """Reset review-related state when a new pipeline run is initiated."""
        self.pending_review = None
        self.review_banner = None
