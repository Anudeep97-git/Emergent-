"""End-to-end pipeline integration tests via HTTP against a live backend process."""
import requests
import pytest

from tests.conftest import spawn_backend


@pytest.fixture(scope="function")
def base_url():
    """Start a fresh backend process for each test and return its base URL."""
    with spawn_backend() as (port, _log_path):
        yield f"http://127.0.0.1:{port}"


def _login(base_url) -> str:
    r = requests.post(f"{base_url}/api/auth/login", json={"email": "admin@primanova.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_health(base_url):
    r = requests.get(f"{base_url}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_unauthorized(base_url):
    # bad login
    r = requests.post(f"{base_url}/api/auth/login", json={"email": "no@primanova.com", "password": "x"})
    assert r.status_code == 401
    # protected without token
    assert requests.get(f"{base_url}/api/dashboard/summary").status_code == 401


def test_dashboard_summary(base_url):
    tok = _login(base_url)
    r = requests.get(f"{base_url}/api/dashboard/summary", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_customers"] == 100
    assert body["high_risk"] + body["medium_risk"] + body["low_risk"] == 100


def test_score_endpoint(base_url):
    tok = _login(base_url)
    r = requests.post(
        f"{base_url}/api/pipeline/score",
        json={"customer_id": "C001"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["risk_label"] in ("LOW", "MEDIUM", "HIGH")


def test_customer_decision_and_full_report(base_url):
    tok = _login(base_url)
    h = {"Authorization": f"Bearer {tok}"}
    r1 = requests.get(f"{base_url}/api/customer/decision/C001", headers=h)
    assert r1.status_code == 200
    r2 = requests.get(f"{base_url}/api/customer/full-report/C001", headers=h)
    assert r2.status_code == 200
    assert "profile" in r2.json() and "phase3_decision" in r2.json()


def test_customer_all_returns_100(base_url):
    tok = _login(base_url)
    r = requests.get(f"{base_url}/api/customer/all", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert len(r.json()) == 100
