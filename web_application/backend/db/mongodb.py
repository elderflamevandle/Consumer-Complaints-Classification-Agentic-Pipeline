"""
Async MongoDB client using Motor.
Collections are typed wrappers so every query goes through a single place.
"""

from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from ..config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_db: AsyncIOMotorDatabase | None = None    # type: ignore[type-arg]


async def connect_db() -> None:
    """Open the Motor connection pool (call at app startup)."""
    global _client, _db
    _client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5_000,
        maxPoolSize=20,
        minPoolSize=2,
    )
    _db = _client[settings.mongodb_db_name]
    await _ensure_indexes()
    logger.info("MongoDB connected — db=%s", settings.mongodb_db_name)


async def close_db() -> None:
    """Close the Motor connection pool (call at app shutdown)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    if _db is None:
        raise RuntimeError("Database not initialised — call connect_db() first")
    return _db


# ── Collection accessors ────────────────────────────────────────────────────

def users_col() -> Any:
    return get_db()["users"]


def complaints_col() -> Any:
    return get_db()["complaints"]


def audit_logs_col() -> Any:
    return get_db()["audit_logs"]


def refresh_tokens_col() -> Any:
    return get_db()["refresh_tokens"]


def pipeline_stages_col() -> Any:
    return get_db()["pipeline_stages"]


def teams_col() -> Any:
    return get_db()["teams"]


def system_logs_col() -> Any:
    return get_db()["system_logs"]


def cfpb_col() -> Any:
    """Read-only access to the existing CFPB complaints collection."""
    return get_db()[settings.cfpb_collection]


# ── Index creation ───────────────────────────────────────────────────────────

async def _ensure_indexes() -> None:
    db = get_db()

    # users
    await db["users"].create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("team_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # teams
    await db["teams"].create_indexes([
        IndexModel([("slug", ASCENDING)], unique=True),
        IndexModel([("is_active", ASCENDING)]),
        IndexModel([("issue_types", ASCENDING)]),
    ])

    # complaints
    await db["complaints"].create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("assigned_team", ASCENDING)]),
        IndexModel([("team_id", ASCENDING)]),
        IndexModel(
            [("complaint_text", "text")],
            name="complaint_text_search",
        ),
    ])

    # audit_logs — append-only; never updated or deleted
    await db["audit_logs"].create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("entity_id", ASCENDING)]),
        IndexModel([("action", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
    ])

    # refresh_tokens
    await db["refresh_tokens"].create_indexes([
        IndexModel([("token_hash", ASCENDING)], unique=True),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),  # TTL index
    ])

    # pipeline_stages
    await db["pipeline_stages"].create_indexes([
        IndexModel([("complaint_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # system_logs — written by MongoLogHandler; TTL auto-expires after 30 days
    await db["system_logs"].create_indexes([
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("level_no", ASCENDING)]),
        IndexModel([("logger", ASCENDING)]),
        IndexModel(
            [("timestamp", ASCENDING)],
            name="system_logs_ttl",
            expireAfterSeconds=30 * 24 * 3600,  # 30-day TTL
        ),
    ])

    logger.info("MongoDB indexes ensured")
