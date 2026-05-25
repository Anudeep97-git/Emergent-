"""Customer router — profile, transactions, risk history, full report, all-customers list."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from models.schemas import (
    CustomerProfile, RiskHistoryEntry,
    CustomerSummary, FullReport, CreditDecision,
)
from services.auth_service import get_current_user
from services import data_service
from services.db import risk_assessments

router = APIRouter()


@router.get("/all", response_model=List[CustomerSummary])
async def all_customers(user=Depends(get_current_user)):
    return data_service.list_all_customers()


@router.get("/profile/{customer_id}", response_model=CustomerProfile)
async def profile(customer_id: str, user=Depends(get_current_user)):
    p = data_service.get_customer_profile(customer_id)
    if not p:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerProfile(full_name=f"Customer {customer_id}", **p)


@router.get("/transactions/{customer_id}")
async def transactions(
    customer_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tx_type: str = Query("all", description="Filter: all | Purchase | Payment | Fee | Credit | Cash Advance"),
    q: str = Query("", description="Free-text search across description"),
    user=Depends(get_current_user),
):
    return data_service.get_customer_transactions(customer_id, page, limit, tx_type=tx_type, query=q)


@router.get("/transactions/{customer_id}/types")
async def transaction_types(customer_id: str, user=Depends(get_current_user)):
    """Distinct transaction types for the type-filter dropdown + total count."""
    return data_service.get_customer_transaction_types(customer_id)


@router.get("/risk-history/{customer_id}", response_model=List[RiskHistoryEntry])
async def risk_history(customer_id: str, user=Depends(get_current_user)):
    cur = risk_assessments.find({"customer_id": customer_id}, {"_id": 0}).sort("assessed_at", -1).limit(50)
    out = []
    async for d in cur:
        out.append(RiskHistoryEntry(
            assessed_at=d.get("assessed_at", ""),
            risk_label=d.get("risk_label", ""),
            risk_score=float(d.get("risk_score", 0)),
            model_version=d.get("model_version", "v1.0.0"),
        ))
    return out


@router.get("/spend-chart/{customer_id}")
async def spend_chart(customer_id: str, user=Depends(get_current_user)):
    return data_service.get_spend_timeseries(customer_id)


@router.get("/decision/{customer_id}", response_model=CreditDecision)
async def decision(customer_id: str, user=Depends(get_current_user)):
    d = data_service.get_credit_decision(customer_id)
    if not d:
        raise HTTPException(status_code=404, detail="No decision for customer")
    return CreditDecision(**d)


@router.get("/full-report/{customer_id}", response_model=FullReport)
async def full_report(customer_id: str, user=Depends(get_current_user)):
    profile = data_service.get_customer_profile(customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found")
    feats = data_service.get_customer_features(customer_id)
    decision = data_service.get_credit_decision(customer_id)
    batch = data_service.get_phase4_batch_result(customer_id)

    # Drop non-numeric keys for phase1_features
    phase1_feats = {}
    for k, v in feats.items():
        if k in ("customer_id", "statement_month"):
            continue
        try:
            phase1_feats[k] = float(v)
        except (TypeError, ValueError):
            continue

    return FullReport(
        profile=CustomerProfile(full_name=f"Customer {customer_id}", **profile),
        phase1_features=phase1_feats,
        phase2_risk={
            "risk_label": decision["risk_label"],
            "risk_score": decision["risk_score"],
            "contributing_factors": decision["contributing_factors"],
        },
        phase3_decision=CreditDecision(**decision),
        phase4_batch_status={
            "eligible_expand": bool(batch.get("eligible_expand", 0)),
            "batch_run_at": str(batch.get("batch_run_at", "")),
            "notification_eligible": bool(batch.get("notification_eligible", False)),
        },
    )
