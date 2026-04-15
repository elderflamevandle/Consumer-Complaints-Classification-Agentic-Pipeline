"""Per-run structured file logger for the FinComplaint AI pipeline.

Creates one .log file per API call under logs/ named:
    run_YYYYMMDD_HHMMSS_<thread_id_prefix>.log

Usage (called from app/api.py):
    logger = RunLogger(thread_id=tid, complaint_text=text, state_code=code)
    try:
        final_state = run_complaint(...)
        logger.write(final_state, http_status=200)
    except Exception as exc:
        logger.write_error(exc, http_status=500)
        raise

Note: Separate from src/tools/audit_logger.py (SQLite node-level decisions).
This logger writes human-readable per-run summaries for operator inspection.
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DIVIDER = "=" * 80
DEFAULT_LOGS_DIR = Path("logs")


class RunLogger:
    """Writes a structured .log file for a single API pipeline run."""

    def __init__(
        self,
        *,
        thread_id: str,
        complaint_text: str,
        state_code: str,
        logs_dir: Path = DEFAULT_LOGS_DIR,
    ) -> None:
        self._thread_id = thread_id
        self._complaint_text = complaint_text
        self._state_code = state_code
        self._started_at = datetime.now(tz=timezone.utc)

        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = self._started_at.strftime("%Y%m%d_%H%M%S")
        tid_prefix = thread_id[:8]
        self._log_path = logs_dir / f"run_{ts}_{tid_prefix}.log"

    @property
    def log_path(self) -> Path:
        return self._log_path

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    def write(self, final_state: dict[str, Any], *, http_status: int = 200) -> None:
        """Write a successful-run log file from final_state."""
        lines = self._build(final_state, http_status=http_status, error=None)
        self._log_path.write_text("\n".join(lines), encoding="utf-8")

    def write_error(self, exc: Exception, *, http_status: int = 500) -> None:
        """Write an error-run log file when the pipeline raises."""
        lines = self._build({}, http_status=http_status, error=str(exc))
        self._log_path.write_text("\n".join(lines), encoding="utf-8")

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build(
        self, state: dict[str, Any], *, http_status: int, error: str | None
    ) -> list[str]:
        lines: list[str] = []
        lines += self._header()
        lines += self._request_section()
        lines += self._agent_table(state)
        lines += self._summary_section(state)
        lines += self._events_section(state)
        lines += self._api_result_section(http_status, error)
        lines.append(_DIVIDER)
        return lines

    def _header(self) -> list[str]:
        return [
            _DIVIDER,
            "FinComplaint AI — Pipeline Run Log",
            _DIVIDER,
        ]

    def _request_section(self) -> list[str]:
        ts = self._started_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        snippet = textwrap.shorten(self._complaint_text, width=120, placeholder="...")
        return [
            f"Run ID      : {self._thread_id}",
            f"Timestamp   : {ts}",
            f"State Code  : {self._state_code}",
            f"Complaint   : {snippet!r}",
            "",
        ]

    def _agent_table(self, state: dict[str, Any]) -> list[str]:
        telemetry: list[dict[str, Any]] = state.get("stage_telemetry", [])
        col = (
            f"{'Node':<22} {'Status':<10} {'Latency(ms)':>11}  "
            f"{'Model':<24} {'Tokens':>6}  {'Attempts':>8}  Fallback"
        )
        lines = ["--- AGENT EXECUTION ---", col, "-" * len(col)]
        for entry in telemetry:
            node = str(entry.get("node", "?"))
            latency = int(entry.get("latency_ms", 0))
            model = str(entry.get("model") or "unknown")[:24]
            tokens = int(entry.get("tokens", 0))
            attempts = int(entry.get("attempts", 0))
            fallback = "Yes" if entry.get("used_fallback") else "No"
            lines.append(
                f"{node:<22} {'OK':<10} {latency:>11}  "
                f"{model:<24} {tokens:>6}  {attempts:>8}  {fallback}"
            )
        if not telemetry:
            lines.append("  (no telemetry captured)")
        lines.append("")
        return lines

    def _summary_section(self, state: dict[str, Any]) -> list[str]:
        telemetry: list[dict[str, Any]] = state.get("stage_telemetry", [])
        total_ms = sum(int(e.get("latency_ms", 0)) for e in telemetry)
        total_tokens = sum(int(e.get("tokens", 0)) for e in telemetry)

        clf = state.get("classification")
        audit = state.get("audit_result")

        lines = ["--- PIPELINE SUMMARY ---"]
        lines.append(f"Total pipeline time  : {total_ms} ms")
        lines.append(f"Total tokens used    : {total_tokens}")
        lines.append(f"Response loop status : {state.get('response_loop_status', '—')}")
        lines.append(f"Rewrite count        : {state.get('rewrite_count', 0)}")
        lines.append(f"Audit verdict        : {getattr(audit, 'verdict', '—')}")

        if clf is not None:
            lines.append(f"Product type         : {getattr(clf, 'product_type', '—')}")
            lines.append(f"Issue type           : {getattr(clf, 'issue_type', '—')}")
            lines.append(f"Severity             : {getattr(clf, 'severity', '—')}")
            lines.append(f"Compliance risk      : {getattr(clf, 'compliance_risk', '—')}")
        lines.append("")
        return lines

    def _events_section(self, state: dict[str, Any]) -> list[str]:
        events: list[str] = state.get("events", [])
        lines = ["--- EVENTS ---"]
        lines += events if events else ["  (no events)"]
        lines.append("")
        return lines

    def _api_result_section(self, http_status: int, error: str | None) -> list[str]:
        status_label = "SUCCESS" if http_status < 400 else "ERROR"
        return [
            "--- API RESULT ---",
            f"Status               : {status_label}",
            f"HTTP Status          : {http_status}",
            f"Error                : {error or 'None'}",
            "",
        ]
