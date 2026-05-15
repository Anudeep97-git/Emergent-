"""C1B Credit Risk Assessment Platform — FastAPI gateway.

All routes nested under /api per Emergent ingress requirements:
  /api/auth/*, /api/pipeline/*, /api/customer/*, /api/dashboard/*, /api/agent/*, /api/platform/*
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

from services.db import ensure_indexes  # noqa: E402
from routers import auth, pipeline, customer, dashboard, agent, platform, mlflow as mlflow_router  # noqa: E402
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
    logger.info(f"{PLATFORM['name']} {PLATFORM['version']} ready.")
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

app.include_router(api_router)

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
