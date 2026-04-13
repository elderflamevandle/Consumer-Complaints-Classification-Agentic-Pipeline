"""
Teams router — endpoints for team members to view their own team context.

These are NOT admin-only endpoints.  Any authenticated analyst or viewer can
call /api/teams/me to see their team information.
Admin-level team CRUD lives in routers/admin.py.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from ..auth.dependencies import AnalystUser, CurrentUser
from ..db.mongodb import complaints_col, teams_col, users_col
from ..models.team import TeamDocument, TeamPublic
from ..models.user import UserDocument, UserPublic, UserRole
from ..services import complaint_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["teams"])


# ── My team ────────────────────────────────────────────────────────────────────

@router.get("/me")
async def get_my_team(current_user: CurrentUser) -> Dict[str, Any]:
    """
    Return the authenticated user's team info + member list.
    Returns 404 if the user is not assigned to any team.
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=404,
            detail="You are not assigned to a team. Contact an admin.",
        )

    team_doc = await teams_col().find_one({"_id": current_user.team_id})
    if not team_doc:
        raise HTTPException(status_code=404, detail="Team not found")

    team = TeamDocument.from_mongo(team_doc)

    # Fetch members
    cursor = users_col().find({"team_id": team.id})
    members = []
    async for raw in cursor:
        u = UserDocument.from_mongo(raw)
        members.append(UserPublic(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role, team_id=u.team_id, team_name=u.team_name,
            is_active=u.is_active, last_login_at=u.last_login_at,
            created_at=u.created_at,
        ).model_dump())

    return {
        "team": TeamPublic(
            id=team.id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            issue_types=team.issue_types,
            product_types=team.product_types,
            is_active=team.is_active,
            member_count=len(members),
            created_at=team.created_at,
            updated_at=team.updated_at,
        ).model_dump(),
        "members": members,
    }


@router.get("/me/complaints")
async def get_my_team_complaints(
    current_user: AnalystUser,
    status_filter: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> Dict[str, Any]:
    """
    List all complaints assigned to the current user's team.
    Admins should use GET /api/complaints (which already has no filter).
    """
    if current_user.role == UserRole.ADMIN:
        # Admins can use this endpoint too — they see all
        complaints = await complaint_service.list_complaints(
            status=status_filter, limit=min(limit, 100), skip=skip
        )
        total = await complaint_service.count_complaints(status=status_filter)
    elif not current_user.team_id:
        raise HTTPException(
            status_code=404,
            detail="You are not assigned to a team.",
        )
    else:
        complaints = await complaint_service.list_complaints(
            team_id=current_user.team_id,
            status=status_filter,
            limit=min(limit, 100),
            skip=skip,
        )
        total = await complaint_service.count_complaints(
            team_id=current_user.team_id, status=status_filter
        )

    from ..routers.complaints import _serialize_complaint
    return {
        "items": [_serialize_complaint(c) for c in complaints],
        "total": total,
        "limit": limit,
        "skip": skip,
        "team_id": current_user.team_id,
        "team_name": current_user.team_name,
    }


@router.get("/me/members")
async def get_my_team_members(current_user: CurrentUser) -> Dict[str, Any]:
    """
    Return the list of users on the current user's team.
    Useful for complaint assignment dropdowns.
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=404,
            detail="You are not assigned to a team.",
        )

    cursor = users_col().find({"team_id": current_user.team_id, "is_active": True})
    members = []
    async for raw in cursor:
        u = UserDocument.from_mongo(raw)
        members.append(UserPublic(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role, team_id=u.team_id, team_name=u.team_name,
            is_active=u.is_active, last_login_at=u.last_login_at,
            created_at=u.created_at,
        ).model_dump())

    return {"members": members, "total": len(members)}
