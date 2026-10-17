"""RBAC + privilege-escalation regression tests (v55).

Scenarios:
  * previewmulti (admin + escrow_agent) must get 403 MFA when active_role=escrow_agent.
  * previewmulti login with active_role=admin should succeed and return admin.
  * certifier cannot claim admin role (403 "do not hold the admin role").
  * certifier logged-in session: admin-only endpoints return 403,
    specialist endpoint /api/v1/inspections returns 200.
  * admin logged-in session: admin endpoints return 200.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@12345"
CERTIFIER = ("certifier@pmcmanagers.com", "Certify@123")
PREVIEWMULTI = ("previewmulti@pmcmanagers.com", "Preview@123")

ADMIN_ONLY = [
    "/api/v1/billing/transactions",
    "/api/v1/docusign/envelopes",
    "/api/v1/registrations",
    "/api/v1/vendors",
]


def staff_login(session, email, password, active_role):
    r = session.post(
        f"{BASE_URL}/api/v1/staff/auth/login",
        json={"email": email, "password": password, "active_role": active_role},
    )
    return r


def admin_login(session, email, password):
    r = session.post(
        f"{BASE_URL}/api/v1/admin/auth/login",
        json={"email": email, "password": password},
    )
    return r


# ---- Escalation guard ----

def test_previewmulti_escrow_role_requires_mfa():
    s = requests.Session()
    r = staff_login(s, *PREVIEWMULTI, "escrow_agent")
    assert r.status_code == 403, r.text
    assert "MFA" in r.text


def test_previewmulti_admin_role_ok():
    s = requests.Session()
    r = staff_login(s, *PREVIEWMULTI, "admin")
    assert r.status_code == 200, r.text
    assert r.json().get("active_role") == "admin"


def test_certifier_cannot_claim_admin():
    s = requests.Session()
    r = staff_login(s, *CERTIFIER, "admin")
    assert r.status_code == 403, r.text
    assert "admin role" in r.text.lower()


# ---- RBAC endpoint matrix ----

@pytest.fixture
def certifier_session():
    s = requests.Session()
    r = staff_login(s, *CERTIFIER, "certifier")
    assert r.status_code == 200, r.text
    csrf = r.json().get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


@pytest.fixture
def admin_session():
    s = requests.Session()
    r = admin_login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    if r.status_code != 200:
        # fallback password
        r = admin_login(s, ADMIN_EMAIL, "Admin@123")
    assert r.status_code == 200, r.text
    data = r.json()
    csrf = data.get("csrf_token")
    token = data.get("access_token") or data.get("token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.mark.parametrize("endpoint", ADMIN_ONLY)
def test_certifier_cannot_hit_admin_endpoints(certifier_session, endpoint):
    r = certifier_session.get(f"{BASE_URL}{endpoint}")
    assert r.status_code == 403, f"{endpoint} -> {r.status_code} {r.text[:200]}"


def test_certifier_can_hit_inspections(certifier_session):
    r = certifier_session.get(f"{BASE_URL}/api/v1/inspections")
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("endpoint", ADMIN_ONLY)
def test_admin_can_hit_admin_endpoints(admin_session, endpoint):
    r = admin_session.get(f"{BASE_URL}{endpoint}")
    assert r.status_code == 200, f"{endpoint} -> {r.status_code} {r.text[:200]}"
