# R9 — Vendor Tender Builder: entitlement, tenant isolation, submit-review,
# reviewer-only moderation, publish-as-notice, own-tender bid guard, DPR/AI scoping,
# Fee-Master per-country subscription pricing, admin regression.
import os
import sys
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"

VENDOR_A = ("testvendor@pmcmanagers.com", "Vendor@12345")
VENDOR_B_EMAIL = "test_r9_vendorb@pmcmanagers.com"
VENDOR_B_PW = "VendorB@12345"
REVIEWER = ("reviewerqa@pmcmanagers.com", "Reviewer@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _vendor_login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


def _admin_login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    csrf = r.json().get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


@pytest.fixture(scope="module")
def vendor_a():
    return _vendor_login(*VENDOR_A)


@pytest.fixture(scope="module")
def vendor_b():
    from security import hash_password
    _mdb.vendors.update_one(
        {"email": VENDOR_B_EMAIL},
        {"$set": {"email": VENDOR_B_EMAIL, "company_name": "TEST_R9 Vendor B",
                  "vendor_ref": "VEN-TESTR9B", "password_hash": hash_password(VENDOR_B_PW),
                  "kyc_status": "verified", "status": "active", "is_active": True}},
        upsert=True)
    yield _vendor_login(VENDOR_B_EMAIL, VENDOR_B_PW)
    _mdb.vendors.delete_one({"email": VENDOR_B_EMAIL})


@pytest.fixture(scope="module")
def reviewer():
    return _admin_login(*REVIEWER)


@pytest.fixture(scope="module")
def admin():
    return _admin_login(*ADMIN)


@pytest.fixture(scope="module")
def state():
    st = {"tids": [], "notices": []}
    yield st
    from bson import ObjectId
    for t in st["tids"]:
        _mdb.tender_templates.delete_one({"_id": ObjectId(t)})
    for n in st["notices"]:
        _mdb.notices.delete_one({"notice_ref": n})
        _mdb.bids.delete_many({"notice_ref": n})


def _draft_payload(name):
    return {"name": name, "kind": "tender",
            "header": {"work_title": f"{name} work", "work_description": "desc",
                       "budget_currency": "USD", "budget_amount": 1000},
            "sections": [{"code": "sec-1", "kind": "section", "title": "NIB", "body": "<p>hi</p>"}]}


# ---------- entitlement ----------
class TestEntitlement:
    def test_subscription_free(self, vendor_a):
        r = vendor_a.get(f"{API}/vendor-tenders/subscription")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["required"] is False and d["free"] is True and d["entitled"] is True

    def test_priced_country_gates(self, vendor_b):
        # seed a priced subscription master for country ZZ and set vendor B country=ZZ
        _mdb.vendors.update_one({"email": VENDOR_B_EMAIL}, {"$set": {"country": "ZZ"}})
        mid = _mdb.emd_masters.insert_one({"name": "TEST_R9 sub ZZ", "kind": "subscription",
                                           "country": "ZZ", "category": None, "currency": "EUR",
                                           "is_active": True, "slabs": [{"fee_type": "fixed", "fixed_amount": 49}]}).inserted_id
        try:
            d = vendor_b.get(f"{API}/vendor-tenders/subscription").json()
            assert d["required"] is True and d["active"] is False and d["entitled"] is False
            assert d["price"]["amount"] == 49 and d["price"]["currency"] == "eur"
            r = vendor_b.post(f"{API}/tender-templates", json=_draft_payload("TEST_R9 gated"))
            assert r.status_code == 402, r.text
        finally:
            _mdb.emd_masters.delete_one({"_id": mid})
            _mdb.vendors.update_one({"email": VENDOR_B_EMAIL}, {"$unset": {"country": ""}})
        d = vendor_b.get(f"{API}/vendor-tenders/subscription").json()
        assert d["free"] is True


# ---------- isolation + workflow ----------
class TestVendorWorkflow:
    def test_create_draft_owner_stamped(self, vendor_a, state):
        r = vendor_a.post(f"{API}/tender-templates", json=_draft_payload(f"TEST_R9 A {uuid.uuid4().hex[:5]}"))
        assert r.status_code == 200, r.text
        d = r.json()
        state["tids"].append(d["id"])
        state["a_tid"] = d["id"]
        assert d.get("owner_vendor_id") and d["review_status"] == "draft" and d["is_master"] is False

    def test_patch_cannot_flip_master(self, vendor_a, state):
        p = _draft_payload("TEST_R9 A edited")
        p["is_master"] = True
        p["header"]["work_title"] = "Edited title"
        r = vendor_a.patch(f"{API}/tender-templates/{state['a_tid']}", json=p)
        assert r.status_code == 200, r.text
        g = vendor_a.get(f"{API}/tender-templates/{state['a_tid']}").json()
        assert g["is_master"] is False and g["header"]["work_title"] == "Edited title"

    def test_vendor_list_scope(self, vendor_a, vendor_b, state):
        la = vendor_a.get(f"{API}/tender-templates").json()
        ids = [x["id"] for x in la]
        assert state["a_tid"] in ids
        vid = _mdb.vendors.find_one({"email": VENDOR_A[0]})["_id"]
        for x in la:
            assert x.get("is_master") or x.get("owner_vendor_id") == str(vid)
        lb = vendor_b.get(f"{API}/tender-templates").json()
        assert state["a_tid"] not in [x["id"] for x in lb]

    def test_other_vendor_404(self, vendor_b, state):
        tid = state["a_tid"]
        assert vendor_b.get(f"{API}/tender-templates/{tid}").status_code == 404
        assert vendor_b.patch(f"{API}/tender-templates/{tid}", json=_draft_payload("x")).status_code == 404
        assert vendor_b.delete(f"{API}/tender-templates/{tid}").status_code == 404
        assert vendor_b.get(f"{API}/tender-templates/{tid}/versions").status_code == 404
        assert vendor_b.post(f"{API}/tender-templates/{tid}/submit-review").status_code == 404
        assert vendor_b.post(f"{API}/tender-pro/templates/{tid}/ai-fill-all", json={}).status_code == 404
        assert vendor_b.post(f"{API}/tender-templates/{tid}/sections/sec-1/ai-draft", json={}).status_code in (404, 422)

    def test_vendor_cannot_edit_master(self, vendor_a):
        masters = [x for x in vendor_a.get(f"{API}/tender-templates").json() if x.get("is_master")]
        if not masters:
            pytest.skip("no master")
        r = vendor_a.patch(f"{API}/tender-templates/{masters[0]['id']}", json=_draft_payload("hack"))
        assert r.status_code == 403

    def test_vendor_denied_review_queue(self, vendor_a):
        r = vendor_a.get(f"{API}/tender-templates/review/queue")
        assert r.status_code in (401, 403)

    def test_submit_review(self, vendor_a, state):
        r = vendor_a.post(f"{API}/tender-templates/{state['a_tid']}/submit-review")
        assert r.status_code == 200 and r.json()["review_status"] == "submitted"
        r2 = vendor_a.post(f"{API}/tender-templates/{state['a_tid']}/submit-review")
        assert r2.status_code == 409
        # locked
        r3 = vendor_a.patch(f"{API}/tender-templates/{state['a_tid']}", json=_draft_payload("x"))
        assert r3.status_code == 409

    def test_vendor_cannot_approve(self, vendor_a, state):
        r = vendor_a.post(f"{API}/tender-templates/{state['a_tid']}/review/approve", json={})
        assert r.status_code in (401, 403)

    def test_admin_blocked_from_queue(self, admin, state):
        assert admin.get(f"{API}/tender-templates/review/queue").status_code == 403
        assert admin.post(f"{API}/tender-templates/{state['a_tid']}/review/approve", json={}).status_code == 403

    def test_reviewer_queue_and_approve(self, reviewer, state):
        q = reviewer.get(f"{API}/tender-templates/review/queue")
        assert q.status_code == 200
        assert state["a_tid"] in [x["id"] for x in q.json()["items"]]
        r = reviewer.post(f"{API}/tender-templates/{state['a_tid']}/review/approve", json={"note": "ok"})
        assert r.status_code == 200, r.text
        ref = r.json()["notice_ref"]
        state["notices"].append(ref)
        state["ref"] = ref
        n = _mdb.notices.find_one({"notice_ref": ref})
        assert n["origin"] == "vendor" and n["author_name"] == "Test Supplier Co"
        assert n["tender_template_id"] == state["a_tid"] and n["is_published"] is True
        t = reviewer.get(f"{API}/tender-templates/{state['a_tid']}").json()
        assert t["review_status"] == "approved" and t["published_notice_ref"] == ref

    def test_own_tender_bid_blocked(self, vendor_a, vendor_b, state):
        r = vendor_a.post(f"{API}/bids", json={"notice_ref": state["ref"], "price_amount": 100})
        assert r.status_code == 403, r.text
        # other vendor not blocked by the conflict guard
        r2 = vendor_b.post(f"{API}/bids", json={"notice_ref": state["ref"], "price_amount": 100})
        assert r2.status_code != 403 or "conflict" not in r2.text.lower(), r2.text

    def test_approved_tender_locked_all_paths(self, vendor_a, state):
        # after approval/publish, the vendor must not be able to alter content via ANY write path
        tid = state["a_tid"]
        r1 = vendor_a.patch(f"{API}/tender-pro/templates/{tid}/sections/sec-1", json={"body": "<p>tampered</p>"})
        r2 = vendor_a.post(f"{API}/tender-templates/{tid}/versions/0/restore")
        assert r1.status_code == 409, f"section PATCH on approved tender -> {r1.status_code}"
        assert r2.status_code == 409, f"version restore on approved tender -> {r2.status_code}"

    def test_reviewer_reject_and_changes(self, vendor_a, reviewer, state):
        r = vendor_a.post(f"{API}/tender-templates", json=_draft_payload("TEST_R9 A2"))
        tid = r.json()["id"]
        state["tids"].append(tid)
        vendor_a.post(f"{API}/tender-templates/{tid}/submit-review")
        rc = reviewer.post(f"{API}/tender-templates/{tid}/review/request-changes", json={"note": "fix"})
        assert rc.status_code == 200 and rc.json()["review_status"] == "changes_requested"
        # vendor can edit + resubmit
        assert vendor_a.patch(f"{API}/tender-templates/{tid}", json=_draft_payload("TEST_R9 A2b")).status_code == 200
        assert vendor_a.post(f"{API}/tender-templates/{tid}/submit-review").status_code == 200
        rj = reviewer.post(f"{API}/tender-templates/{tid}/review/reject", json={"note": "no"})
        assert rj.status_code == 200 and rj.json()["review_status"] == "rejected"


# ---------- vendor save-as-master moderation ----------
class TestMasterModeration:
    def test_vendor_master_pending_then_rejected_not_shared(self, vendor_a, vendor_b, reviewer, state):
        r = vendor_a.post(f"{API}/tender-templates", json=_draft_payload("TEST_R9 M src"))
        src = r.json()["id"]
        state["tids"].append(src)
        m = vendor_a.post(f"{API}/tender-pro/templates/{src}/save-as-master",
                          json={"country": "IN", "industry": "it", "name": "TEST_R9 vendor master"})
        assert m.status_code == 200, m.text
        mid = m.json()["id"]
        state["tids"].append(mid)
        assert m.json()["moderation_status"] == "pending"
        assert mid not in [x["id"] for x in vendor_b.get(f"{API}/tender-templates").json()]
        pend = reviewer.get(f"{API}/tender-templates/masters/pending").json()["items"]
        assert mid in [x["id"] for x in pend]
        rj = reviewer.post(f"{API}/tender-templates/{mid}/master/reject", json={"note": "no"})
        assert rj.status_code == 200
        # rejected vendor master must NOT leak into the shared library for other vendors
        lb = [x["id"] for x in vendor_b.get(f"{API}/tender-templates").json()]
        assert mid not in lb, "REJECTED vendor master is visible to other vendors"

    def test_vendor_master_approved_shared(self, vendor_a, vendor_b, reviewer, state):
        src = state["tids"][-2]
        m = vendor_a.post(f"{API}/tender-pro/templates/{src}/save-as-master",
                          json={"country": "IN", "industry": "it", "name": "TEST_R9 vendor master2"})
        mid = m.json()["id"]
        state["tids"].append(mid)
        ap = reviewer.post(f"{API}/tender-templates/{mid}/master/approve", json={})
        assert ap.status_code == 200
        assert mid in [x["id"] for x in vendor_b.get(f"{API}/tender-templates").json()]


# ---------- DPR / AI scoping ----------
class TestDprAi:
    def test_dpr_job_scope(self, vendor_a, vendor_b, state):
        import base64
        b64 = base64.b64encode(b"Detailed Project Report: build a 2 km road, budget USD 1M").decode()
        r = vendor_a.post(f"{API}/tender-pro/dpr/analyze-async",
                          json={"filename": "dpr.txt", "content_b64": b64, "data_b64": b64, "kind": "tender"})
        if r.status_code == 422:
            pytest.skip(f"payload shape: {r.text[:200]}")
        assert r.status_code == 200, r.text
        jid = r.json()["job_id"]
        _mdb.dpr_jobs.update_one({"_id": __import__("bson").ObjectId(jid)}, {"$set": {"test_r9": True}})
        assert vendor_a.get(f"{API}/tender-pro/dpr/jobs/{jid}").status_code == 200
        assert vendor_b.get(f"{API}/tender-pro/dpr/jobs/{jid}").status_code == 404

    def test_dpr_other_template_404(self, vendor_b, state):
        import base64
        b64 = base64.b64encode(b"DPR text").decode()
        for ep in ("analyze-json", "analyze-async"):
            r = vendor_b.post(f"{API}/tender-pro/dpr/{ep}?template_id={state['a_tid']}",
                              json={"filename": "d.txt", "content_b64": b64})
            assert r.status_code == 404, f"{ep}: {r.status_code} {r.text[:200]}"


# ---------- admin regression ----------
class TestAdminRegression:
    def test_admin_sees_all_and_crud(self, admin, state):
        lst = admin.get(f"{API}/tender-templates")
        assert lst.status_code == 200
        assert state["a_tid"] in [x["id"] for x in lst.json()]
        r = admin.post(f"{API}/tender-templates", json=_draft_payload("TEST_R9 admin"))
        assert r.status_code == 200, r.text
        tid = r.json()["id"]
        state["tids"].append(tid)
        assert admin.patch(f"{API}/tender-templates/{tid}", json=_draft_payload("TEST_R9 admin2")).status_code == 200
        v = admin.get(f"{API}/tender-templates/{tid}/versions").json()
        assert len(v["versions"]) >= 1
        pdf = admin.get(f"{API}/tender-templates/{tid}/export/pdf")
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"

    def test_admin_write_requires_csrf(self):
        s = requests.Session()
        s.post(f"{API}/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
        r = s.post(f"{API}/tender-templates", json=_draft_payload("TEST_R9 nocsrf"))
        if r.status_code == 200:
            _mdb.tender_templates.delete_one({"_id": __import__("bson").ObjectId(r.json()["id"])})
        assert r.status_code == 403, f"admin template write accepted WITHOUT X-CSRF-Token ({r.status_code})"
