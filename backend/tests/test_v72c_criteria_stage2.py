# v72c: Criteria gates (vendor submit/review approve/hosting fee), vendor criteria endpoints, AI check, Stage 2 auto-qualification at technical opening.
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

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
VT1, VT2, HOST, E2E = (f"TEST-VTC1-{RID}", f"TEST-VTC2-{RID}", f"TEST-HOST-{RID}", f"TEST-Q2-{RID}")
REFS = (VT1, VT2, HOST, E2E)
DEMO_PW = "Demo@Pmc2026"
S = {}

MUST = {"id": "mpturn01", "title": "Average annual turnover", "category": "financial", "answer_type": "number",
        "operator": "gte", "threshold": 1000000, "unit": "USD", "proof": "Audited accounts", "proof_required": True,
        "kind": "must_pass", "consortium_rule": "lead"}
ISO = {"id": "mpiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass"}
STAFF = {"id": "scstaff1", "title": "Qualified key staff", "answer_type": "number", "operator": "gte", "threshold": 5,
         "unit": "staff", "kind": "scored", "max_points": 10, "scoring": "auto", "full_points_at": 15}
METH = {"id": "scmeth01", "title": "Methodology and work plan", "answer_type": "text", "kind": "scored",
        "max_points": 20, "scoring": "evaluator"}
DESC = ("Supply and installation of water treatment equipment. Bidders must show average annual turnover of at least "
        "USD 1,000,000 over the last 3 years with audited accounts, hold ISO 9001 certification, have at least 5 "
        "qualified key staff and submit a methodology. Bidders must also have completed 3 similar projects.")


def _now(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def _cleanup():
    for ref in REFS:
        DB.bids.delete_many({"notice_ref": ref})
        DB.notices.delete_many({"notice_ref": ref})
        DB.committees.delete_many({"notice_ref": ref})
        DB.opening_records.delete_many({"notice_ref": ref})
    DB.payment_transactions.delete_many({"session_id": {"$regex": f"TEST-HOST-{RID}"}})
    DB.uploads.delete_many({"key": {"$regex": f"TESTQ2{RID}"}})


def _login_staff(email, pw, role):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pw, "active_role": role})
    if r.status_code != 200:
        pytest.skip(f"staff login {email} failed {r.status_code}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _login_vendor(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"vendor login {email} failed {r.status_code}")
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


@pytest.fixture(scope="module", autouse=True)
def setup():
    _cleanup()
    tv = str(DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})["_id"])
    base = {"is_published": False, "kyc_bypass": True, "category": "", "budget_amount": 100000.0, "budget_currency": "USD",
            "description": DESC, "created_at": _now()}
    for ref in (VT1, VT2):
        DB.notices.insert_one({**base, "notice_ref": ref, "title": f"TEST vendor tender {ref}", "origin": "vendor",
                               "prepared_by_vendor_id": tv, "review_status": "draft", "submission_deadline": _now(days=5)})
    DB.notices.insert_one({**base, "notice_ref": HOST, "title": "TEST hosting", "hosting_fee": {"status": "pending"}})
    DB.notices.insert_one({**base, "notice_ref": E2E, "title": f"TEST stage2 {RID}", "is_published": True,
                           "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"},
                           "tender_criteria": [MUST, ISO, STAFF, METH],
                           "submission_deadline": _now(days=3), "bid_opening_date": _now(days=4)})
    c1 = str(DB.admin_users.find_one({"email": "committee1@demo.pmcmanagers.com"})["_id"])
    c2 = str(DB.admin_users.find_one({"email": "committee2@demo.pmcmanagers.com"})["_id"])
    DB.committees.insert_one({"notice_ref": E2E, "chairperson_id": c1, "member_ids": [c2], "status": "open", "quorum": 2,
                              "votes": [], "created_at": _now()})
    yield
    _cleanup()


@pytest.fixture(scope="module")
def admin():
    return _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


@pytest.fixture(scope="module")
def reviewer():
    return _login_staff("reviewerqa@pmcmanagers.com", "Reviewer@12345", "reviewer")


@pytest.fixture(scope="module")
def tv():
    return _login_vendor("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def nf():
    return _login_vendor("northfield@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def bw():
    return _login_vendor("brightwater@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def c1():
    return _login_staff("committee1@demo.pmcmanagers.com", DEMO_PW, "committee_member")


@pytest.fixture(scope="module")
def c2():
    return _login_staff("committee2@demo.pmcmanagers.com", DEMO_PW, "committee_member")


# ---- Gates + vendor criteria endpoints ----
class TestA_VendorGates:
    def test_submit_without_criteria_409(self, tv):
        r = tv.post(f"{API}/vendor-tenders/{VT1}/submit")
        assert r.status_code == 409, r.text
        assert "criteria" in r.text.lower()

    def test_other_vendor_cannot_read_or_save(self, nf):
        assert nf.get(f"{API}/tender-criteria/{VT1}/mine").status_code == 403
        assert nf.put(f"{API}/tender-criteria/{VT1}/mine", json={"criteria": [MUST]}).status_code == 403
        assert nf.post(f"{API}/tender-criteria/{VT1}/mine/ai-suggest").status_code == 403

    def test_unauth_401(self):
        assert requests.get(f"{API}/tender-criteria/{VT1}/mine").status_code in (401, 403)

    def test_scored_only_still_blocks_submit(self, tv):
        r = tv.put(f"{API}/tender-criteria/{VT1}/mine", json={"criteria": [METH]})
        assert r.status_code == 200, r.text
        assert tv.post(f"{API}/vendor-tenders/{VT1}/submit").status_code == 409

    def test_owner_save_and_get(self, tv):
        r = tv.put(f"{API}/tender-criteria/{VT1}/mine", json={"criteria": [MUST, ISO, METH]})
        assert r.status_code == 200, r.text
        g = tv.get(f"{API}/tender-criteria/{VT1}/mine").json()
        assert [c["id"] for c in g["criteria"]] == ["mpturn01", "mpiso001", "scmeth01"]
        assert g["locked"] is False

    def test_owner_ai_suggest(self, tv):
        r = tv.post(f"{API}/tender-criteria/{VT1}/mine/ai-suggest", timeout=120)
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["criteria"], list)
        S["vendor_suggest_n"] = len(r.json()["criteria"])

    def test_submit_ok_then_locked(self, tv):
        r = tv.post(f"{API}/vendor-tenders/{VT1}/submit")
        assert r.status_code == 200, r.text
        r = tv.put(f"{API}/tender-criteria/{VT1}/mine", json={"criteria": [MUST]})
        assert r.status_code == 409

    def test_reviewer_approve_without_criteria_409(self, reviewer):
        DB.notices.update_one({"notice_ref": VT2}, {"$set": {"review_status": "submitted"}})
        r = reviewer.post(f"{API}/vendor-tenders/{VT2}/approve", json={"note": "x"})
        assert r.status_code == 409, r.text
        assert DB.notices.find_one({"notice_ref": VT2})["is_published"] is False

    def test_reviewer_sees_criteria_and_approves(self, reviewer):
        g = reviewer.get(f"{API}/tender-criteria/{VT1}/admin")
        assert g.status_code == 200 and len(g.json()["criteria"]) == 3
        r = reviewer.post(f"{API}/vendor-tenders/{VT1}/approve", json={"note": "ok"})
        assert r.status_code == 200, r.text
        assert DB.notices.find_one({"notice_ref": VT1})["is_published"] is True


# ---- Hosting fee webhook publishes only with must-pass criteria ----
class TestB_HostingFee:
    def _apply(self, sid):
        sys.path.insert(0, "/app/backend")
        from routers.payments_extra import apply_extra_payment

        async def run():
            import db as dbm
            from motor.motor_asyncio import AsyncIOMotorClient
            dbm_client = AsyncIOMotorClient(ENV["MONGO_URL"].strip('"'))
            import routers.payments_extra as pe
            old = pe.db
            pe.db = dbm_client[ENV["DB_NAME"].strip('"')]
            try:
                await apply_extra_payment(sid)
            except Exception as e:  # emails/alerts may fail out of server context
                print("apply err", e)
            finally:
                pe.db = old
        asyncio.run(run())

    def _tx(self, sid):
        DB.payment_transactions.insert_one({"session_id": sid, "payment_status": "paid", "purpose": "hosting_fee",
                                            "notice_ref": HOST, "amount": 10.0, "currency": "usd",
                                            "payer_email": None, "label": "Hosting"})

    def test_paid_without_criteria_not_published(self):
        sid = f"TEST-HOST-{RID}-a"
        self._tx(sid)
        self._apply(sid)
        n = DB.notices.find_one({"notice_ref": HOST})
        assert n["hosting_fee"]["status"] == "paid"
        assert n["is_published"] is False

    def test_paid_with_criteria_published(self):
        DB.notices.update_one({"notice_ref": HOST}, {"$set": {"tender_criteria": [MUST], "hosting_fee.status": "pending"}})
        sid = f"TEST-HOST-{RID}-b"
        self._tx(sid)
        self._apply(sid)
        assert DB.notices.find_one({"notice_ref": HOST})["is_published"] is True


# ---- AI consistency check ----
class TestC_AICheck:
    def test_vendor_forbidden(self, tv):
        assert tv.post(f"{API}/tender-criteria/{VT2}/ai-check").status_code in (401, 403)

    def test_no_criteria_409(self, admin):
        assert admin.post(f"{API}/tender-criteria/{VT2}/ai-check").status_code == 409

    def test_reviewer_runs_check(self, reviewer):
        r = reviewer.post(f"{API}/tender-criteria/{VT1}/ai-check", timeout=180)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["verdict"] in ("match", "issues")
        assert isinstance(d["issues"], list) and isinstance(d["missing_from_criteria"], list)
        S["ai_check"] = d
        g = reviewer.get(f"{API}/tender-criteria/{VT1}/admin").json()
        assert g["ai_check"] and g["ai_check"]["verdict"] == d["verdict"]

    def test_save_clears_check(self, admin):
        DB.notices.update_one({"notice_ref": VT2}, {"$set": {"criteria_ai_check": {"verdict": "match"}}})
        r = admin.put(f"{API}/tender-criteria/{VT2}", json={"criteria": [MUST]})
        assert r.status_code == 200, r.text
        assert r.json()["ai_check"] is None
        assert "criteria_ai_check" not in DB.notices.find_one({"notice_ref": VT2})


# ---- Stage 2 end-to-end ----
def _upload(s, name):
    key = f"bid-docs/TESTQ2{RID}{uuid.uuid4().hex[:8]}_{name}"
    r = s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, b"%PDF-1.4 q2", "application/pdf")})
    assert r.status_code == 200, r.text
    return key


def _bid(s, turnover, staff, price):
    now = _now()
    docs = [{"kind": "technical", "key": _upload(s, "t.pdf"), "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
            {"kind": "commercial", "key": _upload(s, "c.pdf"), "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now},
            {"kind": "technical", "key": _upload(s, "p.pdf"), "filename": "p.pdf", "size_bytes": 10, "uploaded_at": now,
             "criterion_id": "mpturn01"}]
    r = s.post(f"{API}/bids", json={"notice_ref": E2E, "price_amount": price, "price_currency": "USD",
                                     "technical_notes": "T", "commercial_notes": "C", "documents": docs,
                                     "criteria_answers": [{"criterion_id": "mpturn01", "value": turnover},
                                                          {"criterion_id": "mpiso001", "value": True},
                                                          {"criterion_id": "scstaff1", "value": staff},
                                                          {"criterion_id": "scmeth01", "value": "Our plan"}]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


SIG = {"consent": True}


class TestD_Stage2:
    def test_submit_two_bids(self, nf, bw):
        S["good"] = _bid(nf, 2500000, 10, 9000)
        S["bad"] = _bid(bw, 400000, 20, 8000)
        for k in ("good", "bad"):
            assert DB.bids.find_one({"_id": ObjectId(S[k])})["status"] == "escrow_accepted"

    def test_open_technical(self, c1, c2):
        DB.notices.update_one({"notice_ref": E2E}, {"$set": {"submission_deadline": _now(hours=-3), "bid_opening_date": _now(hours=-2)}})
        r = c1.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "technical", "signer_name": "Committee One", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is False, r.text
        r = c2.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "technical", "signer_name": "Committee Two", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is True, r.text
        assert r.json()["bids_opened"] == 2

    def test_qualification_results(self, c1):
        good = DB.bids.find_one({"_id": ObjectId(S["good"])})
        bad = DB.bids.find_one({"_id": ObjectId(S["bad"])})
        assert good["qualification"]["system_status"] == "qualified"
        assert good.get("technical_cleared_at")
        assert bad["qualification"]["system_status"] == "not_qualified"
        assert not bad.get("technical_cleared_at")
        r = c1.get(f"{API}/tender-criteria/{E2E}/qualification")
        assert r.status_code == 200, r.text
        rows = {b["bid_id"]: b for b in r.json()["bids"]}
        g, b = rows[S["good"]], rows[S["bad"]]
        assert g["status"] == "qualified" and b["status"] == "not_qualified"
        res = {x["criterion_id"]: x for x in g["results"]}
        assert res["mpturn01"]["result"] == "pass"
        assert res["scstaff1"]["points"] == 5.0   # 10 staff on 5->15 for 10 pts
        assert res["scmeth01"]["result"] == "pending"
        assert g["auto_points"] == 5.0 and g["max_points"] == 30.0
        bres = {x["criterion_id"]: x for x in b["results"]}
        assert bres["mpturn01"]["result"] == "fail" and "1,000,000" in bres["mpturn01"]["reason"]
        assert bres["scstaff1"]["points"] == 10.0  # capped
        S["bid_ref_good"], S["bid_ref_bad"] = g["bid_ref"], b["bid_ref"]

    def test_non_member_403(self, admin):
        r = admin.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/doubt",
                       json={"criterion_id": "mpturn01", "reason": "Accounts look inconsistent"})
        assert r.status_code == 403, r.text
        r = admin.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/score", json={"criterion_id": "scmeth01", "points": 5})
        assert r.status_code == 403
        r = admin.post(f"{API}/tender-criteria/{E2E}/bids/{S['bad']}/resolve", json={"decision": "uphold", "note": "fine ok"})
        assert r.status_code == 403

    def test_declared_value_formatted(self):
        bad = DB.bids.find_one({"_id": ObjectId(S["bad"])})
        reasons = " ".join(str(r.get("reason") or "") for r in bad["qualification"].get("results") or [])
        assert "Declared 400,000 USD" in reasons, reasons

    def test_doubt_unknown_criterion_422(self, c1):
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/doubt",
                    json={"criterion_id": "nosuchcrit", "reason": "Accounts look inconsistent"})
        assert r.status_code == 422, r.text

    def test_resolve_without_doubt_409(self, c1):
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['bad']}/resolve", json={"decision": "uphold", "note": "fine ok"})
        assert r.status_code == 409

    def test_evaluator_scores(self, c1, c2):
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/score", json={"criterion_id": "scmeth01", "points": 16})
        assert r.status_code == 200 and r.json()["points"] == 16
        r = c2.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/score", json={"criterion_id": "scmeth01", "points": 12})
        assert r.status_code == 200 and r.json()["points"] == 14
        assert c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/score",
                       json={"criterion_id": "scmeth01", "points": 25}).status_code == 422
        assert c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/score",
                       json={"criterion_id": "mpturn01", "points": 1}).status_code == 422
        q = DB.bids.find_one({"_id": ObjectId(S["good"])})["qualification"]
        assert q["auto_points"] == 19.0

    def test_doubt_blocks_commercial(self, c1):
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/doubt",
                    json={"criterion_id": "mpturn01", "reason": "Audited accounts look inconsistent"})
        assert r.status_code == 200 and r.json()["status"] == "doubt_raised", r.text
        assert not DB.bids.find_one({"_id": ObjectId(S["good"])}).get("technical_cleared_at")
        st = c1.get(f"{API}/bid-opening/{E2E}").json()["stages"]["commercial"]["blockers"]
        S["blockers"] = st
        assert any("doubt" in b for b in st), st
        r = c1.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "commercial", "signer_name": "Committee One", **SIG})
        assert r.status_code == 412

    def test_uphold_restores_cleared(self, c2):
        r = c2.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/resolve", json={"decision": "uphold", "note": "Checked originals"})
        assert r.status_code == 200 and r.json()["status"] == "qualified", r.text
        assert DB.bids.find_one({"_id": ObjectId(S["good"])}).get("technical_cleared_at")

    def test_disqualify_bad_via_doubt(self, c1):
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['bad']}/doubt",
                    json={"criterion_id": "mpiso001", "reason": "ISO certificate appears expired"})
        assert r.status_code == 200
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['bad']}/resolve", json={"decision": "disqualify", "note": "Expired cert"})
        assert r.status_code == 200 and r.json()["status"] == "disqualified"
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['bad']}/doubt",
                    json={"criterion_id": "mpiso001", "reason": "Another doubt here"})
        assert r.status_code == 409

    def test_commercial_opens_only_qualified(self, c1, c2):
        st = c1.get(f"{API}/bid-opening/{E2E}").json()["stages"]["commercial"]["blockers"]
        assert st == [], st
        c1.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "commercial", "signer_name": "Committee One", **SIG})
        r = c2.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "commercial", "signer_name": "Committee Two", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is True, r.text
        assert r.json()["bids_opened"] == 1
        assert DB.bids.find_one({"_id": ObjectId(S["good"])}).get("commercial_unsealed_at")
        assert not DB.bids.find_one({"_id": ObjectId(S["bad"])}).get("commercial_unsealed_at")

    def test_after_commercial_409(self, c1):
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/doubt",
                    json={"criterion_id": "mpturn01", "reason": "Late doubt after opening"})
        assert r.status_code == 409
        r = c1.post(f"{API}/tender-criteria/{E2E}/bids/{S['good']}/score", json={"criterion_id": "scmeth01", "points": 3})
        assert r.status_code == 409

    def test_record_pdf_has_qualification(self, c1):
        r = c1.get(f"{API}/bid-opening/{E2E}/record.pdf", timeout=60)
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
        rec = DB.opening_records.find_one({"notice_ref": E2E}, sort=[("issued_at", -1)])
        quals = {b["bid_ref"]: b["qualification"] for b in rec["record"]["bids"]}
        S["quals"] = quals
        assert quals[S["bid_ref_good"]].startswith("Qualified")
        assert "Disqualified by committee" in quals[S["bid_ref_bad"]]
        assert "Average annual turnover" in quals[S["bid_ref_bad"]]
        try:
            from pypdf import PdfReader
            import io
            txt = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
            assert "qualification" in txt.lower()
        except ImportError:
            pass
