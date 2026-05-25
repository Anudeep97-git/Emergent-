"""Platform configuration & metadata for C1B Credit Risk Assessment Platform."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PHASE_OUTPUTS = ROOT_DIR / "phase_outputs"

PLATFORM = {
    "name": "Prima Nova",
    "version": "v1.0.0",
    "model_engine": "Predictive Model",
    "architecture": "Full-Stack · Agent-Driven · API-First",
    "target_org": "Credit Risk Console",
}

SUCCESS_METRICS = {
    "roc_auc_target": 0.95,
    "api_p95_ms": 300,
    "dashboard_load_s": 2,
    "risk_accuracy_pct": 95,
    "batch_sla": "06:00 nightly",
}

MODEL_PATH = str(PHASE_OUTPUTS / "phase4_outputs" / "phase4_champion_model.pkl")
XGB_MODEL_PATH = str(PHASE_OUTPUTS / "phase2_models" / "xgboost_model.pkl")
FEATURE_COLS_PATH = str(PHASE_OUTPUTS / "phase2_models" / "feature_columns.json")
THRESHOLDS_PATH = str(PHASE_OUTPUTS / "phase2_models" / "bucket_thresholds_v2.json")
REGISTRY_PATH = str(PHASE_OUTPUTS / "phase4_outputs" / "model_registry.json")
PHASE1_CSV = str(PHASE_OUTPUTS / "phase1_ready_for_phase2.csv")
PHASE3_CSV = str(PHASE_OUTPUTS / "phase3_customer_action_plan.csv")
PHASE4_BATCH_CSV = str(PHASE_OUTPUTS / "phase4_outputs" / "batch_scored_customers.csv")
RAW_TRANSACTIONS_CSV = str(PHASE_OUTPUTS / "raw_transactions.csv")

JWT_SECRET = os.environ.get("JWT_SECRET", "c1b_super_secret_key_change_in_prod_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

BASE_APR = 0.18

BUSINESS_RULES = {
    "Low":    {"action": "EXPAND",   "credit_chg": 0.15,  "apr_delta": -0.02},
    "Medium": {"action": "MONITOR",  "credit_chg": 0.00,  "apr_delta":  0.00},
    "High":   {"action": "RESTRICT", "credit_chg": -0.20, "apr_delta":  0.03},
}

MODEL_VERSION = "v1.0.0"
