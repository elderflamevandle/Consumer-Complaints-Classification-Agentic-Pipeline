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


def test_get_demo_by_id_returns_correct_record() -> None:
    """get_demo_by_id should return the correct demo for a known ID, None for unknown."""
    from src.ui.demo_cases import get_demo_by_id, load_golden_demos

    demos = load_golden_demos()
    first_id = demos[0]["id"]

    found = get_demo_by_id(first_id)
    assert found is not None, f"get_demo_by_id should find demo with id '{first_id}'"
    assert found["id"] == first_id

    missing = get_demo_by_id("nonexistent-demo-id")
    assert missing is None, "get_demo_by_id should return None for unknown ID"


def test_dashboard_state_load_demo_sets_fields() -> None:
    """load_demo should populate both complaint_text and selected_demo."""
    from src.ui.dashboard_state import DashboardState

    state = DashboardState()
    state.load_demo(demo_id="demo-001", complaint_text="Test complaint for demo")

    assert state.selected_demo == "demo-001"
    assert state.complaint_text == "Test complaint for demo"


def test_dashboard_state_clear_composer_resets_fields() -> None:
    """clear_composer should blank the composer and clear selected_demo."""
    from src.ui.dashboard_state import DashboardState

    state = DashboardState()
    state.load_demo(demo_id="demo-001", complaint_text="Some demo text")
    state.clear_composer()

    assert state.complaint_text == ""
    assert state.selected_demo is None


def test_demo_complaint_texts_are_substantive() -> None:
    """Each demo complaint_text should be longer than 100 characters for realism."""
    from src.ui.demo_cases import load_golden_demos

    demos = load_golden_demos()
    for demo in demos:
        assert len(demo["complaint_text"]) > 100, (
            f"Demo '{demo['id']}' complaint_text is too short ({len(demo['complaint_text'])} chars); "
            "demo complaints must be realistic and substantive."
        )


def test_demo_catalog_covers_distinct_complaint_categories() -> None:
    """Five golden demos should cover meaningfully distinct complaint scenarios."""
    from src.ui.demo_cases import load_golden_demos

    demos = load_golden_demos()
    titles = [d["title"].lower() for d in demos]

    # All titles should be distinct
    assert len(titles) == len(set(titles)), "Demo titles must be distinct"

    # Each demo should be recognisably different from the others
    for i, title in enumerate(titles):
        for j, other_title in enumerate(titles):
            if i != j:
                assert title != other_title


# ---------------------------------------------------------------------------
# Task 1: Stage telemetry contracts (TDD tests added in 05-02)
# ---------------------------------------------------------------------------


def test_pipeline_runtime_returns_stage_telemetry() -> None:
    """Pipeline runtime must return ordered stage snapshots with status, model, latency, tokens."""
    from src.ui.telemetry import StageTelemetry, StageStatus

    # Each stage snapshot must carry these fields
    snapshot = StageTelemetry(
        stage_name="classifier",
        status=StageStatus.COMPLETED,
        model="llama-3.3-70b-versatile",
        latency_ms=350,
        total_tokens=120,
    )

    assert snapshot.stage_name == "classifier"
    assert snapshot.status == StageStatus.COMPLETED
    assert snapshot.model == "llama-3.3-70b-versatile"
    assert snapshot.latency_ms == 350
    assert snapshot.total_tokens == 120


def test_stage_telemetry_status_enum_covers_pipeline_states() -> None:
    """StageStatus must include at least PENDING, RUNNING, COMPLETED, FAILED."""
    from src.ui.telemetry import StageStatus

    assert hasattr(StageStatus, "PENDING")
    assert hasattr(StageStatus, "RUNNING")
    assert hasattr(StageStatus, "COMPLETED")
    assert hasattr(StageStatus, "FAILED")


def test_stage_telemetry_latency_ms_field_present() -> None:
    """StageTelemetry must have latency_ms field for dashboard rendering."""
    from src.ui.telemetry import StageTelemetry, StageStatus

    snapshot = StageTelemetry(
        stage_name="routing",
        status=StageStatus.PENDING,
        model="",
        latency_ms=0,
        total_tokens=0,
    )
    assert hasattr(snapshot, "latency_ms"), "StageTelemetry must expose latency_ms"


def test_budget_snapshot_exposes_used_tokens_and_warning_flags() -> None:
    """BudgetSnapshot must expose used_tokens, warning, and degrade_non_critical."""
    from src.ui.telemetry import BudgetTelemetry

    budget = BudgetTelemetry(
        used_tokens=8000,
        daily_budget=10000,
        utilization=0.8,
        warning=True,
        degrade_non_critical=False,
    )

    assert budget.used_tokens == 8000
    assert budget.daily_budget == 10000
    assert budget.warning is True
    assert budget.degrade_non_critical is False


def test_audit_event_snapshot_exposes_timestamp_decision_and_model() -> None:
    """AuditEventSnapshot must have timestamp, decision, and model_version fields."""
    from src.ui.telemetry import AuditEventSnapshot

    event = AuditEventSnapshot(
        thread_id="t-001",
        node="classifier",
        timestamp="2026-04-08T10:00:00Z",
        decision="route_continue",
        model_version="llama-3.3-70b-versatile",
        latency_ms=200,
    )

    assert event.timestamp == "2026-04-08T10:00:00Z"
    assert event.decision == "route_continue"
    assert event.model_version == "llama-3.3-70b-versatile"


def test_llm_response_has_total_tokens() -> None:
    """LLMResponse in src/llm/client.py must expose total_tokens for telemetry capture."""
    from src.llm.client import LLMResponse

    resp = LLMResponse(
        text="ok",
        model="llama-3.3-70b-versatile",
        total_tokens=500,
        attempts=1,
        degraded=False,
    )
    assert resp.total_tokens == 500, "LLMResponse.total_tokens must be accessible"


# ---------------------------------------------------------------------------
# Task 2: Runtime snapshot tests (TDD tests added in 05-02)
# ---------------------------------------------------------------------------


def test_runtime_snapshot_exposes_budget_audit_and_final_outputs() -> None:
    """DashboardSnapshot must expose budget, audit_events, final_response, and final_explanation."""
    from src.ui.telemetry import AuditEventSnapshot, BudgetTelemetry, DashboardSnapshot, StageTelemetry, StageStatus

    budget = BudgetTelemetry(
        used_tokens=1000,
        daily_budget=50000,
        utilization=0.02,
        warning=False,
        degrade_non_critical=False,
    )
    stage = StageTelemetry(
        stage_name="classifier",
        status=StageStatus.COMPLETED,
        model="llama-3.3-70b-versatile",
        latency_ms=300,
        total_tokens=100,
    )
    audit_event = AuditEventSnapshot(
        thread_id="t-001",
        node="classifier",
        timestamp="2026-04-08T10:00:00Z",
        decision="route_continue",
        model_version="llama-3.3-70b-versatile",
        latency_ms=300,
    )

    snapshot = DashboardSnapshot(
        thread_id="t-001",
        stages=[stage],
        budget=budget,
        audit_events=[audit_event],
        final_response="We have reviewed your complaint...",
        final_explanation=["Classification: billing issue", "Remediation: refund issued"],
        run_status="completed",
    )

    assert snapshot.thread_id == "t-001"
    assert len(snapshot.stages) == 1
    assert snapshot.budget.used_tokens == 1000
    assert len(snapshot.audit_events) == 1
    assert snapshot.audit_events[0].timestamp == "2026-04-08T10:00:00Z"
    assert snapshot.audit_events[0].decision == "route_continue"
    assert snapshot.final_response is not None
    assert snapshot.final_explanation is not None
    assert snapshot.run_status == "completed"


def test_dashboard_snapshot_audit_events_ordered_chronologically() -> None:
    """Audit events in DashboardSnapshot must be ordered oldest-to-newest."""
    from src.ui.telemetry import AuditEventSnapshot, BudgetTelemetry, DashboardSnapshot, StageTelemetry, StageStatus

    events = [
        AuditEventSnapshot(
            thread_id="t-001",
            node="classifier",
            timestamp="2026-04-08T10:00:00Z",
            decision="route_continue",
            model_version="llama-3.3-70b-versatile",
            latency_ms=100,
        ),
        AuditEventSnapshot(
            thread_id="t-001",
            node="remediator",
            timestamp="2026-04-08T10:01:00Z",
            decision="policy_grounded_action_plan",
            model_version="llama-3.3-70b-versatile",
            latency_ms=200,
        ),
    ]
    budget = BudgetTelemetry(
        used_tokens=0,
        daily_budget=50000,
        utilization=0.0,
        warning=False,
        degrade_non_critical=False,
    )
    stage = StageTelemetry(
        stage_name="classifier",
        status=StageStatus.COMPLETED,
        model="",
        latency_ms=0,
        total_tokens=0,
    )
    snapshot = DashboardSnapshot(
        thread_id="t-001",
        stages=[stage],
        budget=budget,
        audit_events=events,
        final_response=None,
        final_explanation=None,
        run_status="completed",
    )

    timestamps = [e.timestamp for e in snapshot.audit_events]
    assert timestamps == sorted(timestamps), "Audit events must be in chronological order"


def test_run_complaint_facade_returns_dashboard_snapshot() -> None:
    """run_complaint in src/ui/runtime.py must return a DashboardSnapshot."""
    import sqlite3

    from src.llm.client import LLMResponse
    from src.ui.runtime import run_complaint
    from src.ui.telemetry import DashboardSnapshot

    def mock_transport(**_kwargs: object) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"product_type":"credit_card","issue_type":"billing","severity":"medium","compliance_risk":"medium","confidence":0.85}'
                    }
                }
            ],
            "usage": {"total_tokens": 100},
        }

    def mock_connect(path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        return conn

    result = run_complaint(
        complaint_text="My credit card was charged twice for the same transaction.",
        transport=mock_transport,
        db_connect_fn=mock_connect,
    )

    assert isinstance(result, DashboardSnapshot), f"Expected DashboardSnapshot, got {type(result)}"
    assert result.thread_id is not None
    assert len(result.stages) > 0
    assert result.budget is not None
    assert result.run_status in ("completed", "error", "review_required")


def test_runtime_warning_helper_adds_warning_lists_without_clobbering_artifacts() -> None:
    from src.ui.runtime import _with_stage_warnings

    artifacts = {'status': 'ok'}
    enriched = _with_stage_warnings(
        artifacts,
        warnings=['root_cause_used_fallback'],
    )

    assert artifacts == {'status': 'ok'}
    assert enriched['status'] == 'ok'
    assert enriched['warnings'] == ['root_cause_used_fallback']
