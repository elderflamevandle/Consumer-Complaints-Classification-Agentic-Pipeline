"""Typed dashboard session state for the Phase 5 Streamlit control-room shell.

Provides the shared complaint-source contract between the composer, demo loading,
and pipeline runner so all operators enter through the same submission path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardState:
    """Typed representation of the Streamlit session state for the control-room shell.

    Attributes:
        complaint_text: Current text in the shared editable complaint composer.
        selected_demo: Stable ID of the currently loaded golden demo, or None for manual entry.
        active_thread_id: LangGraph thread ID for the currently running or last-run pipeline.
        last_snapshot: Most recent pipeline state snapshot dict for rendering stage cards.
    """

    complaint_text: str = ""
    selected_demo: str | None = None
    active_thread_id: str | None = None
    last_snapshot: dict[str, Any] | None = field(default=None)

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
