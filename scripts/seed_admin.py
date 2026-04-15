"""
Seed script — creates the default admin user if it doesn't already exist.
Run automatically by the mongo-seed service in docker-compose.

Usage (standalone):
    python scripts/seed_admin.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB  = os.getenv("MONGODB_DB_NAME", "fincomplaint_ai")

ADMIN_EMAIL    = os.getenv("SEED_ADMIN_EMAIL",    "admin@fincomplaint.ai")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin1234!")
ADMIN_NAME     = os.getenv("SEED_ADMIN_NAME",     "Admin User")


def _hash(password: str) -> str:
    import bcrypt  # noqa: PLC0415
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


async def seed() -> None:
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=10_000)
    db     = client[MONGODB_DB]
    users  = db["users"]

    existing = await users.find_one({"email": ADMIN_EMAIL})
    if existing:
        print(f"[seed_admin] Admin already exists — {ADMIN_EMAIL}")
        return

    doc = {
        "_id":            str(uuid4()),
        "email":          ADMIN_EMAIL,
        "password_hash":  _hash(ADMIN_PASSWORD),
        "full_name":      ADMIN_NAME,
        "role":           "admin",
        "is_active":      True,
        "failed_login_count": 0,
        "team_id":        None,
        "team_name":      None,
        "last_login_at":  None,
        "created_at":     datetime.now(tz=timezone.utc),
        "updated_at":     datetime.now(tz=timezone.utc),
    }
    await users.insert_one(doc)
    print(f"[seed_admin] Created admin — {ADMIN_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed())
