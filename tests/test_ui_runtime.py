"""Runtime tests for Phase 5 UI module - golden demo catalog and dashboard state."""

from __future__ import annotations

import pytest


def test_demo_catalog_contains_five_curated_cases() -> None:
    """Golden demo catalog must have exactly five cases with required fields."""
    from src.ui.demo_cases import load_golden_demos

    demos = load_golden_demos()

    assert len(demos) == 5, f"Expected 5 golden demos, got {len(demos)}"

    required_fields = {"id", "title", "summary", "complaint_text"}
    for demo in demos:
        assert required_fields.issubset(
            demo.keys()
        ), f"Demo missing required fields: {demo.keys()}"
        assert isinstance(demo["id"], str) and demo["id"], "Demo id must be a non-empty string"
        assert (
            isinstance(demo["title"], str) and demo["title"]
        ), "Demo title must be a non-empty string"
        assert (
            isinstance(demo["summary"], str) and demo["summary"]
        ), "Demo summary must be a non-empty string"
        assert (
            isinstance(demo["complaint_text"], str) and demo["complaint_text"]
        ), "Demo complaint_text must be a non-empty string"


def test_demo_ids_are_stable_and_unique() -> None:
    """Demo IDs must be unique and stable (no duplicates)."""
    from src.ui.demo_cases import load_golden_demos

    demos = load_golden_demos()
    ids = [d["id"] for d in demos]

    assert len(ids) == len(set(ids)), "Demo IDs must be unique"


def test_dashboard_state_has_required_fields() -> None:
    """Dashboard session state must include complaint_text, selected_demo, active_thread_id."""
    from src.ui.dashboard_state import DashboardState

    state = DashboardState()
    assert hasattr(state, "complaint_text"), "DashboardState must have complaint_text"
    assert hasattr(state, "selected_demo"), "DashboardState must have selected_demo"
    assert hasattr(state, "active_thread_id"), "DashboardState must have active_thread_id"
    assert hasattr(state, "last_snapshot"), "DashboardState must have last_snapshot"


def test_dashboard_state_default_values() -> None:
    """Dashboard state should initialize with sensible defaults."""
    from src.ui.dashboard_state import DashboardState

    state = DashboardState()
    assert state.complaint_text == "", "complaint_text should default to empty string"
    assert state.selected_demo is None, "selected_demo should default to None"
    assert state.active_thread_id is None, "active_thread_id should default to None"
    assert state.last_snapshot is None, "last_snapshot should default to None"


def test_demo_cases_load_from_golden_demos_json() -> None:
    """Demo cases should load from the data/golden_demos.json file."""
    import json
    from pathlib import Path

    golden_path = Path("data/golden_demos.json")
    assert golden_path.exists(), "data/golden_demos.json must exist"

    with golden_path.open() as f:
        raw = json.load(f)

    assert isinstance(raw, list), "golden_demos.json must be a JSON array"
    assert len(raw) == 5, f"golden_demos.json must contain exactly 5 entries, got {len(raw)}"
