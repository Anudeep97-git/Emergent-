"""Platform info router — exposes platform metadata + success metrics + model registry + branding."""
from fastapi import APIRouter, Depends, Body

from config import PLATFORM, SUCCESS_METRICS, MODEL_VERSION
from services import data_service
from services import branding_service
from services.auth_service import get_current_user, require_roles

router = APIRouter()


@router.get("/info")
async def platform_info():
    return {
        "platform": PLATFORM,
        "success_metrics": SUCCESS_METRICS,
        "model_version": MODEL_VERSION,
        "model_registry": data_service.registry(),
    }


@router.get("/feature-columns")
async def feature_columns():
    from services.ml_service import feature_columns as fc, thresholds as th
    return {"feature_columns": fc(), "thresholds": th()}


# ---------- Branding (white-label tenant settings) ----------
@router.get("/branding")
async def branding():
    """Unauthenticated — frontend uses this on boot before login."""
    return branding_service.get_branding()


@router.put("/branding")
async def update_branding(payload: dict = Body(...), user=Depends(require_roles("admin"))):
    return branding_service.update_branding(payload, user_email=user.get("email"))


@router.post("/branding/reset")
async def reset_branding(user=Depends(require_roles("admin"))):
    return branding_service.reset_branding()
