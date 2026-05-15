"""C1B Credit Risk Assessment Platform — FastAPI gateway.

All routes nested under /api per Emergent ingress requirements:
  /api/auth/*, /api/pipeline/*, /api/customer/*, /api/dashboard/*, /api/agent/*, /api/platform/*, /api/mlflow/*, /api/observability/*
"""
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Sentry MUST initialise before FastAPI app is created so its middleware can wrap the app
from services import observability_service as obs  # noqa: E402
_sentry_active = obs.init_sentry()

# Prometheus multiprocess bootstrap — must run BEFORE any metric is registered.
from services.metrics_bootstrap import prepare_multiproc_dir, install_worker_death_hook, is_multiproc  # noqa: E402
prepare_multiproc_dir()
install_worker_death_hook()

from services.db import ensure_indexes  # noqa: E402
from routers import auth, pipeline, customer, dashboard, agent, platform, mlflow as mlflow_router, observability, metrics  # noqa: E402
from middleware.error_rate import ErrorRateMiddleware  # noqa: E402
from config import PLATFORM  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("c1b")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    # seed admin + sample customer users if collection empty
    try:
        from seed_db import seed_initial
        await seed_initial()
    except Exception as e:
        logger.warning(f"Seed skipped: {e}")
    logger.info(
        f"{PLATFORM['name']} {PLATFORM['version']} ready. "
        f"Sentry={'ACTIVE' if _sentry_active else 'inactive'} "
        f"PagerDuty={'configured' if obs.is_pagerduty_configured() else 'inactive'} "
        f"Prometheus={'multiproc' if is_multiproc() else 'single-process'}"
    )
    yield


app = FastAPI(
    title=PLATFORM["name"],
    version=PLATFORM["version"],
    description=PLATFORM["architecture"],
    lifespan=lifespan,
)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"platform": PLATFORM["name"], "version": PLATFORM["version"], "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "ok", "version": PLATFORM["version"]}


api_router.include_router(auth.router,      prefix="/auth",      tags=["auth"])
api_router.include_router(pipeline.router,  prefix="/pipeline",  tags=["pipeline"])
api_router.include_router(customer.router,  prefix="/customer",  tags=["customer"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(agent.router,     prefix="/agent",     tags=["agent"])
api_router.include_router(platform.router,  prefix="/platform",  tags=["platform"])
api_router.include_router(mlflow_router.router, prefix="/mlflow", tags=["mlflow"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

app.include_router(api_router)

# Error-rate sliding window middleware (records every response status)
app.add_middleware(ErrorRateMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": str(exc.errors()), "code": 422})
