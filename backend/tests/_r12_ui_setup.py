# R12 UI setup/cleanup: python tests/_r12_ui_setup.py seed|clean
import os, sys, secrets
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
V = "testvendor@pmcmanagers.com"
v = db.vendors.find_one({"email": V})
if sys.argv[1] == "seed":
    db.vendor_category_requests.delete_many({"vendor_ref": v["vendor_ref"]})
    db.vendors.update_one({"_id": v["_id"]}, {"$set": {"country": "XT", "business_categories": []}})
    db.emd_masters.delete_many({"name": {"$regex": "^TEST_R12"}})
    db.emd_masters.insert_one({"name": "TEST_R12 Registration", "country": "XT", "kind": "registration",
        "currency": "usd", "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed",
        "fixed_amount": 25.0}], "is_active": True, "categories": [], "category": None})
    tok = secrets.token_urlsafe(16)
    db.registrations.delete_many({"legal_name": "TEST_R12 Reg UI"})
    rid = db.registrations.insert_one({"status": "draft", "magic_token": tok, "legal_name": "TEST_R12 Reg UI",
        "email": "test_r12_ui@example.com", "business_categories": []}).inserted_id
    print("TOKEN", tok, rid)
else:
    ids = [str(r["_id"]) for r in db.vendor_category_requests.find({"vendor_ref": v["vendor_ref"]})]
    db.vendor_category_requests.delete_many({"vendor_ref": v["vendor_ref"]})
    db.payment_transactions.delete_many({"purpose": "category_fee", "request_id": {"$in": ids}})
    db.fee_receipts.delete_many({"purpose": "category_fee", "request_id": {"$in": ids}})
    db.emd_masters.delete_many({"name": {"$regex": "^TEST_R12"}})
    db.registrations.delete_many({"legal_name": {"$regex": "^TEST_R12"}})
    db.vendors.update_one({"_id": v["_id"]}, {"$set": {"country": None, "business_categories": None}})
    print("cleaned", len(ids))
