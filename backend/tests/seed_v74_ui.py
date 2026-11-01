# Seed / cleanup helper for v74 UI test (TEST_ prefixed data). Usage: python seed_v74_ui.py seed|clean
import sys
from datetime import datetime, timedelta, timezone
import requests
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
API = f"{BASE}/api/v1"

if sys.argv[1] == "clean":
    print("tpl", DB.tender_templates.delete_many({"name": {"$regex": "^TEST_"}}).deleted_count)
    print("notices", DB.notices.delete_many({"title": {"$regex": "^TEST_"}}).deleted_count)
    sys.exit()

s = requests.Session()
r = s.post(f"{API}/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345", "active_role": "admin"})
s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
fut = (datetime.now(timezone.utc) + timedelta(days=25)).strftime("%Y-%m-%dT10:00")
h = {"work_title": "TEST_UI Builder Work", "work_description": "TEST_UI description of the work to be done",
     "tender_value": 75000, "product_category": "Construction", "sub_end": fut}
t = s.post(f"{API}/tender-templates", json={"name": "TEST_UI_builder", "header": h}).json()
print("TPL", t["id"])
crit = [{"id": "c1", "title": "TEST_ Min turnover", "category": "financial", "answer_type": "number",
         "operator": "gte", "threshold": 1000, "unit": "USD", "kind": "must_pass"}]
base = {"description": "TEST_ description long enough here", "category": "Construction",
        "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(), "budget_amount": 1000}
ready = s.post(f"{API}/notices", json={**base, "title": "TEST_UI ready", "tender_criteria": crit,
               "primary_document": {"file_name": "t.pdf", "url": "/api/v1/uploads/x/t.pdf", "content_type": "application/pdf"}}).json()
bare = s.post(f"{API}/notices", json={**base, "title": "TEST_UI bare"}).json()
print("READY", ready["notice_ref"], "BARE", bare["notice_ref"])
