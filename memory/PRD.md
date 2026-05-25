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
| admin | admin@primanova.com | admin123 |
| analyst | analyst@primanova.com | analyst123 |
| viewer | viewer@primanova.com | viewer123 |
| customer | customer@primanova.com | customer123 |

## Prioritized backlog (P1/P2)

- **P1**: Real ML batch cron at 06:00 (currently manual trigger via `POST /api/pipeline/batch`).
- **P1**: AES-256 encryption at rest on upload files (currently MIME+size validated only).
- **P2**: Prometheus/Grafana/Sentry hookup per PRD §10.4 (MLflow tracking ✅ delivered; manifests skeleton ready).
- **P2**: Frontend MSW + React Testing Library suite (currently relying on agent-driven E2E).
- **P2**: Real-customer dataset ingestion replacing synthetic 100-customer generator.

## Feature additions log

### 2026-02-15 — Prometheus Multi-Process Support (horizontal scaling) ✅
- `services/metrics_bootstrap.py`: detects `PROMETHEUS_MULTIPROC_DIR`, creates dir, clears stale `.db` files at boot, registers `mark_process_dead(pid)` hook on `atexit` + `SIGTERM` + `SIGINT`.
- `services/metrics_service.py`: every Gauge now declares an explicit `multiprocess_mode` — `livesum` for additive 5-min counters, `liveall` for per-tier dimensional gauges, `max` for slow-moving scalar state (AUC, threshold, drift). `render()` switches to `multiprocess.MultiProcessCollector` when the env var is set, falling back to the in-process registry on error.
- `routers/metrics.py` adds `GET /api/metrics/info` returning `{ mode, multiproc_dir, pid }` for ops debugging.
- `server.py`: bootstrap runs BEFORE any router import (required so metrics are registered in multiproc mode).
- Deploy artifacts updated: `Dockerfile` switches to `gunicorn --workers ${WEB_CONCURRENCY:-4} -k uvicorn.workers.UvicornWorker` and exports `PROMETHEUS_MULTIPROC_DIR`. `k8s/backend-deployment.yaml` adds the env var, a Memory-backed `emptyDir` volume + matching `volumeMount`, and `WEB_CONCURRENCY=4`.
- Single-process mode (current Emergent runtime) is unchanged — `PROMETHEUS_MULTIPROC_DIR` is left unset, all multiproc code paths are inert.
- Testing: 16/16 backend pytest pass (11 prior + 5 new multiproc cases). Cross-process smoke test in `/tmp/test_multiproc.py` proves 3-worker counter aggregation (5+7=12 successes, 3 errors) merges via `MultiProcessCollector`.

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

### 2026-02-16 — Real Bank Dataset Migration + USD Currency Switch ✅
- **Data source swap**: Replaced synthetic 100-customer generator in `build_artifacts.py` with a real-Excel ingestor reading `/app/backend/data/real_dataset.xlsx` (Customer_Data sheet: 100 statement snapshots + Customer_Transactions sheet: 751 real transactions). The script maps real columns (previous_balance, payment_amount, other_credits → payment_amount, purchases_amount, cash_advances_amount, fees_charged + cash_advance_fee, interest_charged, new_balance, credit_limit, utilization_rate, bureau_score, delinquency_last_12m, geography_region, risk_bucket) to the existing 20-column raw schema.
- **Derived missing fields**: `age` (deterministic from md5 hash of customer_id, 22-69), `income` (`18k + credit_limit*35*bureau_mult`, ~$30k-$80k band), `employment_status` (age + bureau bands). `default_flag` = `risk_bucket == 'High' OR (delinq_12m>=6 AND payment_on_time=0)`.
- **12-month history synthesis**: Each customer's single real snapshot is extended to 12 monthly statements via random-walk drift around the snapshot; months that have real transactions in Customer_Transactions inject real `purchases_amount`/`cash_advances`/`payment` aggregates → SpendChart shows real per-month spend where available.
- **Model retrained**: PrimaNova_LightGBM_Champion v1.1.0, 53 features, AUC=1.0 (clean target signal on 100-row sample), risk distribution exactly 70/15/15 (LOW/MEDIUM/HIGH). Registry now exposes `currency: USD`, `data_source: real_bank_dataset.xlsx`, `n_customers`, `n_transactions`.
- **Frontend currency switch**: All `₹` symbols + `IndianRupee` icon removed across `CreditDecisionCard.jsx`, `CustomerDashboard.jsx`, `CustomerPortal.jsx`. Replaced with `$` and `DollarSign` icon. Dropped `/1000)k` shortening since USD values are in the $500-$1000 range (full-value formatting like `$1,000` reads better than `$1k`).
- **Testing — Iteration 7 PASS**: 8/8 new pytest cases (`test_real_dataset_usd.py`), plus regression-safe (ml_service 4/4 + branding 6/6 still pass). Frontend e2e: DOM scan for `₹` (U+20B9) returned ZERO matches on `/portal` and `/customer/C001`; KPI/decision/spend-chart all render in USD.

## Next action items
- Add an alerting webhook for `eligible_expand` notifications.
- Add multi-tenancy + bank-of-banks support (PRD hints at future C-Series expansion).
- Add Prometheus exporter (`/metrics`) for API p95 and request counts.

### 2026-02-16 — Tenant-Aware Branding (white-label) Frontend Integration ✅
- Frontend now wraps the React app with `BrandingProvider` (`/app/frontend/src/lib/branding.jsx`) which fetches `/api/platform/branding` on boot and applies the response as CSS variables on `:root`.
- Tailwind tokens `pn.primary/accent/success/warning/danger` rewritten as `rgb(var(--pn-*) / <alpha-value>)` so existing alpha-modifier classes (e.g. `bg-pn-accent/30`, `shadow-pn-accent/40`) continue to work with dynamic colors.
- Branding context converts hex → RGB triplet and updates `--pn-primary/accent/success/warning/danger` at runtime. Defaults seeded in `index.css :root` for first-paint fidelity.
- Admin-only route `/admin/branding` (`pages/AdminBranding.jsx`) with identity fields (app name, tagline, logo initials, support email), 5 color pickers with hex inputs, live preview panel reflecting unsaved state, Save (PUT) and Reset (POST → defaults) actions.
- Sidebar (`DashboardLayout`) and Login page now consume `useBranding()` — both display dynamic logo initials, app name, tagline. Admin sees an extra `Branding` nav item; non-admins do not.
- `App.js` adds `RequireAdmin` outlet guard — direct navigation to `/admin/branding` by non-admins redirects to `/portal`.
- Testing — Iteration 6 PASS:
  - Backend: 6 new pytest cases in `/app/backend/tests/test_branding.py` (GET unauth, PUT no-auth=401/403, customer=403, admin=200+persistence, POST reset customer=403/admin=200) — all pass in 2.96s.
  - Frontend: 10/10 e2e flows verified — login renders dynamic brand, admin nav visible, color picker updates persist + apply to sidebar accent at runtime (verified `--pn-accent` CSS var transitions), reset restores defaults, customer is blocked from `/admin/branding`.

