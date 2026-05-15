"""Data service — reads phase_outputs CSVs and exposes customer-centric lookups."""
import json
from functools import lru_cache
from typing import Dict, Any, List, Optional

import pandas as pd

from config import (
    PHASE1_CSV, PHASE3_CSV, PHASE4_BATCH_CSV, REGISTRY_PATH, RAW_TRANSACTIONS_CSV,
)


@lru_cache(maxsize=1)
def _phase1() -> pd.DataFrame:
    return pd.read_csv(PHASE1_CSV)


@lru_cache(maxsize=1)
def _phase3() -> pd.DataFrame:
    return pd.read_csv(PHASE3_CSV)


@lru_cache(maxsize=1)
def _phase4() -> pd.DataFrame:
    return pd.read_csv(PHASE4_BATCH_CSV)


@lru_cache(maxsize=1)
def _raw() -> pd.DataFrame:
    return pd.read_csv(RAW_TRANSACTIONS_CSV)


@lru_cache(maxsize=1)
def registry() -> Dict[str, Any]:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def reload_caches():
    """Force-reload all cached frames after a batch run."""
    _phase1.cache_clear()
    _phase3.cache_clear()
    _phase4.cache_clear()
    _raw.cache_clear()
    registry.cache_clear()


def get_customer_features(customer_id: str) -> Dict[str, Any]:
    df = _phase1()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def get_phase3_action(customer_id: str) -> Dict[str, Any]:
    df = _phase3()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def get_phase4_batch_result(customer_id: str) -> Dict[str, Any]:
    df = _phase4()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        return {}
    rec = row.iloc[0].to_dict()
    reg = registry()
    rec["model_version"] = reg.get("version", "v1.0.0")
    rec["batch_status"] = "COMPLETED"
    rec["notification_eligible"] = bool(rec.get("eligible_expand", 0) == 1)
    return rec


def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    """Latest row from raw transactions = customer profile snapshot."""
    raw = _raw()
    rows = raw[raw["customer_id"] == customer_id]
    if rows.empty:
        return {}
    latest = rows.sort_values("statement_month").iloc[-1].to_dict()
    return {
        "customer_id": customer_id,
        "age": int(latest.get("age", 0)),
        "income": float(latest.get("income", 0)),
        "employment_status": str(latest.get("employment_status", "")),
        "geography_region": str(latest.get("geography_region", "")),
        "credit_limit": float(latest.get("credit_limit", 0)),
        "current_balance": float(latest.get("current_balance", 0)),
        "utilization_rate": float(latest.get("utilization_rate", 0)),
        "bureau_score": int(latest.get("bureau_score", 0)),
        "onboarding_date": str(rows.sort_values("statement_month").iloc[0]["statement_month"]),
    }


def get_customer_transactions(customer_id: str, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
    raw = _raw()
    rows = raw[raw["customer_id"] == customer_id].sort_values("statement_month", ascending=False)
    start = (page - 1) * limit
    end = start + limit
    cols = ["statement_month", "purchases_amount", "cash_advances", "payment_amount",
            "interest_charged", "fees_charged", "new_balance", "utilization_rate"]
    out = rows.iloc[start:end][cols].to_dict(orient="records")
    for r in out:
        r["statement_month"] = str(r["statement_month"])
    return out


def get_spend_timeseries(customer_id: str) -> List[Dict[str, Any]]:
    raw = _raw()
    rows = raw[raw["customer_id"] == customer_id].sort_values("statement_month")
    return [
        {
            "month": str(r["statement_month"]),
            "purchases": float(r["purchases_amount"]),
            "cash_advances": float(r["cash_advances"]),
            "total_spend": float(r["purchases_amount"] + r["cash_advances"]),
        }
        for _, r in rows.iterrows()
    ]


def list_all_customers() -> List[Dict[str, Any]]:
    p3 = _phase3()
    raw = _raw()
    out = []
    for _, r in p3.iterrows():
        cid = r["customer_id"]
        latest = raw[raw["customer_id"] == cid].sort_values("statement_month").iloc[-1]
        out.append({
            "customer_id": cid,
            "full_name": f"Customer {cid}",
            "risk_label": str(r["risk_label"]),
            "risk_score": float(r["risk_score"]),
            "credit_limit": float(r["current_limit"]),
            "utilization_rate": float(latest["utilization_rate"]),
            "recommended_action": str(r["action"]),
        })
    return out


def dashboard_summary() -> Dict[str, Any]:
    p3 = _phase3()
    p4 = _phase4()
    reg = registry()
    counts = p3["risk_label"].value_counts().to_dict()
    return {
        "total_customers": int(len(p3)),
        "high_risk": int(counts.get("HIGH", 0)),
        "medium_risk": int(counts.get("MEDIUM", 0)),
        "low_risk": int(counts.get("LOW", 0)),
        "avg_risk_score": float(p3["risk_score"].mean()),
        "eligible_expand": int(p4["eligible_expand"].sum()),
        "last_batch_run": str(p4["batch_run_at"].iloc[0]) if len(p4) else "",
        "model_version": reg.get("version", "v1.0.0"),
        "roc_auc": float(reg.get("roc_auc", 0.95)),
    }


def get_credit_decision(customer_id: str) -> Dict[str, Any]:
    a = get_phase3_action(customer_id)
    if not a:
        return {}
    feats = get_customer_features(customer_id)
    from services import ml_service  # local import to avoid circular
    factors = ml_service.shap_top5(ml_service._align(feats))
    return {
        "customer_id": customer_id,
        "risk_label": str(a["risk_label"]),
        "risk_score": float(a["risk_score"]),
        "action": str(a["action"]),
        "current_limit": float(a["current_limit"]),
        "recommended_limit": float(a["recommended_limit"]),
        "current_apr": float(a["current_apr"]),
        "recommended_apr": float(a["recommended_apr"]),
        "contributing_factors": factors,
        "opportunity_score": float(a["opportunity_score"]),
        "opportunity_rank": int(a["opportunity_rank"]),
    }
