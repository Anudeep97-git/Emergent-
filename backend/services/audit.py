"""Audit log helper — writes one row per protected API call."""
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from services.db import audit_logs


def _mask_pii(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return "***"
    name, dom = email.split("@", 1)
    return f"{name[:2]}***@{dom}"


async def log(user_id: Optional[str], email: Optional[str], endpoint: str,
              method: str, status_code: int, ip_address: str = "0.0.0.0",
              payload: Optional[Dict[str, Any]] = None):
    body = json.dumps(payload or {}, default=str)
    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]
    doc = {
        "log_id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email_masked": _mask_pii(email),
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "ip_address": ip_address,
        "payload_hash": payload_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await audit_logs.insert_one(doc)
    except Exception:
        # never break business flow on logging error
        pass
