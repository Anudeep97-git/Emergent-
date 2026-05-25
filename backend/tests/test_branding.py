"""Tests for /api/platform/branding endpoints (GET unauth, PUT admin, POST reset admin)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ml-credit-pipeline.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@primanova.com", "admin123")


@pytest.fixture(scope="module")
def customer_token():
    return _login("customer@primanova.com", "customer123")


@pytest.fixture(autouse=True, scope="module")
def _reset_at_end(admin_token):
    yield
    requests.post(f"{API}/platform/branding/reset",
                  headers={"Authorization": f"Bearer {admin_token}"}, timeout=20)


# ---------- GET /api/platform/branding ----------
class TestGetBranding:
    def test_get_unauthenticated_returns_defaults(self):
        r = requests.get(f"{API}/platform/branding", timeout=20)
        assert r.status_code == 200
        data = r.json()
        for k in ("app_name", "app_tagline", "logo_initials",
                  "primary_color", "accent_color",
                  "success_color", "warning_color", "danger_color",
                  "support_email"):
            assert k in data, f"missing key {k} in branding response"
        assert "_id" not in data
        assert isinstance(data["app_name"], str)


# ---------- PUT /api/platform/branding ----------
class TestUpdateBranding:
    def test_put_without_auth_returns_401_or_403(self):
        r = requests.put(f"{API}/platform/branding", json={"app_name": "Hack"}, timeout=20)
        assert r.status_code in (401, 403)

    def test_put_with_customer_role_returns_403(self, customer_token):
        r = requests.put(
            f"{API}/platform/branding",
            json={"app_name": "ShouldFail"},
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=20,
        )
        assert r.status_code == 403

    def test_put_with_admin_updates_and_merges(self, admin_token):
        new_name = "TEST_Prima Test"
        new_accent = "#FF00AA"
        r = requests.put(
            f"{API}/platform/branding",
            json={"app_name": new_name, "accent_color": new_accent},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["app_name"] == new_name
        assert data["accent_color"] == new_accent
        # untouched fields should still have defaults
        assert data["logo_initials"]  # non-empty
        assert data.get("updated_by") == "admin@primanova.com"

        # Verify persistence via GET
        g = requests.get(f"{API}/platform/branding", timeout=20).json()
        assert g["app_name"] == new_name
        assert g["accent_color"] == new_accent


# ---------- POST /api/platform/branding/reset ----------
class TestResetBranding:
    def test_reset_requires_admin(self, customer_token):
        r = requests.post(
            f"{API}/platform/branding/reset",
            headers={"Authorization": f"Bearer {customer_token}"},
            timeout=20,
        )
        assert r.status_code == 403

    def test_reset_clears_to_defaults(self, admin_token):
        # First write a custom value
        requests.put(
            f"{API}/platform/branding",
            json={"app_name": "TEST_WillBeReset", "accent_color": "#123456"},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        # Reset
        r = requests.post(
            f"{API}/platform/branding/reset",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["app_name"] == "Prima Nova"
        assert data["accent_color"].upper() == "#6366F1"
        assert data["logo_initials"] == "PN"
