"""Platform info router — exposes platform metadata + success metrics + model registry."""
from fastapi import APIRouter

from config import PLATFORM, SUCCESS_METRICS, MODEL_VERSION
from services import data_service

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
