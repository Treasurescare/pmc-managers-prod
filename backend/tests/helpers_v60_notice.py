# Helper: create+publish (or delete) a TEST_ notice for v60 UI testing. Usage: python helpers_v60_notice.py create|delete
import sys
from datetime import datetime, timedelta, timezone

import requests
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0]
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
if sys.argv[1] == "delete":
    print(DB.notices.delete_many({"title": {"$regex": "^TEST_UI"}}).deleted_count)
    sys.exit()
s = requests.Session()
r = s.post(f"{BASE}/api/v1/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345", "active_role": "admin"})
s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
dl = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00Z")
r = s.post(f"{BASE}/api/v1/notices", json={"title": "TEST_UI Supply of hospital beds", "description": "TEST UI share bar notice",
           "category": "Medical Equipment", "delivery_country": "GB", "submission_deadline": dl, "budget_amount": 5000})
ref = r.json()["notice_ref"]
print(s.post(f"{BASE}/api/v1/notices/{ref}/publish").status_code, ref)
