# Helper for UI testing of sealed bid opening: `setup` creates TEST_SEALUI notice/committee/bids, `techopen` opens technical, `cleanup` removes.
import sys, json, uuid
from datetime import datetime, timedelta, timezone
import bcrypt, requests
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
API = f"{BASE}/api/v1"
E = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l)
D = MongoClient(E["MONGO_URL"].strip('"'))[E["DB_NAME"].strip('"')]
REF = "TEST_SEALUI_1"
M_EMAIL, PW = "test_sealui_mem@example.com", "TestStaff@12345"
VB = "test_sealui_vb@example.com"


def cleanup():
    D.uploads.delete_many({"key": {"$regex": "TESTUI"}})
    D.bids.delete_many({"notice_ref": REF}); D.notices.delete_many({"notice_ref": REF})
    D.committees.delete_many({"notice_ref": REF}); D.vendors.delete_many({"email": VB})
    D.admin_users.delete_many({"email": M_EMAIL})


def vend(email, pw):
    s = requests.Session(); r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw}); assert r.status_code == 200, r.text
    if r.json().get("csrf_token"): s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def staff(email, pw, role):
    s = requests.Session(); r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pw, "active_role": role}); assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]; return s


def bid(s, price):
    keys = []
    for k in ("t", "c"):
        key = f"bid-docs/TESTUI{uuid.uuid4().hex[:8]}_{k}.pdf"
        assert s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (f"{k}.pdf", b"%PDF-1.4 ui", "application/pdf")}).status_code == 200
        keys.append(key)
    now = datetime.now(timezone.utc).isoformat()
    r = s.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": price, "price_currency": "USD", "technical_notes": "UI TECH", "commercial_notes": "UI COMM",
        "documents": [{"kind": "technical", "key": keys[0], "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
                      {"kind": "commercial", "key": keys[1], "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def setup():
    cleanup()
    fut = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    D.notices.insert_one({"notice_ref": REF, "title": "TEST sealed UI tender", "is_published": True, "kyc_bypass": True, "category": "",
        "budget_amount": 100000.0, "emd_config": {"fixed_amount": 1000.0, "percentage": 0, "currency": "USD"},
        "submission_deadline": fut, "bid_opening_date": fut, "created_at": datetime.now(timezone.utc).isoformat()})
    D.vendors.insert_one({"email": VB, "company_name": "TEST UI Vendor B", "status": "active", "kyc_status": "verified", "is_active": True,
        "vendor_ref": "VEN-TUI1", "password_hash": bcrypt.hashpw(PW.encode(), bcrypt.gensalt()).decode(), "created_at": fut})
    mid = str(D.admin_users.insert_one({"email": M_EMAIL, "name": "TEST UI Member", "role": "certifier", "roles": ["certifier", "committee_member"],
        "password_hash": bcrypt.hashpw(PW.encode(), bcrypt.gensalt()).decode(), "is_active": True, "tenant_id": "PMC-KZ-01",
        "hierarchy_level": 5, "created_at": fut}).inserted_id)
    a = bid(vend("testvendor@pmcmanagers.com", "Vendor@12345"), 7777.0); b = bid(vend(VB, PW), 6666.0)
    D.bids.update_many({"notice_ref": REF}, {"$set": {"status": "escrow_accepted"}})
    chair = str(D.admin_users.find_one({"email": "committee@pmcmanagers.com"})["_id"])
    D.committees.insert_one({"notice_ref": REF, "chairperson_id": chair, "member_ids": [mid], "status": "open", "quorum": 2, "votes": [],
                             "created_at": datetime.now(timezone.utc).isoformat()})
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    D.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": past, "bid_opening_date": past}})
    print(json.dumps({"a": a, "b": b}))


def techopen():
    staff("committee@pmcmanagers.com", "Bid@1234", "committee_member").post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical"})
    r = staff(M_EMAIL, PW, "committee_member").post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical"})
    print(r.status_code, r.text)


{"setup": setup, "techopen": techopen, "cleanup": cleanup}[sys.argv[1]]()
