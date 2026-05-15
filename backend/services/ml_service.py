"""ML scoring service — loads LightGBM Champion, runs predict_proba + SHAP TreeExplainer."""
import json
import joblib
import numpy as np
import pandas as pd
import shap
from datetime import datetime, timezone
from typing import Dict, Any

from config import (
    MODEL_PATH, FEATURE_COLS_PATH, THRESHOLDS_PATH,
    BUSINESS_RULES, BASE_APR, MODEL_VERSION,
)


# Load model + metadata once at import time
_model = joblib.load(MODEL_PATH)
with open(FEATURE_COLS_PATH) as f:
    FEAT_COLS = json.load(f)
with open(THRESHOLDS_PATH) as f:
    _th = json.load(f)
LOW_T = _th.get("lgbm_low_upper", 0.9899)
HIGH_T = _th.get("lgbm_medium_upper", 0.9999)

# SHAP TreeExplainer on the LightGBM booster
try:
    _explainer = shap.TreeExplainer(_model)
except Exception:
    _explainer = None


def _bucket(prob: float) -> str:
    if prob < LOW_T:
        return "Low"
    if prob < HIGH_T:
        return "Medium"
    return "High"


def _align(feature_dict: Dict[str, Any]) -> pd.DataFrame:
    """Align input dict to the model's 53-feature vector. Missing -> 0 (notebook score_customer_portfolio)."""
    df = pd.DataFrame([feature_dict])
    for c in FEAT_COLS:
        if c not in df.columns:
            df[c] = 0
    return df[FEAT_COLS].fillna(0)


def shap_top5(X: pd.DataFrame) -> Dict[str, float]:
    """Top 5 SHAP features by absolute value for a single row."""
    if _explainer is None:
        return {}
    sv = _explainer.shap_values(X)
    if isinstance(sv, list):
        vals = sv[1][0] if len(sv) > 1 else sv[0][0]
    else:
        arr = np.asarray(sv)
        vals = arr[0] if arr.ndim == 2 else arr[0, :, 1] if arr.ndim == 3 else arr[0]
    importance = {FEAT_COLS[i]: float(abs(vals[i])) for i in range(len(FEAT_COLS))}
    top5 = dict(sorted(importance.items(), key=lambda x: -x[1])[:5])
    # round for transport
    return {k: round(v, 4) for k, v in top5.items()}


def predict_risk(feature_dict: Dict[str, Any], current_limit: float = 100000.0) -> Dict[str, Any]:
    X = _align(feature_dict)
    prob = float(_model.predict_proba(X.values)[0, 1])
    bucket = _bucket(prob)
    rule = BUSINESS_RULES[bucket]
    confidence = abs(prob - 0.5) * 2
    chg_pct = rule["credit_chg"] * (0.5 + 0.5 * confidence)
    recommended_limit = round(current_limit * (1 + chg_pct), 2)
    factors = shap_top5(X)
    return {
        "risk_label": bucket.upper(),
        "risk_score": round(prob, 6),
        "confidence": f"{round(confidence * 100, 2)}%",
        "contributing_factors": factors,
        "recommended_action": rule["action"],
        "recommended_apr": round(BASE_APR + rule["apr_delta"], 4),
        "credit_line_change": chg_pct,
        "current_limit": float(current_limit),
        "recommended_limit": recommended_limit,
        "model_version": MODEL_VERSION,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }


def feature_columns():
    return list(FEAT_COLS)


def thresholds():
    return {"low_upper": LOW_T, "medium_upper": HIGH_T}
