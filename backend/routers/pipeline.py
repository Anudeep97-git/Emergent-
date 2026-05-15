"""Pipeline router — Phase 1/2/3/4 endpoints (ingest, validate, features, score, batch)."""
import os
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request

from models.schemas import (
    IngestResponse, ValidationResult, FeatureVectorResponse,
    ScoreRequest, ScoreResponse, BatchRunResponse,
)
from services.auth_service import get_current_user
from services import ml_service, data_service
from services.db import uploaded_files, risk_assessments
from services.audit import log
from config import MODEL_VERSION, PHASE_OUTPUTS

router = APIRouter()

UPLOAD_DIR = PHASE_OUTPUTS / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".csv", ".xlsx", ".json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

REQUIRED_COLUMNS = [
    "customer_id", "statement_month", "previous_balance", "payment_amount",
    "purchases_amount", "cash_advances", "interest_charged", "fees_charged",
    "new_balance", "credit_limit", "current_balance", "utilization_rate",
    "delinquency_status", "days_past_due", "bureau_score", "age", "income",
    "geography_region", "employment_status", "default_flag",
]


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), request: Request = None,
                 user=Depends(get_current_user)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension {ext}. Allowed: .csv .xlsx .json")

    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}{ext}"
    dest = UPLOAD_DIR / safe_name
    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File exceeds 50MB limit")
            out.write(chunk)

    # detect rows
    try:
        if ext == ".csv":
            df = pd.read_csv(dest)
        elif ext == ".xlsx":
            df = pd.read_excel(dest)
        else:
            df = pd.read_json(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Cannot parse file: {e}")

    doc = {
        "file_id": file_id,
        "customer_id": None,
        "filename": file.filename,
        "file_path": str(dest),
        "status": "pending",
        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        "rows_detected": int(len(df)),
        "columns_detected": list(map(str, df.columns)),
        "uploaded_by": user["user_id"],
    }
    await uploaded_files.insert_one(doc)
    if request:
        await log(user["user_id"], user["email"], "/api/pipeline/ingest", "POST", 200,
                  request.client.host if request.client else "0.0.0.0", {"file_id": file_id})

    return IngestResponse(
        file_id=file_id,
        status="pending",
        rows_detected=int(len(df)),
        columns_detected=list(map(str, df.columns)),
        message="File ingested. Run /pipeline/validate next.",
    )


@router.post("/validate", response_model=ValidationResult)
async def validate(file_id: str, user=Depends(get_current_user)):
    doc = await uploaded_files.find_one({"file_id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="file_id not found")
    path = doc["file_path"]
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext == ".xlsx":
        df = pd.read_excel(path)
    else:
        df = pd.read_json(path)

    errors, warnings, checks = [], [], {}
    for col in REQUIRED_COLUMNS:
        present = col in df.columns
        checks[col] = present
        if not present:
            errors.append(f"Missing required column: {col}")

    # null checks
    for col in df.columns:
        nulls = int(df[col].isna().sum())
        if nulls > 0:
            warnings.append(f"{col}: {nulls} null values")

    status = "validated" if not errors else "failed"
    await uploaded_files.update_one({"file_id": file_id}, {"$set": {"status": status}})

    return ValidationResult(
        is_valid=not errors,
        errors=errors,
        warnings=warnings,
        column_checks=checks,
    )


@router.post("/features", response_model=FeatureVectorResponse)
async def features(customer_id: str, user=Depends(get_current_user)):
    feats = data_service.get_customer_features(customer_id)
    if not feats:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not in Phase 1 output")
    cols = ml_service.feature_columns()
    numeric_feats = {c: float(feats.get(c, 0) or 0) for c in cols}
    return FeatureVectorResponse(
        customer_id=customer_id,
        features=numeric_feats,
        n_features=len(cols),
    )


@router.post("/score", response_model=ScoreResponse)
async def score(req: ScoreRequest, request: Request, user=Depends(get_current_user)):
    feats = req.feature_vector
    if not feats:
        feats = data_service.get_customer_features(req.customer_id)
    if not feats:
        raise HTTPException(status_code=404, detail=f"No feature vector for {req.customer_id}")
    current_limit = float(feats.get("credit_limit", 100000))
    out = ml_service.predict_risk(feats, current_limit=current_limit)

    # persist to risk_assessments
    doc = {
        "assessment_id": str(uuid.uuid4()),
        "customer_id": req.customer_id,
        "risk_label": out["risk_label"],
        "risk_score": out["risk_score"],
        "confidence": out["confidence"],
        "shap_factors": out["contributing_factors"],
        "model_version": out["model_version"],
        "recommended_action": out["recommended_action"],
        "recommended_apr": out["recommended_apr"],
        "credit_line_chg": out["credit_line_change"],
        "current_limit": out["current_limit"],
        "recommended_limit": out["recommended_limit"],
        "assessed_at": out["assessed_at"],
    }
    await risk_assessments.insert_one(doc)
    await log(user["user_id"], user["email"], "/api/pipeline/score", "POST", 200,
              request.client.host if request.client else "0.0.0.0", {"customer_id": req.customer_id})

    return ScoreResponse(customer_id=req.customer_id, **out)


@router.post("/batch", response_model=BatchRunResponse)
async def batch(user=Depends(get_current_user)):
    """Phase 4 — re-score all 100 customers from phase1_ready_for_phase2.csv."""
    df = pd.read_csv(__import__("config").PHASE1_CSV)
    high = med = low = exp = 0
    batch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    for _, r in df.iterrows():
        feats = r.to_dict()
        cl = float(feats.get("credit_limit", 100000))
        out = ml_service.predict_risk(feats, current_limit=cl)
        label = out["risk_label"]
        if label == "HIGH": high += 1
        elif label == "MEDIUM": med += 1
        else:
            low += 1
            exp += 1
        await risk_assessments.insert_one({
            "assessment_id": str(uuid.uuid4()),
            "customer_id": r["customer_id"],
            "risk_label": label,
            "risk_score": out["risk_score"],
            "confidence": out["confidence"],
            "shap_factors": out["contributing_factors"],
            "model_version": MODEL_VERSION,
            "recommended_action": out["recommended_action"],
            "recommended_apr": out["recommended_apr"],
            "credit_line_chg": out["credit_line_change"],
            "current_limit": out["current_limit"],
            "recommended_limit": out["recommended_limit"],
            "batch_id": batch_id,
            "assessed_at": now,
        })
    return BatchRunResponse(
        batch_id=batch_id,
        customers_scored=int(len(df)),
        eligible_expand=exp,
        high_risk=high,
        medium_risk=med,
        low_risk=low,
        completed_at=now,
    )
