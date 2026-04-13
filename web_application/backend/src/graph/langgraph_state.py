"""LangGraph-compatible TypedDict state for the FinComplaint AI pipeline.

LangGraph requires state to be a TypedDict (or dataclass) rather than a
Pydantic model so it can perform channel-based partial updates. This module
defines PipelineState and the reducer helpers used by the graph.

The Pydantic models (RoutingState, ClassificationResult, etc.) remain the
canonical data contracts; PipelineState acts as the inter-node carrier.

Node functions should:
  - Accept PipelineState as input
  - Return dict[str, Any] with ONLY the keys they mutate
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from src.agents.remediator import RemediationResult
from src.schemas.auditor import ResponseAuditResult
from src.schemas.classification import (
    ClassificationResult,
    IssueClassificationResult,
    ProductClassificationResult,
)
from src.schemas.explainer import ExplanationResult
from src.schemas.intake import IntakePreparation
from src.schemas.response import ResponseDraft
from src.schemas.root_cause import RootCauseResult


# ---------------------------------------------------------------------------
# Reducer helpers
# ---------------------------------------------------------------------------

def _append_list(existing: list[str], new: list[str]) -> list[str]:
    """Reducer that appends new items to an existing list (no duplicates)."""
    seen = set(existing)
    return existing + [item for item in new if item not in seen]


def _append_dicts(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reducer that appends new dict entries to a list."""
    return existing + new


# ---------------------------------------------------------------------------
# Pipeline state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    """Inter-node state carrier for the LangGraph complaint pipeline.

    Fields marked Annotated[list, reducer] use custom reducers so multiple
    nodes can append to them without clobbering each other.
    """

    # --- Core input ---
    thread_id: str
    raw_complaint: str

    # --- Intake stage ---
    intake: IntakePreparation

    # --- Stage-1 classifier: product ---
    product_classification: ProductClassificationResult

    # --- Stage-2 classifier: issue (conditioned on product) ---
    issue_classification: IssueClassificationResult

    # --- Combined classification (backward-compat with downstream agents) ---
    classification: ClassificationResult

    # --- Routing ---

    # --- RAG / root-cause diagnosis ---
    diagnosis: RootCauseResult

    # --- Remediator ---
    remediation: RemediationResult
    state_code: str                     # US state code for MCP policy lookup

    # --- Response loop ---
    response_draft: ResponseDraft
    audit_result: ResponseAuditResult
    rewrite_count: int
    response_loop_status: str           # 'not_started' | 'needs_rewrite' | 'approved'
    unresolved_issues: Annotated[list[str], _append_list]

    # --- Explainer ---
    explanation: ExplanationResult

    # --- Telemetry / audit trail ---
    events: Annotated[list[str], _append_list]
    stage_telemetry: Annotated[list[dict[str, Any]], _append_dicts]

    # --- Error handling ---
    error: str
