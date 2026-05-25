"""Branding service — single-document `org_settings` collection that drives
the user-facing app name, accent color, and other tenant-customisable bits.

If no doc exists, returns the Prima Nova defaults. Admin-only write.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from services.db import sync_db

org_settings = sync_db.org_settings
SETTINGS_ID = "default"

DEFAULTS: Dict[str, Any] = {
    "_id": SETTINGS_ID,
    "app_name": "Prima Nova",
    "app_tagline": "Credit Risk Console",
    "logo_initials": "PN",
    "primary_color": "#0F172A",
    "accent_color": "#6366F1",
    "success_color": "#10B981",
    "warning_color": "#F59E0B",
    "danger_color": "#F43F5E",
    "support_email": "support@primanova.com",
    "updated_at": None,
    "updated_by": None,
}

ALLOWED_FIELDS = {
    "app_name", "app_tagline", "logo_initials",
    "primary_color", "accent_color",
    "success_color", "warning_color", "danger_color",
    "support_email",
}


def get_branding() -> Dict[str, Any]:
    doc = org_settings.find_one({"_id": SETTINGS_ID}) or {}
    merged = {**DEFAULTS, **{k: v for k, v in doc.items() if v is not None}}
    merged.pop("_id", None)
    return merged


def update_branding(patch: Dict[str, Any], user_email: Optional[str] = None) -> Dict[str, Any]:
    clean = {k: v for k, v in patch.items() if k in ALLOWED_FIELDS and v is not None and str(v).strip() != ""}
    if not clean:
        return get_branding()
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    clean["updated_by"] = user_email or "system"
    org_settings.update_one(
        {"_id": SETTINGS_ID},
        {"$set": clean},
        upsert=True,
    )
    return get_branding()


def reset_branding() -> Dict[str, Any]:
    org_settings.delete_one({"_id": SETTINGS_ID})
    return get_branding()
