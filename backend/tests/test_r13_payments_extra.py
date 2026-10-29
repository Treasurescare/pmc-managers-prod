# R13 — payments wiring: category approve null fix, fee-type country scope + find_rule precedence,
# charge-fee payer email, EMD collector guard, category upsell (bid 403 + interest dedupe),
# doc download fee gate, hosting fee (publish guard + pay/status credit), data intel, refund alerts, cron.
# Run serially: pytest tests/test_r13_payments_extra.py -n 0
import os
import sys
import base64
import asyncio
import pytest
import requests
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
C = "XT"
HVAC = "Heating, ventilation & air-conditioning (HVAC)"
OTHER_CAT = "TEST_R13 Other Category"

from pymongo import MongoClient  # noqa: E402
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ST = {}
DOCS = [{"kind": k, "key": f"TEST_R13_{k}", "filename": f"{k}.pdf", "size_bytes": 10,
         "uploaded_at": "2026-01-01T00:00:00Z"} for k in ("technical", "commercial")]


def _login(path, cred):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": cred[0], "password": cred[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin/auth/login", ADMIN)


@pytest.fixture(scope="module")
def vdoc():
    v = _mdb.vendors.find_one({"email": VENDOR[0]})
    yield v
    _mdb.vendors.update_one({"_id": v["_id"]}, {"$set": {"business_categories": [HVAC], "country": None}})
    _mdb.emd_masters.delete_many({"name": {"$regex": "^TEST_R13"}})
    _mdb.fee_types.delete_many({"code": {"$regex": "^test_r13"}})
    refs = [n["notice_ref"] for n in _mdb.notices.find({"title": {"$regex": "^TEST_R13"}})]
    _mdb.notices.delete_many({"notice_ref": {"$in": refs}})
    _mdb.bids.delete_many({"notice_ref": {"$in": refs}})
    _mdb.doc_purchases.delete_many({"notice_ref": {"$in": refs}})
    _mdb.category_upsell_log.delete_many({"notice_ref": {"$in": refs}})
    _mdb.notifications.delete_many({"related_id": {"$in": refs}})
    _mdb.messages.delete_many({"subject": {"$regex": "|".join(refs) or "^$"}})
    _mdb.payment_transactions.delete_many({"$or": [{"notice_ref": {"$in": refs}}, {"session_id": {"$regex": "^TEST_R13"}},
                                                    {"context_ref": {"$regex": "^TEST_R13"}}]})
    _mdb.fee_receipts.delete_many({"$or": [{"notice_ref": {"$in": refs}}, {"session_id": {"$regex": "^TEST_R13"}}]})
    ids = [str(d["_id"]) for d in _mdb.data_intel_requests.find({"subject": {"$regex": "^TEST_R13"}})]
    _mdb.data_intel_requests.delete_many({"subject": {"$regex": "^TEST_R13"}})
    sids = [t["session_id"] for t in _mdb.payment_transactions.find({"request_id": {"$in": ids}})]
    _mdb.fee_receipts.delete_many({"session_id": {"$in": sids}})
    _mdb.payment_transactions.delete_many({"request_id": {"$in": ids}})
    _mdb.payment_transactions.delete_many({"payer_email": {"$regex": "^test_r13"}})
    _mdb.vendor_category_requests.delete_many({"vendor_ref": v["vendor_ref"], "category_name": {"$regex": "^TEST_R13"}})
    _mdb.uploads.delete_many({"key": {"$regex": "^TEST_R13"}})


@pytest.fixture(scope="module")
def vendor(vdoc):
    _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [HVAC]}})
    return _login("vendor/auth/login", VENDOR)


def _rule(admin, kind, amount, name, country=C, cats=None, calc="fixed"):
    return admin.post(f"{API}/tender-pro/emd-masters", json={
        "name": name, "country": country, "kind": kind, "currency": "USD", "categories": cats or [],
        "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": calc, "fixed_amount": amount}]})


def _notice(admin, cat, published=True, **extra):
    dl = (datetime.now(timezone.utc) + timedelta(days=20)).date().isoformat()
    r = admin.post(f"{API}/notices", json={"title": f"TEST_R13 {cat[:20]}", "description": "TEST_R13 notice description",
                                           "category": cat, "delivery_country": C, "submission_deadline": dl,
                                           "budget_amount": 10000, "is_published": published, **extra})
    assert r.status_code == 200, r.text
    return r.json()["notice_ref"]


class TestApproveNullFix:
    def test_approve_with_null_business_categories(self, admin, vendor, vdoc):
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": None}})
        rid = _mdb.vendor_category_requests.insert_one({
            "vendor_ref": vdoc["vendor_ref"], "vendor_email": vdoc["email"], "category_code": "TEST_R13_A",
            "category_name": "TEST_R13 Approve Cat", "status": "pending", "payment_status": "not_required"}).inserted_id
        r = admin.post(f"{API}/vendors/category-requests/{rid}/approve", json={})
        assert r.status_code == 200, r.text
        v = _mdb.vendors.find_one({"_id": vdoc["_id"]})
        assert v["business_categories"] == ["TEST_R13 Approve Cat"]
        _mdb.vendors.update_one({"_id": vdoc["_id"]}, {"$set": {"business_categories": [HVAC]}})


class TestFeeTypesCountry:
    def test_seeded_types(self, admin):
        r = admin.get(f"{API}/fee-types")
        assert r.status_code == 200
        codes = {t["code"]: t for t in r.json()}
        assert "tender_hosting" in codes and "tender_document_download" in codes
        assert codes["tender_hosting"]["used_in_tender_builder"] is True
        assert all("country_scope" in t for t in r.json())

    def test_selected_country_type_validation(self, admin):
        r = admin.post(f"{API}/fee-types", json={"name": "TEST_R13 Selected", "code": "test_r13_sel",
                                                 "country_scope": "selected", "countries": ["XT"]})
        assert r.status_code == 200, r.text
        assert r.json()["country_scope"] == "selected" and r.json()["countries"] == ["XT"]
        bad = _rule(admin, "test_r13_sel", 5, "TEST_R13 bad", country="ALL")
        assert bad.status_code == 422, bad.text
        bad2 = _rule(admin, "test_r13_sel", 5, "TEST_R13 bad2", country="IN")
        assert bad2.status_code == 422
        ok = _rule(admin, "test_r13_sel", 5, "TEST_R13 ok", country="XT")
        assert ok.status_code == 200, ok.text

    def test_find_rule_precedence(self, admin):
        from routers._fees import find_rule
        assert _rule(admin, "data_intel", 10, "TEST_R13 DI all", country="ALL").status_code == 200
        loop = asyncio.new_event_loop()
        try:
            r = loop.run_until_complete(find_rule("data_intel", "XT", "X"))
            assert r["name"] == "TEST_R13 DI all"
            assert _rule(admin, "data_intel", 20, "TEST_R13 DI XT", country="XT").status_code == 200
            r = loop.run_until_complete(find_rule("data_intel", "XT", "X"))
            assert r["name"] == "TEST_R13 DI XT"
        finally:
            loop.close()


class TestChargeFee:
    def test_admin_requires_payer_email(self, admin):
        mid = _mdb.emd_masters.find_one({"name": "TEST_R13 DI XT"})["_id"]
        r = admin.post(f"{API}/billing/fee-checkout", json={"fee_master_id": str(mid), "tender_value": 0,
                                                           "origin_url": BASE_URL, "context_ref": "TEST_R13"})
        assert r.status_code == 422 and "Payer email" in r.text
        r = admin.post(f"{API}/billing/fee-checkout", json={"fee_master_id": str(mid), "tender_value": 0,
                                                           "origin_url": BASE_URL, "context_ref": "TEST_R13",
                                                           "buyer_email": "test_r13_payer@example.com"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["emailed_to"] == "test_r13_payer@example.com" and d["checkout_url"].startswith("https://")
        assert d["amount"] == 20.0


class TestEmdCollector:
    def test_notice_collector_copied_and_checkout_409(self, admin, vendor):
        ref = _notice(admin, HVAC, emd_collector={"type": "tender_caller", "name": "TEST Caller", "instructions": "Wire to XYZ"})
        ST["hvac_ref"] = ref
        n = _mdb.notices.find_one({"notice_ref": ref})
        assert n["emd_collector"]["type"] == "tender_caller"
        r = vendor.post(f"{API}/bids", json={"notice_ref": ref, "price_amount": 9000, "documents": DOCS})
        assert r.status_code == 200, r.text
        bid = r.json()
        b = _mdb.bids.find_one({"_id": ObjectId(bid["id"])})
        assert b["emd_collector"]["name"] == "TEST Caller"
        print("bid emd_due", b.get("emd_due_amount"), b.get("status"))
        if (b.get("emd_due_amount") or 0) > 0:
            r = vendor.post(f"{API}/payments/emd/checkout", json={"bid_id": bid["id"], "origin_url": BASE_URL})
            assert r.status_code == 409 and "Wire to XYZ" in r.text, r.text
        else:
            pytest.skip("No EMD due computed for the notice — collector guard not reachable")


class TestCategoryUpsell:
    def test_bid_403_and_interest_dedupe(self, admin, vendor, vdoc):
        ref = _notice(admin, OTHER_CAT)
        ST["other_ref"] = ref
        r = vendor.post(f"{API}/bids", json={"notice_ref": ref, "price_amount": 9000, "documents": DOCS})
        assert r.status_code == 403, r.text
        assert r.json()["detail"]["code"] == "category_not_registered"
        for _ in range(2):
            r = vendor.post(f"{API}/notices/{ref}/category-interest")
            assert r.status_code == 200 and r.json()["registered"] is False
        assert _mdb.notifications.count_documents({"related_id": ref}) == 1
        assert _mdb.messages.count_documents({"subject": {"$regex": ref}}) == 1
        assert _mdb.category_upsell_log.count_documents({"notice_ref": ref}) == 1

    def test_interest_registered(self, vendor):
        r = vendor.post(f"{API}/notices/{ST['hvac_ref']}/category-interest")
        assert r.status_code == 200 and r.json()["registered"] is True


class TestDocFee:
    def test_pack_gate(self, admin, vendor, vdoc):
        assert _rule(admin, "tender_document_download", 5, "TEST_R13 Doc").status_code == 200
        ref = ST["hvac_ref"]
        _mdb.uploads.insert_one({"key": "TEST_R13_doc", "data_b64": base64.b64encode(b"hello").decode()})
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"primary_document": {
            "file_name": "t.pdf", "url": "/api/v1/uploads/files/TEST_R13_doc"}}})
        assert requests.get(f"{API}/notices/{ref}/pack").status_code == 401
        r = vendor.get(f"{API}/notices/{ref}/pack")
        assert r.status_code == 402 and r.json()["detail"]["code"] == "doc_fee_required", r.text
        assert admin.get(f"{API}/notices/{ref}/pack").status_code == 200
        q = vendor.get(f"{API}/notices/{ref}/doc-fee").json()
        assert q["required"] is True and q["paid"] is False and q["amount"] == 5.0
        r = vendor.post(f"{API}/notices/{ref}/doc-fee/checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        _mdb.payment_transactions.update_one({"session_id": sid}, {"$set": {"payment_status": "paid"}})
        for _ in range(2):
            s = vendor.get(f"{API}/notices/doc-fee/status/{sid}")
            assert s.status_code == 200 and s.json()["payment_status"] == "paid"
        assert _mdb.fee_receipts.count_documents({"session_id": sid}) == 1
        for _ in range(2):
            assert vendor.get(f"{API}/notices/{ref}/pack").status_code == 200
        assert vendor.post(f"{API}/notices/{ref}/doc-fee/checkout", json={"origin_url": BASE_URL}).status_code == 409

    def test_public_file_not_bypassing_doc_fee(self):
        # individual docs of a fee-gated notice must not be downloadable anonymously
        ref = ST["hvac_ref"]
        k = f"notice-docs/{ref}/TEST_R13_spec.pdf"
        _mdb.uploads.insert_one({"key": k, "data_b64": base64.b64encode(b"x").decode(), "notice_ref": ref})
        try:
            r = requests.get(f"{API}/uploads/public-files/{k}?download=1")
            assert r.status_code in (401, 402), f"anonymous public-files download returned {r.status_code}"
        finally:
            _mdb.uploads.delete_one({"key": k})


class TestHostingFee:
    def test_hosting_flow(self, admin):
        assert _rule(admin, "tender_hosting", 50, "TEST_R13 Host").status_code == 200
        ref = _notice(admin, HVAC, published=False)
        q = admin.get(f"{API}/notices/{ref}/hosting-fee").json()
        assert q["required"] is True and q["amount"] == 50.0
        r = admin.post(f"{API}/notices/{ref}/hosting-fee/request", json={"payer_email": "test_r13_buyer@example.com"})
        assert r.status_code == 200, r.text
        n = _mdb.notices.find_one({"notice_ref": ref})
        assert n["hosting_fee"]["status"] == "unpaid"
        assert admin.post(f"{API}/notices/{ref}/publish").status_code == 409
        # bypass check: PATCH is_published while unpaid
        p = admin.patch(f"{API}/notices/{ref}", json={"is_published": True})
        ST["patch_bypass"] = (p.status_code, _mdb.notices.find_one({"notice_ref": ref}).get("is_published"))
        _mdb.notices.update_one({"notice_ref": ref}, {"$set": {"is_published": False}})
        sid = n["hosting_fee"]["session_id"]
        _mdb.payment_transactions.update_one({"session_id": sid}, {"$set": {"payment_status": "paid"}})
        s = requests.get(f"{API}/pay/status/{sid}")
        assert s.status_code == 200 and s.json()["payment_status"] == "paid"
        n = _mdb.notices.find_one({"notice_ref": ref})
        assert n["is_published"] is True and n["hosting_fee"]["status"] == "paid"

    def test_patch_bypass_report(self):
        code, pub = ST["patch_bypass"]
        assert not pub, f"PATCH is_published=true bypassed unpaid hosting fee (status {code})"


class TestDataIntel:
    def test_flow(self, admin, vendor):
        r = vendor.post(f"{API}/data-intel/requests", json={"kind": "market_insights", "subject": "TEST_R13 intel",
                                                             "country": "XT"})
        assert r.status_code == 200, r.text
        rid = r.json()["id"]
        assert any(x["id"] == rid for x in vendor.get(f"{API}/data-intel/requests/mine").json()["items"])
        lst = admin.get(f"{API}/data-intel/admin").json()["items"]
        it = [x for x in lst if x["id"] == rid][0]
        assert it["suggested_amount"] == 20.0
        assert vendor.post(f"{API}/data-intel/requests/{rid}/checkout", json={"origin_url": BASE_URL}).status_code == 409
        assert admin.post(f"{API}/data-intel/admin/{rid}/deliver", json={"summary": "xxx"}).status_code == 409
        assert admin.post(f"{API}/data-intel/admin/{rid}/quote", json={"amount": 15, "currency": "usd"}).status_code == 200
        r = vendor.post(f"{API}/data-intel/requests/{rid}/checkout", json={"origin_url": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        _mdb.payment_transactions.update_one({"session_id": sid}, {"$set": {"payment_status": "paid"}})
        assert requests.get(f"{API}/pay/status/{sid}").json()["payment_status"] == "paid"
        assert _mdb.data_intel_requests.find_one({"_id": ObjectId(rid)})["status"] == "paid"
        r = admin.post(f"{API}/data-intel/admin/{rid}/deliver", json={"summary": "TEST_R13 summary"})
        assert r.status_code == 200
        d = [x for x in vendor.get(f"{API}/data-intel/requests/mine").json()["items"] if x["id"] == rid][0]
        assert d["status"] == "delivered" and d["delivery"]["summary"] == "TEST_R13 summary"

    def test_decline(self, admin, vendor):
        rid = vendor.post(f"{API}/data-intel/requests", json={"kind": "vendor_report", "subject": "TEST_R13 decline"}).json()["id"]
        assert admin.post(f"{API}/data-intel/admin/{rid}/decline", json={"notes": "nope"}).status_code == 200
        assert admin.post(f"{API}/data-intel/admin/{rid}/decline", json={"notes": "nope"}).status_code == 409

    def test_invalid_id(self, vendor):
        r = vendor.post(f"{API}/data-intel/requests/notanid/checkout", json={"origin_url": BASE_URL})
        assert r.status_code in (404, 409, 422), r.status_code


class TestRefundAlerts:
    def test_list_and_refund_failure(self, admin):
        _mdb.payment_transactions.insert_one({"session_id": "TEST_R13_fake", "purpose": "data_intel", "amount": 1,
                                              "currency": "usd", "needs_refund": True, "updated_at": "9999"})
        lst = admin.get(f"{API}/billing/refund-alerts").json()["items"]
        assert any(x["session_id"] == "TEST_R13_fake" for x in lst)
        r = admin.post(f"{API}/billing/refund-alerts/TEST_R13_fake/refund")
        assert r.status_code == 424
        assert _mdb.payment_transactions.find_one({"session_id": "TEST_R13_fake"}).get("refund_error")
        assert admin.post(f"{API}/billing/refund-alerts/TEST_R13_none/refund").status_code == 404


class TestCron:
    def test_auth(self, vdoc):
        url = f"{API}/cron/category-payment-reminders"
        assert requests.post(url).status_code == 401
        assert requests.post(url, headers={"Authorization": "Bearer wrong"}).status_code == 401
        old = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        rid = _mdb.vendor_category_requests.insert_one({
            "vendor_ref": vdoc["vendor_ref"], "vendor_email": vdoc["email"], "vendor_id": str(vdoc["_id"]),
            "category_code": "TEST_R13_R", "category_name": "TEST_R13 Remind", "status": "payment_pending",
            "payment_status": "unpaid", "fee_amount": 25.0, "fee_currency": "USD", "sent_back_at": old}).inserted_id
        r = requests.post(url, headers={"Authorization": f"Bearer {os.environ['WEBHOOK_CRON_SECRET']}"})
        assert r.status_code == 200 and r.json()["ok"] is True
        import time
        for _ in range(15):
            d = _mdb.vendor_category_requests.find_one({"_id": rid})
            if d.get("reminders_sent"):
                break
            time.sleep(1)
        assert d.get("reminders_sent") == 1 and d.get("last_reminder_at")
