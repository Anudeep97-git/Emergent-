"""Observability router — error-rate stats, manual check/alert, PagerDuty test, state."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth_service import get_current_user, require_roles
from services import observability_service as obs

router = APIRouter()


@router.get("/stats")
async def stats(window_min: Optional[float] = Query(None, ge=0.1, le=60),
                user=Depends(get_current_user)):
    return obs.stats(window_min=window_min)


@router.get("/state")
async def state(user=Depends(get_current_user)):
    s = obs.stats()
    s["pagerduty_state"] = obs.state()
    return s


@router.post("/check")
async def check(user=Depends(require_roles("admin", "analyst"))):
    return obs.check_and_alert()


@router.post("/test-alert")
async def test_alert(user=Depends(require_roles("admin"))):
    """Fire a synthetic test PagerDuty incident (admin only). Useful to validate routing."""
    out = obs.trigger_incident(
        summary="C1B platform — test incident (manual)",
        details={"triggered_by": user["email"], "kind": "manual_test"},
        severity="info",
    )
    return out


@router.post("/test-resolve")
async def test_resolve(user=Depends(require_roles("admin"))):
    return obs.resolve_incident("Manual resolve from C1B test endpoint")


@router.post("/simulate-error")
async def simulate_error(user=Depends(require_roles("admin"))):
    """Throw a 500 so we can validate the error-rate sliding window + Sentry capture."""
    raise HTTPException(status_code=500, detail="Simulated 500 for observability testing")
