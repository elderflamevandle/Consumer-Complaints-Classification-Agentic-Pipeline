"""
Seed default CFPB complaint-routing teams into MongoDB.
Safe to re-run — skips teams whose slug already exists.

Usage (from project root):
    python scripts/seed_teams.py
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

DEFAULT_TEAMS = [
    {
        "name":          "Checking and Savings Account",
        "slug":          "checking-savings-account",
        "description":   "Handles complaints related to checking accounts, savings accounts, and banking fees.",
        "issue_types":   ["BILLING", "PAYMENT"],
        "product_types": ["CHECKING_SAVINGS_ACCOUNT"],
    },
    {
        "name":          "Credit Card",
        "slug":          "credit-card",
        "description":   "Manages credit card disputes, billing errors, interest charges, and unauthorized transactions.",
        "issue_types":   ["BILLING", "FRAUD"],
        "product_types": ["CREDIT_CARD"],
    },
    {
        "name":          "Credit Reporting",
        "slug":          "credit-reporting",
        "description":   "Resolves inaccurate credit report entries, identity theft on credit files, and bureau disputes.",
        "issue_types":   ["CREDIT_REPORTING", "IDENTITY_THEFT"],
        "product_types": ["CREDIT_REPORTING"],
    },
    {
        "name":          "Debt Collection",
        "slug":          "debt-collection",
        "description":   "Addresses improper debt collection practices, harassment, and disputed debt validity.",
        "issue_types":   ["CUSTOMER_SERVICE"],
        "product_types": ["DEBT_COLLECTION"],
    },
    {
        "name":          "Money Transfer",
        "slug":          "money-transfer",
        "description":   "Investigates failed or fraudulent money transfers, wire issues, and prepaid card problems.",
        "issue_types":   ["PAYMENT", "FRAUD"],
        "product_types": ["MONEY_TRANSFER"],
    },
    {
        "name":          "Mortgage",
        "slug":          "mortgage",
        "description":   "Handles mortgage servicing complaints, foreclosure concerns, and loan modification issues.",
        "issue_types":   ["BILLING", "PAYMENT"],
        "product_types": ["MORTGAGE"],
    },
    {
        "name":          "Vehicle Loan & Lease",
        "slug":          "vehicle-loan-lease",
        "description":   "Manages auto loan billing disputes, repossession issues, and dealer financing complaints.",
        "issue_types":   ["BILLING", "PAYMENT"],
        "product_types": ["VEHICLE_LOAN_LEASE"],
    },
    {
        "name":          "Fraud & Security",
        "slug":          "fraud-security",
        "description":   "Investigates account fraud, identity theft, and unauthorized access across all product types.",
        "issue_types":   ["FRAUD", "IDENTITY_THEFT"],
        "product_types": [],
    },
]


async def seed() -> None:
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=10_000)
    db     = client[MONGODB_DB]
    col    = db["teams"]

    now = datetime.now(tz=timezone.utc)
    created = 0
    skipped = 0

    for team in DEFAULT_TEAMS:
        existing = await col.find_one({"slug": team["slug"]})
        if existing:
            print(f"  skip   {team['slug']}")
            skipped += 1
            continue

        doc = {
            "_id":          str(uuid4()),
            "name":         team["name"],
            "slug":         team["slug"],
            "description":  team["description"],
            "issue_types":  team["issue_types"],
            "product_types": team["product_types"],
            "is_active":    True,
            "created_at":   now,
            "updated_at":   now,
        }
        await col.insert_one(doc)
        print(f"  create {team['slug']}  →  {team['name']}")
        created += 1

    client.close()
    print(f"\nDone — {created} created, {skipped} already existed.")


if __name__ == "__main__":
    # Load .env if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    asyncio.run(seed())
