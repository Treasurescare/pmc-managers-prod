# Helper for UI testing of R11 start gate + receipts: `setup` / `cleanup` / `state`
import os, sys, requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
from pymongo import MongoClient
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
CAT, CAT_FREE = "Fire alarm & safety systems", "Office furniture"
VEMAIL = "testvendor@pmcmanagers.com"
SLAB = lambda amt: [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed", "fixed_amount": amt}]

v = db.vendors.find_one({"email": VEMAIL})
vid = str(v["_id"])
if sys.argv[1] == "setup":
    db.vendors.update_one({"email": VEMAIL}, {"$set": {"profile.country": "KZ", "business_categories": [CAT, CAT_FREE]}})
    a = requests.Session()
    r = a.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    a.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    c1 = a.post(f"{API}/fee-types", json={"name": "TEST R11 Start", "timing": "upfront", "calc": "fixed",
                "amount_mode": "single", "category_scope": "selected", "billing": "one_time",
                "used_in_tender_builder": True}).json()["code"]
    c2 = a.post(f"{API}/fee-types", json={"name": "TEST R11 Completion", "timing": "on_completion", "calc": "fixed",
                "amount_mode": "single", "category_scope": "all", "billing": "one_time",
                "used_in_tender_builder": True}).json()["code"]
    print(c1, c2)
    print(a.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R11 start", "country": "KZ", "kind": c1,
          "categories": [CAT], "currency": "USD", "slabs": SLAB(25)}).status_code)
    print(a.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_R11 completion", "country": "KZ", "kind": c2,
          "currency": "USD", "slabs": SLAB(40)}).status_code)
elif sys.argv[1] == "state":
    for c in db.tender_credits.find({"vendor_id": vid}): print("credit", c["status"], c["category"], c.get("total"), c.get("template_id"))
    for r in db.fee_receipts.find({"vendor_id": vid}): print("receipt", r["receipt_no"], r["purpose"], r["total"], r.get("tender_name"))
    for t in db.tender_templates.find({"owner_vendor_id": vid}, {"name": 1, "fees_paid": 1, "header.product_category": 1}): print("tpl", t)
    for t in db.payment_transactions.find({"vendor_id": vid}): print("tx", t["purpose"], t["payment_status"], t.get("credited"))
else:
    db.vendors.update_one({"_id": v["_id"]}, {"$set": {"profile": {}, "business_categories": None}})
    print("tpl", db.tender_templates.delete_many({"owner_vendor_id": vid}).deleted_count)
    print("tx", db.payment_transactions.delete_many({"vendor_id": vid}).deleted_count)
    print("credits", db.tender_credits.delete_many({"vendor_id": vid}).deleted_count)
    print("receipts", db.fee_receipts.delete_many({"vendor_id": vid}).deleted_count)
    print("rules", db.emd_masters.delete_many({"name": {"$regex": "^TEST_"}}).deleted_count)
    print("types", db.fee_types.delete_many({"name": {"$regex": "^TEST R11"}}).deleted_count)
    print(db.fee_types.count_documents({}), db.emd_masters.count_documents({}))
