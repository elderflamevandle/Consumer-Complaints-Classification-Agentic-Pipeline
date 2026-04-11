"""Request/response schemas for the FastAPI pipeline wrapper."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PipelineRunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    complaint_text: str = Field(min_length=1)
    state_code: str = Field(default='XX', min_length=2, max_length=2)


class BatchComplaintRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    complaint_id: str | None = None
    complaint_text: str = Field(min_length=1)
    state_code: str = Field(default='XX', min_length=2, max_length=2)


class PipelineBatchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    complaints: list[BatchComplaintRequest] = Field(min_length=1)


class TelemetrySummary(BaseModel):
    model_config = ConfigDict(extra='forbid')

    total_stage_latency_ms: int
    total_stage_tokens: int
    total_stage_attempts: int
    fallback_stages: list[str]
    rewrite_count: int
    event_count: int
    stage_telemetry: list[dict[str, Any]]


class PipelineOutputs(BaseModel):
    model_config = ConfigDict(extra='forbid')

    scrubbed_text: str = ''
    classification: dict[str, Any] = Field(default_factory=dict)
    diagnosis: dict[str, Any] = Field(default_factory=dict)
    remediation: dict[str, Any] = Field(default_factory=dict)
    response_draft: dict[str, Any] = Field(default_factory=dict)
    audit_result: dict[str, Any] = Field(default_factory=dict)
    explanation: dict[str, Any] = Field(default_factory=dict)


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: str
    thread_id: str
    state_code: str
    wall_time_ms: int
    outputs: PipelineOutputs
    telemetry: TelemetrySummary


class PipelineBatchItemResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    complaint_id: str
    status: str
    error: str = ''
    thread_id: str = ''
    state_code: str
    wall_time_ms: int
    outputs: PipelineOutputs
    telemetry: TelemetrySummary


class PipelineBatchResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: str
    total: int
    completed: int
    failed: int
    results: list[PipelineBatchItemResponse]
