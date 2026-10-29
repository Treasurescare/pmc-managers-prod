# R12 — Paid additional categories: fee-quote, request payment_status, checkout, payment-pending send-back,
# approve guard (409 unpaid), payment apply (idempotent receipt), registration submit >1 category guard.
# Run serially: pytest tests/test_r12_category_fees.py -n 0
import os
import sys
import secrets
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
TEST_COUNTRY = "XT"

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CATS = [c for c in _mdb.categories.find({"is_active": True}).limit(4)]


def _vlogin():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": VENDOR[0], "password": VENDOR[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def vdoc():
    v = _mdb.vendors.find_one({"email": VENDOR[0]})
    before = {k: v.get(k) for k in ("country", "business_categories")}
    yield v
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": before})
    _mdb.emd_masters.delete_many({"name": {"$regex": "^TEST_R12"}})
    ids = [str(r["_id"]) for r in _mdb.vendor_category_requests.find({"vendor_ref": v["vendor_ref"]})]
    _mdb.vendor_category_requests.delete_many({"vendor_ref": v["vendor_ref"]})
    _mdb.payment_transactions.delete_many({"purpose": "category_fee", "request_id": {"$in": ids}})
    _mdb.fee_receipts.delete_many({"purpose": "category_fee", "request_id": {"$in": ids}})


@pytest.fixture(scope="module")
def vendor(vdoc):
    _mdb.vendor_category_requests.delete_many({"vendor_ref": vdoc["vendor_ref"]})
    _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"country": None, "business_categories": []}})
    return _vlogin()


def _req(s, c):
    return s.post(f"{API}/vendor/categories/request",
                  json={"category_code": c["code"], "category_name": c["name"]})


class TestCategoryFees:
    def test_first_category_free_quote(self, vendor):
        r = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[0]["name"]})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["required"] is False and d["reason"] == "first_free" and "free for one category" in d["message"]

    def test_first_request_not_required(self, vendor):
        r = _req(vendor, CATS[0])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["payment_status"] == "not_required" and d["fee_message"] is None

    def test_second_no_rule_free(self, vendor, vdoc):
        # vendor country unset -> no price -> free
        r = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[1]["name"]})
        assert r.json()["reason"] == "no_price" and r.json()["required"] is False

    def test_second_paid_with_rule(self, vendor, vdoc):
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"country": TEST_COUNTRY}})
        _mdb.emd_masters.insert_one({
            "name": "TEST_R12 Registration", "country": TEST_COUNTRY, "kind": "registration", "currency": "usd",
            "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed", "fixed_amount": 25.0}],
            "is_active": True, "categories": [], "category": None})
        q = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[1]["name"]}).json()
        assert q["required"] is True and q["amount"] == 25.0 and q["currency"] == "USD"
        r = _req(vendor, CATS[1])
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["payment_status"] == "unpaid" and d["fee_amount"] == 25.0 and d["fee_currency"] == "USD"
        assert "free for one category" in (d["fee_message"] or "")
        pytest.paid_id = d["id"]

    def test_category_specific_rule_preferred(self, vendor):
        _mdb.emd_masters.insert_one({
            "name": "TEST_R12 Specific", "country": TEST_COUNTRY, "kind": "registration", "currency": "usd",
            "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed", "fixed_amount": 40.0}],
            "is_active": True, "categories": [CATS[2]["name"]], "category": None})
        q = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[2]["name"]}).json()
        assert q["amount"] == 40.0
        q2 = vendor.get(f"{API}/vendor/categories/fee-quote", params={"category_name": CATS[3]["name"]}).json()
        assert q2["amount"] == 25.0

    def test_approve_unpaid_409(self, admin):
        r = admin.post(f"{API}/vendors/category-requests/{pytest.paid_id}/approve", json={})
        assert r.status_code == 409 and "Payment pending" in r.text

    def test_vendor_checkout(self, vendor):
        r = vendor.post(f"{API}/vendor/categories/requests/{pytest.paid_id}/checkout",
                        json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_url"].startswith("https://") and d["session_id"]
        tx = _mdb.payment_transactions.find_one({"session_id": d["session_id"]})
        assert tx["purpose"] == "category_fee" and tx["amount"] == 25.0 and tx["currency"] == "usd"

    def test_send_back_payment_pending(self, admin, vendor):
        r = admin.post(f"{API}/vendors/category-requests/{pytest.paid_id}/payment-pending",
                       json={"origin_url": BASE_URL, "notes": "TEST_R12 please pay"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "payment_pending" and d["checkout_url"].startswith("https://")
        lst = admin.get(f"{API}/vendors/category-requests", params={"status": "payment_pending"}).json()
        assert any(x["id"] == pytest.paid_id for x in lst)
        mine = vendor.get(f"{API}/vendor/categories/mine").json()
        assert any(x["id"] == pytest.paid_id and x["status"] == "payment_pending" for x in mine["pending"])
        # approve while payment_pending -> 409
        assert admin.post(f"{API}/vendors/category-requests/{pytest.paid_id}/approve", json={}).status_code == 409
        # second send-back allowed? should stay 200 (still unpaid) — record sessions
        pytest.sb_session = _mdb.payment_transactions.find_one(
            {"request_id": pytest.paid_id}, sort=[("created_at", -1)])["session_id"]

    def test_duplicate_includes_payment_pending(self, vendor):
        r = _req(vendor, CATS[1])
        assert r.status_code == 409

    def test_checkout_status_applies_payment_idempotent(self, vendor):
        sid = pytest.sb_session
        _mdb.payment_transactions.update_one({"session_id": sid},
                                             {"$set": {"payment_status": "paid", "status": "completed"}})
        for _ in range(2):
            r = vendor.get(f"{API}/vendor/categories/checkout/status/{sid}")
            assert r.status_code == 200 and r.json()["payment_status"] == "paid"
        req = _mdb.vendor_category_requests.find_one({"_id": ObjectId(pytest.paid_id)})
        assert req["payment_status"] == "paid" and req["status"] == "pending"
        assert _mdb.fee_receipts.count_documents({"session_id": sid}) == 1
        rec = _mdb.fee_receipts.find_one({"session_id": sid})
        assert rec["purpose"] == "category_fee" and rec["total"] == 25.0 and rec["currency"] == "USD"

    def test_checkout_after_paid_409(self, vendor):
        r = vendor.post(f"{API}/vendor/categories/requests/{pytest.paid_id}/checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 409

    def test_approve_paid_adds_category(self, admin, vdoc):
        r = admin.post(f"{API}/vendors/category-requests/{pytest.paid_id}/approve", json={})
        assert r.status_code == 200, r.text
        v = _mdb.vendors.find_one({"_id": vdoc["_id"]})
        assert CATS[1]["name"] in v["business_categories"]

    def test_send_back_not_required_409(self, admin, vendor):
        rid = vendor.get(f"{API}/vendor/categories/mine").json()["pending"]
        free = [x for x in rid if x["payment_status"] == "not_required"]
        assert free
        r = admin.post(f"{API}/vendors/category-requests/{free[0]['id']}/payment-pending",
                       json={"origin_url": BASE_URL})
        assert r.status_code == 409


class TestRegistrationSubmitGuard:
    def test_submit_two_categories_400(self):
        tok = secrets.token_urlsafe(16)
        doc = {"status": "draft", "magic_token": tok, "legal_name": "TEST_R12 Reg", "email": "test_r12@example.com",
               "business_categories": ["A", "B"],
               **{d: True for d in ["decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
                                    "decl_data_consent", "decl_fee", "decl_notification"]}}
        rid = _mdb.registrations.insert_one(doc).inserted_id
        try:
            r = requests.post(f"{API}/registrations/{rid}/submit", params={"token": tok})
            assert r.status_code == 400 and "free for one category" in r.text
            _mdb.registrations.update_one({"_id": rid}, {"$set": {"business_categories": ["A"]}})
            r2 = requests.post(f"{API}/registrations/{rid}/submit", params={"token": tok})
            assert "free for one category" not in r2.text
        finally:
            _mdb.registrations.delete_one({"_id": rid})
