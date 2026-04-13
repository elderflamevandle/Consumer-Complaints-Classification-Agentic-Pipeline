"""
Audit service — thin wrapper over audit_logs_col().
NEVER calls update or delete on audit records.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..db.mongodb import audit_logs_col
from ..models.audit_log import AuditAction, AuditLogDocument


async def log_event(
    action: AuditAction,
    *,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Insert one audit record and return its ID."""
    doc = AuditLogDocument(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await audit_logs_col().insert_one(doc.to_mongo())
    return doc.id


async def get_events_for_entity(
    entity_id: str,
    *,
    limit: int = 100,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """Return audit events for a given entity (complaint, user, etc.)."""
    cursor = (
        audit_logs_col()
        .find({"entity_id": entity_id})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        results.append(doc)
    return results


async def get_recent_events(
    *,
    limit: int = 200,
    skip: int = 0,
    action_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Admin: return recent audit events across the system."""
    query: Dict[str, Any] = {}
    if action_filter:
        query["action"] = action_filter
    cursor = (
        audit_logs_col()
        .find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        results.append(doc)
    return results
