"""Observability (Sentry + PagerDuty + error-rate) tests — PRD §10.4 iteration_3."""
import time
import requests
import pytest

ADMIN = {"email": "admin@primanova.com", "password": "admin123"}
ANALYST = {"email": "analyst@primanova.com", "password": "analyst123"}
VIEWER = {"email": "viewer@primanova.com", "password": "viewer123"}


def _login(base_url, creds):
    r = requests.post(f"{base_url}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    return body.get("token") or body.get("access_token")


@pytest.fixture(scope="session")
def admin_h(base_url):
    return {"Authorization": f"Bearer {_login(base_url, ADMIN)}"}


@pytest.fixture(scope="session")
def analyst_h(base_url):
    return {"Authorization": f"Bearer {_login(base_url, ANALYST)}"}


@pytest.fixture(scope="session")
def viewer_h(base_url):
    return {"Authorization": f"Bearer {_login(base_url, VIEWER)}"}


# --- /stats ---
def test_stats_unauthenticated():
    r = requests.get(f"{BASE}/api/observability/stats", timeout=15)
    assert r.status_code in (401, 403)


def test_stats_shape(admin_h):
    r = requests.get(f"{BASE}/api/observability/stats", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    for k in ("window_min", "total_requests", "error_requests", "error_rate",
              "threshold", "exceeds_threshold", "sentry_active",
              "pagerduty_configured", "env"):
        assert k in b, f"missing {k}"
    assert b["threshold"] == 0.01
    assert b["sentry_active"] is False
    assert b["pagerduty_configured"] is False
    assert b["env"] == "preview"
    assert isinstance(b["total_requests"], int)
    assert isinstance(b["error_requests"], int)


def test_stats_custom_window(admin_h):
    r = requests.get(f"{BASE}/api/observability/stats?window_min=1",
                     headers=admin_h, timeout=15)
    assert r.status_code == 200
    b = r.json()
    assert float(b["window_min"]) == 1.0


# --- /state ---
def test_state_shape(admin_h):
    r = requests.get(f"{BASE}/api/observability/state", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "pagerduty_state" in b
    pd = b["pagerduty_state"]
    for k in ("trigger_count", "resolve_count", "last_trigger_at",
              "last_resolve_at", "current_incident_key"):
        assert k in pd, f"missing pd field {k}"
    assert isinstance(pd["trigger_count"], int)
    assert isinstance(pd["resolve_count"], int)


# --- /check RBAC ---
def test_check_admin(admin_h):
    r = requests.post(f"{BASE}/api/observability/check", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "pagerduty_action" in b
    assert b["pagerduty_action"] in (
        "TRIGGERED", "RESOLVED", "NO_ACTION", "ALREADY_OPEN"
    )
    # also has stats keys
    assert "error_rate" in b


def test_check_analyst(analyst_h):
    r = requests.post(f"{BASE}/api/observability/check", headers=analyst_h, timeout=15)
    assert r.status_code == 200, r.text


def test_check_viewer_forbidden(viewer_h):
    r = requests.post(f"{BASE}/api/observability/check", headers=viewer_h, timeout=15)
    assert r.status_code == 403


# --- /test-alert ---
def test_test_alert_admin_noop(admin_h):
    r = requests.post(f"{BASE}/api/observability/test-alert", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b.get("sent") is False
    assert b.get("skipped") is True
    assert "PAGERDUTY_INTEGRATION_KEY" in (b.get("reason") or "")


def test_test_alert_viewer_forbidden(viewer_h):
    r = requests.post(f"{BASE}/api/observability/test-alert", headers=viewer_h, timeout=15)
    assert r.status_code == 403


def test_test_alert_analyst_forbidden(analyst_h):
    r = requests.post(f"{BASE}/api/observability/test-alert", headers=analyst_h, timeout=15)
    assert r.status_code == 403


# --- /test-resolve ---
def test_test_resolve_admin(admin_h):
    r = requests.post(f"{BASE}/api/observability/test-resolve", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    # No real PD configured AND no incident open — should be skipped
    assert b.get("sent") is False


def test_test_resolve_viewer_forbidden(viewer_h):
    r = requests.post(f"{BASE}/api/observability/test-resolve", headers=viewer_h, timeout=15)
    assert r.status_code == 403


# --- /simulate-error ---
def test_simulate_error_admin_increments_counter(admin_h):
    # baseline
    s0 = requests.get(f"{BASE}/api/observability/stats", headers=admin_h, timeout=15).json()
    e0 = s0["error_requests"]

    r = requests.post(f"{BASE}/api/observability/simulate-error",
                      headers=admin_h, timeout=15)
    assert r.status_code == 500

    # small delay for middleware/recording
    time.sleep(0.4)
    s1 = requests.get(f"{BASE}/api/observability/stats", headers=admin_h, timeout=15).json()
    assert s1["error_requests"] >= e0 + 1, f"counter did not increment: {e0} -> {s1['error_requests']}"


def test_simulate_error_viewer_forbidden(viewer_h):
    r = requests.post(f"{BASE}/api/observability/simulate-error",
                      headers=viewer_h, timeout=15)
    assert r.status_code == 403


def test_simulate_error_analyst_forbidden(analyst_h):
    r = requests.post(f"{BASE}/api/observability/simulate-error",
                      headers=analyst_h, timeout=15)
    assert r.status_code == 403
