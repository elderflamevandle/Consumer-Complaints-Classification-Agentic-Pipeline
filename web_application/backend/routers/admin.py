"""
Admin router — user management, system audit log, stats dashboard data.
All endpoints require UserRole.ADMIN.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from ..auth.dependencies import AdminUser
from ..db.mongodb import audit_logs_col, complaints_col, teams_col, users_col
from ..models.audit_log import AuditAction
from ..models.team import TeamDocument, TeamPublic
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


class AssignTeamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    team_id: Optional[str] = None   # None = remove from team


class CreateTeamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    description: str = Field(default="", max_length=500)
    issue_types: List[str] = Field(default_factory=list)
    product_types: List[str] = Field(default_factory=list)


class UpdateTeamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    issue_types: Optional[List[str]] = None
    product_types: Optional[List[str]] = None
    is_active: Optional[bool] = None


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
        {"$set": {"role": body.role, "updated_at": datetime.now(tz=timezone.utc)}},
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
        {"$set": {"is_active": False, "updated_at": datetime.now(tz=timezone.utc)}},
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
        {"$set": {"is_active": True, "updated_at": datetime.now(tz=timezone.utc)}},
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
    now = datetime.now(tz=timezone.utc)
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


# ── Team management ───────────────────────────────────────────────────────────

@router.get("/teams")
async def list_teams(
    current_user: AdminUser,
    include_inactive: bool = False,
) -> Dict[str, Any]:
    query: Dict[str, Any] = {} if include_inactive else {"is_active": True}
    cursor = teams_col().find(query).sort("name", 1)
    teams = []
    async for doc in cursor:
        team = TeamDocument.from_mongo(doc)
        member_count = await users_col().count_documents({"team_id": team.id})
        teams.append(TeamPublic(
            id=team.id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            issue_types=team.issue_types,
            product_types=team.product_types,
            is_active=team.is_active,
            member_count=member_count,
            created_at=team.created_at,
            updated_at=team.updated_at,
        ).model_dump())
    return {"items": teams, "total": len(teams)}


@router.post("/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    body: CreateTeamRequest,
    request: Request,
    current_user: AdminUser,
) -> Dict[str, Any]:
    # Enforce slug uniqueness
    existing = await teams_col().find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=409, detail=f"Team slug '{body.slug}' already exists")

    team = TeamDocument(
        name=body.name,
        slug=body.slug,
        description=body.description,
        issue_types=body.issue_types,
        product_types=body.product_types,
    )
    await teams_col().insert_one(team.to_mongo())
    await log_event(
        AuditAction.TEAM_CREATED,
        user_id=current_user.id,
        entity_type="team",
        entity_id=team.id,
        details={"name": team.name, "slug": team.slug},
        ip_address=request.client.host if request.client else None,
    )
    return {"id": team.id, "name": team.name, "slug": team.slug}


@router.patch("/teams/{team_id}")
async def update_team(
    team_id: str,
    body: UpdateTeamRequest,
    request: Request,
    current_user: AdminUser,
) -> Dict[str, Any]:
    doc = await teams_col().find_one({"_id": team_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Team not found")

    updates: Dict[str, Any] = {"updated_at": datetime.now(tz=timezone.utc)}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.issue_types is not None:
        updates["issue_types"] = body.issue_types
    if body.product_types is not None:
        updates["product_types"] = body.product_types
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    await teams_col().update_one({"_id": team_id}, {"$set": updates})

    # If team was renamed, sync team_name on all member users
    if body.name:
        await users_col().update_many(
            {"team_id": team_id},
            {"$set": {"team_name": body.name, "updated_at": datetime.now(tz=timezone.utc)}},
        )

    await log_event(
        AuditAction.TEAM_UPDATED,
        user_id=current_user.id,
        entity_type="team",
        entity_id=team_id,
        details={k: v for k, v in updates.items() if k != "updated_at"},
        ip_address=request.client.host if request.client else None,
    )
    updated = await teams_col().find_one({"_id": team_id})
    t = TeamDocument.from_mongo(updated)
    return {"id": t.id, "name": t.name, "slug": t.slug, "is_active": t.is_active}


# ── User → Team assignment ─────────────────────────────────────────────────────

@router.patch("/users/{user_id}/team")
async def assign_user_to_team(
    user_id: str,
    body: AssignTeamRequest,
    request: Request,
    current_user: AdminUser,
) -> UserPublic:
    """Assign or remove a user from a team.  Pass team_id=null to unassign."""
    user_doc = await users_col().find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    team_name: Optional[str] = None
    if body.team_id is not None:
        team_doc = await teams_col().find_one({"_id": body.team_id})
        if not team_doc:
            raise HTTPException(status_code=404, detail="Team not found")
        if not team_doc.get("is_active", True):
            raise HTTPException(status_code=400, detail="Cannot assign user to inactive team")
        team_name = team_doc["name"]

    old_team_id = user_doc.get("team_id")
    await users_col().update_one(
        {"_id": user_id},
        {"$set": {
            "team_id": body.team_id,
            "team_name": team_name,
            "updated_at": datetime.now(tz=timezone.utc),
        }},
    )
    await log_event(
        AuditAction.USER_TEAM_ASSIGNED,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        details={"old_team_id": old_team_id, "new_team_id": body.team_id, "team_name": team_name},
        ip_address=request.client.host if request.client else None,
    )
    updated = await users_col().find_one({"_id": user_id})
    u = UserDocument.from_mongo(updated)
    return UserPublic(
        id=u.id, email=u.email, full_name=u.full_name,
        role=u.role, team_id=u.team_id, team_name=u.team_name,
        is_active=u.is_active, last_login_at=u.last_login_at, created_at=u.created_at,
    )
