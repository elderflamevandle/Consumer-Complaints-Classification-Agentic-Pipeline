"""
LangGraph Pipeline Runner — Execution wrapper for the FinComplaint AI pipeline.
Streams node updates to the WebSocket queue and collects the final state.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict

from ..src.graph.pipeline import get_graph

logger = logging.getLogger(__name__)

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

    async def run(self) -> AsyncIterator[PipelineUpdate]:
        """Async generator — yield each update as it happens."""
        graph = get_graph()
        
        initial_state = {
            "thread_id": self.complaint_id,
            "raw_complaint": self.complaint_text,
            "state_code": self.state_code,
            "rewrite_count": 0,
            "events": [],
            "stage_telemetry": [],
            "unresolved_issues": [],
        }

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
                
                if node_telemetry:
                    payload["latency_ms"] = int(node_telemetry.get("duration", 0) * 1000)
                    payload["tokens_used"] = node_telemetry.get("tokens", 0)
                    payload["model"] = node_telemetry.get("model", "unknown")

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
                    payload["assigned_team"] = "General Complaint Resolution"
                    payload["assigned_team_slug"] = "general-resolution"

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

                yield PipelineUpdate(mapped_name, "completed", payload)

    @property
    def final_result(self) -> Dict[str, Any]:
        return self._result
