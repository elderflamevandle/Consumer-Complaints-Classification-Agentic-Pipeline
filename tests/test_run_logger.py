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
        assert "1204" in content

    def test_log_contains_tokens(self, tmp_logger: RunLogger) -> None:
        tmp_logger.write(_make_final_state(), http_status=200)
        content = tmp_logger.log_path.read_text(encoding="utf-8")
        assert "450" in content

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
        # intake(12) + product_classifier(1204) = 1216
        assert "1216" in content
