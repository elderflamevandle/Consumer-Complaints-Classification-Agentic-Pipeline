"""
Migrate all collections from MongoDB Atlas → local MongoDB.

Usage (run from project root, local MongoDB must be running):
  docker compose up -d mongodb
  python scripts/migrate_atlas_to_local.py

The script connects to both databases, copies every document from every
collection in Atlas that has data, and upserts into the local instance.
Existing documents in local are overwritten by _id match (safe to re-run).
"""

import asyncio
import sys

ATLAS_URL  = "mongodb+srv://knimbalk_db_user:Xw8rLGNq2aqpk46C@umd.mcnucik.mongodb.net"
LOCAL_URL  = "mongodb://localhost:27017"
DB_NAME    = "fincomplaint_ai"

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
    except ImportError:
        print("ERROR: motor not installed. Run:  pip install motor")
        sys.exit(1)

    print(f"Connecting to Atlas …")
    src_client = AsyncIOMotorClient(ATLAS_URL, serverSelectionTimeoutMS=10_000)
    src_db = src_client[DB_NAME]

    print(f"Connecting to local MongoDB ({LOCAL_URL}) …")
    dst_client = AsyncIOMotorClient(LOCAL_URL, serverSelectionTimeoutMS=5_000)
    dst_db = dst_client[DB_NAME]

    # Verify both connections
    await src_client.admin.command("ping")
    print("  Atlas OK")
    await dst_client.admin.command("ping")
    print("  Local OK\n")

    total_copied = 0

    for col_name in COLLECTIONS:
        src_col = src_db[col_name]
        dst_col = dst_db[col_name]

        count = await src_col.count_documents({})
        if count == 0:
            print(f"  {col_name:<20} — 0 documents, skipping")
            continue

        print(f"  {col_name:<20} — {count} documents …", end=" ", flush=True)

        docs = await src_col.find({}).to_list(length=None)
        if not docs:
            print("done (empty cursor)")
            continue

        # Upsert each document by _id so re-runs are safe
        from pymongo import ReplaceOne
        ops = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
        result = await dst_col.bulk_write(ops, ordered=False)
        copied = result.upserted_count + result.modified_count + result.matched_count
        print(f"copied {copied}")
        total_copied += copied

    src_client.close()
    dst_client.close()

    print(f"\nDone — {total_copied} documents migrated to local MongoDB.")


if __name__ == "__main__":
    asyncio.run(migrate())
