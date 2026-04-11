"""FastAPI entrypoint for the FinComplaint end-to-end pipeline."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    PipelineBatchRequest,
    PipelineBatchResponse,
    PipelineRunRequest,
    PipelineRunResponse,
)
from src.api.service import run_batch_complaints, run_single_complaint
from src.graph.pipeline import get_graph

app = FastAPI(
    title='FinComplaint Pipeline API',
    version='0.1.0',
    description='Thin API wrapper around the FinComplaint LangGraph pipeline.',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def _warm_graph() -> None:
    get_graph()


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/api/v1/pipeline/run', response_model=PipelineRunResponse)
def run_pipeline(payload: PipelineRunRequest) -> PipelineRunResponse:
    try:
        return run_single_complaint(
            complaint_text=payload.complaint_text,
            state_code=payload.state_code.upper(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post('/api/v1/pipeline/batch', response_model=PipelineBatchResponse)
def run_pipeline_batch(payload: PipelineBatchRequest) -> PipelineBatchResponse:
    try:
        items = [
            {
                'complaint_id': item.complaint_id or str(index),
                'complaint_text': item.complaint_text,
                'state_code': item.state_code.upper(),
            }
            for index, item in enumerate(payload.complaints, start=1)
        ]
        results = run_batch_complaints(items)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    completed = sum(1 for item in results if item.status == 'completed')
    failed = len(results) - completed
    return PipelineBatchResponse(
        status='completed' if failed == 0 else 'partial_failure',
        total=len(results),
        completed=completed,
        failed=failed,
        results=results,
    )
