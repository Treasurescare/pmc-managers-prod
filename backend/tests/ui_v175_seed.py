# v175 UI seed helper: `setup` | `reset` | `cleanup` — TEST_ vendor + TEST_ published 'Wind generators' notice
import os, sys
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
sys.path.insert(0, "/app/backend")
from security import hash_password
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
VREF, VEMAIL, NREF = "TEST-VCSUI-01", "test_vcsui01@example.com", "TEST-WINDUI-01"
cmd = sys.argv[1]
if cmd == "setup":
    db.vendors.update_one({"vendor_ref": VREF}, {"$set": {
        "vendor_ref": VREF, "email": VEMAIL, "company_name": "TEST_ Wind UI Co", "country": "KZ",
        "tenant_id": "PMC-KZ-01", "password_hash": hash_password("Vendor@12345"), "status": "active",
        "kyc_status": "verified", "is_active": True, "business_categories": [],
        "profile": {"country": "KZ", "company_name": "TEST_ Wind UI Co", "business_categories": []},
        "created_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    db.notices.update_one({"notice_ref": NREF}, {"$set": {
        "notice_ref": NREF, "title": "TEST_ Wind generator supply UI", "category": "Wind generators",
        "tenant_id": "PMC-KZ-01", "delivery_country": "KZ", "currency": "USD", "budget_amount": 1000,
        "is_published": True, "document_type": "tender", "status": "published",
        "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()}}, upsert=True)
elif cmd == "reset":
    db.vendors.update_one({"vendor_ref": VREF}, {"$set": {"business_categories": [], "profile.business_categories": []}})
    db.vendor_category_requests.delete_many({"vendor_ref": VREF})
else:
    print(db.vendors.delete_one({"vendor_ref": VREF}).deleted_count, db.notices.delete_one({"notice_ref": NREF}).deleted_count,
          db.vendor_category_requests.delete_many({"vendor_ref": VREF}).deleted_count,
          db.bids.delete_many({"notice_ref": NREF}).deleted_count,
          db.messages.delete_many({"to_vendor_ref": VREF}).deleted_count,
          db.notifications.delete_many({"user_ref": VREF}).deleted_count)
print(cmd, db.vendors.find_one({"vendor_ref": VREF}, {"_id": 0, "business_categories": 1, "profile.business_categories": 1}))
