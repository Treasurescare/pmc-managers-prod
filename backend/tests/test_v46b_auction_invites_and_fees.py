"""v46b — Auction invitations, fee-checkout, and DPR analyze-json regression."""
import os
import time
import base64
import io
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
RA_API = f"{BASE}/api/v1/reverse-auctions"
BILLING = f"{BASE}/api/v1/billing"
TP = f"{BASE}/api/v1/tender-pro"

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PW = "Admin@12345"
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PW = "Vendor@12345"

DPR_URL = "https://customer-assets-4nw71qhi.emergentagent.net/job_tender-hub-57/artifacts/a3p999vz_KMT%20DPR%20and%20FInancials.pdf"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    tok = d.get("token") or d.get("access_token")
    csrf = d.get("csrf_token") or d.get("csrf")
    assert tok and csrf
    s.headers.update({"Authorization": f"Bearer {tok}", "X-CSRF-Token": csrf})
    return s


@pytest.fixture(scope="module")
def vendor():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/vendor/auth/login",
               json={"email": VENDOR_EMAIL, "password": VENDOR_PW}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return s


@pytest.fixture(scope="module")
def auction_id(admin):
    # Reuse existing non-closed auction if possible; otherwise create one
    r = admin.get(RA_API, timeout=30)
    assert r.status_code == 200
    for a in r.json().get("items", []):
        if a.get("status") in ("draft", "live"):
            return a["id"]
    # Need a notice_ref -> pick any existing notice
    n = admin.get(f"{BASE}/api/v1/notices", timeout=30)
    notice_ref = None
    if n.status_code == 200:
        items = n.json() if isinstance(n.json(), list) else n.json().get("items", [])
        if items:
            notice_ref = items[0].get("notice_ref")
    assert notice_ref, "no notice available to seed auction"
    r = admin.post(RA_API, json={
        "notice_ref": notice_ref, "title": "TEST_v46b_auction",
        "currency": "USD", "starting_price": 1000, "floor_price": 100,
        "min_decrement": 10, "duration_minutes": 30, "anti_snipe_seconds": 60,
    }, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()["id"]


# ---------- Invitations ----------
class TestInvitations:
    def test_invite_admin_only(self, auction_id):
        r = requests.post(f"{RA_API}/{auction_id}/invite",
                          json={"emails": ["x@y.com"]}, timeout=30)
        assert r.status_code in (401, 403)

    def test_invite_invalid_auction_404(self, admin):
        r = admin.post(f"{RA_API}/507f1f77bcf86cd799439011/invite",
                       json={"emails": [VENDOR_EMAIL]}, timeout=30)
        assert r.status_code == 404

    def test_invite_filters_invalid_emails(self, admin, auction_id):
        r = admin.post(f"{RA_API}/{auction_id}/invite",
                       json={"emails": ["", "no-at-sign", VENDOR_EMAIL],
                             "note": "TEST_v46b"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        # Only 1 valid should be counted
        assert d["count"] == 1
        emails = [x["email"] for x in d["invited"]]
        assert VENDOR_EMAIL in emails
        # vendor_ref should resolve
        vinv = [x for x in d["invited"] if x["email"] == VENDOR_EMAIL][0]
        assert vinv.get("vendor_ref") == "PMC-VEN-MANUAL-01"

    def test_invite_dedupe_resent_true(self, admin, auction_id):
        # second call with same email
        r = admin.post(f"{RA_API}/{auction_id}/invite",
                       json={"emails": [VENDOR_EMAIL]}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] == 1
        assert d["invited"][0]["resent"] is True

    def test_list_invitations_admin(self, admin, auction_id):
        r = admin.get(f"{RA_API}/{auction_id}/invitations", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d
        found = [x for x in d["items"] if x.get("email") == VENDOR_EMAIL]
        assert len(found) == 1
        row = found[0]
        assert "status" in row
        assert "joined" in row
        assert row.get("vendor_ref") == "PMC-VEN-MANUAL-01"

    def test_list_invitations_requires_admin(self, auction_id):
        r = requests.get(f"{RA_API}/{auction_id}/invitations", timeout=30)
        assert r.status_code in (401, 403)

    def test_resolve_invite_public(self, admin, auction_id):
        # get token
        r = admin.get(f"{RA_API}/{auction_id}/invitations", timeout=30)
        token = [x for x in r.json()["items"] if x["email"] == VENDOR_EMAIL][0]["token"]
        rr = requests.get(f"{RA_API}/invite/resolve/{token}", timeout=30)
        assert rr.status_code == 200
        d = rr.json()
        for k in ("auction_id", "title", "notice_ref", "status", "currency"):
            assert k in d

    def test_resolve_invite_404(self):
        r = requests.get(f"{RA_API}/invite/resolve/nope-nonexistent-token", timeout=30)
        assert r.status_code == 404

    def test_accept_invite_wrong_vendor_403(self, admin, auction_id):
        r = admin.get(f"{RA_API}/{auction_id}/invitations", timeout=30)
        # invite a fake email (not matching vendor session)
        admin.post(f"{RA_API}/{auction_id}/invite",
                   json={"emails": ["someone-else@example.com"]}, timeout=30)
        rows = admin.get(f"{RA_API}/{auction_id}/invitations", timeout=30).json()["items"]
        token = [x for x in rows if x["email"] == "someone-else@example.com"][0]["token"]
        # Vendor accepts — should 403
        v = requests.Session()
        vlog = v.post(f"{BASE}/api/v1/vendor/auth/login",
                       json={"email": VENDOR_EMAIL, "password": VENDOR_PW}, timeout=30)
        assert vlog.status_code == 200
        r2 = v.post(f"{RA_API}/invite/accept/{token}", timeout=30)
        assert r2.status_code == 403

    def test_accept_invite_ok_then_idempotent(self, vendor, admin, auction_id):
        # Use the invite generated for the actual vendor
        rows = admin.get(f"{RA_API}/{auction_id}/invitations", timeout=30).json()["items"]
        token = [x for x in rows if x["email"] == VENDOR_EMAIL][0]["token"]
        r = vendor.post(f"{RA_API}/invite/accept/{token}", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d1 = r.json()
        assert d1["ok"] is True
        assert "alias" in d1
        # Idempotent
        r2 = vendor.post(f"{RA_API}/invite/accept/{token}", timeout=30)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["alias"] == d1["alias"]

    def test_accept_invite_bad_token_404(self, vendor):
        r = vendor.post(f"{RA_API}/invite/accept/never-exists-xyz", timeout=30)
        assert r.status_code == 404


# ---------- Fee Checkout ----------
@pytest.fixture(scope="module")
def emd_master_id(admin):
    r = admin.get(f"{TP}/emd-masters", timeout=30)
    assert r.status_code == 200
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    active = [m for m in items if m.get("is_active", True) and m.get("slabs")]
    if active:
        return active[0].get("id") or active[0].get("_id")
    # seed one
    r = admin.post(f"{TP}/emd-masters", json={
        "name": "TEST_v46b_master", "kind": "emd", "country": "KZ",
        "currency": "KZT", "is_active": True,
        "slabs": [
            {"tender_value_min": 0, "tender_value_max": 10_000_000,
             "fee_type": "fixed", "fixed_amount": 50000},
            {"tender_value_min": 10_000_000, "tender_value_max": None,
             "fee_type": "percentage", "percentage": 0.5},
        ],
    }, timeout=30)
    assert r.status_code in (200, 201), r.text[:300]
    return (r.json().get("id") or r.json().get("_id"))


class TestFeeCheckout:
    def test_unknown_master_404(self):
        r = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": "507f1f77bcf86cd799439011",
            "tender_value": 1_000_000,
            "origin_url": BASE,
        }, timeout=30)
        assert r.status_code == 404

    def test_invalid_master_id_422(self):
        r = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": "garbage!!!",
            "tender_value": 1_000_000,
            "origin_url": BASE,
        }, timeout=30)
        assert r.status_code == 422

    def test_fixed_slab_unauth_ok(self, emd_master_id):
        r = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": emd_master_id,
            "tender_value": 5_000_000,
            "origin_url": BASE,
        }, timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d.get("session_id", "").startswith("cs_test_"), d.get("session_id")
        assert d.get("checkout_url", "").startswith("https://")
        assert "amount" in d and "currency" in d
        assert d["amount"] > 0
        assert "fee_kind" in d and "slab" in d

    def test_admin_auth_uses_email(self, admin, emd_master_id):
        r = admin.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": emd_master_id,
            "tender_value": 5_000_000,
            "origin_url": BASE,
            "context_ref": "TEST_v46b_ctx",
        }, timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["amount"] > 0

    def test_below_all_slabs_422(self, admin):
        # Create a master where lowest slab starts >0 to force miss
        r = admin.post(f"{TP}/emd-masters", json={
            "name": f"TEST_v46b_gap_{int(time.time())}", "kind": "emd",
            "country": "KZ", "currency": "USD", "is_active": True,
            "slabs": [{"tender_value_min": 1_000_000, "tender_value_max": None,
                       "fee_type": "fixed", "fixed_amount": 500}],
        }, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        mid = r.json().get("id") or r.json().get("_id")
        rr = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": mid, "tender_value": 100, "origin_url": BASE,
        }, timeout=30)
        assert rr.status_code == 422, rr.text[:300]

    def test_zero_amount_400(self, admin):
        r = admin.post(f"{TP}/emd-masters", json={
            "name": f"TEST_v46b_zero_{int(time.time())}", "kind": "emd",
            "country": "KZ", "currency": "USD", "is_active": True,
            "slabs": [{"tender_value_min": 0, "tender_value_max": None,
                       "fee_type": "fixed", "fixed_amount": 0}],
        }, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        mid = r.json().get("id") or r.json().get("_id")
        rr = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": mid, "tender_value": 500, "origin_url": BASE,
        }, timeout=30)
        assert rr.status_code == 400, rr.text[:300]

    def test_inactive_master_400(self, admin):
        r = admin.post(f"{TP}/emd-masters", json={
            "name": f"TEST_v46b_inactive_{int(time.time())}", "kind": "emd",
            "country": "KZ", "currency": "USD", "is_active": False,
            "slabs": [{"tender_value_min": 0, "tender_value_max": None,
                       "fee_type": "fixed", "fixed_amount": 100}],
        }, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        mid = r.json().get("id") or r.json().get("_id")
        rr = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": mid, "tender_value": 500, "origin_url": BASE,
        }, timeout=30)
        assert rr.status_code == 400, rr.text[:300]

    def test_percentage_slab_math(self, admin):
        r = admin.post(f"{TP}/emd-masters", json={
            "name": f"TEST_v46b_pct_{int(time.time())}", "kind": "emd",
            "country": "KZ", "currency": "USD", "is_active": True,
            "slabs": [{"tender_value_min": 0, "tender_value_max": None,
                       "fee_type": "percentage", "percentage": 2.5}],
        }, timeout=30)
        mid = r.json().get("id") or r.json().get("_id")
        rr = requests.post(f"{BILLING}/fee-checkout", json={
            "fee_master_id": mid, "tender_value": 1000, "origin_url": BASE,
        }, timeout=30)
        assert rr.status_code == 200, rr.text[:300]
        assert rr.json()["amount"] == 25.0  # 1000 * 2.5 / 100


# ---------- DPR analyze-json regression ----------
class TestDprAnalyzeJson:
    def test_analyze_kmt_pdf(self, admin):
        # Fetch PDF
        pdf = requests.get(DPR_URL, timeout=60)
        assert pdf.status_code == 200, f"could not fetch PDF: {pdf.status_code}"
        b64 = base64.b64encode(pdf.content).decode()
        r = admin.post(f"{TP}/dpr/analyze-json",
                       json={"filename": "KMT_DPR.pdf", "content_b64": b64},
                       timeout=180)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        # Header fields are nested
        hdr = d.get("header") or d
        assert hdr.get("work_title"), f"work_title missing: {list(hdr.keys())}"
        assert hdr.get("work_description"), f"work_description missing"
        assert hdr.get("tender_value"), f"tender_value missing"
        assert hdr.get("budget_currency"), f"budget_currency missing"
