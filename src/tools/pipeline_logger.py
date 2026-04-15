"""
Pipeline execution logger — writes structured JSON-Lines to logs/pipeline.jsonl.

Each log line is a self-contained JSON record so files are grep/jq-friendly.
Uses a TimedRotatingFileHandler (daily rotation, 30-day retention).

Usage:
    from src.tools.pipeline_logger import PipelineLogger

    log = PipelineLogger(complaint_id="abc-123", state_code="CA")
    log.pipeline_start(complaint_text="...")
    log.node_start("intake")
    log.node_complete("intake", latency_ms=120, model="pii-scrubber-v1", tokens=0)
    log.node_failed("root_cause", error="timeout", latency_ms=45000)
    log.pipeline_complete(total_ms=12400, verdict="PASS", assigned_team="fraud-security")
    log.pipeline_failed(error="unhandled exception", total_ms=500)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Log directory resolution ──────────────────────────────────────────────────
# Works whether called from src/ directly or from the web_application/backend container.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "pipeline.jsonl"


# ── Module-level rotating handler (shared across all PipelineLogger instances) ─
def _build_handler() -> logging.Handler:
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(_LOG_FILE),
        when="midnight",
        interval=1,
        backupCount=30,       # 30-day retention
        encoding="utf-8",
        utc=True,
    )
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON — no prefix
    return handler


_pipeline_logger = logging.getLogger("pipeline.execution")
_pipeline_logger.setLevel(logging.DEBUG)
_pipeline_logger.propagate = False  # don't bubble to root logger

if not _pipeline_logger.handlers:
    _pipeline_logger.addHandler(_build_handler())


# ── Human-readable summary logger (pipeline.log, plain text) ─────────────────
_summary_logger = logging.getLogger("pipeline.summary")
_summary_logger.setLevel(logging.DEBUG)
_summary_logger.propagate = False

if not _summary_logger.handlers:
    _summary_log_file = _LOG_DIR / "pipeline_summary.log"
    _summary_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(_summary_log_file),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        utc=True,
    )
    _summary_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    )
    _summary_logger.addHandler(_summary_handler)


# ── Node display names ────────────────────────────────────────────────────────
_NODE_DISPLAY: dict[str, str] = {
    "intake":            "Intake & PII Scrubbing",
    "intake_processor":  "Intake & PII Scrubbing",
    "product_classifier":"Product Classifier",
    "issue_classifier":  "Issue Classifier",
    "root_cause":        "Root Cause Analysis",
    "remediator":        "Remediation Planning",
    "response_writer":   "Response Drafting",
    "writer":            "Response Drafting",
    "response_auditor":  "Compliance Audit",
    "auditor":           "Compliance Audit",
    "explainer":         "Explanation Generation",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _emit(record: dict[str, Any]) -> None:
    """Write a single JSON record to the rotating log file."""
    try:
        _pipeline_logger.debug(json.dumps(record, default=str))
    except Exception:
        pass  # never crash the pipeline for a logging error


class PipelineLogger:
    """Contextual logger scoped to a single complaint pipeline run."""

    def __init__(self, *, complaint_id: str, state_code: str = "XX") -> None:
        self.complaint_id = complaint_id
        self.state_code = state_code
        self._pipeline_start_ts: float = 0.0
        self._node_start_ts: dict[str, float] = {}

    # ── Pipeline lifecycle ────────────────────────────────────────────────────

    def pipeline_start(self, *, complaint_text_length: int = 0) -> None:
        self._pipeline_start_ts = time.monotonic()
        record: dict[str, Any] = {
            "event": "pipeline_start",
            "timestamp": _now_iso(),
            "complaint_id": self.complaint_id,
            "state_code": self.state_code,
            "complaint_text_length": complaint_text_length,
        }
        _emit(record)
        _summary_logger.info(
            "[%-36s] PIPELINE START  state=%s  text_len=%d",
            self.complaint_id, self.state_code, complaint_text_length,
        )

    def pipeline_complete(
        self,
        *,
        total_ms: int,
        verdict: str = "",
        assigned_team: str = "",
        total_tokens: int = 0,
        nodes_run: int = 0,
    ) -> None:
        record: dict[str, Any] = {
            "event": "pipeline_complete",
            "timestamp": _now_iso(),
            "complaint_id": self.complaint_id,
            "state_code": self.state_code,
            "total_latency_ms": total_ms,
            "total_tokens": total_tokens,
            "nodes_run": nodes_run,
            "audit_verdict": verdict,
            "assigned_team": assigned_team,
        }
        _emit(record)
        _summary_logger.info(
            "[%-36s] PIPELINE DONE   total_ms=%-6d  tokens=%-6d  nodes=%d  verdict=%s  team=%s",
            self.complaint_id, total_ms, total_tokens, nodes_run, verdict or "—", assigned_team or "—",
        )

    def pipeline_failed(self, *, error: str, total_ms: int = 0) -> None:
        record: dict[str, Any] = {
            "event": "pipeline_failed",
            "timestamp": _now_iso(),
            "complaint_id": self.complaint_id,
            "state_code": self.state_code,
            "total_latency_ms": total_ms,
            "error": error,
        }
        _emit(record)
        _summary_logger.error(
            "[%-36s] PIPELINE FAILED total_ms=%-6d  error=%s",
            self.complaint_id, total_ms, error,
        )

    # ── Node lifecycle ────────────────────────────────────────────────────────

    def node_start(self, node: str) -> None:
        self._node_start_ts[node] = time.monotonic()
        record: dict[str, Any] = {
            "event": "node_start",
            "timestamp": _now_iso(),
            "complaint_id": self.complaint_id,
            "node": node,
            "node_display": _NODE_DISPLAY.get(node, node),
        }
        _emit(record)

    def node_complete(
        self,
        node: str,
        *,
        latency_ms: int = 0,
        model: str = "",
        tokens: int = 0,
        attempts: int = 1,
        used_fallback: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        # If we didn't see a node_start, compute from node_start_ts or use provided latency
        wall_ms = latency_ms
        if node in self._node_start_ts:
            wall_ms = int((time.monotonic() - self._node_start_ts.pop(node)) * 1000)

        record: dict[str, Any] = {
            "event": "node_complete",
            "timestamp": _now_iso(),
            "complaint_id": self.complaint_id,
            "node": node,
            "node_display": _NODE_DISPLAY.get(node, node),
            "latency_ms": wall_ms,
            "model": model,
            "tokens": tokens,
            "llm_attempts": attempts,
            "used_fallback": used_fallback,
        }
        if extra:
            record.update(extra)
        _emit(record)

        fallback_tag = " [FALLBACK]" if used_fallback else ""
        _summary_logger.info(
            "[%-36s] %-22s  %-28s  %5d ms  %6d tok  %d attempt(s)%s",
            self.complaint_id,
            _NODE_DISPLAY.get(node, node),
            model or "—",
            wall_ms,
            tokens,
            attempts,
            fallback_tag,
        )

    def node_failed(
        self,
        node: str,
        *,
        error: str,
        latency_ms: int = 0,
        model: str = "",
    ) -> None:
        wall_ms = latency_ms
        if node in self._node_start_ts:
            wall_ms = int((time.monotonic() - self._node_start_ts.pop(node)) * 1000)

        record: dict[str, Any] = {
            "event": "node_failed",
            "timestamp": _now_iso(),
            "complaint_id": self.complaint_id,
            "node": node,
            "node_display": _NODE_DISPLAY.get(node, node),
            "latency_ms": wall_ms,
            "model": model,
            "error": error,
        }
        _emit(record)
        _summary_logger.error(
            "[%-36s] %-22s  FAILED  %5d ms  error=%s",
            self.complaint_id,
            _NODE_DISPLAY.get(node, node),
            wall_ms,
            error,
        )
