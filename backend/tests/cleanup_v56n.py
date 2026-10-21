import os, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
s = requests.Session(); d = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"}).json()
s.headers.update({"Authorization": "Bearer " + d["token"], "X-CSRF-Token": d["csrf_token"]})
for a in db.reverse_auctions.find({"title": {"$regex": "^TEST_v56n"}, "status": "live"}):
    print("close", a["title"], s.post(f"{API}/reverse-auctions/{a['_id']}/close").status_code)
for c in db.corrigenda.find({"title": "TEST_v56n corr", "is_active": True}):
    print("del corr", s.delete(f"{API}/notices/{c['notice_ref']}/corrigenda/{c['_id']}", params={"reason": "TEST_v56n cleanup of verification data"}).status_code)
db.notices.update_one({"notice_ref": "PMC-NOT-2026-0101"}, {"$set": {"submission_deadline": "2026-11-13T13:36:23.559299+00:00"}})
print(db.rubrics.find_one({"notice_ref": "PMC-NOT-2026-0016"}, {"_id": 0, "minimum_technical": 1, "commercial_weight": 1}),
      db.rubrics.find_one({"notice_ref": "PMC-NOT-2026-0015"}, {"_id": 0, "minimum_technical": 1, "commercial_weight": 1}))
