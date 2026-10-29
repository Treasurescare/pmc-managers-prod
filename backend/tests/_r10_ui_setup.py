# Helper for UI testing of R10 tender fees: `setup` / `cleanup`
import os, sys, requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
from pymongo import MongoClient
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
CAT = "Fire alarm & safety systems"
VEMAIL = "testvendor@pmcmanagers.com"

if sys.argv[1] == "setup":
    db.vendors.update_one({"email": VEMAIL}, {"$set": {"profile.country": "KZ", "business_categories": [CAT]}})
    a = requests.Session()
    r = a.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    a.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    r = a.post(f"{API}/tender-pro/emd-masters", json={"name": "TEST_UI TM", "country": "KZ", "kind": "tender_management",
        "categories": [CAT], "currency": "USD", "slabs": [
            {"tender_value_min": 0, "tender_value_max": 100000, "fee_type": "fixed", "fixed_amount": 50},
            {"tender_value_min": 100000, "tender_value_max": None, "fee_type": "percentage", "percentage": 1}]})
    print("rule", r.status_code)
    v = requests.Session()
    v.post(f"{API}/vendor/auth/login", json={"email": VEMAIL, "password": "Vendor@12345"})
    r = v.post(f"{API}/tender-templates", json={"name": "TEST_R10UI Fees tender", "kind": "tender",
        "header": {"work_title": "TEST_R10UI work", "work_description": "desc", "budget_currency": "USD",
                   "budget_amount": 50000, "tender_value": 50000, "product_category": CAT},
        "sections": [{"code": "sec-1", "kind": "section", "title": "NIB", "body": "<p>hi</p>"}]})
    print("tid", r.json()["id"])
    print(v.get(f"{API}/vendor-tenders/fees/{r.json()['id']}").json())
else:
    v = db.vendors.find_one({"email": VEMAIL})
    vid = str(v["_id"])
    db.vendors.update_one({"_id": v["_id"]}, {"$set": {"profile": {}, "business_categories": None}})
    print("tpl", db.tender_templates.delete_many({"owner_vendor_id": vid, "name": {"$regex": "^TEST_"}}).deleted_count)
    print("tx", db.payment_transactions.delete_many({"vendor_id": vid}).deleted_count)
    print("rules", db.emd_masters.delete_many({"name": {"$regex": "^TEST_"}}).deleted_count)
    print("types", db.fee_types.delete_many({"code": {"$regex": "^test_"}}).deleted_count)
    print(db.fee_types.count_documents({}), db.emd_masters.count_documents({}))
