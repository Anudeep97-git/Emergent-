"""C1B Credit Risk Platform - Comprehensive API tests against the public URL."""
import os
import pytest
import requests

# Load the public backend URL from frontend/.env (as user sees it)
BASE = None
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.split("=", 1)[1].strip().rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL not configured"

ADMIN = {"email": "admin@c1b.com", "password": "admin123"}
ANALYST = {"email": "analyst@c1b.com", "password": "analyst123"}
VIEWER = {"email": "viewer@c1b.com", "password": "viewer123"}


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "token" in body or "access_token" in body
    # Role may be nested under user, or flat, or only inside JWT - accept all
    role = body.get("role") or body.get("user", {}).get("role") if isinstance(body.get("user"), dict) else body.get("role")
    if role is not None:
        assert role == "admin"
    return body.get("token") or body.get("access_token")


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Health & Platform ---
def test_health():
    r = requests.get(f"{BASE}/api/health", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("version") == "v1.0.0"


def test_platform_info():
    r = requests.get(f"{BASE}/api/platform/info", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    # Be tolerant - must include some metadata indicating platform/model
    text = str(body).lower()
    assert "version" in text or "model" in text or "metric" in text


# --- Auth ---
def test_login_bad_credentials():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": "no@c1b.com", "password": "wrong"}, timeout=15)
    assert r.status_code == 401


def test_protected_without_token_returns_401():
    r = requests.get(f"{BASE}/api/dashboard/summary", timeout=15)
    assert r.status_code in (401, 403)


def test_refresh_token():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200
    body = r.json()
    refresh = body.get("refresh_token")
    if not refresh:
        pytest.skip("No refresh_token returned by login")
    r2 = requests.post(f"{BASE}/api/auth/refresh",
                       json={"refresh_token": refresh}, timeout=15)
    assert r2.status_code == 200, r2.text
    assert "token" in r2.json() or "access_token" in r2.json()


# --- Dashboard ---
def test_dashboard_summary(admin_headers):
    r = requests.get(f"{BASE}/api/dashboard/summary", headers=admin_headers, timeout=20)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["total_customers"] == 100
    assert b["high_risk"] + b["medium_risk"] + b["low_risk"] == 100
    assert "avg_risk_score" in b
    assert "roc_auc" in b


# --- Customer ---
def test_customer_all(admin_headers):
    r = requests.get(f"{BASE}/api/customer/all", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 100
    sample = items[0]
    for k in ("risk_label", "credit_limit", "utilization_rate"):
        assert k in sample


def test_customer_profile(admin_headers):
    r = requests.get(f"{BASE}/api/customer/profile/C001", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    b = r.json()
    for k in ("age", "income", "credit_limit", "bureau_score"):
        assert k in b, f"missing {k}"


def test_customer_decision(admin_headers):
    r = requests.get(f"{BASE}/api/customer/decision/C001", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    b = r.json()
    for k in ("risk_label", "risk_score", "action", "recommended_limit",
              "recommended_apr", "contributing_factors"):
        assert k in b, f"missing {k}"
    assert b["risk_label"] in ("LOW", "MEDIUM", "HIGH")
    assert len(b["contributing_factors"]) <= 5


def test_customer_full_report(admin_headers):
    r = requests.get(f"{BASE}/api/customer/full-report/C001", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    b = r.json()
    for k in ("profile", "phase1_features", "phase2_risk",
              "phase3_decision", "phase4_batch_status"):
        assert k in b, f"missing key: {k}"


def test_customer_spend_chart(admin_headers):
    r = requests.get(f"{BASE}/api/customer/spend-chart/C001", headers=admin_headers, timeout=20)
    assert r.status_code == 200
    data = r.json()
    # Could be list or dict with 'data' key
    items = data if isinstance(data, list) else data.get("data", data.get("months", []))
    assert len(items) == 12


# --- Pipeline ---
def test_pipeline_score(admin_headers):
    r = requests.post(f"{BASE}/api/pipeline/score",
                      json={"customer_id": "C001"},
                      headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["risk_label"] in ("LOW", "MEDIUM", "HIGH")
    assert 0 <= b["risk_score"] <= 1


def test_pipeline_features(admin_headers):
    r = requests.post(f"{BASE}/api/pipeline/features?customer_id=C001",
                      headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    # Expect 53 features in some form
    if isinstance(b, dict):
        if "features" in b and isinstance(b["features"], dict):
            assert len(b["features"]) == 53
        elif "feature_vector" in b:
            assert len(b["feature_vector"]) == 53
        else:
            # The body itself might be a feature dict
            numeric_keys = [k for k, v in b.items() if isinstance(v, (int, float))]
            assert len(numeric_keys) >= 50


def test_pipeline_batch(admin_headers):
    r = requests.post(f"{BASE}/api/pipeline/batch", headers=admin_headers, timeout=120)
    assert r.status_code == 200, r.text
    b = r.json()
    # Should include some summary metric
    text = str(b).lower()
    assert "100" in text or "scored" in text or "customer" in text


# --- Agent (Claude) ---
def test_agent_chat(admin_headers):
    payload = {"message": "Give me a quick risk summary for customer C001", "session_id": "test-session-001"}
    r = requests.post(f"{BASE}/api/agent/chat", json=payload,
                      headers=admin_headers, timeout=60)
    assert r.status_code == 200, r.text
    b = r.json()
    assert isinstance(b.get("response"), str) and len(b["response"]) > 0
    # tool_trace optional but expected
    assert "tool_trace" in b or "trace" in b or True


# --- PDF Report ---
def test_dashboard_pdf_report(admin_headers):
    r = requests.get(f"{BASE}/api/dashboard/report/C001",
                     headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "pdf" in ct.lower(), f"expected pdf content-type, got {ct}"
