"""Tests for the FinComplaint AI FastAPI wrapper (app/api.py).

Run:
    uv run pytest tests/test_api.py -v

Requires:
    - chroma_db/ seeded (run scripts/seed_vectordb.py)
    - GROQ_API_KEY set for live LLM tests, or skip marks will bypass them
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Shared TestClient — builds the graph once per module."""
    with TestClient(app) as c:
        yield c


SAMPLE_COMPLAINT = (
    "I was charged twice for the same transaction on my credit card. "
    "I disputed the charge with the bank three weeks ago but have received "
    "no response and the duplicate charge remains on my account."
)

MINIMAL_COMPLAINT = "Bank charged me an unexpected fee."

# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/health").json()
        assert "status" in body
        assert "groq_enabled" in body
        assert body["status"] == "ok"
        assert isinstance(body["groq_enabled"], bool)


# ---------------------------------------------------------------------------
# POST /api/v1/complaints — input validation
# ---------------------------------------------------------------------------

class TestComplaintValidation:
    def test_missing_complaint_text_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/complaints", json={})
        assert response.status_code == 422

    def test_empty_complaint_text_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/complaints", json={"complaint_text": ""})
        assert response.status_code == 422

    def test_invalid_state_code_length_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/complaints",
            json={"complaint_text": MINIMAL_COMPLAINT, "state_code": "NEW_YORK"},
        )
        assert response.status_code == 422

    def test_valid_request_shape_accepted(self, client: TestClient) -> None:
        """Verify a well-formed request is not rejected at the validation layer.

        Uses a mock graph so the test doesn't require LLM credentials.
        """
        mock_state: dict[str, Any] = {
            "thread_id": "test-thread-123",
            "raw_complaint": MINIMAL_COMPLAINT,
            "state_code": "CA",
            "events": [],
            "stage_telemetry": [],
        }

        with patch("app.api._graph") as mock_graph, \
             patch("app.api.run_complaint", return_value=mock_state):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": MINIMAL_COMPLAINT, "state_code": "CA"},
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/complaints — response structure (mocked pipeline)
# ---------------------------------------------------------------------------

class TestComplaintResponseStructure:
    """Verify the API response envelope using a mocked pipeline."""

    @pytest.fixture()
    def mock_final_state(self) -> dict[str, Any]:
        from unittest.mock import MagicMock

        mock_explanation = MagicMock()
        mock_explanation.model_dump.return_value = {
            "bullets": [
                {"stage": "intake", "summary": "PII scrubbed", "citations": []},
                {"stage": "classification", "summary": "Credit card issue", "citations": []},
                {"stage": "diagnosis", "summary": "Root cause found", "citations": []},
                {"stage": "remediation", "summary": "Action plan created", "citations": []},
                {"stage": "response", "summary": "Draft approved", "citations": []},
            ]
        }

        mock_classification = MagicMock()
        mock_classification.model_dump.return_value = {
            "product_type": "CREDIT_CARD",
            "issue_type": "Problem with a purchase shown on your statement",
            "severity": "HIGH",
            "compliance_risk": "MEDIUM",
            "confidence": 0.92,
        }

        return {
            "thread_id": "test-abc-123",
            "raw_complaint": SAMPLE_COMPLAINT,
            "state_code": "NY",
            "classification": mock_classification,
            "explanation": mock_explanation,
            "response_loop_status": "approved",
            "rewrite_count": 1,
            "events": ["intake_done", "classified", "audited"],
            "stage_telemetry": [{"node": "intake", "duration_ms": 50}],
        }

    def test_response_has_data_key(self, client: TestClient, mock_final_state: dict[str, Any]) -> None:
        with patch("app.api.run_complaint", return_value=mock_final_state):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": SAMPLE_COMPLAINT, "state_code": "NY"},
            )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body

    def test_data_contains_thread_id(self, client: TestClient, mock_final_state: dict[str, Any]) -> None:
        with patch("app.api.run_complaint", return_value=mock_final_state):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": SAMPLE_COMPLAINT},
            )
        data = response.json()["data"]
        assert "thread_id" in data
        assert isinstance(data["thread_id"], str)

    def test_pydantic_models_are_serialised(self, client: TestClient, mock_final_state: dict[str, Any]) -> None:
        """Nested Pydantic objects must be dicts in the JSON output, not raw objects."""
        with patch("app.api.run_complaint", return_value=mock_final_state):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": SAMPLE_COMPLAINT},
            )
        data = response.json()["data"]
        # These should be dicts, not raw Pydantic objects
        assert isinstance(data.get("classification"), dict)
        assert isinstance(data.get("explanation"), dict)

    def test_events_is_list(self, client: TestClient, mock_final_state: dict[str, Any]) -> None:
        with patch("app.api.run_complaint", return_value=mock_final_state):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": SAMPLE_COMPLAINT},
            )
        data = response.json()["data"]
        assert isinstance(data.get("events"), list)

    def test_thread_id_passthrough(self, client: TestClient, mock_final_state: dict[str, Any]) -> None:
        """Provided thread_id must appear in the response data."""
        custom_tid = "my-custom-thread-999"
        mock_final_state["thread_id"] = custom_tid

        with patch("app.api.run_complaint", return_value=mock_final_state):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": SAMPLE_COMPLAINT, "thread_id": custom_tid},
            )
        data = response.json()["data"]
        assert data["thread_id"] == custom_tid


# ---------------------------------------------------------------------------
# POST /api/v1/complaints — error handling
# ---------------------------------------------------------------------------

class TestComplaintErrorHandling:
    def test_pipeline_exception_returns_500(self, client: TestClient) -> None:
        with patch("app.api.run_complaint", side_effect=RuntimeError("Groq rate limit")):
            response = client.post(
                "/api/v1/complaints",
                json={"complaint_text": SAMPLE_COMPLAINT},
            )
        assert response.status_code == 500
        assert "detail" in response.json()

    def test_uninitialised_graph_returns_503(self) -> None:
        """Simulates startup failure — graph is None.

        NOTE: _graph must be set to None INSIDE the TestClient context,
        after the startup event has already fired and rebuilt the graph.
        Setting it before entering the context has no effect because
        startup overwrites it.
        """
        import app.api as api_module
        original = api_module._graph
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                # Startup has now fired. Null out the graph here.
                api_module._graph = None
                response = c.post(
                    "/api/v1/complaints",
                    json={"complaint_text": SAMPLE_COMPLAINT},
                )
            assert response.status_code == 503
        finally:
            api_module._graph = original


# ---------------------------------------------------------------------------
# Live integration test — requires GROQ_API_KEY + seeded chroma_db
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live pipeline test",
)
class TestLivePipeline:
    def test_full_pipeline_returns_approved_status(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/complaints",
            json={
                "complaint_text": SAMPLE_COMPLAINT,
                "state_code": "NY",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]

        # Core fields must be present
        assert "thread_id" in data
        assert "classification" in data
        assert "explanation" in data
        assert "response_loop_status" in data

        # Pipeline should complete
        assert data["response_loop_status"] in ("approved", "escalated")

        # Classification shape
        clf = data["classification"]
        assert "product_type" in clf
        assert "issue_type" in clf
        assert "severity" in clf
        assert "confidence" in clf

        # Explanation bullets
        bullets = data["explanation"]["bullets"]
        assert len(bullets) >= 5
