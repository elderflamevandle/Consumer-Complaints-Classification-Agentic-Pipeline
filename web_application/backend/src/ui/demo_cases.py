"""Golden demo catalog for the Phase 5 Streamlit control-room shell.

Loads the five curated scenario records from data/golden_demos.json so the
Streamlit shell can render them as scenario cards and load them into the
shared editable complaint composer.

This module is intentionally separate from rendering logic so later runtime
and review work can reuse the same catalog contract without importing Streamlit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class DemoRecord(TypedDict):
    """Typed schema for a single golden demo scenario record."""

    id: str
    title: str
    summary: str
    complaint_text: str


_GOLDEN_DEMOS_PATH = Path(__file__).resolve().parents[2] / "data" / "golden_demos.json"


def load_golden_demos() -> list[DemoRecord]:
    """Load the curated golden demo catalog from data/golden_demos.json.

    Returns:
        List of exactly five DemoRecord dicts with stable ids, titles, summaries,
        and complaint text for the Streamlit scenario-card display.

    Raises:
        FileNotFoundError: If data/golden_demos.json does not exist.
        ValueError: If the file does not contain exactly five valid demo records.
    """
    if not _GOLDEN_DEMOS_PATH.exists():
        raise FileNotFoundError(
            f"Golden demos file not found at {_GOLDEN_DEMOS_PATH}. "
            "Ensure data/golden_demos.json exists in the repository root."
        )

    with _GOLDEN_DEMOS_PATH.open(encoding="utf-8") as f:
        raw: list[dict[str, str]] = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("golden_demos.json must be a JSON array of demo records.")

    demos: list[DemoRecord] = []
    for idx, record in enumerate(raw):
        _validate_demo_record(record, idx)
        demos.append(
            DemoRecord(
                id=record["id"],
                title=record["title"],
                summary=record["summary"],
                complaint_text=record["complaint_text"],
            )
        )

    return demos


def get_demo_by_id(demo_id: str) -> DemoRecord | None:
    """Return a single demo record by its stable ID, or None if not found.

    Args:
        demo_id: The stable identifier for the desired golden demo scenario.

    Returns:
        The matching DemoRecord, or None if demo_id is not in the catalog.
    """
    demos = load_golden_demos()
    for demo in demos:
        if demo["id"] == demo_id:
            return demo
    return None


def _validate_demo_record(record: dict[str, str], idx: int) -> None:
    """Validate that a raw dict has all required DemoRecord fields.

    Args:
        record: Raw dict loaded from JSON.
        idx: Zero-based index for error message context.

    Raises:
        ValueError: If any required field is missing or empty.
    """
    required = ("id", "title", "summary", "complaint_text")
    for field_name in required:
        if field_name not in record:
            raise ValueError(
                f"Demo record at index {idx} is missing required field '{field_name}'."
            )
        if not isinstance(record[field_name], str) or not record[field_name].strip():
            raise ValueError(
                f"Demo record at index {idx} field '{field_name}' must be a non-empty string."
            )
