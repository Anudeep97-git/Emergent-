"""MLflow tracking + drift detection + retrain trigger (PRD §10.4).

Reads file-based MLflow store at /app/backend/mlruns/, compares latest run's
ROC-AUC against baseline. If drop > 5% → recommends/triggers retrain.
"""
import os
import sys
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import mlflow
from mlflow.tracking import MlflowClient

from config import PHASE_OUTPUTS

ROOT = Path(__file__).resolve().parent.parent
MLRUNS_DIR = ROOT / "mlruns"
LATEST_POINTER = PHASE_OUTPUTS / "mlflow_latest_run.json"
BASELINE_FILE = PHASE_OUTPUTS / "mlflow_baseline.json"
EXPERIMENT_NAME = "prima_nova_credit_risk"
DRIFT_THRESHOLD = 0.05  # PRD §10.4: retrain if AUC drops > 5%

mlflow.set_tracking_uri(f"file:{MLRUNS_DIR}")


def _client() -> MlflowClient:
    return MlflowClient(tracking_uri=f"file:{MLRUNS_DIR}")


def list_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """List MLflow runs in the prima_nova_credit_risk experiment, newest first."""
    client = _client()
    exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    if not exp:
        return []
    runs = client.search_runs([exp.experiment_id], order_by=["start_time DESC"], max_results=limit)
    out = []
    for r in runs:
        m = r.data.metrics
        t = r.data.tags
        out.append({
            "run_id": r.info.run_id,
            "status": r.info.status,
            "start_time": datetime.fromtimestamp(r.info.start_time / 1000, tz=timezone.utc).isoformat(),
            "roc_auc": float(m.get("roc_auc", 0.0)),
            "high_risk_pct": float(m.get("high_risk_pct", 0.0)),
            "medium_risk_pct": float(m.get("medium_risk_pct", 0.0)),
            "low_risk_pct": float(m.get("low_risk_pct", 0.0)),
            "model_version": t.get("model_version", "unknown"),
            "model_hash": t.get("model_hash", ""),
            "trigger": t.get("trigger", "manual"),
            "run_name": t.get("mlflow.runName", ""),
        })
    return out


def latest_run() -> Dict[str, Any]:
    if LATEST_POINTER.exists():
        with open(LATEST_POINTER) as f:
            return json.load(f)
    runs = list_runs(limit=1)
    return runs[0] if runs else {}


def baseline() -> Dict[str, Any]:
    """Returns the production baseline run (first ever pinned, or first run if none pinned)."""
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE) as f:
            return json.load(f)
    # default: oldest run = baseline
    runs = list_runs(limit=100)
    if not runs:
        return {}
    oldest = runs[-1]
    pin_baseline(oldest["run_id"])
    return baseline()


def pin_baseline(run_id: str) -> Dict[str, Any]:
    """Pin a specific run as the production baseline."""
    client = _client()
    r = client.get_run(run_id)
    doc = {
        "run_id": run_id,
        "roc_auc": float(r.data.metrics.get("roc_auc", 0.0)),
        "model_version": r.data.tags.get("model_version", "unknown"),
        "model_hash": r.data.tags.get("model_hash", ""),
        "pinned_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(BASELINE_FILE, "w") as f:
        json.dump(doc, f, indent=2)
    return doc


def drift_check() -> Dict[str, Any]:
    """Compare latest run's AUC vs baseline. Returns drift status + recommendation."""
    base = baseline()
    latest = latest_run()
    if not base or not latest:
        return {
            "status": "INSUFFICIENT_DATA",
            "drift_detected": False,
            "baseline_auc": 0.0,
            "current_auc": 0.0,
            "auc_drop": 0.0,
            "threshold": DRIFT_THRESHOLD,
            "recommend_retrain": False,
            "message": "Not enough MLflow runs to assess drift.",
        }
    base_auc = float(base.get("roc_auc", 0.0))
    cur_auc = float(latest.get("roc_auc", 0.0))
    drop = base_auc - cur_auc
    drift = drop > DRIFT_THRESHOLD
    return {
        "status": "DRIFT" if drift else "STABLE",
        "drift_detected": drift,
        "baseline_auc": base_auc,
        "baseline_run_id": base.get("run_id"),
        "current_auc": cur_auc,
        "current_run_id": latest.get("run_id"),
        "auc_drop": round(drop, 4),
        "threshold": DRIFT_THRESHOLD,
        "recommend_retrain": drift,
        "message": (
            f"AUC dropped {drop*100:.2f}% from baseline ({base_auc:.4f} → {cur_auc:.4f}) — retrain recommended."
            if drift else
            f"Model AUC stable ({cur_auc:.4f}) vs baseline ({base_auc:.4f})."
        ),
    }


# ---------- Retrain orchestration ----------
_retrain_lock = threading.Lock()
_retrain_state: Dict[str, Any] = {"running": False, "last_status": None, "last_message": None, "last_finished": None}


def retrain_status() -> Dict[str, Any]:
    return dict(_retrain_state)


def _run_retrain_subprocess(trigger: str):
    script = ROOT / "ml" / "build_artifacts.py"
    env = os.environ.copy()
    env["RETRAIN_TRIGGER"] = trigger
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180,
        )
        ok = proc.returncode == 0
        _retrain_state["last_status"] = "SUCCESS" if ok else "FAILED"
        _retrain_state["last_message"] = (proc.stdout[-400:] if ok else proc.stderr[-400:]).strip()
    except Exception as e:
        _retrain_state["last_status"] = "FAILED"
        _retrain_state["last_message"] = f"{type(e).__name__}: {e}"
    finally:
        _retrain_state["running"] = False
        _retrain_state["last_finished"] = datetime.now(timezone.utc).isoformat()
        # Force ml_service to reload the model on next request
        try:
            from services import data_service
            data_service.reload_caches()
        except Exception:
            pass


def trigger_retrain(trigger: str = "manual") -> Dict[str, Any]:
    """Kick off a retrain in a background thread. Returns immediately."""
    with _retrain_lock:
        if _retrain_state["running"]:
            return {"accepted": False, "message": "Retrain already in progress", **_retrain_state}
        _retrain_state["running"] = True
        _retrain_state["last_status"] = "RUNNING"
        _retrain_state["last_message"] = f"Triggered ({trigger})"
        _retrain_state["last_finished"] = None
    t = threading.Thread(target=_run_retrain_subprocess, args=(trigger,), daemon=True)
    t.start()
    return {"accepted": True, "message": "Retrain started in background", **_retrain_state}


def auto_check_and_retrain() -> Dict[str, Any]:
    """Run drift check; if drift detected and not already retraining, kick off retrain."""
    chk = drift_check()
    if chk.get("recommend_retrain") and not _retrain_state["running"]:
        rt = trigger_retrain(trigger="auto_drift")
        chk["retrain_triggered"] = rt["accepted"]
    else:
        chk["retrain_triggered"] = False
    return chk
