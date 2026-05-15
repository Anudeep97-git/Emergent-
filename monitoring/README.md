# C1B Monitoring Stack (PRD §10.4)

This directory contains the production Prometheus + Grafana wiring for the C1B Credit Risk Platform.

## Files

| File | Purpose |
|------|---------|
| `prometheus.yml` | Scrape config — pulls `/api/metrics/` from the c1b-backend every 15s |
| `alerts.yml` | Prometheus alerting rules (p95 > 500ms, error rate > 1%, high-risk > 75%, AUC drift > 5%) |
| `grafana_dashboard.json` | Importable Grafana dashboard with 8 panels (stats + timeseries) |

## Metrics emitted by the backend

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `c1b_api_request_latency_seconds` | Histogram | method, endpoint, status_class | middleware |
| `c1b_api_requests_total` | Counter | method, endpoint, status_class | middleware |
| `c1b_api_error_rate` | Gauge | — | observability sliding window |
| `c1b_api_total_requests_5m` | Gauge | — | observability sliding window |
| `c1b_api_error_requests_5m` | Gauge | — | observability sliding window |
| `c1b_risk_tier_pct` | Gauge | tier=low/medium/high | Phase 3 CSV |
| `c1b_risk_tier_drift_pct` | Gauge | tier=low/medium/high | MLflow baseline diff |
| `c1b_risk_tier_high_threshold` | Gauge | — | PRD §10.4 = 0.75 |
| `c1b_model_roc_auc` | Gauge | — | MLflow latest run |
| `c1b_model_auc_drift` | Gauge | — | MLflow baseline diff |

## Local quickstart

```bash
# 1. Start Prometheus + Grafana
docker run -d --name c1b-prom -p 9090:9090 \
    -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
    -v $(pwd)/monitoring/alerts.yml:/etc/prometheus/alerts.yml \
    prom/prometheus

docker run -d --name c1b-grafana -p 3001:3000 \
    -e GF_SECURITY_ADMIN_PASSWORD=admin \
    grafana/grafana

# 2. Add Prometheus datasource in Grafana UI at http://localhost:3001 (admin/admin)
#    URL: http://host.docker.internal:9090

# 3. Import grafana_dashboard.json → Dashboards → Import → upload JSON
```

## Alerting flow

```
Prometheus  ──(rule fires)──▶  PagerDuty Events API v2 (via webhook)  ──▶  on-call analyst
       │
       └─ Recording rules feed:  c1b_api_error_rate, c1b_model_auc_drift
                                 (used by /api/observability/check to fire incidents directly)
```

## Endpoint security

`GET /api/metrics/` is intentionally **unauthenticated** (per Prometheus best practice). Restrict access at:
- Kubernetes: `NetworkPolicy` allowing only the Prometheus pod into the backend service.
- VPC: scrape only over a private subnet.
- Never expose `/api/metrics/` to the public Internet.

## Horizontal scaling — multi-worker mode

When running `gunicorn --workers N` (or any pre-fork ASGI runner), every worker maintains its own
in-process metric state. To make Prometheus see aggregated values you MUST enable
`prometheus_client`'s multi-process mode:

```bash
export PROMETHEUS_MULTIPROC_DIR=/var/c1b/prom_multiproc
mkdir -p $PROMETHEUS_MULTIPROC_DIR
rm -f $PROMETHEUS_MULTIPROC_DIR/*.db   # on every boot
gunicorn server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8001
```

What the platform does automatically when `PROMETHEUS_MULTIPROC_DIR` is set:

| Layer | Behaviour |
|-------|-----------|
| `services/metrics_bootstrap.py` | Creates the dir, clears stale `.db` files at boot, registers `mark_process_dead(pid)` cleanup on `SIGTERM` / `atexit`. |
| Gauges | Declared with `multiprocess_mode='livesum' \| 'liveall' \| 'max'` so values aggregate sensibly across workers. |
| `/api/metrics/` render | Builds a transient `CollectorRegistry` and runs `multiprocess.MultiProcessCollector(registry)` to merge `counter_*.db`, `histogram_*.db`, `gauge_*.db` files. |
| `/api/metrics/info` | Returns `{ "mode": "multiprocess" \| "single-process", "multiproc_dir": "...", "pid": "..." }` for ops debugging. |

Gauge mode selection rationale:

| Mode | Used for | Why |
|------|----------|-----|
| `livesum` | `c1b_api_total_requests_5m`, `c1b_api_error_requests_5m` | Sliding-window counts are additive across workers. |
| `liveall` | `c1b_risk_tier_pct`, `c1b_risk_tier_drift_pct` | Per-label values are identical across workers (same Phase 3 CSV), so any live worker's reading is correct. |
| `max` | `c1b_api_error_rate`, `c1b_model_roc_auc`, `c1b_model_auc_drift`, threshold | Slow-moving global state — `max` gives the most recent valid sample seen by any worker. |

### Production deployment example (gunicorn)

```dockerfile
ENV PROMETHEUS_MULTIPROC_DIR=/var/c1b/prom_multiproc
ENV WEB_CONCURRENCY=4
CMD ["sh", "-c", "rm -f $PROMETHEUS_MULTIPROC_DIR/*.db; \
     exec gunicorn server:app --workers $WEB_CONCURRENCY \
       --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001"]
```

For dev / single-worker (current Emergent setup), leave `PROMETHEUS_MULTIPROC_DIR` unset —
the exporter automatically falls back to the in-process `CollectorRegistry`.
