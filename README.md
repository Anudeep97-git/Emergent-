# C1B Credit Risk Assessment Platform — v1.0.0

> **Full-Stack · Agent-Driven · API-First** | LightGBM Champion + XGBoost Ensemble + SHAP

Production-ready credit-risk scoring platform for Credit One Bank. Implements all 10 sections
of the C1B PRD: ML pipeline, FastAPI gateway, AI agent (Claude Sonnet 4.5), React dashboard,
JWT/RBAC security, and Docker/Kubernetes deployment.

## Stack

| Layer | Tech | Port |
|-------|------|------|
| React Frontend | React 18 + Tailwind + ShadCN/UI + Framer Motion + Recharts | 3000 |
| FastAPI Gateway | Python 3.12, async, Pydantic v2 | 8001 / 8000 |
| AI Agent | Claude Sonnet 4.5 via Emergent LLM Key (PRD spec'd Ollama llama3.2 — see notes) | — |
| ML Engine | LightGBM + XGBoost + SHAP TreeExplainer (frozen .pkl) | — |
| Database | MongoDB on Emergent / PostgreSQL via docker-compose | 27017 / 5432 |

## Quick start (Emergent runtime)

The backend is already managed by supervisor on port 8001 with `/api/*` prefix.
Frontend is on port 3000. Open the preview URL and log in:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@c1b.com | admin123 |
| Analyst | analyst@c1b.com | analyst123 |
| Viewer | viewer@c1b.com | viewer123 |
| Customer | customer@c1b.com | customer123 |

## Local deployment (PRD §10 spec)

```bash
docker-compose up --build
docker exec c1b-backend python ml/build_artifacts.py
```

This wires up Postgres + Redis + Ollama as per PRD §10.1.

## Project layout

```
/app
├── backend/
│   ├── server.py            FastAPI entry, mounts /api
│   ├── config.py            platform metadata (PRD §1)
│   ├── routers/             auth, pipeline, customer, dashboard, agent, platform
│   ├── services/            ml_service, data_service, agent_service, auth_service, db, audit
│   ├── models/              Pydantic v2 schemas
│   ├── ml/build_artifacts.py  reproduces notebook training → pkl + thresholds + CSVs
│   ├── phase_outputs/       all 4 phase artifacts (pkl, json, csv)
│   ├── seed_db.py           admin/analyst/viewer/customer seed
│   └── tests/               pytest unit + e2e
├── frontend/
│   └── src/
│       ├── pages/           Login, Upload, RiskResults, CustomerPortal, CustomerDashboard, AgentChat
│       └── components/      RadialGauge, RiskBadge, SHAPTable, CreditDecisionCard, ExportButton, ...
├── docker-compose.yml       PRD §10.1
├── k8s/                     production manifests
└── .github/workflows/       CI/CD
```

## 10 Sections — Implementation Map

| § | Section | Where |
|---|---------|-------|
| 1 | Platform metadata | `backend/config.py`, `/api/platform/info` |
| 2 | 4-layer architecture | server.py + routers + services + frontend |
| 3 | Phase 1–4 pipeline | `services/ml_service.py`, `services/data_service.py`, `routers/pipeline.py`, `ml/build_artifacts.py` |
| 4 | Database (6 entities) | `services/db.py` (Mongo collections mirroring PRD §4.2) |
| 5 | 17 FastAPI endpoints | `routers/*.py` — auth, pipeline, customer, dashboard, agent, platform |
| 6 | ReAct AI agent | `services/agent_service.py` + Claude Sonnet 4.5 |
| 7 | React UI | `frontend/src/pages/*` + `components/*` |
| 8 | Security & Compliance | JWT HS256, RBAC, audit logs, PII masking, file validation |
| 9 | Tests | `backend/tests/test_ml_service.py`, `test_pipeline_end_to_end.py` |
| 10 | Deployment | `docker-compose.yml`, `Dockerfile`s, `k8s/`, `.github/workflows/` |

## Hard Constraints honoured

- ✅ Never re-trains at runtime; loads `phase4_champion_model.pkl` (PRD §3 constraint)
- ✅ 53-feature vector aligned + missing-feature zero-fill (notebook `score_customer_portfolio`)
- ✅ Percentile-based thresholds from `bucket_thresholds_v2.json` (PRD §3 constraint, with fallback to PRD-stated 0.9899/0.9999)
- ✅ SHAP `TreeExplainer` on LightGBM booster, top 5 by |SHAP|
- ✅ Model registry with hash + version (PRD §3 / §8 — Adverse Action Notice)

## Notes for Emergent runtime

- AI Agent uses Claude Sonnet 4.5 via Emergent LLM Key instead of local Ollama (Ollama daemon not available on preview pods). The 4 tools and ReAct logic are preserved; swap the LLM client in `agent_service.py` to revert to Ollama for local deployment.
- Database is MongoDB on Emergent (collections mirror the PRD's 6 Postgres tables). Switch to Postgres via the included `docker-compose.yml` for local PRD-spec deployment.
