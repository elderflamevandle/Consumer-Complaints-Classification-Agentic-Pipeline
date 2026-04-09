"""UI-safe complaint runtime facade for the Phase 5 Streamlit dashboard.

Composes the existing pipeline stages (intake, classify, route, root-cause,
remediate, write, audit, explain) into a single call that returns a fully
typed DashboardSnapshot for the control-room rendering layer.

The facade is intentionally UI-safe:
- No Streamlit imports
- No LangGraph state machines (uses agent layer directly for the demo runner)
- Testable with injected transports and in-memory SQLite connections
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Any, Callable

from src.agents.auditor import AuditorAgent
from src.agents.classifier import ClassifierAgent
from src.agents.explainer import ExplainerAgent
from src.agents.remediator import RemediationResult, RemediatorAgent
from src.agents.root_cause import RootCauseAgent
from src.agents.writer import WriterAgent
from src.config import get_settings
from src.intake.pipeline import prepare_intake
from src.llm.client import GroqLLMClient
from src.llm.rate_limiter import TokenBudgetTracker
from src.tools.audit_logger import AuditLogger
from src.tools.mcp_policy_client import MCPPolicyClient
from src.ui.telemetry import (
    AuditEventSnapshot,
    BudgetTelemetry,
    DashboardSnapshot,
    StageTelemetry,
    StageStatus,
    audit_event_from_dict,
    budget_telemetry_from_snapshot,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SHARED_BUDGET_TRACKER: TokenBudgetTracker | None = None


def _get_shared_budget(settings: Any) -> TokenBudgetTracker:
    """Return a module-level singleton budget tracker (reset each session)."""
    global _SHARED_BUDGET_TRACKER  # noqa: PLW0603
    if _SHARED_BUDGET_TRACKER is None:
        _SHARED_BUDGET_TRACKER = TokenBudgetTracker(settings.daily_token_budget)
    return _SHARED_BUDGET_TRACKER


def reset_shared_budget() -> None:
    """Reset the module-level budget tracker (useful for tests)."""
    global _SHARED_BUDGET_TRACKER  # noqa: PLW0603
    _SHARED_BUDGET_TRACKER = None


def _timed_stage(
    stage_name: str,
    fn: Callable[[], Any],
    *,
    model_hint: str = "",
) -> tuple[Any, StageTelemetry]:
    """Run fn(), record wall-clock latency, and return (result, StageTelemetry).

    The StageTelemetry has COMPLETED status on success, FAILED on exception.
    total_tokens is captured from LLMResponse objects where available; other
    stages default to 0.
    """
    start = time.monotonic()
    try:
        result = fn()
        latency_ms = int((time.monotonic() - start) * 1000)
        # Try to extract model/token info from result objects
        model = model_hint
        total_tokens = 0
        # LLMResponse has .model and .total_tokens
        if hasattr(result, "model") and result.model:
            model = str(result.model)
        if hasattr(result, "total_tokens"):
            total_tokens = int(result.total_tokens)
        snapshot = StageTelemetry(
            stage_name=stage_name,
            status=StageStatus.COMPLETED,
            model=model,
            latency_ms=latency_ms,
            total_tokens=total_tokens,
        )
        return result, snapshot
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        snapshot = StageTelemetry(
            stage_name=stage_name,
            status=StageStatus.FAILED,
            model=model_hint,
            latency_ms=latency_ms,
            total_tokens=0,
            error_message=str(exc),
        )
        raise RuntimeError(f"Stage '{stage_name}' failed: {exc}") from exc


def _capture_agent_stage(
    stage_name: str,
    agent: Any,
    fn: Callable[[], Any],
) -> tuple[Any, StageTelemetry]:
    """Run an agent's method, then read model/token metadata from the agent after the call."""
    start = time.monotonic()
    try:
        result = fn()
        latency_ms = int((time.monotonic() - start) * 1000)
        # Agents expose last_model after a call
        model = str(getattr(agent, "last_model", "") or "")
        # Agents don't accumulate total_tokens directly; default 0
        total_tokens = 0
        snapshot = StageTelemetry(
            stage_name=stage_name,
            status=StageStatus.COMPLETED,
            model=model,
            latency_ms=latency_ms,
            total_tokens=total_tokens,
            artifacts=_safe_artifact(result),
        )
        return result, snapshot
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        snapshot = StageTelemetry(
            stage_name=stage_name,
            status=StageStatus.FAILED,
            model=str(getattr(agent, "last_model", "") or ""),
            latency_ms=latency_ms,
            total_tokens=0,
            error_message=str(exc),
        )
        raise RuntimeError(f"Stage '{stage_name}' failed: {exc}") from exc


def _safe_artifact(result: Any) -> dict[str, object]:
    """Extract a safe dict of stage artifacts for expander rendering."""
    try:
        if hasattr(result, "model_dump"):
            raw: dict[str, object] = result.model_dump()
            # Truncate long string values to keep the artifact compact
            return {
                k: (str(v)[:300] if isinstance(v, str) else v)
                for k, v in raw.items()
            }
        if hasattr(result, "__dict__"):
            return {k: str(v)[:200] for k, v in result.__dict__.items() if not k.startswith("_")}
    except Exception:
        pass
    return {}


def _with_stage_warnings(
    artifacts: dict[str, object],
    *,
    warnings: list[str] | None = None,
) -> dict[str, object]:
    normalized = [warning for warning in warnings or [] if warning]
    if not normalized:
        return artifacts

    enriched = dict(artifacts)
    enriched['warnings'] = normalized
    return enriched


def _build_budget_telemetry(tracker: TokenBudgetTracker) -> BudgetTelemetry:
    snap = tracker.snapshot()
    return budget_telemetry_from_snapshot(snap)


def _build_audit_events(
    audit_logger: AuditLogger, thread_id: str
) -> list[AuditEventSnapshot]:
    raw_events = audit_logger.fetch_events(thread_id=thread_id)
    return [audit_event_from_dict(e) for e in raw_events]


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------


def run_complaint(
    complaint_text: str,
    *,
    transport: Callable[..., Any] | None = None,
    db_connect_fn: Callable[[str], sqlite3.Connection] | None = None,
    budget_tracker: TokenBudgetTracker | None = None,
    state_code: str = "CA",
) -> DashboardSnapshot:
    """Execute the full complaint pipeline and return a DashboardSnapshot.

    This is the single entry point used by the Streamlit control room for both
    manual complaint text and loaded golden demo text. It is UI-safe (no
    Streamlit imports) and testable via injected transports and DB connections.

    Args:
        complaint_text: Raw complaint text submitted by the operator.
        transport: Optional LLM transport callable for testing (bypasses real API).
        db_connect_fn: Optional SQLite connect callable for testing (use in-memory DB).
        budget_tracker: Optional pre-configured token budget tracker.
        state_code: Two-letter state code for MCP policy lookups. Defaults to "CA".

    Returns:
        DashboardSnapshot with stage telemetry, budget, audit events, final
        response, explainer artifacts, and run status.
    """
    thread_id = str(uuid.uuid4())
    settings = get_settings()

    # --- shared infrastructure ---
    if budget_tracker is None:
        budget_tracker = _get_shared_budget(settings)

    shared_client = GroqLLMClient(
        transport=transport,
        budget_tracker=budget_tracker,
    )
    audit_logger = AuditLogger(connect_fn=db_connect_fn)

    stages: list[StageTelemetry] = []

    # -------------------------------------------------------------------------
    # Stage 1: Intake + PII scrub
    # -------------------------------------------------------------------------
    try:
        intake_start = time.monotonic()
        intake = prepare_intake(raw_text=complaint_text)
        intake_latency = int((time.monotonic() - intake_start) * 1000)
        stages.append(
            StageTelemetry(
                stage_name="intake",
                status=StageStatus.COMPLETED,
                model="pii-scrubber-v1",
                latency_ms=intake_latency,
                total_tokens=0,
                artifacts={
                    "scrub_confidence": str(intake.scrub_confidence),
                    "review_policy": str(intake.review_policy),
                    "warnings": list(intake.warnings),
                    "classifier_input_length": intake.trace.get("classifier_input_length", "0"),
                },
            )
        )
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="intake",
                status=StageStatus.FAILED,
                model="pii-scrubber-v1",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        return _error_snapshot(thread_id, stages, budget_tracker, str(exc))

    # -------------------------------------------------------------------------
    # Stage 2: Classification
    # -------------------------------------------------------------------------
    classifier = ClassifierAgent(llm_client=shared_client)
    try:
        classify_start = time.monotonic()
        classification = classifier.classify(intake)
        classify_latency = int((time.monotonic() - classify_start) * 1000)
        # Log to audit
        audit_logger.log_node_outcome(
            thread_id=thread_id,
            node="classifier",
            model=str(getattr(shared_client, "_last_model", "llm")),
            latency_ms=classify_latency,
            decision=f"classified_{classification.issue_type.value}",
            scrubbed_text=intake.scrubbed_text[:220],
        )
        stages.append(
            StageTelemetry(
                stage_name="classifier",
                status=StageStatus.COMPLETED,
                model="llm",
                latency_ms=classify_latency,
                total_tokens=0,
                artifacts=_with_stage_warnings(
                    _safe_artifact(classification),
                    warnings=['classifier_used_fallback'] if classifier.used_fallback else None,
                ),
            )
        )
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="classifier",
                status=StageStatus.FAILED,
                model="",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        return _error_snapshot(thread_id, stages, budget_tracker, str(exc))

    # -------------------------------------------------------------------------
    # Stage 3: Root cause diagnosis
    # -------------------------------------------------------------------------
    root_cause_agent = RootCauseAgent(
        llm_client=shared_client,
        audit_logger=audit_logger,
    )
    try:
        rc_start = time.monotonic()
        diagnosis = root_cause_agent.diagnose(
            intake.scrubbed_text,
            thread_id=thread_id,
        )
        rc_latency = int((time.monotonic() - rc_start) * 1000)
        model_used = str(root_cause_agent.last_model or "")
        # Backfill latency to last audit record - log a summarized outcome
        audit_logger.log_node_outcome(
            thread_id=thread_id,
            node="root_cause",
            model=model_used or "heuristic-fallback",
            latency_ms=rc_latency,
            decision=f"diagnosis_{diagnosis.ambiguity_flag.value.lower()}",
            scrubbed_text=intake.scrubbed_text[:220],
        )
        stages.append(
            StageTelemetry(
                stage_name="root_cause",
                status=StageStatus.COMPLETED,
                model=model_used,
                latency_ms=rc_latency,
                total_tokens=0,
                artifacts=_with_stage_warnings(
                    _safe_artifact(diagnosis),
                    warnings=['root_cause_used_fallback'] if root_cause_agent.used_fallback else None,
                ),
            )
        )
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="root_cause",
                status=StageStatus.FAILED,
                model="",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        return _error_snapshot(thread_id, stages, budget_tracker, str(exc))

    # -------------------------------------------------------------------------
    # Stage 4: Remediation (MCP-grounded)
    # -------------------------------------------------------------------------
    remediator = RemediatorAgent(
        llm_client=shared_client,
        audit_logger=audit_logger,
    )
    try:
        rem_start = time.monotonic()
        remediation = remediator.propose_action(
            complaint_text=intake.scrubbed_text,
            classification=classification,
            diagnosis=diagnosis,
            state_code=state_code,
            thread_id=thread_id,
        )
        rem_latency = int((time.monotonic() - rem_start) * 1000)
        stages.append(
            StageTelemetry(
                stage_name="remediator",
                status=StageStatus.COMPLETED,
                model=str(remediator.last_model or "mcp-policy-gate"),
                latency_ms=rem_latency,
                total_tokens=0,
                artifacts=_with_stage_warnings(
                    _safe_artifact(remediation),
                    warnings=(
                        [f"remediation_status_{remediation.status.lower()}"]
                        if remediation.status.lower() != 'ok'
                        else None
                    ),
                ),
            )
        )
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="remediator",
                status=StageStatus.FAILED,
                model="",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        # Remediation failure is not fatal - create a stub remediation for downstream stages
        remediation = RemediationResult(
            status="error",
            route="human_review",
            action_plan=[],
            policy_citations={},
        )

    # -------------------------------------------------------------------------
    # Stage 5: Response writer
    # -------------------------------------------------------------------------
    writer = WriterAgent(
        llm_client=shared_client,
        audit_logger=audit_logger,
    )
    try:
        write_start = time.monotonic()
        response_draft = writer.compose_response(
            complaint_text=intake.scrubbed_text,
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            thread_id=thread_id,
        )
        write_latency = int((time.monotonic() - write_start) * 1000)
        stages.append(
            StageTelemetry(
                stage_name="writer",
                status=StageStatus.COMPLETED,
                model=str(writer.last_model or ""),
                latency_ms=write_latency,
                total_tokens=0,
                artifacts=_with_stage_warnings(
                    _safe_artifact(response_draft),
                    warnings=['writer_used_fallback'] if writer.used_fallback else None,
                ),
            )
        )
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="writer",
                status=StageStatus.FAILED,
                model="",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        return _error_snapshot(thread_id, stages, budget_tracker, str(exc))

    # -------------------------------------------------------------------------
    # Stage 6: Compliance audit
    # -------------------------------------------------------------------------
    auditor = AuditorAgent(
        llm_client=shared_client,
        audit_logger=audit_logger,
    )
    try:
        audit_start = time.monotonic()
        audit_result = auditor.review_response(
            draft=response_draft,
            remediation=remediation,
            thread_id=thread_id,
        )
        audit_latency = int((time.monotonic() - audit_start) * 1000)
        stages.append(
            StageTelemetry(
                stage_name="auditor",
                status=StageStatus.COMPLETED,
                model=str(auditor.last_model or ""),
                latency_ms=audit_latency,
                total_tokens=0,
                artifacts=_with_stage_warnings(
                    _safe_artifact(audit_result),
                    warnings=['auditor_used_fallback'] if auditor.used_fallback else None,
                ),
            )
        )
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="auditor",
                status=StageStatus.FAILED,
                model="",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        return _error_snapshot(thread_id, stages, budget_tracker, str(exc))

    # -------------------------------------------------------------------------
    # Stage 7: Explainer
    # -------------------------------------------------------------------------
    explainer = ExplainerAgent(
        llm_client=shared_client,
        audit_logger=audit_logger,
    )
    try:
        exp_start = time.monotonic()
        explanation = explainer.summarize_chain(
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            final_response=response_draft,
            audit_verdict=audit_result,
            thread_id=thread_id,
        )
        exp_latency = int((time.monotonic() - exp_start) * 1000)
        stages.append(
            StageTelemetry(
                stage_name="explainer",
                status=StageStatus.COMPLETED,
                model=str(explainer.last_model or ""),
                latency_ms=exp_latency,
                total_tokens=0,
                artifacts=_with_stage_warnings(
                    _safe_artifact(explanation),
                    warnings=['explainer_used_fallback'] if explainer.used_fallback else None,
                ),
            )
        )
        final_explanation_bullets = [
            f"[{b.stage}] {b.summary}" for b in explanation.bullets
        ]
    except Exception as exc:
        stages.append(
            StageTelemetry(
                stage_name="explainer",
                status=StageStatus.FAILED,
                model="",
                latency_ms=0,
                total_tokens=0,
                error_message=str(exc),
            )
        )
        final_explanation_bullets = None

    # -------------------------------------------------------------------------
    # Assemble final snapshot
    # -------------------------------------------------------------------------
    budget_telemetry = _build_budget_telemetry(budget_tracker)
    audit_events = _build_audit_events(audit_logger, thread_id)

    return DashboardSnapshot(
        thread_id=thread_id,
        stages=stages,
        budget=budget_telemetry,
        audit_events=audit_events,
        final_response=response_draft.render_text(),
        final_explanation=final_explanation_bullets,
        run_status="completed",
    )


def fetch_budget_snapshot(budget_tracker: TokenBudgetTracker | None = None) -> BudgetTelemetry:
    """Return the current budget telemetry for the header widget.

    Args:
        budget_tracker: Optional tracker; uses the shared module tracker if None.

    Returns:
        BudgetTelemetry ready for the dashboard header widget.
    """
    settings = get_settings()
    tracker = budget_tracker or _get_shared_budget(settings)
    return _build_budget_telemetry(tracker)


def fetch_audit_events(
    thread_id: str,
    *,
    db_connect_fn: Callable[[str], sqlite3.Connection] | None = None,
) -> list[AuditEventSnapshot]:
    """Load chronological audit events for a thread from SQLite.

    Args:
        thread_id: The pipeline thread to load events for.
        db_connect_fn: Optional connect callable for testing.

    Returns:
        List of AuditEventSnapshot ordered oldest-to-newest.
    """
    audit_logger = AuditLogger(connect_fn=db_connect_fn)
    return _build_audit_events(audit_logger, thread_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _error_snapshot(
    thread_id: str,
    stages: list[StageTelemetry],
    budget_tracker: TokenBudgetTracker,
    error_message: str,
) -> DashboardSnapshot:
    """Build an error DashboardSnapshot when a non-recoverable stage fails."""
    return DashboardSnapshot(
        thread_id=thread_id,
        stages=stages,
        budget=_build_budget_telemetry(budget_tracker),
        audit_events=[],
        final_response=None,
        final_explanation=None,
        run_status="error",
        error_message=error_message,
    )
