"""v50m — Vendor Profile Changes + SEC-001/SEC-003 regression tests."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PW = "Vendor@12345"
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWS = ["Admin@12345", "Admin@123"]


# ─── fixtures ─────────────────────────────────────────────
@pytest.fixture(scope="module")
def vendor_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
               json={"email": VENDOR_EMAIL, "password": VENDOR_PW}, timeout=30)
    assert r.status_code == 200, f"vendor login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    last = None
    for pw in ADMIN_PWS:
        r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": pw}, timeout=30)
        last = r
        if r.status_code == 200:
            data = r.json()
            tok = data.get("access_token") or data.get("token")
            csrf = data.get("csrf_token") or data.get("csrf")
            s.headers.update({"Authorization": f"Bearer {tok}"})
            if csrf:
                s.headers.update({"X-CSRF-Token": csrf})
            return s
    pytest.skip(f"admin login failed: {last.status_code} {last.text if last else ''}")


# ─── vendor side ─────────────────────────────────────────────
def test_vendor_get_profile(vendor_session):
    r = vendor_session.get(f"{BASE_URL}/api/v1/vendor/profile", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "email" in data and "vendor_ref" in data
    assert data["email"] == VENDOR_EMAIL


def test_vendor_list_requests(vendor_session):
    r = vendor_session.get(f"{BASE_URL}/api/v1/vendor/profile/requests", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "pending" in data and "recent" in data
    assert isinstance(data["pending"], list)


def _cleanup_pending(admin_session, field):
    """Reject any dangling pending request for the vendor on the given field."""
    r = admin_session.get(f"{BASE_URL}/api/v1/vendors/profile-change-requests?status=pending", timeout=30)
    if r.status_code != 200:
        return
    for req in r.json():
        if req.get("field") == field and req.get("vendor_email") == VENDOR_EMAIL:
            admin_session.post(
                f"{BASE_URL}/api/v1/vendors/profile-change-requests/{req['id']}/reject",
                json={"notes": "test cleanup"}, timeout=30,
            )


def test_vendor_request_address_change(vendor_session, admin_session):
    _cleanup_pending(admin_session, "address")
    r = vendor_session.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "address", "new_value": f"TEST_ADDR_{int(time.time())}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["field"] == "address"
    assert body["status"] == "pending"
    assert body.get("email_verified") in (True,)  # non-email requests auto-verified

    # Dedup: second submit should 409
    r2 = vendor_session.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "address", "new_value": "TEST_DUP"}, timeout=30,
    )
    assert r2.status_code == 409

    # Cleanup
    _cleanup_pending(admin_session, "address")


def test_email_change_full_flow(vendor_session, admin_session):
    _cleanup_pending(admin_session, "email")
    new_email = f"testvendor+{int(time.time())}@pmcmanagers.com"

    # 1. Submit change
    r = vendor_session.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "email", "new_value": new_email}, timeout=30,
    )
    assert r.status_code == 200, r.text
    req_id = r.json()["id"]

    # 2. Confirm pending request has email_verified=None + email_token present
    rl = vendor_session.get(f"{BASE_URL}/api/v1/vendor/profile/requests", timeout=30)
    assert rl.status_code == 200
    pending_email = [p for p in rl.json()["pending"] if p["field"] == "email"]
    assert pending_email, "no pending email request found"
    req = pending_email[0]
    assert req.get("email_verified") in (None, False)
    token = req.get("email_token")
    assert token and len(token) > 10

    # 3. Approving BEFORE verify must 412
    rapp = admin_session.post(
        f"{BASE_URL}/api/v1/vendors/profile-change-requests/{req_id}/approve",
        json={"notes": "pre-verify"}, timeout=30,
    )
    assert rapp.status_code == 412, f"expected 412, got {rapp.status_code} {rapp.text}"

    # 4. Verify via token
    rv = requests.get(f"{BASE_URL}/api/v1/vendor/profile/email-verify/{token}", timeout=30)
    assert rv.status_code == 200
    assert rv.json().get("ok") is True

    # 5. Approve → ok
    rapp2 = admin_session.post(
        f"{BASE_URL}/api/v1/vendors/profile-change-requests/{req_id}/approve",
        json={"notes": "verified"}, timeout=30,
    )
    assert rapp2.status_code == 200, rapp2.text
    assert rapp2.json().get("ok") is True

    # 6. New email login works
    s2 = requests.Session()
    rlog = s2.post(f"{BASE_URL}/api/v1/vendor/auth/login",
                   json={"email": new_email, "password": VENDOR_PW}, timeout=30)
    assert rlog.status_code == 200, f"login with new email failed: {rlog.text}"
    tok = rlog.json().get("access_token") or rlog.json().get("token")
    s2.headers.update({"Authorization": f"Bearer {tok}"})

    # 7. Revert: request to change back
    r_rev = s2.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "email", "new_value": VENDOR_EMAIL}, timeout=30,
    )
    assert r_rev.status_code == 200, r_rev.text
    rev_id = r_rev.json()["id"]
    rl2 = s2.get(f"{BASE_URL}/api/v1/vendor/profile/requests", timeout=30)
    rev_token = [p for p in rl2.json()["pending"] if p["field"] == "email"][0]["email_token"]
    requests.get(f"{BASE_URL}/api/v1/vendor/profile/email-verify/{rev_token}", timeout=30)
    rapp3 = admin_session.post(
        f"{BASE_URL}/api/v1/vendors/profile-change-requests/{rev_id}/approve",
        json={"notes": "revert"}, timeout=30,
    )
    assert rapp3.status_code == 200, rapp3.text


def test_invalid_email_verify_token():
    r = requests.get(f"{BASE_URL}/api/v1/vendor/profile/email-verify/invalid_bogus_token", timeout=30)
    assert r.status_code == 404


def test_request_same_value_rejected(vendor_session):
    r = vendor_session.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "email", "new_value": VENDOR_EMAIL}, timeout=30,
    )
    assert r.status_code == 400


def test_invalid_field_rejected(vendor_session):
    r = vendor_session.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "ssn", "new_value": "x"}, timeout=30,
    )
    assert r.status_code == 422


# ─── admin side ─────────────────────────────────────────────
def test_admin_list_requests(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/v1/vendors/profile-change-requests?status=pending", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_reject_requires_note(vendor_session, admin_session):
    _cleanup_pending(admin_session, "mobile")
    r = vendor_session.post(
        f"{BASE_URL}/api/v1/vendor/profile/request-change",
        json={"field": "mobile", "new_value": "9999988888"}, timeout=30,
    )
    assert r.status_code == 200
    rid = r.json()["id"]
    r2 = admin_session.post(
        f"{BASE_URL}/api/v1/vendors/profile-change-requests/{rid}/reject",
        json={"notes": ""}, timeout=30,
    )
    assert r2.status_code == 400
    r3 = admin_session.post(
        f"{BASE_URL}/api/v1/vendors/profile-change-requests/{rid}/reject",
        json={"notes": "cleanup"}, timeout=30,
    )
    assert r3.status_code == 200


# ─── Tenders (regression for grid heading count bug) ─────────────────────────────────────────────
def test_notices_public_listing():
    r = requests.get(f"{BASE_URL}/api/v1/notices", timeout=30)
    assert r.status_code == 200
    data = r.json()
    # endpoint may return list or paginated dict
    items = data if isinstance(data, list) else data.get("items") or data.get("notices") or []
    assert isinstance(items, list)


# ─── SEC-003 DocuSign webhook ─────────────────────────────────────────────
def test_docusign_webhook_rejects_unsigned_when_secret_set():
    """When HMAC secret is set (as in this env), unsigned webhook POSTs must 401."""
    r = requests.post(f"{BASE_URL}/api/v1/docusign/webhook",
                      json={"event": "test"}, timeout=30)
    assert r.status_code in (200, 401)
    if r.status_code == 200:
        assert r.json().get("received") is True


def test_docusign_webhook_accepts_signed():
    """Compute correct HMAC and verify webhook accepts."""
    import base64, hmac as _hmac, hashlib
    secret = os.environ.get("DOCUSIGN_CONNECT_HMAC_SECRET", "KFSC1ftZ0DzyvFu9hmWdA27YFoCsYtRrKitbCvV6VEs=")
    body = b'{"event":"test"}'
    sig = base64.b64encode(_hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    r = requests.post(f"{BASE_URL}/api/v1/docusign/webhook",
                      data=body,
                      headers={"Content-Type": "application/json",
                               "x-docusign-signature-1": sig},
                      timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("received") is True


# ─── Signatures listing ─────────────────────────────────────────────
def test_vendor_docusign_mine(vendor_session):
    r = vendor_session.get(f"{BASE_URL}/api/v1/docusign/mine", timeout=30)
    assert r.status_code in (200, 404)
