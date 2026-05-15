"""Mongo collections helper. The PRD specifies PostgreSQL but the Emergent
runtime is MongoDB-native. We map the 6 PRD tables to Mongo collections with
the same field shapes (uuid primary keys, JSONB-style nested docs).

Collections:
  users, customers, transactions, risk_assessments, uploaded_files, audit_logs
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient

_mongo_url = os.environ["MONGO_URL"]
_db_name = os.environ["DB_NAME"]

client = AsyncIOMotorClient(_mongo_url)
db = client[_db_name]

users = db.users
customers = db.customers
transactions = db.transactions
risk_assessments = db.risk_assessments
uploaded_files = db.uploaded_files
audit_logs = db.audit_logs


async def ensure_indexes():
    """Mirror PRD §4.2 indexes on Mongo collections."""
    await users.create_index("email", unique=True)
    await risk_assessments.create_index("customer_id")
    await risk_assessments.create_index([("assessed_at", -1)])
    await transactions.create_index([("customer_id", 1), ("txn_date", -1)])
    await audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
    await uploaded_files.create_index([("status", 1), ("upload_timestamp", 1)])
