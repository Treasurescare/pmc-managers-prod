# v62: Admin-editable footer social links + branded vendor fee receipt PDFs.
import asyncio
import os
import sys

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
DEFAULTS = {
    "linkedin": "https://www.linkedin.com/feed/update/urn:li:activity:7521796802216611840/",
    "facebook": "https://www.facebook.com/profile.php?id=61596254811635",
    "instagram": "",  # v63
    "whatsapp": "",  # v63
}
SOC = f"{BASE_URL}/api/v1/marketing/site-social"
PUB = f"{BASE_URL}/api/v1/site/social"
RNO = "TEST-RCPT-0001"
RNO_OTHER = "TEST-RCPT-OTHER"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com",
               "password": "Admin@12345", "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s


@pytest.fixture(scope="module")
def vendor():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    DB.site_settings.delete_one({"_id": "social"})
    DB.fee_receipts.delete_many({"receipt_no": {"$regex": "^TEST-RCPT"}})


@pytest.fixture(scope="module")
def receipt():
    v = DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    assert v, "testvendor missing"
    DB.fee_receipts.delete_many({"receipt_no": {"$regex": "^TEST-RCPT"}})
    DB.fee_receipts.insert_one({"receipt_no": RNO, "vendor_id": str(v["_id"]), "purpose": "category_fee",
                                "lines": [{"name": "TEST_ Extra category", "amount": 49.5}], "total": 49.5,
                                "currency": "GBP", "session_id": "TEST_sess_1", "category": "Medical <b>Equip</b>",
                                "paid_at": "2026-01-10T10:00:00+00:00"})
    DB.fee_receipts.insert_one({"receipt_no": RNO_OTHER, "vendor_id": str(ObjectId()), "purpose": "tender_fee",
                                "lines": [{"name": "x", "amount": 1}], "total": 1, "currency": "GBP",
                                "session_id": "TEST_sess_2", "paid_at": "2026-01-10T10:00:00+00:00"})
    return v


# --- Social links ---
class TestSocial:
    def test_public_defaults(self):
        DB.site_settings.delete_one({"_id": "social"})
        r = requests.get(PUB)
        assert r.status_code == 200
        assert r.json() == DEFAULTS

    def test_admin_save_and_persist(self, admin):
        p = {"linkedin": "https://www.linkedin.com/company/TEST_pmc", "facebook": "https://www.facebook.com/TEST_pmc",
             "instagram": "", "whatsapp": ""}
        r = admin.put(SOC, json=p)
        assert r.status_code == 200, r.text
        assert r.json() == p
        assert requests.get(PUB).json() == p

    def test_strip_whitespace(self, admin):
        r = admin.put(SOC, json={"linkedin": "  https://www.linkedin.com/x  ", "facebook": "https://fb.com/y"})
        assert r.status_code == 200
        assert r.json()["linkedin"] == "https://www.linkedin.com/x"

    def test_empty_hides(self, admin):
        r = admin.put(SOC, json={"linkedin": "https://www.linkedin.com/x", "facebook": ""})
        assert r.status_code == 200
        assert requests.get(PUB).json()["facebook"] == ""

    @pytest.mark.parametrize("bad", ["http://facebook.com/x", "javascript:alert(1)", "ftp://x", "https://a b", "facebook.com"])
    def test_reject_non_https(self, admin, bad):
        r = admin.put(SOC, json={"linkedin": DEFAULTS["linkedin"], "facebook": bad})
        assert r.status_code == 422, (bad, r.status_code)

    def test_missing_csrf(self, admin):
        s = requests.Session()
        s.cookies.update(admin.cookies)
        r = s.put(SOC, json=DEFAULTS)
        assert r.status_code in (401, 403)

    def test_anon_rejected(self):
        r = requests.put(SOC, json=DEFAULTS)
        assert r.status_code in (401, 403)

    def test_vendor_rejected(self, vendor):
        r = vendor.put(SOC, json=DEFAULTS, headers={"X-CSRF-Token": vendor.cookies.get("csrf_token") or "x"})
        assert r.status_code in (401, 403)

    def test_restore_defaults(self, admin):
        r = admin.put(SOC, json=DEFAULTS)
        assert r.status_code == 200
        assert requests.get(PUB).json() == DEFAULTS


# --- Receipts ---
class TestReceipts:
    def test_list_contains(self, vendor, receipt):
        r = vendor.get(f"{BASE_URL}/api/v1/vendor-tenders/receipts")
        assert r.status_code == 200
        nos = [x["receipt_no"] for x in r.json()["items"]]
        assert RNO in nos and RNO_OTHER not in nos

    def test_own_pdf(self, vendor, receipt):
        r = vendor.get(f"{BASE_URL}/api/v1/vendor-tenders/receipts/{RNO}.pdf")
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert RNO in r.headers.get("content-disposition", "")
        assert len(r.content) > 3000

    def test_other_vendor_pdf_404(self, vendor, receipt):
        r = vendor.get(f"{BASE_URL}/api/v1/vendor-tenders/receipts/{RNO_OTHER}.pdf")
        assert r.status_code == 404

    def test_missing_pdf_404(self, vendor, receipt):
        r = vendor.get(f"{BASE_URL}/api/v1/vendor-tenders/receipts/NOPE-999.pdf")
        assert r.status_code == 404

    def test_anon_401(self, receipt):
        r = requests.get(f"{BASE_URL}/api/v1/vendor-tenders/receipts/{RNO}.pdf")
        assert r.status_code == 401

    def test_render_direct_and_issue_receipt(self, receipt):
        sys.path.insert(0, "/app/backend")
        from routers.site_settings import render_receipt_pdf
        pdf = render_receipt_pdf({"receipt_no": "X", "lines": [{"name": "a", "amount": "3"}], "total": 3,
                                  "currency": "INR", "purpose": "weird_purpose"}, {})
        assert pdf[:4] == b"%PDF"
