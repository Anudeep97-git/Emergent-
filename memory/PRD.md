# C1B Credit Risk Assessment Platform — PRD

> **Status**: MVP complete · all 10 PRD sections delivered · backend 16/16 tests pass · frontend 100% flows verified
> **Build date**: 2026-02-15
> **Version**: v1.0.0

## Original problem statement

Build a full-stack credit-risk scoring platform for Credit One Bank (C1B) implementing
all 10 PRD sections: platform config, layered architecture, four-phase ML pipeline
(LightGBM Champion + XGBoost ensemble + SHAP TreeExplainer), database, FastAPI gateway,
LangChain-style ReAct AI agent, React 18 dashboard with Framer Motion animations,
JWT/RBAC security, pytest tests, and Docker/Kubernetes deployment.

## User choices (asked & confirmed at kickoff)

- **Database**: MongoDB (instead of Postgres) — leverages Emergent's native runtime.
- **AI Agent**: Claude Sonnet 4.5 via Emergent Universal LLM Key (replaces local Ollama).
- **ML artifacts**: regenerated via `backend/ml/build_artifacts.py` (53-feature LightGBM Champion).
- **Deployment**: Emergent preview URL with supervisor (Docker Compose + k8s manifests also delivered).
- **Auth**: JWT custom HS256 + RBAC + seeded users.

## What's been implemented (v1.0.0 · Feb 2026)

### Section 1 — Platform Config Module ✅
- `backend/config.py` — single importable source of truth: PLATFORM, SUCCESS_METRICS, MODEL_PATH, BUSINESS_RULES, JWT settings, thresholds paths.
- Exposed via `GET /api/platform/info`.

### Section 2 — Architecture Wiring ✅
- 4-layer: React 18 (port 3000) → FastAPI (port 8001 on Emergent / 8000 PRD-spec) → AI Agent (Claude) → ML engine (frozen LightGBM pkl).
- File structure mirrors PRD §2 exactly under `/app/backend/{routers,services,models,ml,phase_outputs}` and `/app/frontend/src/{pages,components,lib}`.

### Section 3 — Four-Phase ML Pipeline ✅
- **Phase 1**: Feature engineering reproduces notebook's rolling windows, volatility, bureau-trend, spend signals, ratios, encoded fields → 53-feature vector → `phase1_ready_for_phase2.csv`.
- **Phase 2**: LightGBM Champion (n_estimators=200, max_depth=6, lr=0.1, class_weight=balanced) + XGBoost ensemble both saved; SHAP TreeExplainer extracts top-5; percentile thresholds calibrated (rank-based 70/15/15 split with PRD-stated 0.9899/0.9999 fallback).
- **Phase 3**: BUSINESS_RULES + confidence-scaled credit-change + opportunity score → `phase3_customer_action_plan.csv`.
- **Phase 4**: batch scorer + `model_registry.json` with hash → `batch_scored_customers.csv`.
- Endpoints: `POST /api/pipeline/ingest|validate|features|score|batch`.

### Section 4 — Database Design ✅
- 6 Mongo collections mirroring PRD §4.2 Postgres tables: `users`, `customers`, `transactions`, `risk_assessments`, `uploaded_files`, `audit_logs`.
- Indexes created in `services/db.py:ensure_indexes()`.

### Section 5 — FastAPI API Specification ✅
All 17+ endpoints implemented and protected by `Depends(get_current_user)`:
- Auth: `/api/auth/login|register|refresh|logout|me`
- Pipeline: `/api/pipeline/ingest|validate|features|score|batch`
- Customer: `/api/customer/{all,profile/{id},transactions/{id},risk-history/{id},decision/{id},spend-chart/{id},full-report/{id}}`
- Dashboard: `/api/dashboard/summary`, `/api/dashboard/report/{id}` (PDF via ReportLab)
- Agent: `/api/agent/chat`, `/api/agent/tools`
- Platform: `/api/platform/info`, `/api/platform/feature-columns`
- Audit logs written on every protected call (`services/audit.py`).

### Section 6 — AI Agent (Claude Sonnet 4.5) ✅
- `services/agent_service.py` implements ReAct loop with the exact 4 PRD tools (Phase1_FeatureProfile, Phase2_RiskPredict, Phase3_CreditAction, Phase4_PipelineStatus).
- Tools pre-execute server-side with retry; LLM composes final answer in PRD-mandated format.
- Escalation flag: `risk_score > 0.98 AND confidence < 60%`.

### Section 7 — React Frontend ✅
- Pages: `Login`, `Upload`, `RiskResults`, `CustomerPortal`, `CustomerDashboard`, `AgentChat`.
- Components: `RadialGauge` (Framer Motion arc draw 600ms ease-in-out), `RiskBadge` (pulse animation), `SHAPTable` (staggered 0.1s reveals), `CreditDecisionCard` (↑/↓ deltas), `ExportButton` (PDF), `DashboardLayout` (sidebar nav).
- Design tokens exact PRD §7.2: `#0F172A`, `#6366F1`, `#10B981`, `#F59E0B`, `#F43F5E`.

### Section 8 — Security & Compliance ✅
- JWT HS256 / 60-min expiry, refresh tokens.
- RBAC: admin / analyst / viewer / customer roles.
- File upload: whitelisted MIME `.csv .xlsx .json`, 50MB cap.
- PII masking in audit logs (`mask_email`).
- Audit trail every protected call.

### Section 9 — Testing ✅
- `backend/tests/test_ml_service.py`, `test_pipeline_end_to_end.py`.
- Testing subagent verified: 16/16 backend + 100% frontend flows.

### Section 10 — Deployment ✅
- `docker-compose.yml` (PRD §10.1: backend+frontend+postgres+redis+ollama).
- `backend/Dockerfile`, `frontend/Dockerfile` + `nginx.conf`.
- `k8s/backend-deployment.yaml` (3 replicas, readiness probe, resource limits).
- `.github/workflows/deploy.yml` (CI/CD with pytest + docker push + kubectl).

## Test credentials

| Role | Email | Password |
|------|-------|----------|
| admin | admin@c1b.com | admin123 |
| analyst | analyst@c1b.com | analyst123 |
| viewer | viewer@c1b.com | viewer123 |
| customer | customer@c1b.com | customer123 |

## Prioritized backlog (P1/P2)

- **P1**: Real ML batch cron at 06:00 (currently manual trigger via `POST /api/pipeline/batch`).
- **P1**: AES-256 encryption at rest on upload files (currently MIME+size validated only).
- **P2**: Prometheus/Grafana/Sentry hookup per PRD §10.4 (MLflow tracking ✅ delivered; manifests skeleton ready).
- **P2**: Frontend MSW + React Testing Library suite (currently relying on agent-driven E2E).
- **P2**: Real-customer dataset ingestion replacing synthetic 100-customer generator.

## Feature additions log

### 2026-02-15 — Prometheus Exporter for Grafana (PRD §10.4) ✅
- `services/metrics_service.py`: dedicated `CollectorRegistry`; emits:
  - `c1b_api_request_latency_seconds` histogram with PRD-aligned buckets (0.025…5.0s).
  - `c1b_api_requests_total` counter labelled by method/endpoint/status_class.
  - `c1b_api_error_rate`, `c1b_api_total_requests_5m`, `c1b_api_error_requests_5m` gauges fed by the observability sliding window.
  - `c1b_risk_tier_pct{tier}` and `c1b_risk_tier_drift_pct{tier}` gauges (current vs MLflow baseline).
  - `c1b_model_roc_auc`, `c1b_model_auc_drift`, `c1b_risk_tier_high_threshold` (PRD §10.4 = 0.75).
- Endpoint label normalisation collapses `C001/UUIDs/numeric ids` → `{customer_id}/{uuid}/{id}` to bound cardinality.
- `routers/metrics.py` exposes `GET /api/metrics/` (unauthenticated per Prometheus best practice; protect at network/VPC layer in prod).
- Middleware times every request + records latency.
- Deliverables under `/app/monitoring/`: `prometheus.yml`, `alerts.yml` (4 rules: p95 > 500ms, error rate > 1%, high-risk > 75%, AUC drift > 5%), `grafana_dashboard.json` (8 panels), `README.md`.
- UI: ObservabilityPanel gets a "Prometheus /metrics" link badge.
- Testing: 11/11 pytest pass, 100% UI verified.

### 2026-02-15 — Sentry + PagerDuty Observability (PRD §10.4 final piece) ✅
- `services/observability_service.py`: Sentry FastAPI integration (auto-captures unhandled exceptions + 5xx), in-memory sliding-window error-rate tracker (5000 events max), PagerDuty Events API v2 trigger / resolve with dedup_key.
- `middleware/error_rate.py`: starlette middleware records every response status into the sliding window.
- `routers/observability.py` exposes 6 endpoints: `/api/observability/{stats, state, check, test-alert, test-resolve, simulate-error}` with RBAC (admin-only for test-alert/test-resolve/simulate-error; admin+analyst for check).
- Threshold: 1% error rate over 5-minute rolling window (configurable via env vars).
- Graceful no-op when `SENTRY_DSN` / `PAGERDUTY_INTEGRATION_KEY` are unset — every call returns `{sent: false, skipped: true, reason: '...'}`.
- State machine: trigger / already-open / resolve transitions correctly tracked even in no-op mode.
- UI: `components/ObservabilityPanel.jsx` on `/portal` — drift/healthy badge, sentry+PD config badges, rate/window/req-count/threshold KPIs, admin-only Run Check + Fire Test Alert + Resolve Incident buttons. Polls every 15s.
- Testing: 15/15 backend pytest pass, 100% UI flows verified.

### 2026-02-15 — MLflow Tracking + Auto-Retrain (PRD §10.4) ✅
- File-based MLflow store at `/app/backend/mlruns/` — no extra server needed.
- Every `build_artifacts.py` run logs params (LightGBM config), metrics (ROC-AUC, threshold values, risk distribution), and 5 artifacts (pkl, feature_columns.json, thresholds, registry, batch CSV).
- New service `services/mlflow_service.py`: list_runs, baseline, pin_baseline, drift_check, trigger_retrain (subprocess + background thread), auto_check_and_retrain.
- New router `routers/mlflow.py` exposes 8 endpoints: `/api/mlflow/{runs,latest,baseline,baseline/{run_id},drift-check,retrain,retrain-status,auto-check}`.
- RBAC enforced: `/retrain` and `/baseline/{run_id}` are admin-only (verified 403 for analyst/viewer).
- Drift threshold: AUC drop > 5% recommends retrain (configurable via `DRIFT_THRESHOLD`).
- UI: `components/MLflowPanel.jsx` on `/portal` shows drift badge, baseline/current AUC, AUC-drop, runs table; retrain button visible to admin only.
- Auto-check endpoint: drift check + auto-retrain in one call.
- Testing: 15/15 backend pytest pass, 100% UI flows verified.

## Next action items
- Add an alerting webhook for `eligible_expand` notifications.
- Add multi-tenancy + bank-of-banks support (PRD hints at future C-Series expansion).
- Add Prometheus exporter (`/metrics`) for API p95 and request counts.
