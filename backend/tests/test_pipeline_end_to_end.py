"""End-to-end pipeline integration tests via FastAPI TestClient."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from server import app


client = TestClient(app)


def _login() -> str:
    r = client.post("/api/auth/login", json={"email": "admin@c1b.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_unauthorized():
    # bad login
    r = client.post("/api/auth/login", json={"email": "no@c1b.com", "password": "x"})
    assert r.status_code == 401
    # protected without token
    assert client.get("/api/dashboard/summary").status_code == 401


def test_dashboard_summary():
    tok = _login()
    r = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_customers"] == 100
    assert body["high_risk"] + body["medium_risk"] + body["low_risk"] == 100


def test_score_endpoint():
    tok = _login()
    r = client.post(
        "/api/pipeline/score",
        json={"customer_id": "C001"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["risk_label"] in ("LOW", "MEDIUM", "HIGH")


def test_customer_decision_and_full_report():
    tok = _login()
    h = {"Authorization": f"Bearer {tok}"}
    r1 = client.get("/api/customer/decision/C001", headers=h)
    assert r1.status_code == 200
    r2 = client.get("/api/customer/full-report/C001", headers=h)
    assert r2.status_code == 200
    assert "profile" in r2.json() and "phase3_decision" in r2.json()


def test_customer_all_returns_100():
    tok = _login()
    r = client.get("/api/customer/all", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert len(r.json()) == 100
