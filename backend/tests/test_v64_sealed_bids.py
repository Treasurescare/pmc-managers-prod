# v64: Sealed-bid envelopes — encryption at rest, staff redaction, sealed files, gates, committee opening.
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
REF = f"TEST_SEAL_{RID}"
VB_EMAIL = f"test_sealvb_{RID.lower()}@example.com"
VB_PW = "VendorB@12345"
CHAIR_ID = str(DB.admin_users.find_one({"email": "committee@pmcmanagers.com"})["_id"])
STAFF_PW = "TestStaff@12345"
M_EMAIL, ACC_EMAIL = f"test_sealmem_{RID.lower()}@example.com", f"test_sealacc_{RID.lower()}@example.com"
_H = bcrypt.hashpw(STAFF_PW.encode(), bcrypt.gensalt()).decode()
DB.admin_users.delete_many({"email": {"$in": [M_EMAIL, ACC_EMAIL]}})
MEMBER_ID = str(DB.admin_users.insert_one({"email": M_EMAIL, "name": f"TEST Member {RID}", "role": "certifier",
    "roles": ["certifier", "committee_member"], "password_hash": _H, "is_active": True, "tenant_id": "PMC-KZ-01",
    "hierarchy_level": 5, "created_at": datetime.now(timezone.utc).isoformat()}).inserted_id)
DB.admin_users.insert_one({"email": ACC_EMAIL, "name": f"TEST Accounts {RID}", "role": "accounting", "roles": ["accounting"],
    "password_hash": _H, "is_active": True, "tenant_id": "PMC-KZ-01", "hierarchy_level": 5,
    "created_at": datetime.now(timezone.utc).isoformat()})
S = {}  # shared state across ordered tests
TECH_BYTES = b"%PDF-1.4 TEST technical envelope " + RID.encode()
COMM_BYTES = b"%PDF-1.4 TEST commercial envelope " + RID.encode()


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
        pytest.skip(f"{email} as {role} login failed {r.status_code} {r.text[:120]}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _cleanup():
    keys = [u["key"] for u in DB.uploads.find({"key": {"$regex": f"^bid-docs/TEST{RID}"}}, {"key": 1})]
    DB.uploads.delete_many({"key": {"$in": keys}})
    DB.bids.delete_many({"notice_ref": REF})
    DB.notices.delete_many({"notice_ref": REF})
    DB.committees.delete_many({"notice_ref": REF})
    DB.opening_records.delete_many({"notice_ref": REF})
    DB.vendors.delete_many({"email": VB_EMAIL})


@pytest.fixture(scope="module", autouse=True)
def setup():
    _cleanup()
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    DB.notices.insert_one({"notice_ref": REF, "title": f"TEST sealed {RID}", "is_published": True,
                           "kyc_bypass": True, "category": "", "budget_amount": 100000.0,
                           "emd_config": {"fixed_amount": 1000.0, "percentage": 0, "currency": "USD"},
                           "submission_deadline": future, "bid_opening_date": future,
                           "created_at": datetime.now(timezone.utc).isoformat()})
    DB.vendors.insert_one({"email": VB_EMAIL, "company_name": f"TEST Vendor B {RID}", "status": "active",
                           "kyc_status": "verified", "is_active": True, "vendor_ref": f"VEN-T{RID}",
                           "password_hash": bcrypt.hashpw(VB_PW.encode(), bcrypt.gensalt()).decode(),
                           "created_at": datetime.now(timezone.utc).isoformat()})
    yield
    _cleanup()
    DB.admin_users.delete_many({"email": {"$in": [M_EMAIL, ACC_EMAIL]}})


@pytest.fixture(scope="module")
def va():
    return _vendor("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def vb():
    return _vendor(VB_EMAIL, VB_PW)


@pytest.fixture(scope="module")
def admin():
    return _staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


def _upload(sess, name, body):
    key = f"bid-docs/TEST{RID}{uuid.uuid4().hex[:8]}_{name}"
    r = sess.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, body, "application/pdf")})
    assert r.status_code == 200, r.text
    return key


def _submit(sess, price, tag):
    tk, ck = _upload(sess, f"tech_{tag}.pdf", TECH_BYTES + tag.encode()), _upload(sess, f"comm_{tag}.pdf", COMM_BYTES + tag.encode())
    now = datetime.now(timezone.utc).isoformat()
    r = sess.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": price, "price_currency": "USD",
                                       "technical_notes": f"TECH NOTE {tag}", "commercial_notes": f"COMM NOTE {tag}",
                                       "documents": [{"kind": "technical", "key": tk, "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
                                                     {"kind": "commercial", "key": ck, "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]})
    assert r.status_code == 200, r.text
    return r.json(), tk, ck


# ---- uploads: sealing at rest ----
class TestA_Uploads:
    def test_anon_bid_docs_upload_401(self):
        r = requests.post(f"{API}/uploads/direct", data={"key": f"bid-docs/TEST{RID}anon_x.pdf"},
                          files={"file": ("x.pdf", b"abc", "application/pdf")})
        assert r.status_code == 401

    def test_upload_sealed_in_mongo(self, va):
        key = _upload(va, "probe.pdf", TECH_BYTES)
        u = DB.uploads.find_one({"key": key})
        assert u["sealed"] is True and u["owner_vendor_id"]
        import base64
        assert TECH_BYTES not in base64.b64decode(u["data_b64"])
        r = va.get(f"{API}/uploads/files/{key}")
        assert r.status_code == 200 and r.content == TECH_BYTES


# ---- bid creation + storage ----
class TestB_Create:
    def test_create_bids(self, va, vb):
        a, tka, cka = _submit(va, 12345.5, "A")
        b, tkb, ckb = _submit(vb, 9999.0, "B")
        S.update(a=a["id"], b=b["id"], tka=tka, cka=cka, tkb=tkb, ckb=ckb)
        assert a["price_amount"] == 12345.5 and a["technical_notes"] == "TECH NOTE A" and a["commercial_notes"] == "COMM NOTE A"
        assert "sealed" not in a
        assert a["status"] == "emd_pending"

    def test_mongo_encrypted(self):
        d = DB.bids.find_one({"_id": ObjectId(S["a"])})
        assert d["seal_v"] == 1
        assert d["price_amount"] is None and d["technical_notes"] is None and d["commercial_notes"] is None
        assert set(d["sealed"]) == {"price_amount", "technical_notes", "commercial_notes"}
        assert "12345" not in str(d["sealed"]) and "TECH NOTE" not in str(d["sealed"])

    def test_vendor_views_plaintext(self, va):
        r = va.get(f"{API}/bids/{S['a']}")
        assert r.status_code == 200
        d = r.json()
        assert d["price_amount"] == 12345.5 and d["commercial_notes"] == "COMM NOTE A" and "sealed" not in d
        mine = [x for x in va.get(f"{API}/bids/mine").json() if x["id"] == S["a"]]
        assert mine and mine[0]["price_amount"] == 12345.5 and mine[0]["technical_notes"] == "TECH NOTE A"

    def test_vendor_patch_keeps_sealed(self, va):
        r = va.patch(f"{API}/bids/{S['a']}", json={"technical_notes": "TECH NOTE A v2"})
        assert r.status_code == 200, r.text
        assert r.json()["technical_notes"] == "TECH NOTE A v2"
        d = DB.bids.find_one({"_id": ObjectId(S["a"])})
        assert d["technical_notes"] is None and "v2" not in str(d["sealed"])


# ---- staff redaction ----
class TestC_Redaction:
    @pytest.mark.parametrize("email,pw,role", [
        ("adminsupport@pmcmanagers.com", "Admin@12345", "admin"),
        ("reviewerqa@pmcmanagers.com", "Reviewer@12345", "reviewer"),
        (ACC_EMAIL, STAFF_PW, "accounting"),
        ("committee@pmcmanagers.com", "Bid@1234", "committee_member"),
    ])
    def test_staff_sees_sealed(self, email, pw, role):
        s = _staff(email, pw, role)
        r = s.get(f"{API}/bids/admin/{S['a']}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["documents"] == [] and d["price_amount"] is None and d["technical_notes"] is None and d["commercial_notes"] is None
        assert d["envelope_state"] == "sealed" and d["sealed_documents_count"] == 2 and "sealed" not in d
        assert d["company_name"] and d["vendor_email"] and d["submitted_at"] and d["status"] == "emd_pending"
        assert "emd_due_amount" in d
        rows = s.get(f"{API}/bids", params={"notice_ref": REF}).json()
        for row in rows:
            assert row["price_amount"] is None and row["documents"] == [] and row["envelope_state"] == "sealed"

    def test_audit_bid_viewed(self, admin):
        admin.get(f"{API}/bids/admin/{S['a']}")
        bid_ref = DB.bids.find_one({"_id": ObjectId(S["a"])})["bid_ref"]
        assert DB.audit_events.find_one({"event_type": "bid.viewed", "target_id": bid_ref})


# ---- sealed file access ----
class TestD_Files:
    def test_owner_200_other_vendor_403_admin_403(self, va, vb, admin):
        r = va.get(f"{API}/uploads/files/{S['tka']}")
        assert r.status_code == 200 and r.content.startswith(TECH_BYTES)
        assert vb.get(f"{API}/uploads/files/{S['tka']}").status_code == 403
        assert admin.get(f"{API}/uploads/files/{S['tka']}").status_code == 403
        assert admin.get(f"{API}/uploads/files/{S['cka']}").status_code == 403
        assert requests.get(f"{API}/uploads/files/{S['tka']}").status_code == 401
        assert requests.get(f"{API}/uploads/public-files/{S['tka']}").status_code == 403

    def test_bundle_skips_sealed(self, va, admin):
        r = admin.post(f"{API}/uploads/bundle", json={"keys": [S["tka"], S["cka"]]})
        assert r.status_code == 404
        r = va.post(f"{API}/uploads/bundle", json={"keys": [S["tka"], S["cka"]]})
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/zip")


# ---- workflow gates while sealed ----
class TestE_Gates:
    def test_technical_clear_412(self, admin):
        assert admin.post(f"{API}/bids/{S['a']}/technical-clear").status_code == 412

    def test_financial_open_412(self, admin):
        DB.bids.update_one({"_id": ObjectId(S["a"])}, {"$set": {"technical_cleared_at": "x"}})
        try:
            r = admin.post(f"{API}/bids/{S['a']}/financial-open")
            assert r.status_code == 412 and "committee" in r.text
        finally:
            DB.bids.update_one({"_id": ObjectId(S["a"])}, {"$unset": {"technical_cleared_at": ""}})

    def test_decision_admin_flag_412(self, admin):
        r = admin.post(f"{API}/bids/{S['a']}/decision", json={"action": "flag", "role": "admin"})
        assert r.status_code == 412, r.text

    def test_decision_certifier_412(self):
        s = _staff(M_EMAIL, STAFF_PW, "certifier")
        assert s.post(f"{API}/bids/{S['a']}/decision", json={"action": "accept", "role": "certifier"}).status_code == 412

    def test_decision_accounting_412(self):
        s = _staff(ACC_EMAIL, STAFF_PW, "accounting")
        assert s.post(f"{API}/bids/{S['a']}/decision", json={"action": "accept", "role": "accounting"}).status_code == 412

    def test_escrow_accept_pre_opening(self):
        DB.bids.update_one({"_id": ObjectId(S["b"])}, {"$set": {"status": "emd_paid"}})
        s = _staff("escrow@pmcmanagers.com", "Escrow@123", "escrow_agent")
        r = s.post(f"{API}/bids/{S['b']}/decision", json={"action": "accept", "role": "escrow_agent"})
        assert r.status_code == 200, r.text
        assert DB.bids.find_one({"_id": ObjectId(S["b"])})["status"] == "escrow_accepted"


# ---- committee opening ----
class TestF_Opening:
    def test_no_committee_state(self, admin):
        r = admin.get(f"{API}/bid-opening/{REF}")
        assert r.status_code == 200
        d = r.json()
        assert d["committee"] == [] and any("committee" in b for b in d["stages"]["technical"]["blockers"])

    def test_state_with_committee_and_pre_deadline_412(self):
        DB.committees.insert_one({"notice_ref": REF, "chairperson_id": CHAIR_ID, "member_ids": [MEMBER_ID],
                                  "status": "open", "votes": [], "created_at": datetime.now(timezone.utc).isoformat()})
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        d = chair.get(f"{API}/bid-opening/{REF}").json()
        assert {m["id"] for m in d["committee"]} == {CHAIR_ID, MEMBER_ID}
        assert d["bids_total"] == 2 and d["bids_emd_confirmed"] == 1 and d["opening_at"]
        t = d["stages"]["technical"]
        assert t["i_can_approve"] is True and len(t["pending"]) == 2
        assert any("still open" in b for b in t["blockers"])
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 412

    def test_non_member_403(self, admin):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": past, "bid_opening_date": past}})
        assert admin.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True}).status_code == 403
        assert admin.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "bogus", "signer_name": "TEST Signer", "consent": True}).status_code == 422

    def test_opening_date_future_412(self):
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"bid_opening_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}})
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 412 and "opening date" in r.text
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"bid_opening_date": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}})

    def test_commercial_before_technical_412(self):
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True}).status_code == 412

    def test_technical_partial_then_double_409(self, admin):
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 200, r.text
        assert r.json()["opened"] is False and r.json()["remaining"] == 1
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True}).status_code == 409
        d = admin.get(f"{API}/bids/admin/{S['b']}").json()
        assert d["envelope_state"] == "sealed"

    def test_technical_all_approve_opens_only_emd_confirmed(self, admin):
        mem = _staff(M_EMAIL, STAFF_PW, "committee_member")
        r = mem.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 200, r.text
        assert r.json()["opened"] is True and r.json()["bids_opened"] == 1
        n = DB.notices.find_one({"notice_ref": REF})
        assert n.get("technical_opened_at")
        db_b = DB.bids.find_one({"_id": ObjectId(S["b"])})
        assert db_b["technical_notes"] == "TECH NOTE B" and db_b["technical_unsealed_at"] and db_b["price_amount"] is None
        db_a = DB.bids.find_one({"_id": ObjectId(S["a"])})
        assert db_a["technical_notes"] is None and not db_a.get("technical_unsealed_at")
        b = admin.get(f"{API}/bids/admin/{S['b']}").json()
        assert b["envelope_state"] == "technical_open" and b["technical_notes"] == "TECH NOTE B"
        assert [d["kind"] for d in b["documents"]] == ["technical"] and b["price_amount"] is None
        a = admin.get(f"{API}/bids/admin/{S['a']}").json()
        assert a["envelope_state"] == "sealed" and a["documents"] == []
        assert DB.audit_events.find_one({"event_type": "bid_opening.technical_opened", "target_id": REF})

    def test_files_after_technical_open(self, admin):
        r = admin.get(f"{API}/uploads/files/{S['tkb']}")
        assert r.status_code == 200 and r.content.startswith(TECH_BYTES)
        assert admin.get(f"{API}/uploads/files/{S['ckb']}").status_code == 403
        assert admin.get(f"{API}/uploads/files/{S['tka']}").status_code == 403

    def test_post_technical_gates(self, admin):
        r = admin.post(f"{API}/bids/{S['b']}/technical-clear")
        assert r.status_code == 200, r.text
        assert admin.post(f"{API}/bids/{S['b']}/financial-open").status_code == 412
        acc = _staff(ACC_EMAIL, STAFF_PW, "accounting")
        assert acc.post(f"{API}/bids/{S['b']}/decision", json={"action": "accept", "role": "accounting"}).status_code == 412
        r = admin.post(f"{API}/bids/{S['b']}/decision", json={"action": "flag", "role": "admin"})
        assert r.status_code != 412, r.text

    def test_commercial_opening(self, admin):
        chair = _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        mem = _staff(M_EMAIL, STAFF_PW, "committee_member")
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True}).json()["opened"] is False
        r = mem.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", "signer_name": "TEST Signer", "consent": True})
        assert r.status_code == 200 and r.json()["opened"] is True and r.json()["bids_opened"] == 1
        db_b = DB.bids.find_one({"_id": ObjectId(S["b"])})
        assert db_b["price_amount"] == 9999.0 and db_b["commercial_notes"] == "COMM NOTE B" and db_b["financial_opened_at"]
        assert DB.notices.find_one({"notice_ref": REF}).get("commercial_opened_at")
        b = admin.get(f"{API}/bids/admin/{S['b']}").json()
        assert b["envelope_state"] == "commercial_open" and b["price_amount"] == 9999.0 and len(b["documents"]) == 2
        assert admin.get(f"{API}/uploads/files/{S['ckb']}").status_code == 200
        a = admin.get(f"{API}/bids/admin/{S['a']}").json()
        assert a["price_amount"] is None and a["envelope_state"] == "sealed"
        st = admin.get(f"{API}/bid-opening/{REF}").json()
        assert st["stages"]["commercial"]["opened_at"] and st["stages"]["technical"]["opened_at"]
