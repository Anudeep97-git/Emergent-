"""Prometheus /metrics endpoint — unauthenticated text/plain payload for scraping."""
from fastapi import APIRouter
from fastapi.responses import Response

from services import metrics_service
from prometheus_client import CONTENT_TYPE_LATEST

router = APIRouter()


@router.get("/")
async def prometheus_metrics():
    """Prometheus scrape endpoint. NOTE: intentionally unauthenticated per Prometheus best practice
    (lock it down at the network layer / VPC; do not expose publicly in production)."""
    payload = metrics_service.render()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
