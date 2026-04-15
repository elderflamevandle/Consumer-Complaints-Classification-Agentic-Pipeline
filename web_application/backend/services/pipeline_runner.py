"""
LangGraph Pipeline Runner — Execution wrapper for the FinComplaint AI pipeline.
Streams node updates to the WebSocket queue and collects the final state.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict

from src.graph.pipeline import get_graph
from src.tools.pipeline_logger import PipelineLogger

logger = logging.getLogger(__name__)

# ── Team routing ──────────────────────────────────────────────────────────────
# Maps keywords found in issue_type (lowercased) → team slug.
# Slugs MUST match the slug field in the MongoDB teams collection.
# First matching rule wins (most-specific first).
_ISSUE_TEAM_RULES: list[tuple[str, str]] = [
    # Credit Reporting team
    ("credit monitoring",                   "credit-reporting"),
    ("identity theft",                      "credit-reporting"),
    ("improper use of your report",         "credit-reporting"),
    ("incorrect information on your report","credit-reporting"),
    ("fraud alert",                         "credit-reporting"),
    ("security freeze",                     "credit-reporting"),
    ("unable to get your credit report",    "credit-reporting"),
    ("investigation into an existing",      "credit-reporting"),
    ("credit report",                       "credit-reporting"),
    ("credit score",                        "credit-reporting"),
    # Debt Collection team
    ("attempts to collect debt",            "debt-collection"),
    ("communication tactics",               "debt-collection"),
    ("electronic communications",           "debt-collection"),
    ("false statements",                    "debt-collection"),
    ("threatened to contact",               "debt-collection"),
    ("negative or legal action",            "debt-collection"),
    ("written notification about debt",     "debt-collection"),
    # Money Transfer team
    ("fraud or scam",                       "money-transfer"),
    ("incorrect exchange rate",             "money-transfer"),
    ("lost or stolen money order",          "money-transfer"),
    ("mobile wallet",                       "money-transfer"),
    ("money was not available",             "money-transfer"),
    ("unauthorized transactions",           "money-transfer"),
    ("wrong amount charged",                "money-transfer"),
    ("unexpected or other fees",            "money-transfer"),
    # Mortgage team
    ("applying for a mortgage",             "mortgage"),
    ("closing on a mortgage",               "mortgage"),
    ("struggling to pay mortgage",          "mortgage"),
    ("trouble during payment process",      "mortgage"),
    ("mortgage",                            "mortgage"),
    # Vehicle Loan & Lease team
    ("getting a loan or lease",             "vehicle-loan-lease"),
    ("managing the loan or lease",          "vehicle-loan-lease"),
    ("problems at the end of the loan",     "vehicle-loan-lease"),
    ("repossession",                        "vehicle-loan-lease"),
    ("struggling to pay your loan",         "vehicle-loan-lease"),
    # Credit Card team
    ("closing your account",                "credit-card"),
    ("fees or interest",                    "credit-card"),
    ("getting a credit card",               "credit-card"),
    ("struggling to pay your bill",         "credit-card"),
    ("trouble using your card",             "credit-card"),
    ("purchase shown on your statement",    "credit-card"),
    ("problem when making payments",        "credit-card"),
    ("credit card",                         "credit-card"),
    # Checking & Savings Account team
    ("closing an account",                  "checking-savings-account"),
    ("managing an account",                 "checking-savings-account"),
    ("opening an account",                  "checking-savings-account"),
    ("funds being low",                     "checking-savings-account"),
    ("lender or other company charging",    "checking-savings-account"),
]

# Fallback: product_type → team slug when no issue-type rule matches.
_PRODUCT_TEAM_MAP: dict[str, str] = {
    "CHECKING_SAVINGS_ACCOUNT": "checking-savings-account",
    "CREDIT_CARD":              "credit-card",
    "CREDIT_REPORTING":         "credit-reporting",
    "DEBT_COLLECTION":          "debt-collection",
    "MONEY_TRANSFER":           "money-transfer",
    "MORTGAGE":                 "mortgage",
    "VEHICLE_LOAN_LEASE":       "vehicle-loan-lease",
}

_TEAM_DISPLAY: dict[str, str] = {
    "checking-savings-account": "Checking and Savings Account",
    "credit-card":              "Credit Card",
    "credit-reporting":         "Credit Reporting",
    "debt-collection":          "Debt Collection",
    "money-transfer":           "Money Transfer",
    "mortgage":                 "Mortgage",
    "vehicle-loan-lease":       "Vehicle Loan & Lease",
    "general-resolution":       "General Complaint Resolution",
}


def _resolve_team(classification: Any) -> tuple[str, str]:
    """Return (slug, display_name) from a ClassificationResult or dict."""
    issue_lower = ""
    product_upper = ""
    if hasattr(classification, "issue_type"):
        issue_lower = str(classification.issue_type).lower()
        product_upper = str(getattr(classification, "product_type", "")).upper()
    elif isinstance(classification, dict):
        issue_lower = str(classification.get("issue_type", "")).lower()
        product_upper = str(classification.get("product_type", "")).upper()

    for keyword, slug in _ISSUE_TEAM_RULES:
        if keyword in issue_lower:
            return slug, _TEAM_DISPLAY.get(slug, slug.replace("-", " ").title())

    slug = _PRODUCT_TEAM_MAP.get(product_upper, "general-resolution")
    return slug, _TEAM_DISPLAY.get(slug, slug.replace("-", " ").title())

class PipelineUpdate:
    __slots__ = ("node", "event", "payload", "timestamp")

    def __init__(self, node: str, event: str, payload: Dict[str, Any]):
        self.node = node
        self.event = event           # "started" | "completed" | "failed" | "interrupted"
        self.payload = payload
        self.timestamp = datetime.now(tz=timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "pipeline_update",
            "node": self.node,
            "event": self.event,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

class PipelineRunner:
    """
    Runs the real LangGraph pipeline for a single complaint.
    Yields PipelineUpdate objects that callers can forward to WebSocket clients.
    """

    def __init__(
        self,
        complaint_id: str,
        complaint_text: str,
        state_code: str = "CA",
    ):
        self.complaint_id = complaint_id
        self.complaint_text = complaint_text
        self.state_code = state_code
        self._result: Dict[str, Any] = {}
        self._plog = PipelineLogger(complaint_id=complaint_id, state_code=state_code)

    async def run(self) -> AsyncIterator[PipelineUpdate]:
        """Async generator — yield each update as it happens."""
        graph = get_graph()

        self._plog.pipeline_start(complaint_text_length=len(self.complaint_text))
        pipeline_t0 = time.monotonic()
        nodes_run = 0
        total_tokens = 0

        initial_state = {
            "thread_id": self.complaint_id,
            "raw_complaint": self.complaint_text,
            "state_code": self.state_code,
            "rewrite_count": 0,
            "events": [],
            "stage_telemetry": [],
            "unresolved_issues": [],
        }

        try:
          # Stream the graph execution node by node
          # astream() yields a dict of {node_name: state_updates}
          async for output in graph.astream(initial_state):
            for node_name, state_update in output.items():
                # Accumulate state internally
                self._result.update(state_update)

                # Build the payload for the WebSocket
                payload: Dict[str, Any] = {
                    "message": f"Completed {node_name.replace('_', ' ').title()}"
                }

                # Try to extract telemetry for this node
                telemetries = state_update.get("stage_telemetry", [])
                node_telemetry = {}
                for t in telemetries:
                    if t.get("node") == node_name:
                        node_telemetry = t

                node_latency_ms = node_telemetry.get("latency_ms", 0)
                node_tokens     = node_telemetry.get("tokens", 0)
                node_model      = node_telemetry.get("model", "unknown")
                node_attempts   = node_telemetry.get("attempts", 1)
                node_fallback   = node_telemetry.get("used_fallback", False)

                if node_telemetry:
                    payload["latency_ms"]  = node_latency_ms
                    payload["tokens_used"] = node_tokens
                    payload["model"]       = node_model

                nodes_run += 1
                total_tokens += node_tokens

                # Map specific outputs expected by the UI and the service
                mapped_name = node_name
                
                if node_name == "intake_processor":
                    mapped_name = "intake"
                    intake_data = state_update.get("intake", {})
                    payload["scrubbed_text"] = "Pending extraction..."
                    if hasattr(intake_data, "scrubbed_text"):
                        payload["scrubbed_text"] = intake_data.scrubbed_text
                    elif isinstance(intake_data, dict):
                        payload["scrubbed_text"] = intake_data.get("scrubbed_text", "")
                    payload["pii_redacted_count"] = 0
                    
                elif node_name == "product_classifier":
                    mapped_name = "classifier"
                    # We just log it visually; UI often hooks directly into 'classification' from 'issue_classifier' below
                    
                elif node_name == "issue_classifier":
                    mapped_name = "routing"  # Or "classifier"
                    classification_data = state_update.get("classification", {})
                    if hasattr(classification_data, "model_dump"):
                        payload["classification"] = classification_data.model_dump()
                    else:
                        payload["classification"] = classification_data
                    payload["route"] = "continue"
                    payload["review_required"] = False
                    
                elif node_name == "root_cause":
                    diagnosis_data = state_update.get("diagnosis", {})
                    root_c = ""
                    evid = []
                    if hasattr(diagnosis_data, "root_cause"):
                        root_c = diagnosis_data.root_cause
                        evid = getattr(diagnosis_data, "evidence_citations", [])
                    elif isinstance(diagnosis_data, dict):
                        root_c = diagnosis_data.get("root_cause", "")
                        evid = diagnosis_data.get("evidence_citations", [])
                    
                    payload["root_cause"] = root_c
                    payload["evidence_count"] = len(evid)
                    
                elif node_name == "remediator":
                    remediation = state_update.get("remediation", {})
                    actions = []
                    citations = []
                    if hasattr(remediation, "action_plan"):
                        actions = [s.action for s in remediation.action_plan]
                        citations = getattr(remediation, "citations", [])
                    elif isinstance(remediation, dict):
                        plan = remediation.get("action_plan", [])
                        if plan and hasattr(plan[0], "action"):
                            actions = [s.action for s in plan]
                        else:
                            actions = [str(x) for x in plan]
                        citations = remediation.get("citations", [])
                        
                    payload["action_plan"] = actions
                    payload["policy_citations"] = citations
                    # Route to team based on classification already in accumulated state
                    classification = self._result.get("classification")
                    team_slug, team_display = _resolve_team(classification)
                    payload["assigned_team"] = team_display
                    payload["assigned_team_slug"] = team_slug
                    # Persist routing in final_result so complaint_service can write it to DB
                    self._result["assigned_team_slug"] = team_slug
                    self._result["assigned_team"] = team_display

                elif node_name == "response_writer":
                    mapped_name = "writer"
                    draft = state_update.get("response_draft", "")
                    if hasattr(draft, "content"): draft = draft.content
                    elif isinstance(draft, dict): draft = draft.get("content", "")
                    payload["response_draft_preview"] = draft[:300] + "…" if isinstance(draft, str) else str(draft)

                elif node_name == "response_auditor":
                    mapped_name = "auditor"
                    audit = state_update.get("audit_result", {})
                    verdict = ""
                    fail_codes = []
                    if hasattr(audit, "verdict"):
                        verdict = audit.verdict
                        fail_codes = getattr(audit, "failed_checks", [])
                    elif isinstance(audit, dict):
                        verdict = audit.get("verdict", "")
                        fail_codes = audit.get("failed_checks", [])
                    payload["verdict"] = verdict
                    payload["fail_codes"] = fail_codes
                    
                elif node_name == "explainer":
                    expl = state_update.get("explanation", "")
                    if hasattr(expl, "bullets"): expl = str(expl.bullets)
                    elif isinstance(expl, dict): expl = str(expl.get("bullets", ""))
                    payload["explanation_preview"] = expl[:400] + "…" if isinstance(expl, str) else str(expl)

                # ── Pipeline file log ─────────────────────────────────────
                _log_extra: Dict[str, Any] = {}
                if node_name == "remediator":
                    _log_extra["assigned_team"] = payload.get("assigned_team", "")
                elif node_name == "response_auditor":
                    _log_extra["audit_verdict"] = str(payload.get("verdict", ""))
                elif node_name == "root_cause":
                    _log_extra["evidence_count"] = payload.get("evidence_count", 0)

                self._plog.node_complete(
                    node_name,
                    latency_ms=node_latency_ms,
                    model=node_model,
                    tokens=node_tokens,
                    attempts=node_attempts,
                    used_fallback=node_fallback,
                    extra=_log_extra if _log_extra else None,
                )

                yield PipelineUpdate(mapped_name, "completed", payload)

          # ── Pipeline complete ──────────────────────────────────────────
          total_ms = int((time.monotonic() - pipeline_t0) * 1000)
          verdict = ""
          audit = self._result.get("audit_result")
          if hasattr(audit, "verdict"):
              verdict = str(audit.verdict)
          elif isinstance(audit, dict):
              verdict = str(audit.get("verdict", ""))
          self._plog.pipeline_complete(
              total_ms=total_ms,
              verdict=verdict,
              assigned_team=self._result.get("assigned_team", ""),
              total_tokens=total_tokens,
              nodes_run=nodes_run,
          )

        except Exception as exc:
            total_ms = int((time.monotonic() - pipeline_t0) * 1000)
            self._plog.pipeline_failed(error=str(exc), total_ms=total_ms)
            raise

    @property
    def final_result(self) -> Dict[str, Any]:
        return self._result
