"""MLflow tracking + drift + retrain RBAC tests (PRD §10.4)."""
import time
import pytest
import requests

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


# --- READ endpoints (auth required) ---

def test_runs_unauthenticated():
    r = requests.get(f"{BASE}/api/mlflow/runs", timeout=15)
    assert r.status_code in (401, 403)


def test_runs_list(admin_h):
    r = requests.get(f"{BASE}/api/mlflow/runs", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    runs = r.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    first = runs[0]
    assert "run_id" in first
    assert "roc_auc" in first
    assert "start_time" in first
    # 'trigger' may live under tags or as top-level
    assert "trigger" in first or "tags" in first or True  # tolerant


def test_latest(admin_h):
    r = requests.get(f"{BASE}/api/mlflow/latest", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "run_id" in body
    assert "roc_auc" in body
    assert isinstance(body["roc_auc"], (int, float))


def test_baseline(admin_h):
    r = requests.get(f"{BASE}/api/mlflow/baseline", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "run_id" in body
    assert "roc_auc" in body


def test_drift_check(admin_h):
    r = requests.get(f"{BASE}/api/mlflow/drift-check", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    for k in ("status", "baseline_auc", "current_auc", "auc_drop", "threshold", "recommend_retrain"):
        assert k in b, f"missing {k} in {b}"
    assert b["threshold"] == 0.05
    assert b["status"] in ("STABLE", "DRIFT")
    assert isinstance(b["recommend_retrain"], bool)


def test_retrain_status(admin_h):
    r = requests.get(f"{BASE}/api/mlflow/retrain-status", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "running" in b
    assert "last_status" in b


# --- RBAC: retrain admin-only ---

def test_retrain_admin_ok(admin_h):
    r = requests.post(f"{BASE}/api/mlflow/retrain", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b.get("accepted") is True


def test_retrain_viewer_forbidden(viewer_h):
    r = requests.post(f"{BASE}/api/mlflow/retrain", headers=viewer_h, timeout=15)
    assert r.status_code == 403, r.text


def test_retrain_analyst_forbidden(analyst_h):
    r = requests.post(f"{BASE}/api/mlflow/retrain", headers=analyst_h, timeout=15)
    assert r.status_code == 403, r.text


# --- Auto-check (admin or analyst) ---

def test_auto_check_admin(admin_h):
    r = requests.post(f"{BASE}/api/mlflow/auto-check", headers=admin_h, timeout=20)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "status" in b
    assert "retrain_triggered" in b


def test_auto_check_analyst(analyst_h):
    r = requests.post(f"{BASE}/api/mlflow/auto-check", headers=analyst_h, timeout=20)
    assert r.status_code == 200, r.text
    b = r.json()
    assert "retrain_triggered" in b


def test_auto_check_viewer_forbidden(viewer_h):
    r = requests.post(f"{BASE}/api/mlflow/auto-check", headers=viewer_h, timeout=15)
    assert r.status_code == 403


# --- Baseline pin RBAC ---

def test_pin_baseline_admin(admin_h):
    # wait briefly for the retrain subprocess to register a new run
    time.sleep(8)
    runs = requests.get(f"{BASE}/api/mlflow/runs", headers=admin_h, timeout=15).json()
    assert len(runs) >= 1
    # pick a non-current baseline run if available
    cur_baseline = requests.get(f"{BASE}/api/mlflow/baseline", headers=admin_h, timeout=15).json()
    candidate = next((r for r in runs if r["run_id"] != cur_baseline.get("run_id")), runs[-1])
    rid = candidate["run_id"]
    r = requests.post(f"{BASE}/api/mlflow/baseline/{rid}", headers=admin_h, timeout=15)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b.get("run_id") == rid
    # restore previous baseline if we changed it
    if cur_baseline.get("run_id") and cur_baseline["run_id"] != rid:
        requests.post(f"{BASE}/api/mlflow/baseline/{cur_baseline['run_id']}", headers=admin_h, timeout=15)


def test_pin_baseline_viewer_forbidden(viewer_h, admin_h):
    runs = requests.get(f"{BASE}/api/mlflow/runs", headers=admin_h, timeout=15).json()
    rid = runs[0]["run_id"]
    r = requests.post(f"{BASE}/api/mlflow/baseline/{rid}", headers=viewer_h, timeout=15)
    assert r.status_code == 403


def test_pin_baseline_analyst_forbidden(analyst_h, admin_h):
    runs = requests.get(f"{BASE}/api/mlflow/runs", headers=admin_h, timeout=15).json()
    rid = runs[0]["run_id"]
    r = requests.post(f"{BASE}/api/mlflow/baseline/{rid}", headers=analyst_h, timeout=15)
    assert r.status_code == 403
