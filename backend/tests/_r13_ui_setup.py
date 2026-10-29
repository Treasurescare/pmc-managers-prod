# R13 UI seed/clean: python tests/_r13_ui_setup.py seed|clean
import os, sys, json, base64, requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
from pymongo import MongoClient
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
HVAC = "Heating, ventilation & air-conditioning (HVAC)"


def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


def seed():
    a = admin()
    for kind, amt, nm in (("tender_document_download", 5, "TEST_R13UI Doc"), ("tender_hosting", 50, "TEST_R13UI Host")):
        r = a.post(f"{API}/tender-pro/emd-masters", json={"name": nm, "country": "XT", "kind": kind, "currency": "USD",
              "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed", "fixed_amount": amt}]})
        assert r.status_code == 200, r.text
    dl = (datetime.now(timezone.utc) + timedelta(days=20)).date().isoformat()
    out = {}
    for key, cat, pub in (("hvac", HVAC, True), ("other", "TEST_R13 Other Category", True), ("unpub", HVAC, False)):
        r = a.post(f"{API}/notices", json={"title": f"TEST_R13UI {key}", "description": "TEST_R13UI notice description",
              "category": cat, "delivery_country": "XT", "submission_deadline": dl, "budget_amount": 10000, "is_published": pub,
              "emd_collector": {"type": "tender_caller", "name": "TEST Caller", "instructions": "Wire to XYZ"}})
        assert r.status_code == 200, r.text
        ref = r.json()["notice_ref"]; out[key] = ref
        k = f"notice-docs/{ref}/TEST_R13_spec.pdf"
        db.uploads.insert_one({"key": k, "data_b64": base64.b64encode(b"%PDF-1.4 test").decode(), "notice_ref": ref})
        db.notices.update_one({"notice_ref": ref}, {"$set": {"primary_document": {"file_name": "spec.pdf", "url": f"/api/v1/uploads/files/{k}"}}})
    db.payment_transactions.insert_one({"session_id": "TEST_R13UI_fake", "purpose": "data_intel", "amount": 1.0,
        "currency": "usd", "needs_refund": True, "vendor_ref": "VEN-TEST01", "updated_at": "9999-01-01"})
    print(json.dumps(out))


def clean():
    refs = [n["notice_ref"] for n in db.notices.find({"title": {"$regex": "^TEST_R13UI"}})]
    db.notices.delete_many({"notice_ref": {"$in": refs}})
    db.emd_masters.delete_many({"name": {"$regex": "^TEST_R13"}})
    db.uploads.delete_many({"notice_ref": {"$in": refs}})
    for c in ("bids", "doc_purchases", "category_upsell_log", "payment_transactions", "fee_receipts"):
        db[c].delete_many({"notice_ref": {"$in": refs}})
    db.notifications.delete_many({"related_id": {"$in": refs}})
    for r in refs:
        db.messages.delete_many({"subject": {"$regex": r}})
    ids = [str(d["_id"]) for d in db.data_intel_requests.find({"subject": {"$regex": "^TEST_R13"}})]
    db.data_intel_requests.delete_many({"subject": {"$regex": "^TEST_R13"}})
    sids = [t["session_id"] for t in db.payment_transactions.find({"request_id": {"$in": ids}})]
    db.fee_receipts.delete_many({"$or": [{"session_id": {"$in": sids}}, {"tender_name": {"$regex": "^TEST_R13"}}]})
    db.payment_transactions.delete_many({"$or": [{"request_id": {"$in": ids}}, {"session_id": {"$regex": "^TEST_R13"}},
                                                  {"payer_email": {"$regex": "^test_r13"}}]})
    db.fee_types.delete_many({"code": {"$regex": "^test_r13"}})
    db.vendors.update_one({"email": "testvendor@pmcmanagers.com"}, {"$set": {"business_categories": [HVAC], "country": None}})
    print("cleaned", refs)


{"seed": seed, "clean": clean}[sys.argv[1]]()
