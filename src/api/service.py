"""Service helpers that adapt the pipeline's final_state into API responses."""

from __future__ import annotations

import time
from typing import Any

from src.api.schemas import (
    PipelineBatchItemResponse,
    PipelineOutputs,
    PipelineRunResponse,
    TelemetrySummary,
)
from src.graph.pipeline import get_graph, run_complaint


def _safe_model_dump(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, 'model_dump'):
        dumped = value.model_dump(mode='json')
        return dumped if isinstance(dumped, dict) else {'value': dumped}
    if isinstance(value, dict):
        return value
    return {'value': str(value)}


def _safe_scrubbed_text(final_state: dict[str, Any]) -> str:
    intake = final_state.get('intake')
    scrubbed = getattr(intake, 'scrubbed_text', '')
    return scrubbed if isinstance(scrubbed, str) else ''


def _telemetry_summary(final_state: dict[str, Any]) -> TelemetrySummary:
    stage_telemetry = list(final_state.get('stage_telemetry') or [])
    return TelemetrySummary(
        total_stage_latency_ms=sum(int(item.get('latency_ms', 0)) for item in stage_telemetry),
        total_stage_tokens=sum(int(item.get('tokens', 0)) for item in stage_telemetry),
        total_stage_attempts=sum(int(item.get('attempts', 0)) for item in stage_telemetry),
        fallback_stages=[
            str(item.get('node', ''))
            for item in stage_telemetry
            if bool(item.get('used_fallback'))
        ],
        rewrite_count=int(final_state.get('rewrite_count', 0)),
        event_count=len(final_state.get('events') or []),
        stage_telemetry=stage_telemetry,
    )


def _outputs(final_state: dict[str, Any]) -> PipelineOutputs:
    return PipelineOutputs(
        scrubbed_text=_safe_scrubbed_text(final_state),
        classification=_safe_model_dump(final_state.get('classification')),
        diagnosis=_safe_model_dump(final_state.get('diagnosis')),
        remediation=_safe_model_dump(final_state.get('remediation')),
        response_draft=_safe_model_dump(final_state.get('response_draft')),
        audit_result=_safe_model_dump(final_state.get('audit_result')),
        explanation=_safe_model_dump(final_state.get('explanation')),
    )


def run_single_complaint(*, complaint_text: str, state_code: str) -> PipelineRunResponse:
    graph = get_graph()
    started = time.monotonic()
    final_state = run_complaint(
        graph,
        complaint_text=complaint_text,
        state_code=state_code,
    )
    wall_time_ms = int((time.monotonic() - started) * 1000)
    return PipelineRunResponse(
        status='completed',
        thread_id=str(final_state.get('thread_id', '')),
        state_code=state_code,
        wall_time_ms=wall_time_ms,
        outputs=_outputs(final_state),
        telemetry=_telemetry_summary(final_state),
    )


def run_batch_complaints(
    complaints: list[dict[str, str]],
) -> list[PipelineBatchItemResponse]:
    graph = get_graph()
    results: list[PipelineBatchItemResponse] = []

    for index, complaint in enumerate(complaints, start=1):
        complaint_id = complaint.get('complaint_id') or str(index)
        complaint_text = complaint['complaint_text']
        state_code = complaint.get('state_code') or 'XX'
        started = time.monotonic()

        try:
            final_state = run_complaint(
                graph,
                complaint_text=complaint_text,
                state_code=state_code,
            )
            status = 'completed'
            error = ''
        except Exception as exc:
            final_state = {}
            status = 'failed'
            error = str(exc)

        wall_time_ms = int((time.monotonic() - started) * 1000)
        results.append(
            PipelineBatchItemResponse(
                complaint_id=complaint_id,
                status=status,
                error=error,
                thread_id=str(final_state.get('thread_id', '')),
                state_code=state_code,
                wall_time_ms=wall_time_ms,
                outputs=_outputs(final_state),
                telemetry=_telemetry_summary(final_state),
            )
        )

    return results
