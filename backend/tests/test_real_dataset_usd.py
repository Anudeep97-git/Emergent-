"""
Iteration 7 — validates the real-bank-dataset migration & USD currency switch.
Covers: /api/platform/info, /api/dashboard/summary, /api/customer/all,
        /api/customer/profile/{C001,C009}, /api/customer/decision/{C001,C009},
        /api/customer/spend-chart/C001
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ml-credit-pipeline.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@primanova.com", "password": "admin123"},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok, "no token returned"
    return tok


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ─────────── /api/platform/info ───────────
class TestPlatformInfo:
    def test_model_registry_real_dataset_usd(self):
        r = requests.get(f"{BASE_URL}/api/platform/info", timeout=15)
        assert r.status_code == 200
        reg = r.json().get("model_registry", {})
        assert reg.get("version") == "v1.1.0"
        assert reg.get("currency") == "USD"
        assert reg.get("n_customers") == 100
        assert reg.get("n_transactions") == 751
        assert reg.get("data_source") == "real_bank_dataset.xlsx"


# ─────────── /api/dashboard/summary ───────────
class TestDashboardSummary:
    def test_dashboard_counts_and_distribution(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/dashboard/summary", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("total_customers") == 100
        assert d.get("model_version") == "v1.1.0"
        assert d.get("low_risk") == 70
        assert d.get("medium_risk") == 15
        assert d.get("high_risk") == 15
        # avg_risk_score should be a float between 0 and 1
        assert 0.0 <= d.get("avg_risk_score") <= 1.0


# ─────────── /api/customer/all ───────────
class TestCustomerAll:
    def test_all_customers_usd_range(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/customer/all", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) == 100
        # Validate USD limits are in $500-$1000 range (per request)
        limits = [row["credit_limit"] for row in rows]
        assert min(limits) >= 500.0, f"min credit_limit too low: {min(limits)}"
        assert max(limits) <= 1000.0, f"max credit_limit too high: {max(limits)}"
        # All rows must have customer_id & risk_label
        for row in rows[:5]:
            assert "customer_id" in row
            assert row.get("risk_label") in {"LOW", "MEDIUM", "HIGH"}


# ─────────── /api/customer/profile/{id} ───────────
class TestCustomerProfile:
    def test_c001_profile_usd(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/customer/profile/C001", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["customer_id"] == "C001"
        assert d["credit_limit"] == 700.0
        assert abs(d["current_balance"] - 236.86) < 0.5
        assert abs(d["utilization_rate"] - 0.3384) < 0.01
        assert d["geography_region"] == "West"
        assert d["employment_status"] == "salaried"
        assert d["age"] == 40
        # Income derived: credit_limit*35 + 18000 + bureau adj => ~$30k-$80k
        assert 30000 <= d["income"] <= 80000, f"income out of expected USD band: {d['income']}"

    def test_c009_profile_high_risk(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/customer/profile/C009", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["customer_id"] == "C009"
        # High-risk customer typically has higher utilization
        assert d["utilization_rate"] > 0.5


# ─────────── /api/customer/decision/{id} ───────────
class TestCustomerDecision:
    def test_c001_low_expand(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/customer/decision/C001", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["risk_label"] == "LOW"
        assert d["action"] == "EXPAND"
        assert d["recommended_limit"] > d["current_limit"], "EXPAND must increase limit"

    def test_c009_high_restrict(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/customer/decision/C009", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["risk_label"] == "HIGH"
        assert d["action"] == "RESTRICT"
        assert d["recommended_limit"] < d["current_limit"], "RESTRICT must reduce limit"
        # Expect ~20% reduction
        ratio = d["recommended_limit"] / d["current_limit"]
        assert 0.75 <= ratio <= 0.85, f"unexpected reduction ratio {ratio}"


# ─────────── /api/customer/spend-chart/{id} ───────────
class TestSpendChart:
    def test_c001_spend_chart_12_months(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/customer/spend-chart/C001", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) == 12, f"expected 12 monthly rows, got {len(rows)}"
        # At least some rows must have positive purchases
        positive = [row for row in rows if row.get("purchases", 0) > 0]
        assert len(positive) > 0, "expected at least one month with positive purchases"
        for row in rows:
            assert "month" in row
            assert "purchases" in row
            assert "total_spend" in row
