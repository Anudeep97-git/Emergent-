"""Mongo collections helper. The PRD specifies PostgreSQL but the Emergent
runtime is MongoDB-native. We map the 6 PRD tables to Mongo collections with
the same field shapes (uuid primary keys, JSONB-style nested docs).

Collections:
  users, customers, transactions, risk_assessments, uploaded_files, audit_logs
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

_mongo_url = os.environ["MONGO_URL"]
_db_name = os.environ["DB_NAME"]

client = AsyncIOMotorClient(_mongo_url)
db = client[_db_name]

sync_client = MongoClient(_mongo_url)
sync_db = sync_client[_db_name]

users = db.users
customers = db.customers
transactions = db.transactions
risk_assessments = db.risk_assessments
uploaded_files = db.uploaded_files
audit_logs = db.audit_logs

sync_users = sync_db.users
sync_customers = sync_db.customers
sync_transactions = sync_db.transactions
sync_risk_assessments = sync_db.risk_assessments
sync_uploaded_files = sync_db.uploaded_files
sync_audit_logs = sync_db.audit_logs


def _ensure_indexes_sync():
  """Mirror PRD §4.2 indexes using sync pymongo for startup lifespans."""
  sync_users.create_index("email", unique=True)
  sync_risk_assessments.create_index("customer_id")
  sync_risk_assessments.create_index([("assessed_at", -1)])
  sync_transactions.create_index([("customer_id", 1), ("txn_date", -1)])
  sync_audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
  sync_uploaded_files.create_index([("status", 1), ("upload_timestamp", 1)])

async def ensure_indexes():
  """Mirror PRD §4.2 indexes on Mongo collections."""
  await asyncio.to_thread(_ensure_indexes_sync)
