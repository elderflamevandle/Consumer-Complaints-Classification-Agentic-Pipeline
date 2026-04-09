"""
Admin router — user management, system audit log, stats dashboard data.
All endpoints require UserRole.ADMIN.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..auth.dependencies import AdminUser
from ..auth.password import hash_password, validate_password_policy
from ..db.mongodb import audit_logs_col, complaints_col, users_col
from ..models.audit_log import AuditAction
from ..models.user import UserDocument, UserPublic, UserRole
from ..services.audit_service import log_event, get_recent_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class UpdateRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: UserRole


class DeactivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Optional[str] = Field(default=None, max_length=500)


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    current_user: AdminUser,
    limit: int = 50,
    skip: int = 0,
) -> Dict[str, Any]:
    cursor = users_col().find({}).sort("created_at", -1).skip(skip).limit(min(limit, 200))
    users = []
    async for doc in cursor:
        u = UserDocument.from_mongo(doc)
        users.append(UserPublic(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role, is_active=u.is_active,
            last_login_at=u.last_login_at, created_at=u.created_at,
        ).model_dump())
    total = await users_col().count_documents({})
    return {"items": users, "total": total}


@router.patch("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    request: Request,
    current_user: AdminUser,
) -> UserPublic:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    doc = await users_col().find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = doc.get("role")
    await users_col().update_one(
        {"_id": user_id},
        {"$set": {"role": body.role, "updated_at": datetime.utcnow()}},
    )
    await log_event(
        AuditAction.USER_ROLE_CHANGED,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        details={"old_role": old_role, "new_role": body.role},
        ip_address=request.client.host if request.client else None,
    )

    updated = await users_col().find_one({"_id": user_id})
    u = UserDocument.from_mongo(updated)
    return UserPublic(
        id=u.id, email=u.email, full_name=u.full_name,
        role=u.role, is_active=u.is_active,
        last_login_at=u.last_login_at, created_at=u.created_at,
    )


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    body: DeactivateRequest,
    request: Request,
    current_user: AdminUser,
) -> Dict[str, str]:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    await users_col().update_one(
        {"_id": user_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
    )
    await log_event(
        AuditAction.USER_DEACTIVATED,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        details={"reason": body.reason},
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "User deactivated"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    request: Request,
    current_user: AdminUser,
) -> Dict[str, str]:
    await users_col().update_one(
        {"_id": user_id},
        {"$set": {"is_active": True, "updated_at": datetime.utcnow()}},
    )
    await log_event(
        AuditAction.USER_ACTIVATED,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "User activated"}


# ── System audit log ──────────────────────────────────────────────────────────

@router.get("/audit")
async def system_audit_log(
    current_user: AdminUser,
    action_filter: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
) -> Dict[str, Any]:
    events = await get_recent_events(
        limit=min(limit, 500),
        skip=skip,
        action_filter=action_filter,
    )
    return {"events": events, "total": len(events)}


# ── Dashboard stats ───────────────────────────────────────────────────────────

@router.get("/stats")
async def dashboard_stats(current_user: AdminUser) -> Dict[str, Any]:
    now = datetime.utcnow()
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    # Complaint counts by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    by_status: Dict[str, int] = {}
    async for doc in complaints_col().aggregate(pipeline):
        by_status[doc["_id"]] = doc["count"]

    # Complaints by product type
    product_pipeline = [
        {"$match": {"classification": {"$exists": True}}},
        {"$group": {"_id": "$classification.product_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    by_product: List[Dict[str, Any]] = []
    async for doc in complaints_col().aggregate(product_pipeline):
        by_product.append({"product": doc["_id"], "count": doc["count"]})

    # Complaints by severity
    severity_pipeline = [
        {"$match": {"classification": {"$exists": True}}},
        {"$group": {"_id": "$classification.severity", "count": {"$sum": 1}}},
    ]
    by_severity: Dict[str, int] = {}
    async for doc in complaints_col().aggregate(severity_pipeline):
        by_severity[doc["_id"]] = doc["count"]

    # Daily counts for last 7 days
    daily_pipeline = [
        {"$match": {"created_at": {"$gte": last_7d}}},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_counts: List[Dict[str, Any]] = []
    async for doc in complaints_col().aggregate(daily_pipeline):
        d = doc["_id"]
        daily_counts.append({
            "date": f"{d['year']}-{d['month']:02d}-{d['day']:02d}",
            "count": doc["count"],
        })

    total_complaints = await complaints_col().count_documents({})
    total_users = await users_col().count_documents({})
    recent_complaints = await complaints_col().count_documents({"created_at": {"$gte": last_7d}})
    pending = by_status.get("pending", 0) + by_status.get("processing", 0)
    interrupted = by_status.get("interrupted", 0)

    return {
        "totals": {
            "complaints": total_complaints,
            "users": total_users,
            "pending": pending,
            "interrupted_awaiting_review": interrupted,
            "last_7_days": recent_complaints,
        },
        "by_status": by_status,
        "by_product": by_product,
        "by_severity": by_severity,
        "daily_volume": daily_counts,
    }
