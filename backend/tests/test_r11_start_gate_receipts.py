# R11 — Start-of-tender payment gate ("tender credits") + fee receipts.
# Covers /vendor-tenders/start/check|quote|checkout|checkout/status, credit consumption on
# POST /tender-templates, DPR analyze gate, receipts (idempotent) and /vendor-tenders/receipts.
# Run serially: pytest tests/test_r11_start_gate_receipts.py -n 0
import os
import sys
import base64
import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
VB_EMAIL, VB_PW = "test_r11_vendorb@pmcmanagers.com", "VendorB@12345"
CAT = "Fire alarm & safety systems"
CAT_FREE = "Office furniture"

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
B64 = base64.b64encode(b"Detailed project report: build a fire alarm system for a school.").decode()


def _vlogin(e, p):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": e, "password": p})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def vid():
    return str(_mdb.vendors.find_one({"email": VENDOR[0]})["_id"])


@pytest.fixture(scope="module")
def vendor(vid):
    v = _mdb.vendors.find_one({"_id": ObjectId(vid)})
    before = {k: v.get(k) for k in ("profile", "business_categories")}
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": {"profile.country": "KZ",
                                                          "business_categories": [CAT, CAT_FREE]}})
    yield _vlogin(*VENDOR)
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": before})
    _mdb.tender_templates.delete_many({"owner_vendor_id": vid, "name": {"$regex": "^TEST_R11"}})
    _mdb.tender_credits.delete_many({"vendor_id": vid})
    _mdb.fee_receipts.delete_many({"vendor_id": vid})
    _mdb.payment_transactions.delete_many({"vendor_id": vid, "purpose": {"$in": ["tender_fee", "tender_credit"]}})
    _mdb.emd_masters.delete_many({"name": {"$regex": "^TEST_R11"}})
    _mdb.fee_types.delete_many({"name": {"$regex": "^TEST R11"}})
    _mdb.dpr_jobs.delete_many({"filename": "TEST_R11.txt"})


@pytest.fixture(scope="module")
def vendor_b():
    from security import hash_password
    _mdb.vendors.update_one({"email": VB_EMAIL}, {"$set": {
        "email": VB_EMAIL, "company_name": "TEST_R11 B", "vendor_ref": "VEN-TESTR11B",
        "password_hash": hash_password(VB_PW), "kyc_status": "verified", "status": "active",
        "is_active": True}}, upsert=True)
    yield _vlogin(VB_EMAIL, VB_PW)
    _mdb.vendors.delete_one({"email": VB_EMAIL})


@pytest.fixture(scope="module")
def st():
    return {}


def _tpl(name, header=None):
    return {"name": name, "kind": "tender", "header": header or {"work_title": f"{name} work"},
            "sections": [{"code": "sec-1", "kind": "section", "title": "NIB", "body": "<p>hi</p>"}]}


def _mark_paid(sid):
    _mdb.payment_transactions.update_one({"session_id": sid},
        {"$set": {"payment_status": "paid", "status": "completed"}})


class TestNotRequired:
    def test_check_not_required(self, vendor):
        r = vendor.get(f"{API}/vendor-tenders/start/check")
        assert r.status_code == 200, r.text
        assert r.json() == {"required": False, "credit": None}

    def test_create_without_credit_ok(self, vendor):
        r = vendor.post(f"{API}/tender-templates", json=_tpl("TEST_R11 free create"))
        assert r.status_code == 200, r.text
        assert "credit_id" not in r.json() or not r.json().get("credit_id")


class TestStartGate:
    def test_setup(self, admin, vendor, st):
        r = admin.post(f"{API}/fee-types", json={"name": "TEST R11 Start", "timing": "upfront", "calc": "fixed",
                       "amount_mode": "single", "category_scope": "selected", "billing": "one_time",
                       "used_in_tender_builder": True})
        assert r.status_code == 200, r.text
        st["code"] = r.json()["code"]
        rr = admin.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R11 start", "country": "KZ",
                        "kind": st["code"], "categories": [CAT], "currency": "USD",
                        "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed",
                                   "fixed_amount": 25}]})
        assert rr.status_code == 200, rr.text
        st["rule"] = rr.json()["id"]
        r2 = admin.post(f"{API}/fee-types", json={"name": "TEST R11 Completion", "timing": "on_completion",
                        "calc": "fixed", "amount_mode": "single", "category_scope": "all", "billing": "one_time",
                        "used_in_tender_builder": True})
        assert r2.status_code == 200, r2.text
        st["code2"] = r2.json()["code"]
        rr2 = admin.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R11 completion", "country": "KZ",
                         "kind": st["code2"], "currency": "USD",
                         "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed",
                                    "fixed_amount": 40}]})
        assert rr2.status_code == 200, rr2.text
        st["rule2"] = rr2.json()["id"]

    def test_check_required(self, vendor):
        d = vendor.get(f"{API}/vendor-tenders/start/check").json()
        assert d["required"] is True and d["credit"] is None

    def test_create_402(self, vendor):
        r = vendor.post(f"{API}/tender-templates", json=_tpl("TEST_R11 blocked"))
        assert r.status_code == 402, r.text

    @pytest.mark.parametrize("ep", ["analyze-json", "analyze-async"])
    def test_dpr_402(self, vendor, ep):
        r = vendor.post(f"{API}/tender-pro/dpr/{ep}", json={"filename": "TEST_R11.txt", "content_b64": B64})
        assert r.status_code == 402, r.text

    def test_admin_not_gated(self, admin, st):
        r = admin.post(f"{API}/tender-templates", json=_tpl("TEST_R11 admin"))
        assert r.status_code == 200, r.text
        _mdb.tender_templates.delete_one({"_id": ObjectId(r.json()["id"])})

    def test_quote(self, vendor, st):
        r = vendor.post(f"{API}/vendor-tenders/start/quote", json={"category": CAT, "tender_value": 50000})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total"] == 25 and d["currency"] == "USD"
        assert [f["code"] for f in d["fees"]] == [st["code"]]

    def test_quote_unapproved_403(self, vendor):
        r = vendor.post(f"{API}/vendor-tenders/start/quote", json={"category": "Nuclear reactors"})
        assert r.status_code == 403, r.text

    def test_quote_validation(self, vendor):
        assert vendor.post(f"{API}/vendor-tenders/start/quote", json={"category": ""}).status_code == 422
        assert vendor.post(f"{API}/vendor-tenders/start/quote",
                           json={"category": CAT, "tender_value": -5}).status_code == 422

    def test_checkout_pending(self, vendor, vid, st):
        r = vendor.post(f"{API}/vendor-tenders/start/checkout",
                        json={"category": CAT, "tender_value": 50000, "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_url"].startswith("https://checkout.stripe.com")
        st["sid"] = d["session_id"]
        cr = _mdb.tender_credits.find_one({"session_id": st["sid"]})
        assert cr and cr["status"] == "pending" and cr["total"] == 25 and cr["category"] == CAT
        st["credit"] = str(cr["_id"])
        s = vendor.get(f"{API}/vendor-tenders/start/checkout/status/{st['sid']}").json()
        assert s["payment_status"] != "paid"
        assert vendor.get(f"{API}/vendor-tenders/start/check").json()["credit"] is None
        assert vendor.post(f"{API}/tender-templates", json=_tpl("TEST_R11 blocked2")).status_code == 402

    def test_status_foreign_404(self, vendor_b, st):
        assert vendor_b.get(f"{API}/vendor-tenders/start/checkout/status/{st['sid']}").status_code == 404

    def test_paid_issues_receipt_once(self, vendor, vid, st):
        _mark_paid(st["sid"])
        for _ in range(3):
            s = vendor.get(f"{API}/vendor-tenders/start/checkout/status/{st['sid']}")
            assert s.status_code == 200 and s.json()["payment_status"] == "paid"
            assert s.json()["credit_id"] == st["credit"]
        assert _mdb.tender_credits.find_one({"_id": ObjectId(st["credit"])})["status"] == "paid"
        recs = list(_mdb.fee_receipts.find({"session_id": st["sid"]}))
        assert len(recs) == 1
        rec = recs[0]
        assert rec["purpose"] == "tender_start" and rec["total"] == 25 and rec["currency"] == "USD"
        assert rec["receipt_no"].startswith("PMC-RCPT-") and len(rec["receipt_no"]) == 15
        assert rec["category"] == CAT and rec["lines"][0]["amount"] == 25
        st["rno"] = rec["receipt_no"]

    def test_webhook_path_idempotent(self, st):
        import asyncio
        from routers.vendor_tenders import apply_credit_payment
        asyncio.new_event_loop().run_until_complete(apply_credit_payment(st["sid"]))
        assert _mdb.fee_receipts.count_documents({"session_id": st["sid"]}) == 1

    def test_check_shows_credit(self, vendor, st):
        d = vendor.get(f"{API}/vendor-tenders/start/check").json()
        assert d["required"] and d["credit"]["id"] == st["credit"] and d["credit"]["category"] == CAT

    def test_dpr_async_allowed_with_credit(self, vendor):
        r = vendor.post(f"{API}/tender-pro/dpr/analyze-async", json={"filename": "TEST_R11.txt", "content_b64": B64})
        assert r.status_code == 200, r.text
        assert r.json().get("job_id")

    def test_create_consumes_credit(self, vendor, st):
        r = vendor.post(f"{API}/tender-templates?credit_id={st['credit']}",
                        json=_tpl("TEST_R11 paid", {"work_title": "TEST_R11 paid work", "product_category": "Other"}))
        assert r.status_code == 200, r.text
        d = r.json()
        st["tid"] = d["id"]
        assert d["header"]["product_category"] == CAT
        assert float(d["header"]["tender_value"]) == 50000
        assert d["fees_paid"][st["code"]]["amount"] == 25
        cr = _mdb.tender_credits.find_one({"_id": ObjectId(st["credit"])})
        assert cr["status"] == "used" and cr["template_id"] == st["tid"]
        fees = vendor.get(f"{API}/vendor-tenders/fees/{st['tid']}").json()["fees"]
        up = next(f for f in fees if f["code"] == st["code"])
        assert up["paid"] is True

    def test_second_create_402(self, vendor):
        assert vendor.post(f"{API}/tender-templates", json=_tpl("TEST_R11 again")).status_code == 402
        r = vendor.post(f"{API}/tender-pro/dpr/analyze-json", json={"filename": "TEST_R11.txt", "content_b64": B64})
        assert r.status_code == 402

    def test_paid_draft_work_allowed(self, vendor, st):
        r = vendor.patch(f"{API}/tender-pro/templates/{st['tid']}/sections/sec-1", json={"body": "<p>ok</p>"})
        assert r.status_code == 200, r.text

    def test_free_category_credit(self, vendor, st):
        q = vendor.post(f"{API}/vendor-tenders/start/quote", json={"category": CAT_FREE}).json()
        assert q["total"] == 0 and q["fees"] == []
        r = vendor.post(f"{API}/vendor-tenders/start/checkout", json={"category": CAT_FREE, "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["free"] is True and d["credit_id"]
        t = vendor.post(f"{API}/tender-templates?credit_id={d['credit_id']}", json=_tpl("TEST_R11 free cat"))
        assert t.status_code == 200, t.text
        assert t.json()["header"]["product_category"] == CAT_FREE

    def test_invalid_credit_id_rejected(self, vendor, st):
        # a used credit id must not be reusable
        assert vendor.post(f"{API}/tender-templates?credit_id={st['credit']}",
                           json=_tpl("TEST_R11 reuse")).status_code == 402


class TestReceipts:
    def test_tender_fee_receipt(self, vendor, admin, st):
        # make a second upfront per-tender fee not covered by the credit: raise value → no; use a
        # direct tender_fee tx on the paid draft for the existing on-completion seeded fee instead.
        fees = vendor.get(f"{API}/vendor-tenders/fees/{st['tid']}").json()["fees"]
        due = [f for f in fees if not f["paid"] and not f["needs_value"]]
        if not due:
            pytest.skip("No unpaid per-tender fee applies to this draft")
        r = vendor.post(f"{API}/vendor-tenders/fees/{st['tid']}/checkout",
                        json={"fee_code": due[0]["code"], "origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        _mark_paid(sid)
        for _ in range(2):
            assert vendor.get(f"{API}/vendor-tenders/fees/checkout/status/{sid}").json()["payment_status"] == "paid"
        recs = list(_mdb.fee_receipts.find({"session_id": sid}))
        assert len(recs) == 1 and recs[0]["purpose"] == "tender_fee"
        assert recs[0]["tender_name"] == "TEST_R11 paid work" and recs[0]["category"] == CAT
        st["fee_rno"] = recs[0]["receipt_no"]

    def test_receipts_list_own(self, vendor, st):
        r = vendor.get(f"{API}/vendor-tenders/receipts")
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        nos = [x["receipt_no"] for x in items]
        assert st["rno"] in nos
        assert all("_id" not in x for x in items)
        if st.get("fee_rno"):
            assert st["fee_rno"] in nos and nos.index(st["fee_rno"]) < nos.index(st["rno"])  # newest first

    def test_receipts_other_vendor_empty(self, vendor_b):
        r = vendor_b.get(f"{API}/vendor-tenders/receipts")
        assert r.status_code == 200 and r.json()["items"] == []

    def test_receipts_requires_vendor(self, admin):
        assert requests.get(f"{API}/vendor-tenders/receipts").status_code in (401, 403)
        assert admin.get(f"{API}/vendor-tenders/receipts").status_code in (401, 403)

    def test_teardown_rule(self, admin, st):
        for k in ("rule", "rule2"):
            assert admin.delete(f"{API}/tender-pro/emd-masters/{st[k]}").status_code == 200
        ids = {x["code"]: x["id"] for x in admin.get(f"{API}/fee-types").json()}
        for k in ("code", "code2"):
            assert admin.delete(f"{API}/fee-types/{ids[st[k]]}").status_code == 200
