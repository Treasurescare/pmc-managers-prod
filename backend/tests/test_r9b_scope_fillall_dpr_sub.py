# R9b — Vendor scope rules, submit-review enforcement, category request cap,
# AI Fill-All background job, async DPR analysis (multi-page + blank PDF),
# per-country subscription gate (Fee Master kind=subscription) + Stripe checkout session.
# Run serially: pytest tests/test_r9b_scope_fillall_dpr_sub.py -n 0
import os
import sys
import time
import base64
import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
VENDOR_B_EMAIL = "test_r9b_vendorb@pmcmanagers.com"
VENDOR_B_PW = "VendorB@12345"
REVIEWER = ("reviewerqa@pmcmanagers.com", "Reviewer@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _vlogin(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


def _alogin(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _vid():
    return str(_mdb.vendors.find_one({"email": VENDOR[0]})["_id"])


def _payload(name, cat=None, sections=None):
    h = {"work_title": f"{name} work", "work_description": "Construction of a rural road",
         "budget_currency": "USD", "budget_amount": 100000}
    if cat:
        h["product_category"] = cat
    return {"name": name, "kind": "tender", "header": h,
            "sections": sections or [{"code": "sec-1", "kind": "section", "title": "NIB", "body": "<p>x</p>"}]}


@pytest.fixture(scope="module")
def vendor():
    return _vlogin(*VENDOR)


@pytest.fixture(scope="module")
def vendor_b():
    from security import hash_password
    _mdb.vendors.update_one({"email": VENDOR_B_EMAIL}, {"$set": {
        "email": VENDOR_B_EMAIL, "company_name": "TEST_R9b Vendor B", "vendor_ref": "VEN-TESTR9BB",
        "password_hash": hash_password(VENDOR_B_PW), "kyc_status": "verified",
        "status": "active", "is_active": True}}, upsert=True)
    yield _vlogin(VENDOR_B_EMAIL, VENDOR_B_PW)
    _mdb.vendors.delete_one({"email": VENDOR_B_EMAIL})


@pytest.fixture(scope="module")
def reviewer():
    return _alogin(*REVIEWER)


@pytest.fixture(scope="module")
def admin():
    return _alogin(*ADMIN)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    vid = _vid()
    _mdb.tender_templates.delete_many({"owner_vendor_id": vid, "name": {"$regex": "^TEST_"}})
    _mdb.tender_templates.delete_many({"name": {"$regex": "^TEST_R9b"}})
    _mdb.ai_fill_jobs.delete_many({"owner_id": vid})
    _mdb.dpr_jobs.delete_many({"owner_id": vid})
    _mdb.vendor_category_requests.delete_many({"vendor_ref": "VEN-TEST01", "rationale": "TEST_R9b"})
    _mdb.platform_config.delete_one({"key": "vendor_scope_rules"})
    _mdb.emd_masters.delete_many({"name": {"$regex": "^TEST_"}})
    _mdb.payment_transactions.delete_many({"vendor_id": vid, "purpose": "tender_builder_sub"})
    _mdb.vendors.update_one({"email": VENDOR[0]}, {"$set": {"business_categories": None},
                                                   "$unset": {"tender_builder_sub": "", "profile.country": ""}})


# ---------- scope rules config ----------
class TestScopeRules:
    def test_defaults(self, reviewer):
        _mdb.platform_config.delete_one({"key": "vendor_scope_rules"})
        r = reviewer.get(f"{API}/vendor-tenders/scope-rules")
        assert r.status_code == 200, r.text
        assert r.json() == {"restrict_to_approved_categories": True, "max_pending_tenders": 3,
                            "max_pending_category_requests": 5}

    def test_put_requires_csrf_and_role(self, vendor):
        s = requests.Session()
        s.post(f"{API}/admin/auth/login", json={"email": REVIEWER[0], "password": REVIEWER[1]})
        body = {"restrict_to_approved_categories": True, "max_pending_tenders": 3, "max_pending_category_requests": 5}
        assert s.put(f"{API}/vendor-tenders/scope-rules", json=body).status_code == 403
        assert vendor.put(f"{API}/vendor-tenders/scope-rules", json=body).status_code in (401, 403)
        assert vendor.get(f"{API}/vendor-tenders/scope-rules").status_code in (401, 403)

    def test_put_validation_and_persist(self, reviewer):
        bad = reviewer.put(f"{API}/vendor-tenders/scope-rules",
                           json={"restrict_to_approved_categories": True, "max_pending_tenders": -1,
                                 "max_pending_category_requests": 5})
        assert bad.status_code == 422
        r = reviewer.put(f"{API}/vendor-tenders/scope-rules",
                         json={"restrict_to_approved_categories": True, "max_pending_tenders": 1,
                               "max_pending_category_requests": 1})
        assert r.status_code == 200, r.text
        g = reviewer.get(f"{API}/vendor-tenders/scope-rules").json()
        assert g["max_pending_tenders"] == 1 and g["max_pending_category_requests"] == 1

    def test_vendor_scope_snapshot(self, vendor):
        r = vendor.get(f"{API}/vendor-tenders/scope")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["rules"]["max_pending_tenders"] == 1
        assert "approved_categories" in d and "pending_tenders" in d and "pending_category_requests" in d


# ---------- submit-review enforcement ----------
class TestSubmitEnforcement:
    def test_missing_category_422(self, vendor):
        tid = vendor.post(f"{API}/tender-templates", json=_payload("TEST_R9b nocat")).json()["id"]
        r = vendor.post(f"{API}/tender-templates/{tid}/submit-review")
        assert r.status_code == 422, r.text

    def test_unapproved_category_403(self, vendor):
        _mdb.vendors.update_one({"email": VENDOR[0]}, {"$set": {"business_categories": ["Works"]}})
        tid = vendor.post(f"{API}/tender-templates", json=_payload("TEST_R9b badcat", "Goods")).json()["id"]
        r = vendor.post(f"{API}/tender-templates/{tid}/submit-review")
        assert r.status_code == 403, r.text

    def test_case_insensitive_ok_then_cap_429(self, vendor):
        t1 = vendor.post(f"{API}/tender-templates", json=_payload("TEST_R9b ok1", "works")).json()["id"]
        r = vendor.post(f"{API}/tender-templates/{t1}/submit-review")
        assert r.status_code == 200 and r.json()["review_status"] == "submitted", r.text
        t2 = vendor.post(f"{API}/tender-templates", json=_payload("TEST_R9b ok2", "Works")).json()["id"]
        r2 = vendor.post(f"{API}/tender-templates/{t2}/submit-review")
        assert r2.status_code == 429, r2.text
        assert vendor.get(f"{API}/vendor-tenders/scope").json()["pending_tenders"] == 1

    def test_zero_means_no_limit(self, vendor, reviewer):
        reviewer.put(f"{API}/vendor-tenders/scope-rules",
                     json={"restrict_to_approved_categories": True, "max_pending_tenders": 0,
                           "max_pending_category_requests": 1})
        t2 = [x for x in vendor.get(f"{API}/tender-templates").json() if x.get("name") == "TEST_R9b ok2"][0]["id"]
        r = vendor.post(f"{API}/tender-templates/{t2}/submit-review")
        assert r.status_code == 200, r.text

    def test_restrict_off_allows_any_category(self, vendor, reviewer):
        reviewer.put(f"{API}/vendor-tenders/scope-rules",
                     json={"restrict_to_approved_categories": False, "max_pending_tenders": 0,
                           "max_pending_category_requests": 1})
        tid = [x for x in vendor.get(f"{API}/tender-templates").json() if x.get("name") == "TEST_R9b badcat"][0]["id"]
        assert vendor.post(f"{API}/tender-templates/{tid}/submit-review").status_code == 200


# ---------- category request cap ----------
class TestCategoryCap:
    def test_category_request_cap_429(self, vendor):
        cats = list(_mdb.categories.find({"is_active": True}).limit(2))
        r1 = vendor.post(f"{API}/vendor/categories/request",
                         json={"category_code": cats[0]["code"], "category_name": cats[0]["name"], "rationale": "TEST_R9b"})
        assert r1.status_code == 200, r1.text
        r2 = vendor.post(f"{API}/vendor/categories/request",
                         json={"category_code": cats[1]["code"], "category_name": cats[1]["name"], "rationale": "TEST_R9b"})
        assert r2.status_code == 429, r2.text


# ---------- AI Fill-All background job ----------
class TestFillAllAsync:
    def test_fill_all_job(self, vendor, vendor_b, reviewer):
        reviewer.put(f"{API}/vendor-tenders/scope-rules",
                     json={"restrict_to_approved_categories": True, "max_pending_tenders": 0,
                           "max_pending_category_requests": 5})
        secs = [{"code": f"s{i}", "kind": "section", "title": t, "body": ""}
                for i, t in enumerate(["Notice Inviting Tender", "Scope of Work", "Eligibility Criteria"])]
        secs.append({"code": "s9", "kind": "section", "title": "Keep", "body": "<p>KEEP_ME</p>"})
        tid = vendor.post(f"{API}/tender-templates", json=_payload("TEST_R9b fill", "Works", secs)).json()["id"]
        r = vendor.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all-async", json={"length": "short"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total"] == 3 and d["job_id"]
        jid = d["job_id"]
        r2 = vendor.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all-async", json={"length": "short"})
        assert r2.json()["job_id"] == jid and r2.json().get("resumed") is True
        assert vendor_b.get(f"{API}/tender-pro/ai-fill-jobs/{jid}").status_code == 404
        st = None
        for _ in range(60):
            st = vendor.get(f"{API}/tender-pro/ai-fill-jobs/{jid}").json()
            if st["status"] in ("done", "failed"):
                break
            time.sleep(5)
        print("fill job", st)
        assert st["status"] == "done" and st["done"] == 3 and st["failed"] == 0 and st["progress"] == 100
        t = vendor.get(f"{API}/tender-templates/{tid}").json()
        bodies = {s["code"]: s.get("body") or "" for s in t["sections"]}
        assert all(len(bodies[f"s{i}"]) > 50 for i in range(3))
        assert bodies["s9"] == "<p>KEEP_ME</p>"
        # nothing left -> immediate done
        r3 = vendor.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all-async", json={})
        assert r3.json()["total"] == 0 and r3.json()["status"] == "done"
        # submitted draft -> 409
        _mdb.vendors.update_one({"email": VENDOR[0]}, {"$set": {"business_categories": ["Works"]}})
        assert vendor.post(f"{API}/tender-templates/{tid}/submit-review").status_code == 200
        assert vendor.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all-async", json={}).status_code == 409


# ---------- async DPR ----------
def _poll_dpr(s, jid, limit=300):
    t0 = time.time()
    st = None
    while time.time() - t0 < limit:
        st = s.get(f"{API}/tender-pro/dpr/jobs/{jid}").json()
        if st["status"] in ("done", "failed"):
            break
        time.sleep(5)
    return st, time.time() - t0


class TestDprAsync:
    def test_multipage_pdf(self, vendor):
        from make_test_pdfs import make_dpr
        b64 = base64.b64encode(open(make_dpr(), "rb").read()).decode()
        r = vendor.post(f"{API}/tender-pro/dpr/analyze-async?kind=tender",
                        json={"filename": "TEST_dpr_25p.pdf", "content_b64": b64})
        assert r.status_code == 200, r.text
        st, el = _poll_dpr(vendor, r.json()["job_id"])
        print("dpr", st["status"], st.get("phase"), st.get("error"), f"{el:.0f}s")
        assert st["status"] == "done", st
        assert st["result"]

    def test_blank_pdf_clear_error(self, vendor):
        from make_test_pdfs import make_blank
        b64 = base64.b64encode(open(make_blank(), "rb").read()).decode()
        r = vendor.post(f"{API}/tender-pro/dpr/analyze-async?kind=tender",
                        json={"filename": "TEST_blank.pdf", "content_b64": b64})
        assert r.status_code == 200, r.text
        st, _ = _poll_dpr(vendor, r.json()["job_id"], 120)
        print("blank", st)
        assert st["status"] == "failed" and "scan" in (st.get("error") or "").lower()


# ---------- per-country subscription + checkout ----------
class TestSubscription:
    def test_priced_country_gate_and_checkout(self, vendor, admin):
        _mdb.vendors.update_one({"email": VENDOR[0]}, {"$set": {"profile.country": "KZ"}})
        r = admin.post(f"{API}/tender-pro/emd-masters", json={
            "name": "TEST_ sub KZ", "country": "KZ", "kind": "subscription", "currency": "USD",
            "slabs": [{"tender_value_min": 0, "fee_type": "fixed", "fixed_amount": 10}]})
        assert r.status_code in (200, 201), r.text
        d = vendor.get(f"{API}/vendor-tenders/subscription").json()
        assert d["required"] is True and d["entitled"] is False and d["price"]["amount"] == 10
        assert vendor.post(f"{API}/tender-templates", json=_payload("TEST_R9b gated", "Works")).status_code == 402
        co = vendor.post(f"{API}/vendor-tenders/subscription/checkout", json={"origin_url": BASE_URL})
        assert co.status_code == 200, co.text
        assert co.json()["checkout_url"].startswith("https://checkout.stripe.com")
        tx = _mdb.payment_transactions.find_one({"session_id": co.json()["session_id"]})
        assert tx and tx["amount"] == 10 and tx["currency"] == "usd"
        stt = vendor.get(f"{API}/vendor-tenders/subscription/checkout/status/{co.json()['session_id']}")
        assert stt.status_code == 200 and stt.json()["payment_status"] != "paid"
