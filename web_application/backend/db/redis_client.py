"""
Async Redis client using redis.asyncio (redis-py v4+).
Used for: rate limiting, refresh-token blocklist, account-lockout counters,
          CSRF token store, session cache.
"""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from ..config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None  # type: ignore[type-arg]


async def connect_redis() -> None:
    global _redis
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis_pool_size,
    )
    # Verify connection
    await _redis.ping()
    logger.info("Redis connected — url=%s", settings.redis_url)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


def get_redis() -> Redis | None:  # type: ignore[type-arg]
    """Return the Redis client, or None if unavailable."""
    return _redis


def _redis_available() -> bool:
    return _redis is not None


# ── High-level helpers ───────────────────────────────────────────────────────

class RedisKeys:
    """Centralised key templates — never build keys inline."""

    @staticmethod
    def login_attempts(ip: str) -> str:
        return f"lockout:attempts:{ip}"

    @staticmethod
    def account_locked(user_id: str) -> str:
        return f"lockout:locked:{user_id}"

    @staticmethod
    def refresh_token_blocklist(token_hash: str) -> str:
        return f"token:revoked:{token_hash}"

    @staticmethod
    def csrf_token(session_id: str) -> str:
        return f"csrf:{session_id}"

    @staticmethod
    def rate_limit(key: str) -> str:
        return f"ratelimit:{key}"

    @staticmethod
    def budget_used(date_str: str) -> str:
        return f"budget:used:{date_str}"


async def increment_login_attempts(ip: str) -> int:
    if not _redis_available():
        return 0
    r = get_redis()
    key = RedisKeys.login_attempts(ip)
    count = await r.incr(key)
    if count == 1:
        # Set expiry on first write
        await r.expire(key, settings.account_lockout_minutes * 60)
    return count


async def get_login_attempts(ip: str) -> int:
    if not _redis_available():
        return 0
    r = get_redis()
    val = await r.get(RedisKeys.login_attempts(ip))
    return int(val) if val else 0


async def clear_login_attempts(ip: str) -> None:
    if not _redis_available():
        return
    await get_redis().delete(RedisKeys.login_attempts(ip))


async def set_account_locked(user_id: str) -> None:
    if not _redis_available():
        return
    r = get_redis()
    key = RedisKeys.account_locked(user_id)
    await r.setex(key, settings.account_lockout_minutes * 60, "1")


async def is_account_locked(user_id: str) -> bool:
    if not _redis_available():
        return False
    return bool(await get_redis().get(RedisKeys.account_locked(user_id)))


async def revoke_refresh_token(token_hash: str, ttl_seconds: int) -> None:
    if not _redis_available():
        return
    r = get_redis()
    key = RedisKeys.refresh_token_blocklist(token_hash)
    await r.setex(key, ttl_seconds, "1")


async def is_refresh_token_revoked(token_hash: str) -> bool:
    if not _redis_available():
        return False
    return bool(await get_redis().get(RedisKeys.refresh_token_blocklist(token_hash)))


async def set_csrf_token(session_id: str, token: str, ttl: int = 3600) -> None:
    if not _redis_available():
        return
    await get_redis().setex(RedisKeys.csrf_token(session_id), ttl, token)


async def get_csrf_token(session_id: str) -> Optional[str]:
    if not _redis_available():
        return None
    return await get_redis().get(RedisKeys.csrf_token(session_id))
