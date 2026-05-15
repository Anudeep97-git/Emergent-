"""Prometheus exporter — request latency histogram, error-rate gauge, risk-tier drift gauges.

Exposed at GET /api/metrics in Prometheus text format. Grafana derives p50/p95/p99
from the latency histogram via `histogram_quantile(0.95, ...)`.

Supports both single-process and multi-worker (gunicorn) deployments:
  * Set `PROMETHEUS_MULTIPROC_DIR=/var/c1b/prom_multiproc` before launching workers.
  * All gauges declare a `multiprocess_mode` so values aggregate sensibly across processes.
  * /metrics renders via `multiprocess.MultiProcessCollector` in multiproc mode.
"""
import os
import time
import logging
import threading
from typing import Dict

import pandas as pd
from prometheus_client import (
    CollectorRegistry, Histogram, Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST,
)

from services.metrics_bootstrap import is_multiproc, MULTIPROC_DIR

logger = logging.getLogger("c1b.metrics")

# Use a dedicated registry to avoid clashing with default global one
REGISTRY = CollectorRegistry()

# Counters and Histograms are aggregated across processes by prometheus_client
# automatically (sum semantics). Gauges need an explicit `multiprocess_mode`.
# We choose:
#   - 'livesum' for additive gauges (total/error counts in a rolling window)
#   - 'liveall' for per-label dimensional gauges (risk tier breakdown)
#   - 'max' for slow-moving scalar state (model AUC, thresholds)
_GAUGE_KW_LIVESUM = {"multiprocess_mode": "livesum"} if is_multiproc() else {}
_GAUGE_KW_LIVEALL = {"multiprocess_mode": "liveall"} if is_multiproc() else {}
_GAUGE_KW_MAX = {"multiprocess_mode": "max"} if is_multiproc() else {}

# ---------- API request latency histogram ----------
# Bucket boundaries (seconds): align with PRD p95 < 300ms target
LATENCY_BUCKETS = (0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0)
api_latency = Histogram(
    "c1b_api_request_latency_seconds",
    "Latency of FastAPI requests in seconds",
    labelnames=("method", "endpoint", "status_class"),
    buckets=LATENCY_BUCKETS,
    registry=REGISTRY,
)

# ---------- Counters / gauges ----------
api_requests_total = Counter(
    "c1b_api_requests_total",
    "Total HTTP requests handled by the API",
    labelnames=("method", "endpoint", "status_class"),
    registry=REGISTRY,
)

api_error_rate = Gauge(
    "c1b_api_error_rate",
    "Rolling 5-minute error rate (5xx / total)",
    registry=REGISTRY,
    **_GAUGE_KW_MAX,
)

api_total_requests_5m = Gauge(
    "c1b_api_total_requests_5m",
    "Total requests in the last 5 minutes",
    registry=REGISTRY,
    **_GAUGE_KW_LIVESUM,
)

api_error_requests_5m = Gauge(
    "c1b_api_error_requests_5m",
    "5xx error requests in the last 5 minutes",
    registry=REGISTRY,
    **_GAUGE_KW_LIVESUM,
)

# ---------- Risk-tier distribution gauges ----------
risk_tier_pct = Gauge(
    "c1b_risk_tier_pct",
    "Current % of customers in each risk tier (0.0–1.0)",
    labelnames=("tier",),
    registry=REGISTRY,
    **_GAUGE_KW_LIVEALL,
)
risk_tier_drift_pct = Gauge(
    "c1b_risk_tier_drift_pct",
    "Drift in risk tier % vs MLflow baseline (current minus baseline)",
    labelnames=("tier",),
    registry=REGISTRY,
    **_GAUGE_KW_LIVEALL,
)
risk_tier_high_threshold = Gauge(
    "c1b_risk_tier_high_threshold",
    "Configured high-risk alert threshold (PRD §10.4 = 0.75)",
    registry=REGISTRY,
    **_GAUGE_KW_MAX,
)
risk_tier_high_threshold.set(0.75)  # PRD §10.4: alert if High Risk % > 75%

# ---------- Model gauges ----------
model_roc_auc = Gauge(
    "c1b_model_roc_auc",
    "ROC-AUC of the currently deployed LightGBM model",
    registry=REGISTRY,
    **_GAUGE_KW_MAX,
)
model_auc_drift = Gauge(
    "c1b_model_auc_drift",
    "AUC drop vs baseline (PRD §10.4: retrain if > 0.05)",
    registry=REGISTRY,
    **_GAUGE_KW_MAX,
)


# ---------- Public API ----------
def observe_request(method: str, endpoint: str, status_code: int, duration_seconds: float):
    status_class = f"{status_code // 100}xx"
    # Normalise endpoint to keep label cardinality low: strip ids
    ep = _normalise_endpoint(endpoint)
    api_latency.labels(method=method, endpoint=ep, status_class=status_class).observe(duration_seconds)
    api_requests_total.labels(method=method, endpoint=ep, status_class=status_class).inc()


def _normalise_endpoint(path: str) -> str:
    """Replace path params (UUIDs, customer IDs like C001) with placeholders."""
    parts = []
    for seg in path.strip("/").split("/"):
        if not seg:
            continue
        if len(seg) > 24 and "-" in seg:
            parts.append("{uuid}")
        elif seg.startswith("C") and seg[1:].isdigit():
            parts.append("{customer_id}")
        elif seg.isdigit():
            parts.append("{id}")
        else:
            parts.append(seg)
    return "/" + "/".join(parts) if parts else "/"


def render() -> bytes:
    """Refresh derived gauges and return the Prometheus text-format payload.

    In multi-process mode, build a transient registry that aggregates the on-disk
    .db files written by every worker — this is the prometheus_client pattern that
    makes gauges/histograms consistent across `gunicorn --workers N`.
    """
    _refresh_gauges()
    if is_multiproc():
        try:
            from prometheus_client import multiprocess
            aggregated = CollectorRegistry()
            multiprocess.MultiProcessCollector(aggregated)
            return generate_latest(aggregated)
        except Exception as e:
            logger.warning("Multiproc render failed, falling back: %s: %s", type(e).__name__, e)
    return generate_latest(REGISTRY)


def render_info() -> Dict[str, str]:
    return {
        "mode": "multiprocess" if is_multiproc() else "single-process",
        "multiproc_dir": MULTIPROC_DIR or "",
        "pid": str(os.getpid()),
    }


# ---------- Derived gauge refresh ----------
_refresh_lock = threading.Lock()


def _refresh_gauges():
    if not _refresh_lock.acquire(blocking=False):
        return
    try:
        # Error rate (from observability sliding window)
        from services import observability_service as obs
        s = obs.stats()
        api_error_rate.set(s["error_rate"])
        api_total_requests_5m.set(s["total_requests"])
        api_error_requests_5m.set(s["error_requests"])

        # Risk-tier distribution (from Phase 3 CSV)
        try:
            from services import data_service
            summary = data_service.dashboard_summary()
            total = max(int(summary["total_customers"]), 1)
            current = {
                "low": summary["low_risk"] / total,
                "medium": summary["medium_risk"] / total,
                "high": summary["high_risk"] / total,
            }
            for tier, pct in current.items():
                risk_tier_pct.labels(tier=tier).set(float(pct))

            # Drift vs MLflow baseline
            from services import mlflow_service
            base = mlflow_service.baseline() or {}
            base_run_id = base.get("run_id")
            if base_run_id:
                from mlflow.tracking import MlflowClient
                cli = MlflowClient(tracking_uri=f"file:{mlflow_service.MLRUNS_DIR}")
                try:
                    run = cli.get_run(base_run_id)
                    base_m = run.data.metrics
                    base_dist = {
                        "low": float(base_m.get("low_risk_pct", current["low"])),
                        "medium": float(base_m.get("medium_risk_pct", current["medium"])),
                        "high": float(base_m.get("high_risk_pct", current["high"])),
                    }
                    for tier in ("low", "medium", "high"):
                        risk_tier_drift_pct.labels(tier=tier).set(current[tier] - base_dist[tier])
                except Exception:
                    pass

            # Model AUC + drift
            latest = mlflow_service.latest_run() or {}
            cur_auc = float(latest.get("roc_auc", summary.get("roc_auc", 0.0)))
            base_auc = float(base.get("roc_auc", cur_auc))
            model_roc_auc.set(cur_auc)
            model_auc_drift.set(max(base_auc - cur_auc, 0.0))
        except Exception as e:
            logger.warning("Derived gauge refresh failed: %s: %s", type(e).__name__, e)
    finally:
        _refresh_lock.release()
