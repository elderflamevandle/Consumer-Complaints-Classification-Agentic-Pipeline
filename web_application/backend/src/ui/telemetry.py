"""Typed stage telemetry and budget/audit snapshot contracts for the Phase 5 dashboard.

Provides stable, machine-readable typed objects that the Streamlit control room
uses to render stage cards, the audit tab, and the budget widget without
coupling to raw pipeline internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StageStatus(str, Enum):
    """Pipeline stage execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageTelemetry:
    """Typed telemetry snapshot for a single pipeline stage.

    Attributes:
        stage_name: Canonical stage identifier (e.g. "classifier", "remediator").
        status: Current execution status of the stage.
        model: LLM model identifier used by the stage, empty string if N/A.
        latency_ms: Wall-clock latency in milliseconds for the stage.
        total_tokens: Total tokens consumed by the stage's LLM call.
        artifacts: Optional dict of stage-specific output artifacts for expander display.
        error_message: Human-readable error detail when status is FAILED.
    """

    stage_name: str
    status: StageStatus
    model: str
    latency_ms: int
    total_tokens: int
    artifacts: dict[str, object] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class BudgetTelemetry:
    """Daily token-budget snapshot for the compact header widget.

    Attributes:
        used_tokens: Total tokens consumed today across all pipeline runs.
        daily_budget: Configured daily token ceiling.
        utilization: Fractional utilization in [0, 1].
        warning: True when utilization >= warning threshold (default 80%).
        degrade_non_critical: True when utilization >= degrade threshold (default 90%).
    """

    used_tokens: int
    daily_budget: int
    utilization: float
    warning: bool
    degrade_non_critical: bool


@dataclass
class AuditEventSnapshot:
    """Single audit event for the chronological audit tab.

    Attributes:
        thread_id: LangGraph thread the event belongs to.
        node: Pipeline node/stage that emitted the event.
        timestamp: ISO-8601 UTC timestamp string from the audit logger.
        decision: Decision label recorded at this node (e.g. "route_continue").
        model_version: LLM model identifier that produced the decision.
        latency_ms: Latency reported for the node call.
    """

    thread_id: str
    node: str
    timestamp: str
    decision: str
    model_version: str
    latency_ms: int


@dataclass
class DashboardSnapshot:
    """Full dashboard state snapshot returned by the runtime facade after a run.

    Attributes:
        thread_id: Active pipeline thread identifier.
        stages: Ordered list of per-stage telemetry snapshots.
        budget: Current daily token-budget state.
        audit_events: Chronologically ordered audit decision events for this thread.
        final_response: Customer-facing response text produced by the pipeline, or None.
        final_explanation: Ordered list of explainer bullet summary strings, or None.
        run_status: High-level run outcome ("completed", "review_required", "error").
        error_message: Error detail when run_status is "error".
    """

    thread_id: str
    stages: list[StageTelemetry]
    budget: BudgetTelemetry
    audit_events: list[AuditEventSnapshot]
    final_response: Optional[str]
    final_explanation: Optional[list[str]]
    run_status: str
    error_message: str | None = None


def budget_telemetry_from_snapshot(snapshot: object) -> BudgetTelemetry:
    """Convert a TokenBudgetTracker.snapshot() result to a BudgetTelemetry for the UI.

    Args:
        snapshot: A BudgetSnapshot dataclass instance from src.llm.rate_limiter.

    Returns:
        BudgetTelemetry ready for rendering in the dashboard header widget.
    """
    return BudgetTelemetry(
        used_tokens=int(getattr(snapshot, "used_tokens", 0)),
        daily_budget=int(getattr(snapshot, "daily_budget", 1)),
        utilization=float(getattr(snapshot, "utilization", 0.0)),
        warning=bool(getattr(snapshot, "warning", False)),
        degrade_non_critical=bool(getattr(snapshot, "degrade_non_critical", False)),
    )


def audit_event_from_dict(event_dict: dict[str, object]) -> AuditEventSnapshot:
    """Convert an AuditLogger.fetch_events() row dict to an AuditEventSnapshot.

    Args:
        event_dict: Raw dict from AuditLogger.fetch_events() with node, timestamp,
                    model, latency_ms, and decision keys.

    Returns:
        AuditEventSnapshot ready for rendering in the audit tab.
    """
    return AuditEventSnapshot(
        thread_id=str(event_dict.get("thread_id", "")),
        node=str(event_dict.get("node", "")),
        timestamp=str(event_dict.get("timestamp", "")),
        decision=str(event_dict.get("decision", "")),
        model_version=str(event_dict.get("model", "")),
        latency_ms=int(event_dict.get("latency_ms", 0)),
    )
