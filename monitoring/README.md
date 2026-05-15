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
