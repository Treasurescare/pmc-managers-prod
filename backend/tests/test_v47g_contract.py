"""v47g contract tests: admin bid detail + DocuSign resend/combined-pdf contract validation."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://tender-hub-57.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS = "Admin@12345"
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PASS = "Vendor@12345"

BID_ID = "6ab7349dbd6e363382301c69"
ENV_COMPLETED = "3f85221f-7a63-808b-801f-0a3869820a7f"
ENV_SENT = "03422578-a120-818d-803e-f834fc85076d"
ENV_NONEXIST = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(scope="module")
def admin_auth():
    r = requests.post(f"{BASE_URL}/api/v1/admin/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    d = r.json()
    return {"token": d.get("token") or d.get("access_token"),
            "csrf": d.get("csrf_token") or d.get("csrf"),
            "raw": d}


@pytest.fixture(scope="module")
def vendor_auth():
    for path in ["/api/v1/vendor/auth/login", "/api/v1/vendors/auth/login", "/api/v1/auth/vendor/login"]:
        r = requests.post(f"{BASE_URL}{path}",
                          json={"email": VENDOR_EMAIL, "password": VENDOR_PASS}, timeout=30)
        if r.status_code == 200:
            d = r.json()
            return {"token": d.get("token") or d.get("access_token"), "path": path}
    pytest.skip(f"vendor login failed all paths: {r.status_code} {r.text[:200]}")


# --- Admin Bid Detail ---
def test_admin_bid_detail_ok(admin_auth):
    h = {"Authorization": f"Bearer {admin_auth['token']}"}
    r = requests.get(f"{BASE_URL}/api/v1/bids/admin/{BID_ID}", headers=h, timeout=30)
    assert r.status_code == 200, f"got {r.status_code}: {r.text[:300]}"
    d = r.json()
    # required fields
    for k in ["bid_ref", "status"]:
        assert k in d, f"missing {k}; keys={list(d.keys())}"
    # documents and workflow must exist even if empty
    assert isinstance(d.get("documents", []), list)
    assert isinstance(d.get("workflow_history", []), list)


def test_admin_bid_detail_forbidden_for_vendor(vendor_auth):
    h = {"Authorization": f"Bearer {vendor_auth['token']}"}
    r = requests.get(f"{BASE_URL}/api/v1/bids/admin/{BID_ID}", headers=h, timeout=30)
    assert r.status_code in (401, 403), f"vendor should be denied, got {r.status_code}"


# --- DocuSign Resend contract ---
def test_docusign_resend_completed_returns_400(admin_auth):
    h = {"Authorization": f"Bearer {admin_auth['token']}"}
    if admin_auth.get("csrf"):
        h["X-CSRF-Token"] = admin_auth["csrf"]
    r = requests.post(f"{BASE_URL}/api/v1/docusign/envelopes/{ENV_COMPLETED}/resend",
                      headers=h, timeout=30)
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
    body = r.text.lower()
    assert "status" in body or "completed" in body, f"error msg should mention status: {r.text[:200]}"


def test_docusign_resend_sent_200_or_502(admin_auth):
    """Hit backend internally to bypass Cloudflare's 502 HTML replacement."""
    # Login internally to get a fresh token (external token still valid too)
    lr = requests.post("http://localhost:8001/api/v1/admin/auth/login",
                       json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    tok = lr.json().get("token") or lr.json().get("access_token")
    h = {"Authorization": f"Bearer {tok}"}
    r = requests.post(f"http://localhost:8001/api/v1/docusign/envelopes/{ENV_SENT}/resend",
                      headers=h, timeout=45)
    assert r.status_code in (200, 502), f"expected 200|502, got {r.status_code}: {r.text[:300]}"
    if r.status_code == 502:
        body = r.json()
        detail = str(body.get("detail", "")).lower()
        assert "docusign" in detail and "resend" in detail, f"bad 502 body: {body}"


def test_docusign_resend_nonexistent_404(admin_auth):
    h = {"Authorization": f"Bearer {admin_auth['token']}"}
    if admin_auth.get("csrf"):
        h["X-CSRF-Token"] = admin_auth["csrf"]
    r = requests.post(f"{BASE_URL}/api/v1/docusign/envelopes/{ENV_NONEXIST}/resend",
                      headers=h, timeout=30)
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:300]}"


# --- Combined PDF ---
def test_docusign_combined_pdf_no_crash(admin_auth):
    h = {"Authorization": f"Bearer {admin_auth['token']}"}
    r = requests.get(f"{BASE_URL}/api/v1/docusign/envelopes/{ENV_COMPLETED}/combined-pdf",
                     headers=h, timeout=45)
    # must not crash; either PDF or well-formed 4xx/502
    assert r.status_code in (200, 400, 401, 403, 404, 409, 502), f"unexpected {r.status_code}: {r.text[:200]}"
    if r.status_code == 200:
        ct = r.headers.get("content-type", "")
        assert "pdf" in ct.lower() or len(r.content) > 100
