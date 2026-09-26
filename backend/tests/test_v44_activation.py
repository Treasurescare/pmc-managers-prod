"""v44 patch tests — admin activate endpoint + directors persist + existing regression."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWD = "Admin@12345"


@pytest.fixture(scope="module")
def admin_auth():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    if r.status_code != 200:
        # fallback
        r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": "Admin@123"}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    csrf = data.get("csrf_token")
    assert token and csrf, f"missing token/csrf in {data}"
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf,
        "Content-Type": "application/json",
    })
    return s


def _invite(admin, email=None):
    email = email or f"TEST_v44_{int(time.time()*1000)}@example.com"
    r = admin.post(f"{BASE_URL}/api/v1/vendors/invite",
                   json={"email": email, "company_name": "TEST Co", "country": "GB"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()  # {vendor_ref, email, verify_url}


# ---- Activate endpoint ----
def test_activate_unauth_401():
    r = requests.post(f"{BASE_URL}/api/v1/vendors/PMC-SUP-000001/activate",
                      json={"mode": "resend_link"}, timeout=30)
    assert r.status_code in (401, 403), r.status_code


def test_activate_404_missing(admin_auth):
    r = admin_auth.post(f"{BASE_URL}/api/v1/vendors/PMC-SUP-999999/activate",
                        json={"mode": "resend_link"})
    assert r.status_code == 404, r.text


def test_activate_resend_link_ok(admin_auth):
    inv = _invite(admin_auth)
    r = admin_auth.post(f"{BASE_URL}/api/v1/vendors/{inv['vendor_ref']}/activate",
                        json={"mode": "resend_link"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["mode"] == "resend_link"
    assert "verify_url" in j and j["email"] == inv["email"].lower()


def test_activate_set_password_missing_pwd_400(admin_auth):
    inv = _invite(admin_auth)
    r = admin_auth.post(f"{BASE_URL}/api/v1/vendors/{inv['vendor_ref']}/activate",
                        json={"mode": "set_password"})
    # pydantic min_length=8 on password when supplied; but None is allowed → handler raises 400
    assert r.status_code == 400, r.text


def test_activate_set_password_and_login(admin_auth):
    inv = _invite(admin_auth)
    pwd = "TestPass12345!"
    r = admin_auth.post(f"{BASE_URL}/api/v1/vendors/{inv['vendor_ref']}/activate",
                        json={"mode": "set_password", "password": pwd})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True and j["mode"] == "set_password" and j["is_active"] is True
    # already-active guard
    r2 = admin_auth.post(f"{BASE_URL}/api/v1/vendors/{inv['vendor_ref']}/activate",
                         json={"mode": "resend_link"})
    assert r2.status_code == 400, r2.text
    # vendor can login
    lr = requests.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                       json={"email": inv["email"], "password": pwd}, timeout=30)
    assert lr.status_code == 200, f"vendor login failed: {lr.status_code} {lr.text}"


# ---- Regression: invite + list ----
def test_invite_and_list(admin_auth):
    inv = _invite(admin_auth)
    r = admin_auth.get(f"{BASE_URL}/api/v1/vendors")
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", data.get("vendors", []))
    assert any(v.get("vendor_ref") == inv["vendor_ref"] for v in items)


# ---- Regression: verify/{token}/complete ----
def test_verify_complete_flow(admin_auth):
    inv = _invite(admin_auth)
    token = inv["verify_url"].rstrip("/").split("/")[-1]
    r = requests.post(f"{BASE_URL}/api/v1/vendors/verify/{token}/complete",
                      json={"password": "Verify12345!"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


# ---- Directors payload persistence ----
def test_directors_persist():
    # start a registration
    email = f"TEST_dir_{int(time.time()*1000)}@example.com"
    r = requests.post(f"{BASE_URL}/api/v1/registrations",
                      json={"email": email, "company_name": "TEST Co", "country": "GB",
                            "data_processing_consent": True}, timeout=30)
    assert r.status_code in (200, 201), r.text
    j = r.json()
    reg_id = j.get("id")
    token = j.get("magic_token")
    assert reg_id and token, j

    directors = [{
        "full_name": "Jane Doe", "role": "Director", "nationality": "GB",
        "id_number": "X123", "ownership_percent": "50", "address": "1 Bond St",
    }]
    pr = requests.patch(f"{BASE_URL}/api/v1/registrations/{reg_id}?token={token}",
                        json={"directors": directors}, timeout=30)
    assert pr.status_code == 200, pr.text
    gr = requests.get(f"{BASE_URL}/api/v1/registrations/resume/{token}", timeout=30)
    assert gr.status_code == 200, gr.text
    body = gr.json()
    got = body.get("directors") or body.get("registration", {}).get("directors")
    assert got and got[0]["full_name"] == "Jane Doe", body
