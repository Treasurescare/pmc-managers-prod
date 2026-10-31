# v64c: Signed bid-opening record — e-signature approve, record.pdf (ledger stamp + QR), public verify + tamper detection.
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import fitz  # pymupdf
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
REF = f"TEST_SEALREC_{RID}"
VB_EMAIL = f"test_sealrecvb_{RID.lower()}@example.com"
VB_PW = "VendorB@12345"
CHAIR_ID = str(DB.admin_users.find_one({"email": "committee@pmcmanagers.com"})["_id"])
STAFF_PW = "TestStaff@12345"
M_EMAIL = f"test_sealrecmem_{RID.lower()}@example.com"
_H = bcrypt.hashpw(STAFF_PW.encode(), bcrypt.gensalt()).decode()
CHAIR_SIG = f"TEST Chair Signer {RID}"
MEM_SIG = f"TEST Member Signer {RID}"
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
    DB.uploads.delete_many({"key": {"$regex": f"TESTREC{RID}"}})
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
    DB.notices.insert_one({"notice_ref": REF, "title": f"TEST sealed record {RID}", "is_published": True,
                           "kyc_bypass": True, "category": "", "budget_amount": 100000.0,
                           "emd_config": {"fixed_amount": 1000.0, "percentage": 0, "currency": "USD"},
                           "submission_deadline": future, "bid_opening_date": future,
                           "created_at": datetime.now(timezone.utc).isoformat()})
    DB.vendors.insert_one({"email": VB_EMAIL, "company_name": f"TEST Vendor REC {RID}", "status": "active",
                           "kyc_status": "verified", "is_active": True, "vendor_ref": f"VEN-RC{RID}",
                           "password_hash": bcrypt.hashpw(VB_PW.encode(), bcrypt.gensalt()).decode(),
                           "created_at": datetime.now(timezone.utc).isoformat()})
    S["mid"] = str(DB.admin_users.insert_one({"email": M_EMAIL, "name": f"TEST REC Member {RID}", "role": "certifier",
        "roles": ["certifier", "committee_member"], "password_hash": _H, "is_active": True, "tenant_id": "PMC-KZ-01",
        "hierarchy_level": 5, "created_at": datetime.now(timezone.utc).isoformat()}).inserted_id)
    yield
    _cleanup()


@pytest.fixture(scope="module")
def admin():
    return _staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


@pytest.fixture(scope="module")
def chair():
    return _staff("committee@pmcmanagers.com", "Bid@1234", "committee_member")


@pytest.fixture(scope="module")
def mem():
    return _staff(M_EMAIL, STAFF_PW, "committee_member")


def _upload(sess, name):
    key = f"bid-docs/TESTREC{RID}{uuid.uuid4().hex[:8]}_{name}"
    r = sess.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, b"%PDF-1.4 rec " + name.encode(), "application/pdf")})
    assert r.status_code == 200, r.text
    return key


def _create(sess, price):
    now = datetime.now(timezone.utc).isoformat()
    docs = [{"kind": "technical", "key": _upload(sess, "t.pdf"), "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
            {"kind": "commercial", "key": _upload(sess, "c.pdf"), "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]
    r = sess.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": price, "price_currency": "USD",
                                       "technical_notes": "TN", "commercial_notes": "CN", "documents": docs})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _sig(stage, name, consent=True):
    return {"stage": stage, "signer_name": name, "consent": consent}


def _pdf(sess):
    r = sess.get(f"{API}/bid-opening/{REF}/record.pdf")
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:5] == b"%PDF-"
    doc = fitz.open(stream=r.content, filetype="pdf")
    text = "\n".join(p.get_text() for p in doc)
    return r, doc, text


class TestA_Setup:
    def test_bids_and_committee(self):
        S["c"] = _create(_vendor("testvendor@pmcmanagers.com", "Vendor@12345"), 5000.0)
        S["d"] = _create(_vendor(VB_EMAIL, VB_PW), 4000.0)
        DB.bids.update_many({"notice_ref": REF}, {"$set": {"status": "escrow_accepted"}})
        DB.committees.insert_one({"notice_ref": REF, "chairperson_id": CHAIR_ID, "member_ids": [S["mid"]],
                                  "status": "open", "votes": [], "created_at": datetime.now(timezone.utc).isoformat()})
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": past, "bid_opening_date": past}})

    def test_record_pdf_412_before_opening(self, admin):
        r = admin.get(f"{API}/bid-opening/{REF}/record.pdf")
        assert r.status_code == 412, r.text


class TestB_SignValidation:
    def test_consent_false_422(self, chair):
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json=_sig("technical", CHAIR_SIG, False))
        assert r.status_code == 422 and "Tick the box" in r.text, r.text

    def test_missing_signer_422(self, chair):
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "consent": True})
        assert r.status_code == 422

    def test_short_signer_422(self, chair):
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json=_sig("technical", "ab")).status_code == 422

    def test_long_signer_422(self, chair):
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json=_sig("technical", "x" * 121)).status_code == 422

    def test_missing_consent_422(self, chair):
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", "signer_name": CHAIR_SIG}).status_code == 422

    def test_non_member_403(self, admin):
        assert admin.post(f"{API}/bid-opening/{REF}/approve", json=_sig("technical", "TEST Admin")).status_code == 403

    def test_nothing_stored(self):
        n = DB.notices.find_one({"notice_ref": REF})
        assert not (n.get("opening_approvals") or {}).get("technical")


class TestC_TechnicalSign:
    def test_chair_signs(self, chair):
        r = chair.post(f"{API}/bid-opening/{REF}/approve", json=_sig("technical", "  " + CHAIR_SIG + "  "))
        assert r.status_code == 200 and r.json()["opened"] is False and r.json()["remaining"] == 1, r.text
        a = DB.notices.find_one({"notice_ref": REF})["opening_approvals"]["technical"][0]
        sig = a["signature"]
        assert a["by_id"] == CHAIR_ID and sig["name"] == CHAIR_SIG
        assert sig["ip"] and isinstance(sig["user_agent"], str) and "electronic signature" in sig["statement"]
        S["chair_ip"] = sig["ip"]
        print("stored signer IP:", sig["ip"], "UA:", sig["user_agent"][:60])

    def test_member_signs_opens(self, mem):
        r = mem.post(f"{API}/bid-opening/{REF}/approve", json=_sig("technical", MEM_SIG))
        assert r.status_code == 200 and r.json()["opened"] is True and r.json()["bids_opened"] == 2, r.text


class TestD_RecordPdf:
    def test_pdf_contents(self, admin):
        r, doc, text = _pdf(admin)
        p = doc[0].rect
        assert p.width > p.height, "PDF should be landscape"
        flat = " ".join(text.split())
        for needle in (REF, CHAIR_SIG, MEM_SIG, "committee@pmcmanagers.com", M_EMAIL, "Audit-ledger stamp",
                       "Record fingerprint", "Ledger hash", "Bid opening record", S["chair_ip"]):
            assert needle in flat, f"missing {needle!r}"
        rec = DB.opening_records.find_one({"notice_ref": REF})
        S["code1"], S["sha1"], S["ledger1"] = rec["code"], rec["sha256"], rec["ledger"]
        assert rec["code"] in flat and rec["code"] in r.headers.get("content-disposition", "")
        sha_compact = flat.replace(" ", "")
        assert rec["sha256"] in sha_compact and rec["ledger"]["current_hash"] in sha_compact
        assert "5,000.00" not in flat and "4,000.00" not in flat, "prices must stay hidden before commercial opening"
        assert "Confirmed" in flat
        assert sum(len(pg.get_images()) for pg in doc) >= 1, "QR image missing"
        print("PDF pages:", len(doc), "size:", p)

    def test_reuse_same_code(self, admin):
        r, _, _ = _pdf(admin)
        assert S["code1"] in r.headers.get("content-disposition", "")
        assert DB.opening_records.count_documents({"notice_ref": REF}) == 1
        assert DB.audit_events.count_documents({"event_type": "bid_opening.record_issued", "target_id": REF}) == 1

    def test_ledger_event_matches(self):
        ev = DB.audit_events.find_one({"seq": S["ledger1"]["seq"]})
        assert ev["event_type"] == "bid_opening.record_issued" and ev["payload"]["sha256"] == S["sha1"]
        assert ev["current_hash"] == S["ledger1"]["current_hash"]

    def test_rbac(self, chair, mem):
        assert chair.get(f"{API}/bid-opening/{REF}/record.pdf").status_code == 200
        assert mem.get(f"{API}/bid-opening/{REF}/record.pdf").status_code == 200
        assert requests.get(f"{API}/bid-opening/{REF}/record.pdf").status_code in (401, 403)
        v = _vendor("testvendor@pmcmanagers.com", "Vendor@12345")
        assert v.get(f"{API}/bid-opening/{REF}/record.pdf").status_code in (401, 403)
        assert DB.opening_records.count_documents({"notice_ref": REF}) == 1


class TestE_Verify:
    def test_unknown(self):
        r = requests.get(f"{API}/bid-opening/verify/NOTAREALCODE")
        assert r.status_code == 200 and r.json()["valid"] is False

    def test_valid(self):
        r = requests.get(f"{API}/bid-opening/verify/{S['code1'].lower()}")
        d = r.json()
        assert r.status_code == 200 and d["valid"] is True, d
        assert d["notice_ref"] == REF and d["ledger_seq"] == S["ledger1"]["seq"] and d["bids_opened"] == 2
        assert set(d["signed_by"]["technical"]) == {CHAIR_SIG, MEM_SIG} and d["signed_by"]["commercial"] == []

    def test_tamper_audit_hash(self):
        seq = S["ledger1"]["seq"]
        DB.audit_events.update_one({"seq": seq}, {"$set": {"current_hash": "0" * 64}})
        try:
            assert requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()["valid"] is False
        finally:
            DB.audit_events.update_one({"seq": seq}, {"$set": {"current_hash": S["ledger1"]["current_hash"]}})
        assert requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()["valid"] is True

    def test_tamper_record_sha(self):
        DB.opening_records.update_one({"code": S["code1"]}, {"$set": {"sha256": "f" * 64}})
        try:
            assert requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()["valid"] is False
        finally:
            DB.opening_records.update_one({"code": S["code1"]}, {"$set": {"sha256": S["sha1"]}})
        assert requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()["valid"] is True

    def test_tamper_record_body_only(self):
        """Changing the stored record content (signer names) without touching sha256 should invalidate."""
        orig = DB.opening_records.find_one({"code": S["code1"]})["record"]
        DB.opening_records.update_one({"code": S["code1"]}, {"$set": {"record.approvals.technical.0.name": "FORGED NAME"}})
        try:
            d = requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()
            print("body-only tamper ->", d["valid"], d["signed_by"])
            assert d["valid"] is False, "verify does not recompute sha256 over stored record body"
        finally:
            DB.opening_records.update_one({"code": S["code1"]}, {"$set": {"record": orig}})

    def test_tamper_audit_payload_only(self):
        """Changing the ledger event body (without current_hash) should invalidate."""
        seq = S["ledger1"]["seq"]
        DB.audit_events.update_one({"seq": seq}, {"$set": {"actor_email": "forged@example.com"}})
        try:
            d = requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()
            print("ledger payload tamper ->", d["valid"])
            assert d["valid"] is False, "verify does not recompute ledger event hash"
        finally:
            DB.audit_events.update_one({"seq": seq}, {"$set": {"actor_email": "adminsupport@pmcmanagers.com"}})


class TestF_Commercial:
    def test_commercial_new_code(self, admin, chair, mem):
        assert admin.post(f"{API}/bids/{S['c']}/technical-clear").status_code == 200
        r = admin.post(f"{API}/bids/{S['d']}/decision", json={"action": "reject", "role": "admin", "notes": "TEST"})
        if r.status_code != 200:
            DB.bids.update_one({"_id": ObjectId(S["d"])}, {"$set": {"status": "rejected"}})
        assert chair.post(f"{API}/bid-opening/{REF}/approve", json=_sig("commercial", CHAIR_SIG)).status_code == 200
        r = mem.post(f"{API}/bid-opening/{REF}/approve", json=_sig("commercial", MEM_SIG))
        assert r.status_code == 200 and r.json()["opened"] is True and r.json()["bids_opened"] == 1, r.text
        r, _, text = _pdf(admin)
        flat = " ".join(text.split())
        assert S["code1"] not in r.headers.get("content-disposition", "")
        assert "5,000.00" in flat and "4,000.00" not in flat
        assert DB.opening_records.count_documents({"notice_ref": REF}) == 2
        assert DB.audit_events.count_documents({"event_type": "bid_opening.record_issued", "target_id": REF}) == 2
        code2 = DB.opening_records.find_one({"notice_ref": REF}, sort=[("_id", -1)])["code"]
        d = requests.get(f"{API}/bid-opening/verify/{code2}").json()
        assert d["valid"] is True and set(d["signed_by"]["commercial"]) == {CHAIR_SIG, MEM_SIG}
        # the old (technical-only) code still verifies as a historical record
        assert requests.get(f"{API}/bid-opening/verify/{S['code1']}").json()["valid"] is True
