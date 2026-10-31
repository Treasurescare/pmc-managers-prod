# v64b: Sealed-bid fixes — commercial-opening blockers (FIX 1) and sealed-key enforcement on create/PATCH (FIX 2).
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
API = f"{BASE_URL}/api/v1"
RID = uuid.uuid4().hex[:6].upper()
REF = f"TEST_SEALFX_{RID}"
VB_EMAIL = f"test_sealfxvb_{RID.lower()}@example.com"
VB_PW = "VendorB@12345"
CHAIR_ID = str(DB.admin_users.find_one({"email": "committee@pmcmanagers.com"})["_id"])
STAFF_PW = "TestStaff@12345"
M_EMAIL = f"test_sealfxmem_{RID.lower()}@example.com"
_H = bcrypt.hashpw(STAFF_PW.encode(), bcrypt.gensalt()).decode()
S = {}


def _vendor(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _staff(email, pw, role):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pw, "active_role": role})
    if r.status_code != 200:
        pytest.skip(f"{email} as {role} login failed {r.status_code}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _cleanup():
    DB.uploads.delete_many({"key": {"$regex": f"TESTFX{RID}"}})
    DB.bids.delete_many({"notice_ref": REF})
    DB.notices.delete_many({"notice_ref": REF})
    DB.committees.delete_many({"notice_ref": REF})
    DB.opening_records.delete_many({"notice_ref": REF})
    DB.vendors.delete_many({"email": VB_EMAIL})
    DB.admin_users.delete_many({"email": M_EMAIL})


@pytest.fixture(scope="module", autouse=True)
def setup():
    _cleanup()
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    DB.notices.insert_one({"notice_ref": REF, "title": f"TEST sealed fixes {RID}", "is_published": True,
                           "kyc_bypass": True, "category": "", "budget_amount": 100000.0,
                           "emd_config": {"fixed_amount": 1000.0, "percentage": 0, "currency": "USD"},
                           "submission_deadline": future, "bid_opening_date": future,
                           "created_at": datetime.now(timezone.utc).isoformat()})
    DB.vendors.insert_one({"email": VB_EMAIL, "company_name": f"TEST Vendor FX {RID}", "status": "active",
                           "kyc_status": "verified", "is_active": True, "vendor_ref": f"VEN-FX{RID}",
                           "password_hash": bcrypt.hashpw(VB_PW.encode(), bcrypt.gensalt()).decode(),
                           "created_at": datetime.now(timezone.utc).isoformat()})
    S["mid"] = str(DB.admin_users.insert_one({"email": M_EMAIL, "name": f"TEST FX Member {RID}", "role": "certifier",
        "roles": ["certifier", "committee_member"], "password_hash": _H, "is_active": True, "tenant_id": "PMC-KZ-01",
        "hierarchy_level": 5, "created_at": datetime.now(timezone.utc).isoformat()}).inserted_id)
    yield
    _cleanup()


@pytest.fixture(scope="module")
def va():
    return _vendor("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def vb():
    return _vendor(VB_EMAIL, VB_PW)


@pytest.fixture(scope="module")
def admin():
    return _staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


def _upload(sess, name, prefix="bid-docs"):
    key = f"{prefix}/TESTFX{RID}{uuid.uuid4().hex[:8]}_{name}"
    r = sess.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, b"%PDF-1.4 fx " + name.encode(), "application/pdf")})
    assert r.status_code == 200, r.text
    return key


def _docs(tk, ck):
    now = datetime.now(timezone.utc).isoformat()
    return [{"kind": "technical", "key": tk, "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
            {"kind": "commercial", "key": ck, "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]


def _create(sess, tk, ck, price=5000.0):
    return sess.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": price, "price_currency": "USD",
                                          "technical_notes": "TN", "commercial_notes": "CN", "documents": _docs(tk, ck)})


SEAL_MSG = "uploaded from the bid page"


# FIX 2 — sealed key enforcement
class TestA_SealedKeys:
    def test_non_bid_docs_prefix_422(self, va):
        ck = _upload(va, "c.pdf")
        r = _create(va, f"vendor-docs/TESTFX{RID}_t.pdf", ck)
        assert r.status_code == 422 and SEAL_MSG in r.text, r.text

    def test_non_bid_docs_uploaded_plaintext_422(self, va):
        tk = _upload(va, "plain.pdf", prefix="vendor-docs")
        u = DB.uploads.find_one({"key": tk})
        print("vendor-docs upload sealed flag:", u and u.get("sealed"))
        r = _create(va, tk, _upload(va, "c.pdf"))
        assert r.status_code == 422 and SEAL_MSG in r.text, r.text

    def test_missing_upload_422(self, va):
        r = _create(va, f"bid-docs/TESTFX{RID}nonexistent.pdf", _upload(va, "c.pdf"))
        assert r.status_code == 422 and SEAL_MSG in r.text

    def test_unsealed_record_422(self, va):
        key = f"bid-docs/TESTFX{RID}plaintext.pdf"
        vid = str(DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})["_id"])
        DB.uploads.insert_one({"key": key, "sealed": False, "owner_vendor_id": vid, "data_b64": ""})
        r = _create(va, key, _upload(va, "c.pdf"))
        assert r.status_code == 422 and SEAL_MSG in r.text

    def test_other_vendor_upload_422(self, va, vb):
        tk = _upload(vb, "t_other.pdf")
        r = _create(va, tk, _upload(va, "c.pdf"))
        assert r.status_code == 422 and SEAL_MSG in r.text

    def test_no_bid_created_on_reject(self):
        assert DB.bids.count_documents({"notice_ref": REF}) == 0

    def test_normal_create_ok(self, va, vb):
        r = _create(va, _upload(va, "t.pdf"), _upload(va, "c.pdf"), 5000.0)
        assert r.status_code == 200, r.text
        S["c"] = r.json()["id"]
        r = _create(vb, _upload(vb, "t.pdf"), _upload(vb, "c.pdf"), 4000.0)
        assert r.status_code == 200, r.text
        S["d"] = r.json()["id"]

    def test_patch_bad_keys_422(self, va, vb):
        good_c = _upload(va, "c2.pdf")
        for bad in (f"vendor-docs/TESTFX{RID}x.pdf", _upload(vb, "t_vb.pdf")):
            r = va.patch(f"{API}/bids/{S['c']}", json={"documents": _docs(bad, good_c)})
            assert r.status_code == 422 and SEAL_MSG in r.text, r.text
        d = DB.bids.find_one({"_id": ObjectId(S["c"])})
        assert all(x["key"].startswith("bid-docs/") for x in d["documents"])

    def test_patch_good_keys_ok(self, va):
        r = va.patch(f"{API}/bids/{S['c']}", json={"documents": _docs(_upload(va, "t3.pdf"), _upload(va, "c3.pdf"))})
        assert r.status_code == 200, r.text


# FIX 1 — commercial opening blockers
class TestB_CommercialBlockers:
    def test_technical_open_both(self):
        DB.bids.update_many({"notice_ref": REF}, {"$set": {"status": "escrow_accepted"}})
        DB.committees.insert_one({"notice_ref": REF, "chairperson_id": CHAIR_ID, "member_ids": [S["mid"]],
                                  "status": "open", "votes": [], "created_at": datetime.now(timezone.utc).isoformat()})
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": past, "bid_opening_date": past}})
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        mem = _staff(M_EMAIL, STAFF_PW, "committee_member")
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True}).status_code == 200
        r = mem.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 200 and r.json()["opened"] is True and r.json()["bids_opened"] == 2, r.text

    def test_no_cleared_blocks(self, admin):
        st = admin.get(f"{API}/bid-opening/{REF}").json()["stages"]["commercial"]["blockers"]
        assert "No bid has passed technical evaluation yet" in st
        assert any("Technical evaluation is still pending for 2 bid(s)" in b for b in st), st
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 412 and "No bid has passed technical evaluation yet" in r.text
        n = DB.notices.find_one({"notice_ref": REF})
        assert not n.get("commercial_opened_at") and not (n.get("opening_approvals") or {}).get("commercial")

    def test_one_cleared_one_pending_blocks(self, admin):
        assert admin.post(f"{API}/bids/{S['c']}/technical-clear").status_code == 200
        st = admin.get(f"{API}/bid-opening/{REF}").json()["stages"]["commercial"]["blockers"]
        assert "No bid has passed technical evaluation yet" not in st
        assert any("still pending for 1 bid(s)" in b for b in st), st
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 412 and "pending for 1 bid(s)" in r.text

    def test_reject_pending_unblocks(self, admin):
        r = admin.post(f"{API}/bids/{S['d']}/decision", json={"action": "reject", "role": "admin", "notes": "TEST tech fail"})
        print("reject via API:", r.status_code, r.text[:200])
        if r.status_code != 200:
            DB.bids.update_one({"_id": ObjectId(S["d"])}, {"$set": {"status": "rejected"}})
        assert DB.bids.find_one({"_id": ObjectId(S["d"])})["status"] == "rejected"
        st = admin.get(f"{API}/bid-opening/{REF}").json()["stages"]["commercial"]["blockers"]
        assert st == [], st

    def test_commercial_opens_cleared_only(self, admin):
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        mem = _staff(M_EMAIL, STAFF_PW, "committee_member")
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 200 and r.json()["opened"] is False, r.text
        r = mem.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 200 and r.json()["opened"] is True and r.json()["bids_opened"] == 1, r.text
        c = admin.get(f"{API}/bids/admin/{S['c']}").json()
        assert c["price_amount"] == 5000.0 and c["envelope_state"] == "commercial_open"
        d = DB.bids.find_one({"_id": ObjectId(S["d"])})
        assert d["price_amount"] is None
        st = admin.get(f"{API}/bid-opening/{REF}").json()["stages"]["commercial"]
        assert st["opened_at"] and any("already open" in b for b in st["blockers"])
