"""LangGraph node functions for the FinComplaint AI multi-agent pipeline.

Each node function:
  - Accepts PipelineState
  - Returns dict[str, Any] with only the keys it modifies
  - Wraps an existing agent or service from src/agents/ or src/tools/

Node execution order (defined in pipeline.py):
  intake → product_classifier → issue_classifier → router
    → [human_review interrupt if needed]
    → root_cause → remediator → response_writer → response_auditor
    → [loop back to response_writer if needs_rewrite]
    → explainer → END
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from src.agents.auditor import AuditorAgent
from src.agents.explainer import ExplainerAgent
from src.agents.issue_classifier import IssueClassifierAgent
from src.agents.product_classifier import ProductClassifierAgent
from src.agents.remediator import RemediatorAgent
from src.agents.root_cause import RootCauseAgent
from src.agents.writer import WriterAgent
from src.graph.langgraph_state import PipelineState
from src.intake.pipeline import prepare_intake
from src.schemas.classification import ProductType
from src.tools.audit_logger import AuditLogger
from src.tools.mcp_policy_client import MCPPolicyClient

# ---------------------------------------------------------------------------
# Agent singletons (lazy-initialised per-process)
# ---------------------------------------------------------------------------

_product_classifier: ProductClassifierAgent | None = None
_issue_classifier: IssueClassifierAgent | None = None
_root_cause_agent: RootCauseAgent | None = None
_remediator_agent: RemediatorAgent | None = None
_writer_agent: WriterAgent | None = None
_auditor_agent: AuditorAgent | None = None
_explainer_agent: ExplainerAgent | None = None
_audit_logger: AuditLogger | None = None


def _get_product_classifier() -> ProductClassifierAgent:
    global _product_classifier
    if _product_classifier is None:
        _product_classifier = ProductClassifierAgent()
    return _product_classifier


def _get_issue_classifier() -> IssueClassifierAgent:
    global _issue_classifier
    if _issue_classifier is None:
        _issue_classifier = IssueClassifierAgent()
    return _issue_classifier


def _get_root_cause_agent() -> RootCauseAgent:
    global _root_cause_agent
    if _root_cause_agent is None:
        _root_cause_agent = RootCauseAgent()
    return _root_cause_agent


def _get_remediator_agent() -> RemediatorAgent:
    global _remediator_agent
    if _remediator_agent is None:
        _remediator_agent = RemediatorAgent()
    return _remediator_agent


def _get_writer_agent() -> WriterAgent:
    global _writer_agent
    if _writer_agent is None:
        _writer_agent = WriterAgent()
    return _writer_agent


def _get_auditor_agent() -> AuditorAgent:
    global _auditor_agent
    if _auditor_agent is None:
        _auditor_agent = AuditorAgent()
    return _auditor_agent


def _get_explainer_agent() -> ExplainerAgent:
    global _explainer_agent
    if _explainer_agent is None:
        _explainer_agent = ExplainerAgent()
    return _explainer_agent


def _get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# ---------------------------------------------------------------------------
# Helper: telemetry record
# ---------------------------------------------------------------------------

def _telemetry(
    node: str,
    latency_ms: int,
    model: str = '',
    tokens: int = 0,
    attempts: int = 0,
    used_fallback: bool = False,
) -> dict[str, Any]:
    return {
        'node': node,
        'latency_ms': latency_ms,
        'model': model,
        'tokens': tokens,
        'attempts': attempts,
        'used_fallback': used_fallback,
        'timestamp': time.time(),
    }


# ---------------------------------------------------------------------------
# Node: intake (PII scrubbing + pre-processing)
# ---------------------------------------------------------------------------

def intake_processor_node(state: PipelineState) -> dict[str, Any]:
    """Scrub PII and prepare the complaint for LLM processing."""
    raw = state.get('raw_complaint', '')
    thread_id = state.get('thread_id') or str(uuid.uuid4())

    t0 = time.monotonic()
    intake = prepare_intake(raw_text=raw)
    latency = int((time.monotonic() - t0) * 1000)

    return {
        'thread_id': thread_id,
        'intake': intake,
        'events': [f'{thread_id}:intake_complete'],
        'stage_telemetry': [_telemetry('intake', latency, model='pii-scrubber-v1')],
    }


# ---------------------------------------------------------------------------
# Node: product_classifier (Stage 1)
# ---------------------------------------------------------------------------

def product_classifier_node(state: PipelineState) -> dict[str, Any]:
    """Stage-1 classifier: identify financial product from complaint text."""
    intake = state['intake']
    thread_id = state['thread_id']

    agent = _get_product_classifier()
    t0 = time.monotonic()
    product_result = agent.classify_product(intake)
    latency = int((time.monotonic() - t0) * 1000)

    return {
        'product_classification': product_result,
        'events': [f'{thread_id}:product_classified:{product_result.product.value}'],
        'stage_telemetry': [
            _telemetry(
                'product_classifier',
                latency,
                model=agent.last_model or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node: issue_classifier (Stage 2)
# ---------------------------------------------------------------------------

def issue_classifier_node(state: PipelineState) -> dict[str, Any]:
    """Stage-2 classifier: identify issue, severity, compliance risk (product-conditioned)."""
    intake = state['intake']
    thread_id = state['thread_id']
    product_result = state['product_classification']

    agent = _get_issue_classifier()
    t0 = time.monotonic()
    issue_result = agent.classify_issue(
        intake,
        product_result.product,
        product_reasoning=product_result.reasoning,
    )
    latency = int((time.monotonic() - t0) * 1000)

    # Merge into the combined ClassificationResult for downstream compat
    combined = issue_result.to_classification_result(product_result.product)

    return {
        'issue_classification': issue_result,
        'classification': combined,
        'events': [
            f'{thread_id}:issue_classified:{issue_result.issue.value}',
            f'{thread_id}:severity:{issue_result.severity.value}',
        ],
        'stage_telemetry': [
            _telemetry(
                'issue_classifier',
                latency,
                model=agent.last_model or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node: root_cause (RAG diagnosis)
# ---------------------------------------------------------------------------

def root_cause_node(state: PipelineState) -> dict[str, Any]:
    """RAG-based root-cause diagnosis against historical CFPB complaints."""
    complaint_text = state['intake'].scrubbed_text
    classification = state['classification']
    thread_id = state['thread_id']

    agent = _get_root_cause_agent()
    t0 = time.monotonic()
    diagnosis = agent.diagnose(
        complaint_text=complaint_text,
        thread_id=thread_id,
    )
    latency = int((time.monotonic() - t0) * 1000)

    return {
        'diagnosis': diagnosis,
        'events': [f'{thread_id}:root_cause_complete'],
        'stage_telemetry': [
            _telemetry(
                'root_cause',
                latency,
                model=getattr(agent, 'last_model', '') or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node: remediator (MCP policy grounding)
# ---------------------------------------------------------------------------

def remediator_node(state: PipelineState) -> dict[str, Any]:
    """Grounds the action plan in MCP regulatory policy for the state."""
    complaint_text = state['intake'].scrubbed_text
    classification = state['classification']
    diagnosis = state['diagnosis']
    thread_id = state['thread_id']
    state_code = state.get('state_code', 'XX')

    agent = _get_remediator_agent()
    t0 = time.monotonic()
    remediation = agent.propose_action(
        complaint_text=complaint_text,
        classification=classification,
        diagnosis=diagnosis,
        state_code=state_code,
        thread_id=thread_id,
    )
    latency = int((time.monotonic() - t0) * 1000)

    return {
        'remediation': remediation,
        'events': [f'{thread_id}:remediation_complete'],
        'stage_telemetry': [
            _telemetry(
                'remediator',
                latency,
                model=agent.last_model or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node: response_writer (Actor)
# ---------------------------------------------------------------------------

def response_writer_node(state: PipelineState) -> dict[str, Any]:
    """Draft a 4-block customer-facing response grounded in remediation steps."""
    complaint_text = state['intake'].scrubbed_text
    classification = state['classification']
    diagnosis = state['diagnosis']
    remediation = state['remediation']
    thread_id = state['thread_id']
    unresolved = list(state.get('unresolved_issues') or [])

    agent = _get_writer_agent()
    t0 = time.monotonic()
    draft = agent.compose_response(
        complaint_text=complaint_text,
        classification=classification,
        diagnosis=diagnosis,
        remediation=remediation,
        unresolved_issues=unresolved,
        thread_id=thread_id,
    )
    latency = int((time.monotonic() - t0) * 1000)

    return {
        'response_draft': draft,
        'response_loop_status': 'needs_review',
        'events': [f'{thread_id}:response_drafted'],
        'stage_telemetry': [
            _telemetry(
                'response_writer',
                latency,
                model=agent.last_model or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node: response_auditor (Critic)
# ---------------------------------------------------------------------------

MAX_REWRITE_ATTEMPTS = 2


def response_auditor_node(state: PipelineState) -> dict[str, Any]:
    """Audit the draft response for compliance, tone, and policy citations."""
    draft = state['response_draft']
    remediation = state['remediation']
    thread_id = state['thread_id']
    rewrite_count = state.get('rewrite_count', 0)

    agent = _get_auditor_agent()
    t0 = time.monotonic()
    audit = agent.review_response(
        draft=draft,
        remediation=remediation,
        thread_id=thread_id,
    )
    latency = int((time.monotonic() - t0) * 1000)

    from src.schemas.auditor import AuditVerdict

    if audit.verdict == AuditVerdict.PASS:
        status = 'approved'
        route = 'continue'
    elif rewrite_count >= MAX_REWRITE_ATTEMPTS:
        status = 'approved'  # force through after max rewrites
    else:
        status = 'needs_rewrite'

    return {
        'audit_result': audit,
        'response_loop_status': status,
        'rewrite_count': rewrite_count + 1 if status == 'needs_rewrite' else rewrite_count,
        'unresolved_issues': list(audit.must_fix_items) if status == 'needs_rewrite' else [],
        'events': [f'{thread_id}:audit_{audit.verdict.value.lower()}'],
        'stage_telemetry': [
            _telemetry(
                'response_auditor',
                latency,
                model=agent.last_model or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node: explainer (Audit trail)
# ---------------------------------------------------------------------------

def explainer_node(state: PipelineState) -> dict[str, Any]:
    """Generate deterministic 5-7 bullet audit trail for compliance database."""
    classification = state['classification']
    diagnosis = state['diagnosis']
    remediation = state['remediation']
    draft = state['response_draft']
    audit = state['audit_result']
    thread_id = state['thread_id']

    agent = _get_explainer_agent()
    t0 = time.monotonic()
    explanation = agent.summarize_chain(
        classification=classification,
        diagnosis=diagnosis,
        remediation=remediation,
        final_response=draft,
        audit_verdict=audit,
        thread_id=thread_id,
    )
    latency = int((time.monotonic() - t0) * 1000)

    return {
        'explanation': explanation,
        'events': [f'{thread_id}:pipeline_complete'],
        'stage_telemetry': [
            _telemetry(
                'explainer',
                latency,
                model=agent.last_model or 'unknown',
                tokens=getattr(agent, 'last_total_tokens', 0),
                attempts=getattr(agent, 'last_llm_attempts', 0),
                used_fallback=getattr(agent, 'used_fallback', False),
            )
        ],
    }
