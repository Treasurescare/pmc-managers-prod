# v166 UI seed/cleanup: python tests/seed_v166_ui.py seed|clean
import os, sys, json
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
d = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def seed():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token") or ""
    dl = (datetime.now(timezone.utc) + timedelta(days=20)).date().isoformat()
    out = {}
    for k in ("draft_priv", "draft_pub", "pub_fee", "pub_public"):
        r = s.post(f"{API}/notices", json={"title": f"TEST_V166UI {k}", "description": "TEST_V166UI description",
                                           "category": "Civil Works", "delivery_country": "KZ", "submission_deadline": dl,
                                           "budget_amount": 10000, "is_published": False})
        out[k] = r.json()["notice_ref"]
    d.notices.update_one({"notice_ref": out["draft_pub"]}, {"$set": {"buyer_type": "public_sector"}})
    d.notices.update_one({"notice_ref": out["pub_fee"]}, {"$set": {"is_published": True, "winner_fee_enabled": True, "winner_fee_pct": 0.30}})
    d.notices.update_one({"notice_ref": out["pub_public"]}, {"$set": {"is_published": True}})
    d.buyer_classifications.insert_one({"notice_ref": out["pub_public"], "buyer_type": "public_sector", "status": "verified", "TEST_V166UI": True})
    v = d.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    b = d.bids.insert_one({"notice_ref": out["pub_fee"], "vendor_id": str(v["_id"]), "bid_ref": "TEST_V166UI-W", "status": "awarded",
                           "price_amount": 250000.0, "price_currency": "USD", "vendor_email": v["email"]}).inserted_id
    out["bid"] = str(b)
    print(json.dumps(out))


def clean():
    refs = [n["notice_ref"] for n in d.notices.find({"title": {"$regex": "^TEST_V166UI"}})]
    print(d.notices.delete_many({"notice_ref": {"$in": refs}}).deleted_count,
          d.bids.delete_many({"notice_ref": {"$in": refs}}).deleted_count,
          d.buyer_classifications.delete_many({"notice_ref": {"$in": refs}}).deleted_count)


seed() if sys.argv[1] == "seed" else clean()
