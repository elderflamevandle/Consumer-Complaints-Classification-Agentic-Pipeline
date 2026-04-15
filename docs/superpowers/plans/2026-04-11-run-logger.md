# Run Logger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** At every `POST /api/v1/complaints` call, write a structured `.log` file to `logs/` capturing each agent's execution time, status, output summary, and final API success/failure.

**Architecture:** A `RunLogger` class in `app/run_logger.py` reads the `stage_telemetry` list already emitted by every pipeline node, plus the top-level `final_state` fields, and writes one human-readable log file per run. `app/api.py` wraps `run_complaint()` with `RunLogger.write()` / `RunLogger.write_error()` calls.

**Tech Stack:** Python stdlib only (`pathlib`, `textwrap`, `datetime`). No new dependencies.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/run_logger.py` | `RunLogger` class — builds and writes `.log` files |
| Create | `tests/test_run_logger.py` | Unit tests for `RunLogger` |
| Create | `logs/.gitkeep` | Ensures directory exists in git |
| Modify | `.gitignore` | Ignore `logs/*.log` files |
| Modify | `app/api.py` | Wrap `run_complaint()` with `RunLogger` |

---

## Task 1: Create `logs/` directory and update `.gitignore`

**Files:**
- Create: `logs/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Create the logs directory placeholder**

```bash
New-Item -ItemType File -Path "logs/.gitkeep" -Force
```

Or create the file with empty content.

- [ ] **Step 2: Add logs/*.log to .gitignore**

Append to `.gitignore`:
```
logs/*.log
```

- [ ] **Step 3: Commit**

```bash
git add logs/.gitkeep .gitignore
git commit -m "chore: add logs/ directory for per-run log files"
```

---

## Task 2: Write failing tests for `RunLogger`

**Files:**
- Create: `tests/test_run_logger.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for app/run_logger.py — per-run structured file logger."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.run_logger import RunLogger

SAMPLE_THREAD_ID = "abc123de-0000-0000-0000-000000000000"
SAMPLE_COMPLAINT = "I was charged twice for the same credit card transaction."
SAMPLE_STATE = "NY"


@pytest.fixture()
def tmp_logger(tmp_path: Path) -> RunLogger:
    """RunLogger writing to a temp directory."""
    return RunLogger(
        thread_id=SAMPLE_THREAD_ID,
        complaint_text=SAMPLE_COMPLAINT,
        state_code=SAMPLE_STATE,
        logs_dir=tmp_path,
    )


def _make_final_state() -> dict:
    clf = MagicMock()
    clf.product_type = "CREDIT_CARD"
    clf.issue_type = "Problem with a purchase shown on your statement"
    clf.severity = "HIGH"
    clf.compliance_risk = "MEDIUM"

    audit = MagicMock()
    audit.verdict = "PASS"

    return {
        "thread_id": SAMPLE_THREAD_ID,
        "classification": clf,
        "audit_result": audit,
        "response_loop_status": "approved",
        "rewrite_count": 0,
        "events": [
            f"{SAMPLE_THREAD_ID}:intake_complete",
            f"{SAMPLE_THREAD_ID}:pipeline_complete",
        ],
        "stage_telemetry": [
            {
                "node": "intake",
                "latency_ms": 12,
                "model": "pii-scrubber-v1",
                "tokens": 0,
                "attempts": 0,
                "used_fallback": False,
                "timestamp": time.time(),
            },
            {
                "node": "product_classifier",
                "latency_ms": 1204,
                "model": "llama3-70b-8192",
                "tokens": 450,
                "attempts": 1,
                "used_fallback": False,
                "timestamp": time.time(),
            },
        ],
    }


class TestRunLoggerFileCreation:
    def test_creates_log_file_on_write(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        assert tmp_logger.log_path.exists()

    def test_log_filename_contains_thread_prefix(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        assert "abc123de" in tmp_logger.log_path.name

    def test_log_filename_has_log_extension(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        assert tmp_logger.log_path.suffix == ".log"

    def test_write_error_creates_log_file(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write_error(RuntimeError("Groq timeout"), http_status=500)
        assert tmp_logger.log_path.exists()


class TestRunLoggerContent:
    def test_log_contains_thread_id(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert SAMPLE_THREAD_ID in content

    def test_log_contains_state_code(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert SAMPLE_STATE in content

    def test_log_contains_complaint_snippet(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "charged twice" in content

    def test_log_contains_agent_names(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "intake" in content
        assert "product_classifier" in content

    def test_log_contains_latency(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "1204" in content  # product_classifier latency

    def test_log_contains_total_tokens(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "450" in content  # product_classifier tokens

    def test_log_contains_audit_verdict(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "PASS" in content

    def test_log_contains_response_loop_status(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "approved" in content

    def test_log_contains_events(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "intake_complete" in content

    def test_log_marks_success_on_200(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "SUCCESS" in content

    def test_log_marks_error_on_500(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write_error(RuntimeError("boom"), http_status=500)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "ERROR" in content
        assert "boom" in content

    def test_total_pipeline_time_is_sum_of_latencies(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        # 12 + 1204 = 1216 ms
        assert "1216" in content
```

- [ ] **Step 2: Run tests to verify they fail (RunLogger doesn't exist yet)**

```bash
uv run pytest tests/test_run_logger.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.run_logger'`

---

## Task 3: Implement `RunLogger`

**Files:**
- Create: `app/run_logger.py`

- [ ] **Step 1: Write the implementation**

```python
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

Note: This logger is separate from src/tools/audit_logger.py (SQLite).
That logger records node-level decisions; this one writes human-readable
run summaries to files for operator inspection.
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
        col = f"{'Node':<22} {'Status':<10} {'Latency(ms)':>11}  {'Model':<24} {'Tokens':>6}  {'Attempts':>8}  Fallback"
        lines = ["--- AGENT EXECUTION ---", col, "-" * len(col)]
        for entry in telemetry:
            node = str(entry.get("node", "?"))
            latency = int(entry.get("latency_ms", 0))
            model = str(entry.get("model") or "unknown")[:24]
            tokens = int(entry.get("tokens", 0))
            attempts = int(entry.get("attempts", 0))
            fallback = "Yes" if entry.get("used_fallback") else "No"
            lines.append(
                f"{node:<22} {'OK':<10} {latency:>11}  {model:<24} {tokens:>6}  {attempts:>8}  {fallback}"
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
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_run_logger.py -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add app/run_logger.py tests/test_run_logger.py
git commit -m "feat: add RunLogger for per-run structured .log files"
```

---

## Task 4: Integrate `RunLogger` into `app/api.py`

**Files:**
- Modify: `app/api.py`

- [ ] **Step 1: Replace the `process_complaint` function body in `app/api.py`**

The current function (lines ~55–80) does:
```python
    try:
        final_state = run_complaint(...)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

Replace with:
```python
from app.run_logger import RunLogger

@app.post("/api/v1/complaints", response_model=ComplaintResponse, tags=["pipeline"])
def process_complaint(request: ComplaintRequest) -> ComplaintResponse:
    ...
    if _graph is None:
        raise HTTPException(status_code=503, detail="Pipeline graph not initialised.")

    tid = request.thread_id or str(uuid.uuid4())
    logger = RunLogger(
        thread_id=tid,
        complaint_text=request.complaint_text,
        state_code=request.state_code,
    )

    try:
        final_state: dict[str, Any] = run_complaint(
            _graph,
            complaint_text=request.complaint_text,
            state_code=request.state_code,
            thread_id=tid,
        )
    except Exception as exc:
        logger.write_error(exc, http_status=500)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    serialised: dict[str, Any] = {}
    for key, value in final_state.items():
        if hasattr(value, "model_dump"):
            serialised[key] = value.model_dump()
        else:
            serialised[key] = value

    logger.write(final_state, http_status=200)
    return ComplaintResponse(data=serialised)
```

Also add `import uuid` at the top if not already present.

- [ ] **Step 2: Verify the server still starts**

```bash
uv run uvicorn app.api:app --reload --port 8000
```

Expected: server starts, no import errors.

- [ ] **Step 3: Make a test request and check a log file was created**

```bash
curl -s -X POST http://localhost:8000/api/v1/complaints \
  -H "Content-Type: application/json" \
  -d '{"complaint_text": "I was charged twice", "state_code": "NY"}' | python -m json.tool
ls logs/
cat logs/run_*.log
```

Expected: a `run_YYYYMMDD_HHMMSS_*.log` file appears with all sections filled.

- [ ] **Step 4: Run the full test suite to confirm nothing regressed**

```bash
uv run pytest -q
```

Expected: all tests pass (including `tests/test_api.py` and `tests/test_run_logger.py`).

- [ ] **Step 5: Commit**

```bash
git add app/api.py
git commit -m "feat: write per-run .log file for every API complaint call"
```

---

## Self-Review

**Spec coverage:**
- [x] New .log file per API run — Task 1 (directory) + Task 4 (integration)
- [x] Each agent's execution time — Task 3 `_agent_table` reads `latency_ms` from `stage_telemetry`
- [x] Each agent's status — Task 3 `_agent_table` writes `OK` per node (pipeline only reaches end on success)
- [x] Each agent's output summary — Task 3 `_summary_section` captures classification, audit verdict, rewrite count
- [x] Final API success/failure — Task 3 `_api_result_section` + `write_error` for exceptions

**No placeholders:** All code is complete and runnable.

**Type consistency:** `RunLogger.__init__` accepts `logs_dir: Path`, tests pass `tmp_path` (a `Path`). `write()` and `write_error()` signatures are consistent across tasks.
