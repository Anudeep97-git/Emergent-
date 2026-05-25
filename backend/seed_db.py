"""Seed initial data: admin user + sample customer user.
Idempotent — checks existence before inserting.
Uses synchronous pymongo for lifespan startup.
"""
import uuid
import asyncio
from datetime import datetime, timezone

from services.db import sync_users as users
from services.auth_service import hash_password


SEED_USERS = [
    {
        "email": "admin@primanova.com",
        "password": "admin123",
        "full_name": "Platform Admin",
        "role": "admin",
        "is_existing_customer": True,
    },
    {
        "email": "analyst@primanova.com",
        "password": "analyst123",
        "full_name": "Risk Analyst",
        "role": "analyst",
        "is_existing_customer": True,
    },
    {
        "email": "viewer@primanova.com",
        "password": "viewer123",
        "full_name": "Read Only Viewer",
        "role": "viewer",
        "is_existing_customer": True,
    },
    {
        "email": "customer@primanova.com",
        "password": "customer123",
        "full_name": "Demo Customer (C001)",
        "role": "customer",
        "is_existing_customer": True,
        "customer_id": "C001",
    },
]


async def seed_initial():
    def _seed_sync():
        # one-time purge of legacy @c1b.com seed users
        try:
            users.delete_many({"email": {"$regex": "@c1b\\.com$"}})
        except Exception:
            pass
        for u in SEED_USERS:
            existing = users.find_one({"email": u["email"]}, {"_id": 0})
            if existing:
                continue
            doc = {
                "user_id": str(uuid.uuid4()),
                "email": u["email"],
                "password_hash": hash_password(u["password"]),
                "role": u["role"],
                "full_name": u["full_name"],
                "is_existing_customer": u.get("is_existing_customer", False),
                "customer_id": u.get("customer_id"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None,
            }
            users.insert_one(doc)

    await asyncio.to_thread(_seed_sync)
