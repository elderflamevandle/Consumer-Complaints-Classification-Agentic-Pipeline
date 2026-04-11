"""FastAPI wrapper for the FinComplaint AI end-to-end pipeline.

Usage:
    uv run uvicorn app.api:app --reload

Endpoints:
    POST /api/v1/complaints  — run the full pipeline, returns final PipelineState
    GET  /api/v1/health      — readiness check
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.graph.pipeline import build_graph, run_complaint

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ComplaintRequest(BaseModel):
    complaint_text: str = Field(min_length=1, description="Raw consumer complaint text.")
    state_code: str = Field(default="XX", min_length=2, max_length=2, description="US state code for MCP policy lookup (e.g. 'NY').")
    thread_id: str | None = Field(default=None, description="Optional tracking ID. Auto-generated if omitted.")


class ComplaintResponse(BaseModel):
    data: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    groq_enabled: bool


# ---------------------------------------------------------------------------
# App setup — graph is built once at startup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FinComplaint AI",
    description="Complaint triage pipeline: intake → classify → diagnose → remediate → draft → audit → explain.",
    version="1.0.0",
)

_graph: Any = None


@app.on_event("startup")
def _startup() -> None:
    global _graph
    _graph = build_graph()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/v1/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Readiness check. Returns whether Groq LLM is configured."""
    from src.config import get_settings
    settings = get_settings()
    return HealthResponse(status="ok", groq_enabled=settings.groq_enabled)


@app.post("/api/v1/complaints", response_model=ComplaintResponse, tags=["pipeline"])
def process_complaint(request: ComplaintRequest) -> ComplaintResponse:
    """Run the full FinComplaint AI pipeline for a single complaint.

    Returns the complete final PipelineState as `data`, including:
    - `intake`            — PII-scrubbed intake preparation
    - `classification`    — product / issue / severity / compliance_risk
    - `diagnosis`         — root-cause analysis with evidence citations
    - `remediation`       — MCP-grounded action plan
    - `response_draft`    — customer-facing response draft
    - `audit_result`      — compliance audit verdict
    - `response_loop_status` — 'approved' | 'escalated'
    - `explanation`       — stage-by-stage audit trail bullets
    - `events`            — pipeline event log
    - `stage_telemetry`   — per-node timing and token data
    """
    if _graph is None:
        raise HTTPException(status_code=503, detail="Pipeline graph not initialised.")

    try:
        final_state: dict[str, Any] = run_complaint(
            _graph,
            complaint_text=request.complaint_text,
            state_code=request.state_code,
            thread_id=request.thread_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Serialise Pydantic models nested inside the TypedDict
    serialised: dict[str, Any] = {}
    for key, value in final_state.items():
        if hasattr(value, "model_dump"):
            serialised[key] = value.model_dump()
        else:
            serialised[key] = value

    return ComplaintResponse(data=serialised)
