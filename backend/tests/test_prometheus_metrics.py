"""Pytest suite for Prometheus /api/metrics/ exporter (iteration 4).

Validates content-type, all expected metric families, histogram buckets,
counter increments after generating traffic, endpoint label normalization
(C001 -> {customer_id}), and 5xx counter increment after simulate-error.
"""
import re
import time
import pytest
import requests


def _metrics_url(base_url):
    return f"{base_url}/api/metrics/"


def _login_url(base_url):
    return f"{base_url}/api/auth/login"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_token(base_url):
    r = requests.post(_login_url(base_url), json={"email": "admin@primanova.com", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _get_metrics(base_url):
    r = requests.get(_metrics_url(base_url), timeout=15)
    assert r.status_code == 200, f"metrics endpoint not 200: {r.status_code}"
    return r


def _parse_value(body: str, metric_pattern: str) -> float | None:
    """Find the first non-comment line matching metric_pattern, return its value."""
    rx = re.compile(rf"^{metric_pattern}\s+([0-9eE+\-\.]+)\s*$", re.MULTILINE)
    m = rx.search(body)
    return float(m.group(1)) if m else None


def _counter_total(body: str, endpoint: str, method: str = "GET", status_class: str = "2xx") -> float:
    """Read c1b_api_requests_total for given labels (order-independent)."""
    rx = re.compile(
        r'^c1b_api_requests_total\{([^}]*)\}\s+([0-9eE+\-\.]+)\s*$', re.MULTILINE
    )
    for m in rx.finditer(body):
        labels = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if (labels.get("endpoint") == endpoint
            and labels.get("method") == method
            and labels.get("status_class") == status_class):
            return float(m.group(2))
    return 0.0


# ---------- tests ----------
class TestMetricsEndpointShape:
    """GET /api/metrics/ basic contract."""

    def test_unauthenticated_200_and_content_type(self):
        # generate one request so histogram lines materialise
        try:
            requests.get(f"{BASE_URL}/api/dashboard/summary", timeout=10)
        except Exception:
            pass
        r = _get_metrics()
        ct = r.headers.get("content-type", "")
        assert "text/plain" in ct
        assert "version=0.0.4" in ct
        # at least the 32 baseline lines (HELP/TYPE for all expected families)
        assert r.text.count("\n") >= 30

    def test_help_and_type_lines_present(self):
        body = _get_metrics().text
        assert "# HELP c1b_api_request_latency_seconds Latency of FastAPI requests in seconds" in body
        assert "# TYPE c1b_api_request_latency_seconds histogram" in body

    def test_error_rate_gauge_numeric(self):
        body = _get_metrics().text
        v = _parse_value(body, r"c1b_api_error_rate")
        assert v is not None and 0.0 <= v <= 1.0

    def test_risk_tier_pct_sums_to_one(self):
        body = _get_metrics().text
        parts = {}
        for tier in ("low", "medium", "high"):
            parts[tier] = _parse_value(body, rf'c1b_risk_tier_pct\{{tier="{tier}"\}}')
            assert parts[tier] is not None, f"missing tier {tier}"
        total = sum(parts.values())
        assert 0.95 <= total <= 1.05, f"tiers don't sum to ~1: {parts} total={total}"

    def test_risk_tier_drift_gauges_present(self):
        body = _get_metrics().text
        for tier in ("low", "medium", "high"):
            v = _parse_value(body, rf'c1b_risk_tier_drift_pct\{{tier="{tier}"\}}')
            assert v is not None, f"missing drift gauge for {tier}"

    def test_model_gauges_present(self):
        body = _get_metrics().text
        auc = _parse_value(body, r"c1b_model_roc_auc")
        drift = _parse_value(body, r"c1b_model_auc_drift")
        assert auc is not None
        assert drift is not None

    def test_high_threshold_is_0_75(self):
        body = _get_metrics().text
        v = _parse_value(body, r"c1b_risk_tier_high_threshold")
        assert v == 0.75

    def test_histogram_buckets_present(self, admin_headers):
        # generate one request to ensure the histogram is materialised in the registry
        requests.get(f"{BASE_URL}/api/dashboard/summary", headers=admin_headers, timeout=10)
        time.sleep(0.3)
        body = _get_metrics().text
        expected = ["0.025", "0.05", "0.1", "0.2", "0.3", "0.5", "1.0", "2.0", "5.0", "+Inf"]
        for le in expected:
            # bucket lines look like: c1b_api_request_latency_seconds_bucket{...,le="0.05"} 3.0
            pat = rf'c1b_api_request_latency_seconds_bucket\{{[^}}]*le="{re.escape(le)}"[^}}]*\}}'
            assert re.search(pat, body), f"missing histogram bucket le={le}"


class TestCounterAndLabelNormalization:
    """Hit endpoints and verify counters + endpoint label normalization."""

    def test_dashboard_summary_counter_increases_by_5(self, admin_headers):
        ep = "/api/dashboard/summary"
        before = _counter_total(_get_metrics().text, ep)
        for _ in range(5):
            r = requests.get(f"{BASE_URL}{ep}", headers=admin_headers, timeout=15)
            assert r.status_code == 200
        # tiny delay to let middleware flush
        time.sleep(0.5)
        after = _counter_total(_get_metrics().text, ep)
        delta = after - before
        assert delta >= 5, f"counter did not increase by 5: before={before} after={after}"

    def test_customer_id_endpoint_label_normalized(self, admin_headers):
        # hit a path containing C001 — should be normalized to {customer_id}
        r = requests.get(f"{BASE_URL}/api/customer/C001/profile", headers=admin_headers, timeout=15)
        # don't assert on status (may be 200/404 depending on data) — only that label is normalised
        assert r.status_code in (200, 404, 422)
        time.sleep(0.3)
        body = _get_metrics().text
        # there should be NO raw "C001" inside any endpoint label
        bad = re.findall(r'endpoint="[^"]*\bC001\b[^"]*"', body)
        assert not bad, f"endpoint label contains raw customer id: {bad[:3]}"
        # And there SHOULD be at least one endpoint with {customer_id} placeholder
        good = re.findall(r'endpoint="[^"]*\{customer_id\}[^"]*"', body)
        assert good, "no endpoint label with {customer_id} placeholder found"


class TestErrorCounter:
    """POST /api/observability/simulate-error -> 5xx counter increments."""

    def test_simulate_error_increments_5xx_counter(self, admin_headers):
        ep = "/api/observability/simulate-error"
        before = _counter_total(_get_metrics().text, ep, method="POST", status_class="5xx")
        r = requests.post(f"{BASE_URL}{ep}", headers=admin_headers, timeout=15)
        assert r.status_code == 500, f"simulate-error should be 500, got {r.status_code}"
        time.sleep(0.3)
        after = _counter_total(_get_metrics().text, ep, method="POST", status_class="5xx")
        assert after - before >= 1, f"5xx counter did not increase: before={before} after={after}"



# ---------------------------------------------------------------------
# Iteration 5: Prometheus multi-process support
# ---------------------------------------------------------------------
class TestMetricsInfoEndpoint:
    """GET /api/metrics/info — single-process mode in current Emergent runtime."""

    def test_info_endpoint_200_and_shape(self):
        r = requests.get(f"{BASE_URL}/api/metrics/info", timeout=15)
        assert r.status_code == 200, f"/api/metrics/info not 200: {r.status_code} {r.text}"
        data = r.json()
        # Shape contract
        assert set(data.keys()) >= {"mode", "multiproc_dir", "pid"}
        assert data["mode"] in ("single-process", "multiprocess")
        assert isinstance(data["multiproc_dir"], str)
        assert isinstance(data["pid"], str)
        assert data["pid"].isdigit() and int(data["pid"]) > 0

    def test_info_returns_single_process_in_emergent_runtime(self):
        # Current supervisor config uses uvicorn --workers 1 (no PROMETHEUS_MULTIPROC_DIR)
        r = requests.get(f"{BASE_URL}/api/metrics/info", timeout=15)
        data = r.json()
        assert data["mode"] == "single-process", f"expected single-process, got {data}"
        assert data["multiproc_dir"] == "", f"multiproc_dir should be empty: {data}"

    def test_info_unauthenticated(self):
        # Same scrape pattern as /api/metrics/ — no Authorization required
        r = requests.get(f"{BASE_URL}/api/metrics/info", timeout=15)
        assert r.status_code == 200


class TestMultiprocBootstrap:
    """Static checks: bootstrap module exposes the required helpers, gauges declare modes."""

    def test_bootstrap_module_exports(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from services import metrics_bootstrap as mb
        assert callable(mb.is_multiproc)
        assert callable(mb.prepare_multiproc_dir)
        assert callable(mb.install_worker_death_hook)
        # In current runtime (no env var), is_multiproc must be False
        assert mb.is_multiproc() is False

    def test_server_invokes_bootstrap_before_routers(self):
        # Static source-level check
        src = open("/app/backend/server.py").read()
        i_prep = src.find("prepare_multiproc_dir()")
        i_hook = src.find("install_worker_death_hook()")
        i_routers = src.find("from routers import")
        assert i_prep != -1 and i_hook != -1 and i_routers != -1
        assert i_prep < i_routers, "prepare_multiproc_dir() must run BEFORE importing routers"
        assert i_hook < i_routers, "install_worker_death_hook() must run BEFORE importing routers"
