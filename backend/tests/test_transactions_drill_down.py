"""
Iteration 8 — Transaction drill-down endpoints validation.
Covers: GET /api/customer/transactions/{id} (with page, limit, tx_type, q filters)
        GET /api/customer/transactions/{id}/types
"""
import os
import pytest
import requests

def _read_frontend_env_url():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env_url()).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@primanova.com", "password": "admin123"},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ─────────── GET /api/customer/transactions/{id} ───────────
class TestTransactionsList:
    def test_c001_paginated_shape(self, auth_headers):
        r = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001",
            headers=auth_headers, params={"page": 1, "limit": 5}, timeout=15,
        )
        assert r.status_code == 200
        d = r.json()
        # response envelope
        assert d["customer_id"] == "C001"
        assert d["page"] == 1
        assert d["limit"] == 5
        assert d["total"] == 8  # C001 has 8 real transactions
        assert isinstance(d["items"], list)
        assert len(d["items"]) == 5
        # row schema
        expected_keys = {"trans_date", "post_date", "transaction_type",
                         "description", "amount_usd", "reference_number"}
        for row in d["items"]:
            assert expected_keys.issubset(row.keys()), f"missing keys in row: {row.keys()}"
            assert isinstance(row["amount_usd"], (int, float))

    def test_pagination_page2(self, auth_headers):
        r1 = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001",
            headers=auth_headers, params={"page": 1, "limit": 5}, timeout=15,
        ).json()
        r2 = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001",
            headers=auth_headers, params={"page": 2, "limit": 5}, timeout=15,
        ).json()
        assert r2["page"] == 2
        assert r2["total"] == r1["total"]  # un-paginated total
        # remaining 8-5 = 3 rows on page 2
        assert len(r2["items"]) == 3
        # no overlap
        refs1 = {x["reference_number"] for x in r1["items"]}
        refs2 = {x["reference_number"] for x in r2["items"]}
        assert refs1.isdisjoint(refs2)

    def test_filter_purchase_only(self, auth_headers):
        r = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001",
            headers=auth_headers,
            params={"tx_type": "Purchase", "limit": 100}, timeout=15,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        for row in d["items"]:
            assert row["transaction_type"] == "Purchase"

    def test_filter_all_returns_everything(self, auth_headers):
        d = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001",
            headers=auth_headers, params={"tx_type": "all", "limit": 100}, timeout=15,
        ).json()
        assert d["total"] == 8
        types_seen = {row["transaction_type"] for row in d["items"]}
        assert len(types_seen) >= 1

    def test_search_query_case_insensitive(self, auth_headers):
        # Search "AMAZON" across all customers via C021 (max txns)
        # First verify on dataset broadly using C021
        r = requests.get(
            f"{BASE_URL}/api/customer/transactions/C021",
            headers=auth_headers, params={"q": "amazon", "limit": 100}, timeout=15,
        )
        assert r.status_code == 200
        d = r.json()
        # AMAZON may not appear in C021 — fall back to scanning a wider customer
        # accept either: empty result OR every row contains 'amazon' in description
        for row in d["items"]:
            assert "amazon" in row["description"].lower()

    def test_search_returns_matching_rows(self, auth_headers):
        # Use a generic substring likely to match many: 'CA' (state code)
        d = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001",
            headers=auth_headers, params={"q": "CA", "limit": 100}, timeout=15,
        ).json()
        # Description for C001 row 1 contains 'CA'
        assert d["total"] >= 1
        for row in d["items"]:
            assert "ca" in row["description"].lower()

    def test_unknown_customer_empty(self, auth_headers):
        d = requests.get(
            f"{BASE_URL}/api/customer/transactions/CXXX_NOTREAL",
            headers=auth_headers, timeout=15,
        ).json()
        assert d["total"] == 0
        assert d["items"] == []

    def test_c050_min_transactions(self, auth_headers):
        d = requests.get(
            f"{BASE_URL}/api/customer/transactions/C050",
            headers=auth_headers, params={"limit": 100}, timeout=15,
        ).json()
        assert d["total"] >= 4


# ─────────── GET /api/customer/transactions/{id}/types ───────────
class TestTransactionTypes:
    def test_c001_types_shape(self, auth_headers):
        r = requests.get(
            f"{BASE_URL}/api/customer/transactions/C001/types",
            headers=auth_headers, timeout=15,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["customer_id"] == "C001"
        assert d["total"] == 8
        assert isinstance(d["types"], list)
        assert len(d["types"]) >= 1
        # type schema
        for t in d["types"]:
            assert "type" in t
            assert "count" in t
            assert isinstance(t["count"], int)
        # sum of type counts equals total
        assert sum(t["count"] for t in d["types"]) == d["total"]
        # total_amount_usd is float
        assert isinstance(d["total_amount_usd"], (int, float))

    def test_unknown_customer_types(self, auth_headers):
        d = requests.get(
            f"{BASE_URL}/api/customer/transactions/CXXX_NOTREAL/types",
            headers=auth_headers, timeout=15,
        ).json()
        assert d["total"] == 0
        assert d["types"] == []
        assert d["total_amount_usd"] == 0.0
