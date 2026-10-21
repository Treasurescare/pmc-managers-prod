# Register 2 participants on the iter104 UI-created auction (manualvendor via API + 1 seeded DB row)
import os, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
aid = open("/tmp/auction_id").read().strip()
v = requests.Session(); vd = v.post(f"{API}/vendor/auth/login", json={"email": "manualvendor@pmcmanagers.com", "password": "Vendor@12345"}).json()
if vd.get("token"): v.headers["Authorization"] = "Bearer " + vd["token"]
if vd.get("csrf_token"): v.headers["X-CSRF-Token"] = vd["csrf_token"]
r = v.post(f"{API}/reverse-auctions/{aid}/register"); print("register", r.status_code, r.text[:200])
db.reverse_auction_participants.insert_one({"auction_id": aid, "vendor_id": "TEST_iter104_vendor", "vendor_email": "TEST_iter104@example.com", "alias": "Bidder Y", "company_name": "TEST_iter104"})
print("participants", db.reverse_auction_participants.count_documents({"auction_id": aid}))
