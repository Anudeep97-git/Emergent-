"""MLflow router — exposes run history, baseline pin, drift check, retrain trigger."""
from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth_service import get_current_user, require_roles
from services import mlflow_service

router = APIRouter()


@router.get("/runs")
async def list_runs(limit: int = Query(20, ge=1, le=100), user=Depends(get_current_user)):
    return mlflow_service.list_runs(limit=limit)


@router.get("/latest")
async def latest(user=Depends(get_current_user)):
    return mlflow_service.latest_run()


@router.get("/baseline")
async def get_baseline(user=Depends(get_current_user)):
    return mlflow_service.baseline()


@router.post("/baseline/{run_id}")
async def set_baseline(run_id: str, user=Depends(require_roles("admin"))):
    try:
        return mlflow_service.pin_baseline(run_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot pin baseline: {e}")


@router.get("/drift-check")
async def drift_check(user=Depends(get_current_user)):
    return mlflow_service.drift_check()


@router.post("/retrain")
async def retrain(user=Depends(require_roles("admin"))):
    return mlflow_service.trigger_retrain(trigger="manual")


@router.get("/retrain-status")
async def retrain_status(user=Depends(get_current_user)):
    return mlflow_service.retrain_status()


@router.post("/auto-check")
async def auto_check(user=Depends(require_roles("admin", "analyst"))):
    """One-call: drift check + auto-retrain if AUC drop > 5%."""
    return mlflow_service.auto_check_and_retrain()
