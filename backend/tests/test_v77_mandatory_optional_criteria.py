# v77: mandatory vs optional pass/fail criteria + min_optional, optional proof rejection, auto L1 after commercial, proof check report PDF
# Seeds TEST_OPT-* notice, committee (demo committee1+2), 4 sealed bids; cleans everything at module teardown (OPT_TEST_KEEP=1 keeps it).
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
REF = os.environ.get("OPT_TEST_REF") or f"TEST_OPT-{uuid.uuid4().hex[:6].upper()}"
KEEP = os.environ.get("OPT_TEST_KEEP") == "1"
PW = "Demo@Pmc2026"
C1, C2 = "committee1@demo.pmcmanagers.com", "committee2@demo.pmcmanagers.com"
VA, VB, VC, VD = "testvendor@pmcmanagers.com", "northfield@demo.pmcmanagers.com", "brightwater@demo.pmcmanagers.com", "kestrel@demo.pmcmanagers.com"
SIG = {"signer_name": "Committee", "consent": True, "typed_signature": "Committee"}
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
    key = f"bid-docs/TESTOPT{uuid.uuid4().hex[:8]}_{name}"
    r = s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, body, mime)})
    assert r.status_code < 300, r.text
    return key


def cleanup():
    for c in ("bids", "notices", "committees", "opening_records", "comparison_runs"):
        DB[c].delete_many({"notice_ref": REF})
    DB.notifications.delete_many({"related_notice_ref": REF})
    DB.uploads.delete_many({"key": {"$regex": "TESTOPT"}})


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
M1 = {"id": "opturn01", "title": "Average annual turnover", "answer_type": "number", "operator": "gte", "threshold": 500000, "unit": "GBP",
      "kind": "must_pass", "consortium_rule": "lead", "proof": "Audited accounts", "proof_required": True}
O1 = {"id": "opiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "lead",
      "proof": "ISO certificate", "proof_required": True, "mandatory": False}
O2 = {"id": "opsafe01", "title": "Safety accreditation", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "lead",
      "proof": "Safety certificate", "proof_required": True, "mandatory": False}
O3 = {"id": "opins001", "title": "Professional indemnity insurance", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "lead",
      "mandatory": False}
SC = {"id": "opmeth01", "title": "Methodology", "answer_type": "text", "kind": "scored", "max_points": 10, "consortium_rule": "lead"}
CRIT = [M1, O1, O2, O3, SC]


@pytest.fixture(scope="module", autouse=True)
def seeded():
    cleanup()
    DB.notices.insert_one({"notice_ref": REF, "title": "TEST optional criteria tender", "is_published": True, "kyc_bypass": True, "category": "",
                           "budget_amount": 2000000.0, "budget_currency": "GBP", "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "GBP"},
                           "created_at": now(), "published_at": now(), "submission_deadline": now(days=5), "bid_opening_date": now(days=6),
                           "description": "TEST", "tenant_id": "PMC-KZ-01"})
    c1 = str(DB.admin_users.find_one({"email": C1})["_id"])
    c2 = str(DB.admin_users.find_one({"email": C2})["_id"])
    DB.committees.insert_one({"notice_ref": REF, "chairperson_id": c1, "member_ids": [c2], "status": "open", "quorum": 2, "votes": [], "created_at": now()})
    S.update(admin=staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin"), c1=staff(C1, PW, "committee_member"),
             c2=staff(C2, PW, "committee_member"), c1id=c1, c2id=c2)
    print("REF", REF)
    yield
    if not KEEP:
        cleanup()


def _doc(s, name, body=b"PK\x03\x04 fake docx", mime=DOCX, cid=None, kind="technical"):
    d = {"kind": kind, "key": upload(s, name, body, mime), "filename": name, "size_bytes": len(body), "uploaded_at": now()}
    if cid:
        d["criterion_id"] = cid
    return d


def _base_docs(s):
    return [_doc(s, "technical.pdf", b"%PDF-1.4 t", "application/pdf"), _doc(s, "price.pdf", b"%PDF-1.4 p", "application/pdf", kind="commercial")]


def _bid(s, price, answers, docs):
    return s.post(f"{API}/bids", json={"notice_ref": REF, "price_amount": price, "price_currency": "GBP", "technical_notes": "T",
                                       "commercial_notes": "C", "documents": docs, "criteria_answers": answers})


def _q(bid):
    return DB.bids.find_one({"_id": ObjectId(S[bid])})["qualification"]


class TestA_CriteriaSave:
    def test_defaults_and_min_optional_roundtrip(self):
        crit = [{k: v for k, v in c.items() if k != "mandatory"} for c in CRIT]  # no mandatory flag sent
        r = S["admin"].put(f"{API}/tender-criteria/{REF}", json={"criteria": crit})
        assert r.status_code == 200, r.text
        m = {c["id"]: c["mandatory"] for c in r.json()["criteria"]}
        assert all(m[c] is True for c in ("opturn01", "opiso001", "opsafe01", "opins001")) and m["opmeth01"] is False, m
        assert r.json()["min_optional"] is None
        r = S["admin"].put(f"{API}/tender-criteria/{REF}", json={"criteria": CRIT, "min_optional": 2})
        assert r.status_code == 200, r.text
        assert r.json()["min_optional"] == 2
        g = S["admin"].get(f"{API}/tender-criteria/{REF}/admin").json()
        assert g["min_optional"] == 2 and {c["id"]: c["mandatory"] for c in g["criteria"]}["opiso001"] is False
        pub = requests.get(f"{API}/tender-criteria/{REF}").json()
        assert pub["min_optional"] == 2 and {c["id"]: c["mandatory"] for c in pub["criteria"]}["opins001"] is False
        assert DB.notices.find_one({"notice_ref": REF})["criteria_min_optional"] == 2

    def test_min_optional_validation(self):
        for bad in (-1, 61, "x"):
            assert S["admin"].put(f"{API}/tender-criteria/{REF}", json={"criteria": CRIT, "min_optional": bad}).status_code == 422
        assert DB.notices.find_one({"notice_ref": REF})["criteria_min_optional"] == 2


class TestB_Submit:
    def test_mandatory_gaps_only(self):
        a = vendor(VA)
        r = _bid(a, 900000, [], _base_docs(a))
        assert r.status_code == 422, r.text
        det = r.json()["detail"]
        assert "Average annual turnover (answer)" in det and "Average annual turnover (proof)" in det
        assert "ISO" not in det and "Safety" not in det and "indemnity" not in det and "Methodology" not in det, det

    def test_answered_optional_needs_proof(self):
        a = vendor(VA)
        docs = _base_docs(a) + [_doc(a, "acc-a.docx", cid="opturn01")]
        r = _bid(a, 900000, [{"criterion_id": "opturn01", "value": 750000}, {"criterion_id": "opiso001", "value": True}], docs)
        assert r.status_code == 422 and "ISO 9001 certification (proof)" in r.json()["detail"], r.text
        assert "Safety" not in r.json()["detail"]

    def test_submit_four_bids(self):
        a, b, c, d = vendor(VA), vendor(VB), vendor(VC), vendor(VD)
        iso_b = pdf("Northfield Ltd\nISO 9001:2015 Certificate of Registration\nQuality Management System\nValid until 31 December 2027\nCertificate no. Q-12345")
        plan = {
            # A: mandatory ok, O1+O2 yes, O3 unanswered -> 2/3 optional (need 2) -> qualified
            "A": (a, 900000, [("opturn01", 750000), ("opiso001", True), ("opsafe01", True)], [("acc-a.docx", "opturn01"), ("iso-a.docx", "opiso001"), ("safe-a.docx", "opsafe01")]),
            # B: everything -> 3/3 -> qualified, cheapest
            "B": (b, 800000, [("opturn01", 800000), ("opiso001", True), ("opsafe01", True), ("opins001", True), ("opmeth01", "Plan")],
                  [("acc-b.docx", "opturn01"), ("iso-b.pdf", "opiso001"), ("safe-b.docx", "opsafe01")]),
            # C: mandatory fails -> not qualified
            "C": (c, 500000, [("opturn01", 100000), ("opiso001", True), ("opsafe01", True), ("opins001", True)],
                  [("acc-c.docx", "opturn01"), ("iso-c.docx", "opiso001"), ("safe-c.docx", "opsafe01")]),
            # D: mandatory ok, O1 yes, O2 no answer, O3 yes -> 2/3 -> qualified
            "D": (d, 950000, [("opturn01", 900000), ("opiso001", True), ("opins001", True)], [("acc-d.docx", "opturn01"), ("iso-d.docx", "opiso001")]),
        }
        for key, (s, price, ans, proofs) in plan.items():
            docs = _base_docs(s) + [(_doc(s, n, iso_b, "application/pdf", cid=cid) if n.endswith(".pdf") else _doc(s, n, cid=cid)) for n, cid in proofs]
            r = _bid(s, price, [{"criterion_id": k, "value": v} for k, v in ans], docs)
            assert r.status_code < 300, f"{key}: {r.text}"
            S[key] = r.json()["id"]
        DB.notices.update_one({"notice_ref": REF}, {"$set": {"submission_deadline": now(hours=-3), "bid_opening_date": now(hours=-2)}})


class TestC_TechnicalEvaluation:
    def test_open_technical(self):
        assert S["c1"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", **SIG}).status_code == 200
        r = S["c2"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "technical", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is True, r.text

    def test_evaluation_results(self):
        qa, qb, qc, qd = (_q(k) for k in "ABCD")
        assert qa["system_status"] == "qualified" and qa["optional_summary"] == {"passed": 2, "total": 3, "required": 2}
        ins = next(r for r in qa["results"] if r["criterion_id"] == "opins001")
        assert ins["result"] == "fail" and ins["reason"] == "Not answered (optional criterion)" and ins["mandatory"] is False
        assert next(r for r in qa["results"] if r["criterion_id"] == "opturn01")["mandatory"] is True
        assert qb["system_status"] == "qualified" and qb["optional_summary"]["passed"] == 3
        assert qc["system_status"] == "not_qualified" and qc["optional_summary"]["passed"] == 3
        assert qd["system_status"] == "qualified" and qd["optional_summary"]["passed"] == 2
        assert set(qa["proof_reviews"]) == {"opturn01", "opiso001", "opsafe01"}
        assert set(qb["proof_reviews"]) == {"opturn01", "opiso001", "opsafe01"}
        assert set(qd["proof_reviews"]) == {"opturn01", "opiso001"}
        d = S["c1"].get(f"{API}/tender-criteria/{REF}/qualification").json()
        bids = {x["bid_id"]: x for x in d["bids"]}
        assert bids[S["A"]].get("optional_summary") == {"passed": 2, "total": 3, "required": 2}, bids[S["A"]].keys()

    def test_preliminary_notice_has_optional_line(self):
        deadline = time.time() + 30
        while time.time() < deadline and not DB.bids.find_one({"_id": ObjectId(S["A"])}).get("qualification_notices"):
            time.sleep(2)
        n = DB.bids.find_one({"_id": ObjectId(S["A"])})["qualification_notices"][0]
        assert n["kind"] == "preliminary" and n["optional_summary"]["required"] == 2
        assert "Optional criteria met: <b>2 of 3</b>" in n["body"], n["body"]

    def test_ai_reads_pdf_proof(self):
        deadline = time.time() + 180
        while time.time() < deadline:
            pr = _q("B")["proof_reviews"]["opiso001"]
            if pr["ai_status"] not in ("pending", "running"):
                break
            time.sleep(6)
        print("AI B iso:", pr)
        assert pr["ai_status"] == "done" and pr["ai"]["verdict"] in ("match", "unclear"), pr
        assert _q("A")["proof_reviews"]["opiso001"]["ai_status"] == "unreadable"


def _vote(who, bid, cid, decision, comment=None):
    r = S[who].post(f"{API}/tender-criteria/{REF}/bids/{S[bid]}/proofs/{cid}/vote", json={"decision": decision, "comment": comment})
    assert r.status_code == 200, r.text
    return r.json()


class TestD_ProofVotes:
    def test_reject_optional_keeps_bid_when_enough(self):
        for cid in ("opturn01", "opiso001"):
            _vote("c1", "B", cid, "accept")
            assert _vote("c2", "B", cid, "accept")["status"] == "accepted"
        _vote("c1", "B", "opsafe01", "accept")
        assert _vote("c2", "B", "opsafe01", "reject", "Safety certificate expired in 2023")["status"] == "rejected"
        b = DB.bids.find_one({"_id": ObjectId(S["B"])})
        q = b["qualification"]
        assert "decision" not in q and b.get("technical_cleared_at"), q.get("decision_note")
        assert q["optional_summary"]["passed"] == 2
        r = next(x for x in q["results"] if x["criterion_id"] == "opsafe01")
        assert r["result"] == "fail" and "Safety certificate expired" in r["reason"]

    def test_reject_optional_below_min_disqualifies(self):
        _vote("c1", "A", "opturn01", "accept")
        _vote("c2", "A", "opturn01", "accept")
        _vote("c1", "A", "opiso001", "reject", "Certificate belongs to another company")
        assert _vote("c2", "A", "opiso001", "accept")["status"] == "rejected"
        b = DB.bids.find_one({"_id": ObjectId(S["A"])})
        q = b["qualification"]
        assert q["decision"] == "disqualified" and not b.get("technical_cleared_at")
        assert "now meets 1 of the 2 optional criteria required" in q["decision_note"], q["decision_note"]
        assert q["optional_summary"]["passed"] == 1

    def test_reject_mandatory_disqualifies(self):
        _vote("c1", "D", "opiso001", "accept")
        _vote("c2", "D", "opiso001", "accept")
        _vote("c1", "D", "opturn01", "reject", "Accounts show GBP 300,000")
        assert _vote("c2", "D", "opturn01", "reject", "Turnover too low in accounts")["status"] == "rejected"
        q = _q("D")
        assert q["decision"] == "disqualified" and "Average annual turnover" in q["decision_note"]
        assert "optional criteria required" not in q["decision_note"]
        assert q["optional_summary"]["passed"] == 2


class TestE_ProofReport:
    def test_report_pdf_content(self):
        r = S["admin"].get(f"{API}/tender-criteria/{REF}/proof-report.pdf", timeout=60)
        assert r.status_code == 200 and r.content[:4] == b"%PDF", r.text[:300]
        assert "attachment" in r.headers.get("content-disposition", "")
        txt = " ".join(" ".join(p.get_text().split()) for p in fitz.open(stream=r.content, filetype="pdf"))
        for b in "ABCD":
            ref = DB.bids.find_one({"_id": ObjectId(S[b])})["bid_ref"]
            assert ref in txt, ref
        for s in ("mandatory", "optional", "Safety certificate expired", "Certificate belongs to another company", "iso-b.pdf",
                  "committee1@demo.pmcmanagers.com", "Optional criteria met", "Not answered (optional criterion)", "disqualified"):
            assert s in txt, s

    def test_report_permissions(self):
        assert S["c1"].get(f"{API}/tender-criteria/{REF}/proof-report.pdf", timeout=60).status_code == 200
        assert vendor(VA).get(f"{API}/tender-criteria/{REF}/proof-report.pdf").status_code in (401, 403)
        assert requests.get(f"{API}/tender-criteria/{REF}/proof-report.pdf").status_code in (401, 403)
        assert S["admin"].get(f"{API}/tender-criteria/TEST_NOPE-XYZ/proof-report.pdf").status_code == 404


class TestF_CommercialAutoL1:
    def test_latest_empty_before(self):
        r = S["c1"].get(f"{API}/comparison/l1/{REF}/latest")
        assert r.status_code == 200 and r.json()["result"] is None

    def test_commercial_open_runs_l1(self):
        st = S["c1"].get(f"{API}/bid-opening/{REF}").json()["stages"]["commercial"]["blockers"]
        assert st == [], st
        assert S["c1"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", **SIG}).status_code == 200
        r = S["c2"].post(f"{API}/bid-opening/{REF}/approve", json={"stage": "commercial", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is True and r.json()["bids_opened"] == 1, r.text
        d = S["c1"].get(f"{API}/comparison/l1/{REF}/latest").json()
        assert d["result"] and d["run_at"] and d["run_by"] == C2
        res = d["result"]
        assert [x["bid_id"] for x in res["ranked"]] == [S["B"]] and res["l1_winner"]["bid_id"] == S["B"]
        assert res["l1_winner"]["rank"] == 1 if "rank" in res["l1_winner"] else True
        assert vendor(VA).get(f"{API}/comparison/l1/{REF}/latest").status_code in (401, 403)

    def test_final_notice_optional_line(self):
        n = DB.bids.find_one({"_id": ObjectId(S["B"])})["qualification_notices"][-1]
        assert n["kind"] == "final" and "Optional criteria met: <b>2 of 3</b>" in n["body"]
