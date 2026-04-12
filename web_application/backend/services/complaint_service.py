"""
Complaint business-logic service.
All DB access goes through MongoDB collections; no raw SQL ever.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..db.mongodb import complaints_col, pipeline_stages_col, teams_col
from ..models.audit_log import AuditAction
from ..models.complaint import (
    ClassificationResult,
    ComplaintDocument,
    ComplaintStatus,
    PipelineStageDocument,
    RemediationStep,
)
from .audit_service import log_event
from .pipeline_runner import PipelineRunner

PIPELINE_NODES = [
    "intake",
    "classifier",
    "routing",
    "root_cause",
    "remediator",
    "writer",
    "auditor",
    "explainer",
]

logger = logging.getLogger(__name__)

# In-memory registry of running pipelines so WS handlers can subscribe.
# Key: complaint_id  Value: asyncio.Queue of PipelineUpdate
_running_pipelines: Dict[str, asyncio.Queue] = {}  # type: ignore[type-arg]


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def create_complaint(
    user_id: str,
    complaint_text: str,
    state_code: str = "CA",
    ip: Optional[str] = None,
) -> ComplaintDocument:
    doc = ComplaintDocument(
        user_id=user_id,
        complaint_text=complaint_text,
        state_code=state_code,
        status=ComplaintStatus.PENDING,
    )
    await complaints_col().insert_one(doc.to_mongo())

    await log_event(
        AuditAction.COMPLAINT_CREATED,
        user_id=user_id,
        entity_type="complaint",
        entity_id=doc.id,
        details={"state_code": state_code, "text_length": len(complaint_text)},
        ip_address=ip,
    )
    return doc


async def get_complaint(complaint_id: str) -> Optional[ComplaintDocument]:
    raw = await complaints_col().find_one({"_id": complaint_id})
    if not raw:
        return None
    return ComplaintDocument.from_mongo(raw)


def _build_complaint_query(
    user_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a MongoDB query for complaint access control.

    Scoping rules:
      - Admin:   no user_id / team_id filter → sees everything
      - Analyst: user_id AND team_id provided → $or clause (own + team's)
      - Viewer:  user_id only → only their own submissions
    """
    query: Dict[str, Any] = {}

    if user_id and team_id:
        # Analyst: own complaints OR team-assigned complaints
        query["$or"] = [{"user_id": user_id}, {"team_id": team_id}]
    elif user_id:
        query["user_id"] = user_id

    if status:
        query["status"] = status

    return query


async def list_complaints(
    *,
    user_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[ComplaintDocument]:
    query = _build_complaint_query(user_id=user_id, team_id=team_id, status=status)
    cursor = (
        complaints_col()
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = []
    async for raw in cursor:
        docs.append(ComplaintDocument.from_mongo(raw))
    return docs


async def count_complaints(
    *,
    user_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status: Optional[str] = None,
) -> int:
    query = _build_complaint_query(user_id=user_id, team_id=team_id, status=status)
    return await complaints_col().count_documents(query)


async def update_complaint_fields(
    complaint_id: str,
    fields: Dict[str, Any],
) -> None:
    fields["updated_at"] = datetime.now(tz=timezone.utc)
    await complaints_col().update_one({"_id": complaint_id}, {"$set": fields})


# ── Pipeline stages ────────────────────────────────────────────────────────────

async def get_pipeline_stages(complaint_id: str) -> List[Dict[str, Any]]:
    cursor = pipeline_stages_col().find({"complaint_id": complaint_id}).sort("created_at", 1)
    stages = []
    async for raw in cursor:
        raw["id"] = str(raw.pop("_id"))
        stages.append(raw)
    return stages


async def upsert_stage(
    complaint_id: str,
    node: str,
    status: str,
    output: Optional[Dict[str, Any]] = None,
    latency_ms: int = 0,
    tokens_used: int = 0,
    model_used: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    now = datetime.now(tz=timezone.utc)
    await pipeline_stages_col().update_one(
        {"complaint_id": complaint_id, "node": node},
        {
            "$set": {
                "status": status,
                "output": output,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "model_used": model_used,
                "error": error,
                "updated_at": now,
            },
            "$setOnInsert": {
                "_id": PipelineStageDocument(
                    complaint_id=complaint_id, node=node
                ).id,
                "created_at": now,
            },
        },
        upsert=True,
    )


# ── Pipeline execution ────────────────────────────────────────────────────────

def get_pipeline_queue(complaint_id: str) -> Optional[asyncio.Queue]:  # type: ignore[type-arg]
    return _running_pipelines.get(complaint_id)


async def run_pipeline(
    complaint_id: str,
    complaint_text: str,
    state_code: str,
    user_id: str,
) -> None:
    """
    Launch the mock pipeline as a background task.
    Updates are pushed to an asyncio.Queue that WS handlers consume.
    """
    queue: asyncio.Queue = asyncio.Queue()  # type: ignore[type-arg]
    _running_pipelines[complaint_id] = queue

    await update_complaint_fields(complaint_id, {"status": ComplaintStatus.PROCESSING})
    await log_event(
        AuditAction.PIPELINE_STARTED,
        user_id=user_id,
        entity_type="complaint",
        entity_id=complaint_id,
    )

    # Initialise all stage records as "pending"
    for node in PIPELINE_NODES:
        await upsert_stage(complaint_id, node, "pending")

    async def _worker():
        runner = PipelineRunner(complaint_id, complaint_text, state_code)
        try:
            async for update in runner.run():
                # Persist stage result
                await upsert_stage(
                    complaint_id,
                    update.node,
                    update.event if update.event in ("completed", "failed", "interrupted") else "running",
                    output=update.payload,
                    latency_ms=update.payload.get("latency_ms", 0),
                    tokens_used=update.payload.get("tokens_used", 0),
                    model_used=update.payload.get("model"),
                )
                # Push to WS queue
                await queue.put(update.to_dict())

            # Apply final results to complaint document.
            # Pipeline state values are Pydantic models — call model_dump() before
            # storing so pymongo can BSON-encode them.
            final = runner.final_result
            update_fields: Dict[str, Any] = {}

            def _to_doc(val: Any) -> Any:
                """Convert Pydantic models → dicts recursively."""
                if hasattr(val, "model_dump"):
                    return val.model_dump()
                if isinstance(val, list):
                    return [_to_doc(v) for v in val]
                return val

            # intake → scrubbed_text
            intake = final.get("intake")
            if intake is not None:
                scrubbed = getattr(intake, "scrubbed_text", None) or (
                    intake.get("scrubbed_text") if isinstance(intake, dict) else None
                )
                if scrubbed:
                    update_fields["scrubbed_text"] = scrubbed

            # classification (ClassificationResult Pydantic model)
            if "classification" in final:
                update_fields["classification"] = _to_doc(final["classification"])

            # diagnosis / root cause (RootCauseResult)
            if "diagnosis" in final:
                diag = _to_doc(final["diagnosis"])
                update_fields["root_cause"] = diag.get("root_cause", "") if isinstance(diag, dict) else str(diag)
                update_fields["root_cause_evidence"] = diag.get("evidence_citations", []) if isinstance(diag, dict) else []

            # remediation (RemediationResult)
            if "remediation" in final:
                rem = _to_doc(final["remediation"])
                if isinstance(rem, dict):
                    plan = rem.get("action_plan", [])
                    update_fields["remediation_steps"] = [
                        (s.get("action", str(s)) if isinstance(s, dict) else str(s)) for s in plan
                    ]
                    update_fields["policy_citations"] = rem.get("citations", [])
                    # Team assignment from remediation
                    assigned = rem.get("assigned_team") or rem.get("assigned_team_slug")
                    if assigned:
                        update_fields["assigned_team"] = assigned

            # response_draft (ResponseDraft Pydantic model)
            if "response_draft" in final:
                draft = final["response_draft"]
                if hasattr(draft, "content"):
                    update_fields["response_draft"] = draft.content
                elif isinstance(draft, dict):
                    update_fields["response_draft"] = draft.get("content", str(draft))
                else:
                    update_fields["response_draft"] = str(draft)

            # audit_result (ResponseAuditResult)
            if "audit_result" in final:
                audit = _to_doc(final["audit_result"])
                update_fields["audit_verdict"] = (
                    audit.get("verdict", "") if isinstance(audit, dict) else str(audit)
                )

            # explanation (ExplanationResult)
            if "explanation" in final:
                update_fields["explanation"] = _to_doc(final["explanation"])

            # review_required flag
            if "review_required" in final:
                update_fields["review_required"] = final["review_required"]

            # Resolve team_id from slug if present
            if "assigned_team_slug" in final:
                team_doc = await teams_col().find_one({"slug": final["assigned_team_slug"]})
                if team_doc:
                    update_fields["team_id"] = team_doc["_id"]

            # Pipeline state has no "status" key — infer from presence of explanation node.
            final_status = final.get("status") or (
                ComplaintStatus.COMPLETE if "explanation" in final else ComplaintStatus.FAILED
            )
            update_fields["status"] = final_status
            if final_status == ComplaintStatus.COMPLETE:
                update_fields["completed_at"] = datetime.now(tz=timezone.utc)

            await update_complaint_fields(complaint_id, update_fields)

            audit_action = (
                AuditAction.PIPELINE_INTERRUPTED
                if final_status == ComplaintStatus.INTERRUPTED
                else AuditAction.PIPELINE_COMPLETED
            )
            await log_event(
                audit_action,
                user_id=user_id,
                entity_type="complaint",
                entity_id=complaint_id,
                details={"status": final_status},
            )

            # Signal WS consumers that stream is done
            await queue.put({"type": "pipeline_done", "status": final_status})

        except Exception as exc:
            logger.exception("Pipeline failed for complaint %s", complaint_id)
            await update_complaint_fields(complaint_id, {"status": ComplaintStatus.FAILED})
            await log_event(
                AuditAction.PIPELINE_FAILED,
                user_id=user_id,
                entity_type="complaint",
                entity_id=complaint_id,
                details={"error": str(exc)},
            )
            await queue.put({"type": "pipeline_done", "status": "failed", "error": str(exc)})
        finally:
            _running_pipelines.pop(complaint_id, None)

    asyncio.create_task(_worker())


async def resume_pipeline_after_review(
    complaint_id: str,
    action: str,
    reviewer_id: str,
    reviewer_notes: Optional[str],
    edited_text: Optional[str],
    user_id: str,
    ip: Optional[str] = None,
) -> ComplaintDocument:
    """Apply a reviewer decision and re-run pipeline from root_cause onward."""
    complaint = await get_complaint(complaint_id)
    if not complaint:
        raise ValueError(f"Complaint {complaint_id} not found")

    if complaint.status != ComplaintStatus.INTERRUPTED:
        raise ValueError(f"Complaint {complaint_id} is not awaiting review")

    update_fields: Dict[str, Any] = {
        "review_action": action,
        "reviewer_id": reviewer_id,
        "reviewer_notes": reviewer_notes,
        "reviewed_at": datetime.now(tz=timezone.utc),
    }
    if action == "reject":
        update_fields["status"] = ComplaintStatus.REJECTED
        await update_complaint_fields(complaint_id, update_fields)
        await log_event(
            AuditAction.COMPLAINT_REVIEWED,
            user_id=reviewer_id,
            entity_type="complaint",
            entity_id=complaint_id,
            details={"action": "reject"},
            ip_address=ip,
        )
        return (await get_complaint(complaint_id))  # type: ignore[return-value]

    # approve or edit — resume pipeline
    text = edited_text or complaint.complaint_text
    update_fields["status"] = ComplaintStatus.PROCESSING
    if edited_text:
        update_fields["complaint_text"] = edited_text
    await update_complaint_fields(complaint_id, update_fields)

    await log_event(
        AuditAction.COMPLAINT_REVIEWED,
        user_id=reviewer_id,
        entity_type="complaint",
        entity_id=complaint_id,
        details={"action": action},
        ip_address=ip,
    )

    # Re-run from root_cause (skip intake + classifier + routing)
    await run_pipeline(complaint_id, text, complaint.state_code, user_id)

    return (await get_complaint(complaint_id))  # type: ignore[return-value]
