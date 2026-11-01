# v76: AI proof reading at technical opening + unanimous committee proof votes + award method (L1 / weighted)
# Seeds TEST_PROOF-* notice, committee (demo committee1+2), 3 sealed bids; cleans everything at module teardown.
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import fitz
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL") or [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0]
API = BASE.rstrip("/") + "/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
REF = os.environ.get("PROOF_TEST_REF") or f"TEST_PROOF-{uuid.uuid4().hex[:6].upper()}"
KEEP = os.environ.get("PROOF_TEST_KEEP") == "1"
PW = "Demo@Pmc2026"
C1, C2 = "committee1@demo.pmcmanagers.com", "committee2@demo.pmcmanagers.com"
VA, VB, VC = "testvendor@pmcmanagers.com", "northfield@demo.pmcmanagers.com", "brightwater@demo.pmcmanagers.com"
S = {}


def now(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def staff(email, pw, role):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pw, "active_role": role})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def vendor(email):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": PW if "demo" in email else "Vendor@12345"})
    assert r.status_code == 200, r.text
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def pdf(text):
    d = fitz.open()
    p = d.new_page()
    p.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=12)
    return d.tobytes()


def upload(s, name, body, mime):
    key = f"bid-docs/TESTPROOF{uuid.uuid4().hex[:8]}_{name}"
    r = s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, body, mime)})
    assert r.status_code < 300, r.text
    return key


def cleanup():
    for c in ("bids", "notices", "committees", "opening_records"):
        DB[c].delete_many({"notice_ref": REF})
    DB.notifications.delete_many({"related_notice_ref": REF})
    DB.uploads.delete_many({"key": {"$regex": "TESTPROOF"}})


CRIT = [
    {"id": "tpturn01", "title": "Average annual turnover", "answer_type": "number", "operator": "gte", "threshold": 500000, "unit": "GBP",
     "kind": "must_pass", "consortium_rule": "lead", "proof": "Audited accounts", "proof_required": True},
    {"id": "tpiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "lead",
     "proof": "ISO certificate", "proof_required": False},
]


@pytest.fixture(scope="module", autouse=True)
def seeded():
    cleanup()
    DB.notices.insert_one({"notice_ref": REF, "title": "TEST proof review tender", "is_published": True, "kyc_bypass": True, "category": "",
                           "budget_amount": 2000000.0, "budget_currency": "GBP", "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "GBP"},
                           "created_at": now(), "published_at": now(), "submission_deadline": now(days=5), "bid_opening_date": now(days=6),
                           "description": "TEST", "tenant_id": "PMC-KZ-01"})
    c1 = str(DB.admin_users.find_one({"email": C1})["_id"])
    c2 = str(DB.admin_users.find_one({"email": C2})["_id"])
    DB.committees.insert_one({"notice_ref": REF, "chairperson_id": c1, "member_ids": [c2], "status": "open", "quorum": 2, "votes": [], "created_at": now()})
    S.update(admin=staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin"), c1=staff(C1, PW, "committee_member"),
             c2=staff(C2, PW, "committee_member"), c1id=c1, c2id=c2)
    yield
    if not KEEP:
        cleanup()


def _docs(s, proof_name, proof_body, proof_mime, iso=None):
    d = [{"kind": "technical", "key": upload(s, "technical.pdf", b"%PDF-1.4 t", "application/pdf"), "filename": "technical.pdf", "size_bytes": 10, "uploaded_at": now()},
         {"kind": "commercial", "key": upload(s, "price.pdf", b"%PDF-1.4 p", "application/pdf"), "filename": "price.pdf", "size_bytes": 10, "uploaded_at": now()},
         {"kind": "technical", "key": upload(s, proof_name, proof_body, proof_mime), "filename": proof_name, "size_bytes": len(proof_body),
          "uploaded_at": now(), "criterion_id": "tpturn01"}]
    if iso:
        d.append({"kind": "technical", "key": upload(s, iso, b"PK\x03\x04 fake docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                  "filename": iso, "size_bytes": 20, "uploaded_at": now(), "criterion_id": "tpiso001"})
    return d


class TestProofReview:
    def test_01_award_method_put_and_admin_get(self):
        r = S["admin"].put(f"{API}/tender-criteria/{REF}", json={"criteria": CRIT, "award_method": "weighted"})
        assert r.status_code == 200, r.text
        assert r.json()["award_method"] == "weighted"
        g = S["admin"].get(f"{API}/tender-criteria/{REF}/admin").json()
        assert g["award_method"] == "weighted"
        r = S["admin"].put(f"{API}/tender-criteria/{REF}", json={"criteria": CRIT, "award_method": "l1"})
        assert r.status_code == 200 and r.json()["award_method"] == "l1"
        assert S["admin"].put(f"{API}/tender-criteria/{REF}", json={"criteria": CRIT, "award_method": "bogus"}).status_code == 422

    def test_02_submit_bids_and_open_technical(self):
        a, b, c = vendor(VA), vendor(VB), vendor(VC)
        acc = pdf("ACME Supplies Ltd\nAudited financial statements for the year ended 31 March 2025\nTotal annual turnover: GBP 400,000\nAuditor: Smith & Co")
        good = pdf("Northfield Ltd\nAudited financial statements for the year ended 31 March 2025\nTotal annual turnover: GBP 800,000\nAuditor: Jones LLP")
        for s, price, turn, docs, key in ((a, 900000, 750000, _docs(a, "accounts-a.pdf", acc, "application/pdf", iso="iso-cert.docx"), "A"),
                                          (b, 1000000, 800000, _docs(b, "accounts-b.pdf", good, "application/pdf"), "B"),
                                          (c, 500000, 100000, _docs(c, "accounts-c.pdf", good, "application/pdf"), "C")):
            r = s.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": price, "price_currency": "GBP", "technical_notes": "T", "commercial_notes": "C",
                                            "documents": docs, "criteria_answers": [{"criterion_id": "tpturn01", "value": turn}, {"criterion_id": "tpiso001", "value": True}]})
            assert r.status_code < 300, r.text
            S[key] = r.json()["id"]
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": now(hours=-3), "bid_opening_date": now(hours=-2)}})
        sig = {"signer_name": "Committee", "consent": True, "typed_signature": "Committee"}
        r1 = S["c1"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", **sig})
        assert r1.status_code == 200, r1.text
        r2 = S["c2"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", **sig})
        assert r2.status_code == 200 and r2.json()["opened"] is True, r2.text

    def test_03_qualification_shape(self):
        d = S["c1"].get(f"{API}/tender-criteria/{REF}/qualification").json()
        assert d["committee_size"] == 2 and d["i_am_member"] is True and d["me"] == S["c1id"] and d["award_method"] == "l1"
        bids = {x["bid_id"]: x for x in d["bids"]}
        a, b, c = bids[S["A"]], bids[S["B"]], bids[S["C"]]
        assert a["system_status"] == "qualified" and b["system_status"] == "qualified" and c["system_status"] != "qualified"
        assert set(a["proof_reviews"]) == {"tpturn01", "tpiso001"}
        assert set(b["proof_reviews"]) == {"tpturn01"}
        assert not c.get("proof_reviews")
        assert a["proof_files"]["tpturn01"][0]["filename"] == "accounts-a.pdf"
        assert a["proof_reviews"]["tpturn01"]["status"] == "pending" and a["proof_reviews"]["tpturn01"]["votes"] == {}
        ad = S["admin"].get(f"{API}/tender-criteria/{REF}/qualification").json()
        assert ad["i_am_member"] is False

    def test_04_commercial_blocked_by_pending_proofs(self):
        st = S["c1"].get(f"{API}/bid-opening/{REF}").json()
        bl = st["stages"]["commercial"]["blockers"]
        assert any("Proof review is still pending on 2 qualified bid" in x for x in bl), bl
        sig = {"signer_name": "Committee", "consent": True, "typed_signature": "Committee"}
        r = S["c1"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", **sig})
        assert r.status_code == 412

    def test_05_ai_readings(self):
        deadline = time.time() + 180
        while time.time() < deadline:
            d = S["c1"].get(f"{API}/tender-criteria/{REF}/qualification").json()
            bids = {x["bid_id"]: x for x in d["bids"]}
            prs = [bids[S["A"]]["proof_reviews"]["tpturn01"], bids[S["A"]]["proof_reviews"]["tpiso001"], bids[S["B"]]["proof_reviews"]["tpturn01"]]
            if all(p["ai_status"] not in ("pending", "running") for p in prs):
                break
            time.sleep(6)
        print("AI results:", prs)
        a_turn, a_iso, b_turn = prs
        assert a_iso["ai_status"] == "unreadable"
        assert a_turn["ai_status"] == "done" and a_turn["ai"]["verdict"] == "mismatch", a_turn
        assert "400" in str(a_turn["ai"]["found_value"])
        assert b_turn["ai_status"] == "done" and b_turn["ai"]["verdict"] == "match", b_turn

    def test_06_rerun_permissions(self):
        assert S["admin"].post(f"{API}/tender-criteria/{REF}/proof-ai/run").status_code == 200
        r = S["c1"].post(f"{API}/tender-criteria/{REF}/proof-ai/run")
        assert r.status_code == 200 and r.json()["started"] is True
        v = vendor(VA)
        assert v.post(f"{API}/tender-criteria/{REF}/proof-ai/run").status_code in (401, 403)

    def test_07_vote_validation(self):
        u = f"{API}/tender-criteria/{REF}/bids/{S['B']}/proofs/tpturn01/vote"
        assert S["admin"].post(u, json={"decision": "accept"}).status_code == 403
        assert S["c1"].post(u, json={"decision": "reject", "comment": "bad"}).status_code == 422
        assert S["c1"].post(u, json={"decision": "maybe"}).status_code == 422
        assert S["c1"].post(f"{API}/tender-criteria/{REF}/bids/{S['B']}/proofs/nope/vote", json={"decision": "accept"}).status_code == 404
        assert S["c1"].post(f"{API}/tender-criteria/{REF}/bids/{S['C']}/proofs/tpturn01/vote", json={"decision": "accept"}).status_code == 404

    def test_08_unanimous_accept(self):
        u = f"{API}/tender-criteria/{REF}/bids/{S['B']}/proofs/tpturn01/vote"
        r = S["c1"].post(u, json={"decision": "accept"})
        assert r.status_code == 200 and r.json() == {"status": "pending", "votes": 1, "needed": 2}
        r = S["c2"].post(u, json={"decision": "accept", "comment": "Figures match"})
        assert r.status_code == 200 and r.json()["status"] == "accepted"
        assert S["c1"].post(u, json={"decision": "reject", "comment": "changed mind"}).status_code == 409
        bid = DB.bids.find_one({"_id": ObjectId(S["B"])})
        assert bid["qualification"]["proof_reviews"]["tpturn01"]["status"] == "accepted"
        assert bid.get("technical_cleared_at")
        # AI result must survive the vote write
        assert bid["qualification"]["proof_reviews"]["tpturn01"]["ai_status"] == "done"

    def test_09_change_vote_then_reject_disqualifies(self):
        ui = f"{API}/tender-criteria/{REF}/bids/{S['A']}/proofs/tpiso001/vote"
        assert S["c1"].post(ui, json={"decision": "accept"}).json()["status"] == "pending"
        assert S["c2"].post(ui, json={"decision": "accept"}).json()["status"] == "accepted"
        u = f"{API}/tender-criteria/{REF}/bids/{S['A']}/proofs/tpturn01/vote"
        assert S["c1"].post(u, json={"decision": "reject", "comment": "Turnover in accounts is 400k"}).json()["status"] == "pending"
        r = S["c1"].post(u, json={"decision": "accept"})  # change vote
        assert r.status_code == 200 and r.json()["votes"] == 1
        bid = DB.bids.find_one({"_id": ObjectId(S["A"])})
        assert bid["qualification"]["proof_reviews"]["tpturn01"]["votes"][S["c1id"]]["decision"] == "accept"
        r = S["c2"].post(u, json={"decision": "reject", "comment": "Accounts show GBP 400,000 not 750,000"})
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        bid = DB.bids.find_one({"_id": ObjectId(S["A"])})
        q = bid["qualification"]
        assert q["decision"] == "disqualified" and "Average annual turnover" in q["decision_note"]
        assert not bid.get("technical_cleared_at")
        assert S["c1"].post(u, json={"decision": "accept"}).status_code == 409
        d = S["c1"].get(f"{API}/tender-criteria/{REF}/qualification").json()
        assert {x["bid_id"]: x for x in d["bids"]}[S["A"]]["status"] == "disqualified"

    def test_10_commercial_unblocked_and_open(self):
        st = S["c1"].get(f"{API}/bid-opening/{REF}").json()
        bl = st["stages"]["commercial"]["blockers"]
        assert not any("Proof review" in x for x in bl), bl
        assert bl == [], bl
        sig = {"signer_name": "Committee", "consent": True, "typed_signature": "Committee"}
        assert S["c1"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", **sig}).status_code == 200
        r = S["c2"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", **sig})
        assert r.status_code == 200 and r.json()["opened"] is True, r.text
        assert r.json()["bids_opened"] == 1

    def test_11_award_report_l1(self):
        r = S["admin"].get(f"{API}/evaluations/award-report/{REF}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["award_method"] == "l1"
        print("L1 rows:", [(x["bid_id"], x.get("price"), x["qualifies"], x.get("combined")) for x in d.get("ranking") or d.get("rows") or []])
        assert d["recommendation"] and d["recommendation"]["bid_id"] == S["B"]

    def test_12_l1_comparison_award_method(self):
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"award_method": "weighted"}})
        r = S["admin"].post(f"{API}/comparison/l1/{REF}")
        assert r.status_code == 200, r.text
        assert r.json()["award_method"] == "weighted"

    def test_13_award_report_weighted(self):
        d = S["admin"].get(f"{API}/evaluations/award-report/{REF}").json()
        assert d["award_method"] == "weighted"
        rows = d.get("ranking") or d.get("rows") or []
        print("weighted rows:", [(x["bid_id"], x.get("price"), x["qualifies"], x.get("combined")) for x in rows])
        print("weighted recommendation:", d["recommendation"] and d["recommendation"]["bid_id"], "B=", S["B"], "A=", S["A"], "C=", S["C"])
        combined = [x["combined"] for x in rows]
        assert combined == sorted(combined, reverse=True)
