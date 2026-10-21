import os, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
s = requests.Session(); d = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"}).json()
s.headers.update({"Authorization": "Bearer " + d["token"], "X-CSRF-Token": d["csrf_token"]})
ids = []
for t in ("TEST_v56n UI auction READY", "TEST_v56n UI auction EMPTY"):
    a = s.post(f"{API}/reverse-auctions", json={"notice_ref": "PMC-NOT-2026-0100", "title": t, "starting_price": 20000, "floor_price": 1000, "min_decrement": 100, "duration_minutes": 60}).json()
    ids.append(a["id"])
v = requests.Session(); vd = v.post(f"{API}/vendor/auth/login", json={"email": "manualvendor@pmcmanagers.com", "password": "Vendor@12345"}).json()
if vd.get("token"): v.headers["Authorization"] = "Bearer " + vd["token"]
if vd.get("csrf_token"): v.headers["X-CSRF-Token"] = vd["csrf_token"]
print("register", v.post(f"{API}/reverse-auctions/{ids[0]}/register").status_code)
db.reverse_auction_participants.insert_one({"auction_id": ids[0], "vendor_id": "TEST_seed_vendor", "vendor_email": "TEST_seed@example.com", "alias": "Bidder Z", "company_name": "TEST_seed"})
print("READY", ids[0], "EMPTY", ids[1])
