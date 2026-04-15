"""
Migrate all collections from local Docker MongoDB → Atlas.

Run via docker-compose:
    docker compose run --rm migrate

Or directly (local MongoDB must be reachable):
    ATLAS_URL=<atlas_url> python scripts/migrate_to_atlas.py
"""

from __future__ import annotations

import asyncio
import os
import sys

LOCAL_URL = os.getenv("LOCAL_MONGODB_URL", "mongodb://mongodb:27017")
ATLAS_URL = os.getenv("MONGODB_URL", "")
DB_NAME   = os.getenv("MONGODB_DB_NAME", "fincomplaint_ai")

COLLECTIONS = [
    "users",
    "teams",
    "complaints",
    "audit_logs",
    "refresh_tokens",
    "pipeline_stages",
    "system_logs",
]


async def migrate() -> None:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from pymongo import ReplaceOne
    except ImportError:
        print("ERROR: motor not installed.")
        sys.exit(1)

    if not ATLAS_URL:
        print("ERROR: MONGODB_URL (Atlas) not set.")
        sys.exit(1)

    print(f"Source : {LOCAL_URL}")
    print(f"Target : {ATLAS_URL[:40]}…")
    print(f"DB     : {DB_NAME}\n")

    src = AsyncIOMotorClient(LOCAL_URL,  serverSelectionTimeoutMS=8_000)
    dst = AsyncIOMotorClient(ATLAS_URL, serverSelectionTimeoutMS=10_000)

    await src.admin.command("ping")
    print("Local MongoDB  — connected")
    await dst.admin.command("ping")
    print("Atlas          — connected\n")

    src_db = src[DB_NAME]
    dst_db = dst[DB_NAME]
    total  = 0

    for col_name in COLLECTIONS:
        count = await src_db[col_name].count_documents({})
        if count == 0:
            print(f"  {col_name:<22} 0 docs — skip")
            continue

        docs = await src_db[col_name].find({}).to_list(length=None)
        ops  = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
        try:
            res = await dst_db[col_name].bulk_write(ops, ordered=False)
            n   = res.upserted_count + res.modified_count + res.matched_count
        except Exception as e:
            # BulkWriteError: partial success — count what got through, skip dupes
            result = getattr(e, "details", {})
            n = (result.get("nUpserted", 0) +
                 result.get("nMatched",  0) +
                 result.get("nModified", 0))
            skipped = len(result.get("writeErrors", []))
            print(f"  {col_name:<22} {n} docs copied  ({skipped} skipped — already exist)")
            total += n
            continue
        print(f"  {col_name:<22} {n} docs copied")
        total += n

    src.close()
    dst.close()
    print(f"\nDone — {total} total documents migrated to Atlas.")


if __name__ == "__main__":
    asyncio.run(migrate())
