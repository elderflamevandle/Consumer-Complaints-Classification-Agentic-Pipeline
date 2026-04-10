"""
Complaint router — CRUD + pipeline trigger + WebSocket live stream.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import bleach
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..auth.dependencies import AnalystUser, CurrentUser
from ..models.audit_log import AuditAction
from ..models.complaint import ComplaintStatus
from ..models.user import UserRole
from ..services import audit_service, complaint_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["complaints"])

# ── Request/Response schemas ──────────────────────────────────────────────────

class SubmitComplaintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_text: str = Field(min_length=20, max_length=10_000)
    state_code: str = Field(default="CA", min_length=2, max_length=2, pattern="^[A-Z]{2}$")

    @field_validator("complaint_text")
    @classmethod
    def _strip(cls, v: str) -> str:
        return bleach.clean(v, tags=[], strip=True).strip()


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(pattern="^(approve|edit|reject)$")
    reviewer_notes: Optional[str] = Field(default=None, max_length=2_000)
    edited_text: Optional[str] = Field(default=None, min_length=20, max_length=10_000)


class AssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_team: str = Field(min_length=1, max_length=200)


def _serialize_complaint(c: Any) -> Dict[str, Any]:
    """Convert ComplaintDocument to API-safe dict (never exposes complaint_text raw)."""
    d = c.model_dump()
    d["id"] = d.pop("_id", d.get("id", ""))
    # Expose scrubbed text to API; keep original PII-containing text server-side only
    d.pop("complaint_text", None)
    return d


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    body: SubmitComplaintRequest,
    request: Request,
    current_user: AnalystUser,
) -> Dict[str, Any]:
    ip = request.client.host if request.client else None

    complaint = await complaint_service.create_complaint(
        user_id=current_user.id,
        complaint_text=body.complaint_text,
        state_code=body.state_code,
        ip=ip,
    )

    # Fire-and-forget pipeline
    asyncio.create_task(
        complaint_service.run_pipeline(
            complaint_id=complaint.id,
            complaint_text=body.complaint_text,
            state_code=body.state_code,
            user_id=current_user.id,
        )
    )

    return {
        "id": complaint.id,
        "status": complaint.status,
        "created_at": complaint.created_at.isoformat(),
        "websocket_url": f"/ws/complaints/{complaint.id}",
    }


@router.get("")
async def list_complaints(
    current_user: CurrentUser,
    status_filter: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> Dict[str, Any]:
    """
    Access control:
      - Admin   → no filter, sees all complaints
      - Analyst → sees complaints in their team OR submitted by themselves
      - Viewer  → sees only complaints they submitted
    """
    uid: Optional[str] = None
    tid: Optional[str] = None

    if current_user.role == UserRole.ADMIN:
        pass  # no filter
    elif current_user.role == UserRole.ANALYST:
        uid = current_user.id
        tid = current_user.team_id  # May be None if analyst is unassigned
    else:
        uid = current_user.id  # Viewer: own only

    complaints = await complaint_service.list_complaints(
        user_id=uid,
        team_id=tid,
        status=status_filter,
        limit=min(limit, 100),
        skip=skip,
    )
    total = await complaint_service.count_complaints(
        user_id=uid, team_id=tid, status=status_filter
    )

    return {
        "items": [_serialize_complaint(c) for c in complaints],
        "total": total,
        "limit": limit,
        "skip": skip,
    }


@router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: str,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    complaint = await complaint_service.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Access rules:
    #   Admin   → always allowed
    #   Analyst → allowed if they submitted it OR it belongs to their team
    #   Viewer  → allowed only if they submitted it
    is_owner = complaint.user_id == current_user.id
    is_team_member = (
        current_user.role == UserRole.ANALYST
        and current_user.team_id is not None
        and complaint.team_id == current_user.team_id
    )
    if current_user.role != UserRole.ADMIN and not is_owner and not is_team_member:
        raise HTTPException(status_code=403, detail="Access denied")

    stages = await complaint_service.get_pipeline_stages(complaint_id)
    result = _serialize_complaint(complaint)
    result["pipeline_stages"] = stages
    return result


@router.post("/{complaint_id}/review")
async def submit_review(
    complaint_id: str,
    body: ReviewRequest,
    request: Request,
    current_user: AnalystUser,
) -> Dict[str, Any]:
    complaint = await complaint_service.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.status != ComplaintStatus.INTERRUPTED:
        raise HTTPException(status_code=409, detail="Complaint is not awaiting review")

    updated = await complaint_service.resume_pipeline_after_review(
        complaint_id=complaint_id,
        action=body.action,
        reviewer_id=current_user.id,
        reviewer_notes=body.reviewer_notes,
        edited_text=body.edited_text,
        user_id=current_user.id,
        ip=request.client.host if request.client else None,
    )
    return _serialize_complaint(updated)


@router.post("/{complaint_id}/assign")
async def assign_complaint(
    complaint_id: str,
    body: AssignRequest,
    request: Request,
    current_user: AnalystUser,
) -> Dict[str, Any]:
    complaint = await complaint_service.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    await complaint_service.update_complaint_fields(
        complaint_id, {"assigned_team": body.assigned_team}
    )
    await audit_service.log_event(
        AuditAction.COMPLAINT_ASSIGNED,
        user_id=current_user.id,
        entity_type="complaint",
        entity_id=complaint_id,
        details={"assigned_team": body.assigned_team},
        ip_address=request.client.host if request.client else None,
    )
    complaint = await complaint_service.get_complaint(complaint_id)
    return _serialize_complaint(complaint)


@router.get("/{complaint_id}/audit")
async def get_audit_trail(
    complaint_id: str,
    current_user: CurrentUser,
    limit: int = 100,
    skip: int = 0,
) -> Dict[str, Any]:
    complaint = await complaint_service.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    is_owner = complaint.user_id == current_user.id
    is_team_member = (
        current_user.role == UserRole.ANALYST
        and current_user.team_id is not None
        and complaint.team_id == current_user.team_id
    )
    if current_user.role != UserRole.ADMIN and not is_owner and not is_team_member:
        raise HTTPException(status_code=403, detail="Access denied")

    events = await audit_service.get_events_for_entity(
        complaint_id, limit=limit, skip=skip
    )
    return {"complaint_id": complaint_id, "events": events, "total": len(events)}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/{complaint_id}")
async def complaint_websocket(websocket: WebSocket, complaint_id: str):
    await websocket.accept()
    logger.info("WS connected for complaint %s", complaint_id)

    try:
        # Wait up to 2 s for the pipeline queue to appear
        queue = None
        for _ in range(20):
            queue = complaint_service.get_pipeline_queue(complaint_id)
            if queue is not None:
                break
            await asyncio.sleep(0.1)

        if queue is None:
            # Pipeline may already be done; send current state and close
            complaint = await complaint_service.get_complaint(complaint_id)
            if complaint:
                stages = await complaint_service.get_pipeline_stages(complaint_id)
                await websocket.send_json({
                    "type": "current_state",
                    "complaint": _serialize_complaint(complaint),
                    "stages": stages,
                })
            await websocket.close()
            return

        # Stream updates until pipeline signals done
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=120.0)
                await websocket.send_json(update)
                if update.get("type") == "pipeline_done":
                    # Send final complaint state
                    complaint = await complaint_service.get_complaint(complaint_id)
                    if complaint:
                        stages = await complaint_service.get_pipeline_stages(complaint_id)
                        await websocket.send_json({
                            "type": "final_state",
                            "complaint": _serialize_complaint(complaint),
                            "stages": stages,
                        })
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        logger.info("WS disconnected for complaint %s", complaint_id)
    except Exception as exc:
        logger.exception("WS error for complaint %s: %s", complaint_id, exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
