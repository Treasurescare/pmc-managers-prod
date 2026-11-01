# v79: Bidder debrief endpoint (GET /api/v1/bids/{id}/debrief), losing-bidder email (_loss_reason/_flag_losing_emds_for_refund), secret_scan.py
# Seeds TEST_DBRF-* notices/bids for northfield demo vendor directly in Mongo; cleans at module teardown.
import asyncio
import os
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL") or [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0]
API = BASE.rstrip("/") + "/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
TAG = uuid.uuid4().hex[:5].upper()
REF = f"TEST_DBRF-{TAG}"
REF2 = f"TEST_DBRF2-{TAG}"
VEMAIL = "northfield@demo.pmcmanagers.com"
S = {}
SCAN = "/app/scripts/secret_scan.py"


def now(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def cleanup():
    q = {"notice_ref": {"$regex": "^TEST_DBRF"}}
    for c in ("bids", "notices", "comparison_runs"):
        DB[c].delete_many(q)
    DB.audit_logs.delete_many({"details.notice_ref": {"$regex": "^TEST_DBRF"}})
    DB.notifications.delete_many({"$or": [{"title": {"$regex": "TEST_DBRF"}}, {"body": {"$regex": "TEST_DBRF"}}]})


def mk_bid(ref, n, vendor_id, status, price, q=None, **kw):
    b = {"notice_ref": ref, "bid_ref": f"{ref}-B{n}", "vendor_id": vendor_id, "company_name": f"TEST Co {n}",
         "vendor_email": f"test{n}@example.com", "price_amount": price, "price_currency": "GBP", "status": status,
         "created_at": now(days=-3), "documents": [], "workflow_history": []}
    if q:
        b["qualification"] = q
    b.update(kw)
    return str(DB.bids.insert_one(b).inserted_id)


QUAL_OK = {"system_status": "qualified", "results": [
    {"criterion_id": "c1", "title": "ISO 9001", "rule": "must be yes", "mandatory": True, "kind": "must_pass", "value": "yes", "result": "pass", "reason": None},
    {"criterion_id": "c2", "title": "Staff count", "rule": ">= 50", "mandatory": False, "kind": "must_pass", "value": 20, "unit": "people", "result": "fail", "reason": "20 < 50"}],
    "proof_reviews": {
        "c1": {"status": "accepted", "votes": {"m1": {"by": "committee1@demo.pmcmanagers.com", "decision": "accept", "comment": None},
                                                 "m2": {"by": "committee2@demo.pmcmanagers.com", "decision": "accept", "comment": None}}},
        "c2": {"status": "rejected", "votes": {"m1": {"by": "committee1@demo.pmcmanagers.com", "decision": "reject", "comment": "Payroll proof is unreadable"},
                                                 "m2": {"by": "committee2@demo.pmcmanagers.com", "decision": "accept", "comment": None}}}},
    "optional_summary": {"passed": 1, "total": 2, "required": 1}}

QUAL_NQ = {"system_status": "not_qualified", "results": [
    {"criterion_id": "c1", "title": "ISO 9001", "rule": "must be yes", "mandatory": True, "kind": "must_pass", "value": "no", "result": "fail", "reason": "Answer is no"}],
    "optional_summary": {"passed": 0, "total": 2, "required": 1}}

QUAL_DQ = {"system_status": "qualified", "decision": "disqualified", "decision_note": "Forged certificate <script>alert(1)</script>",
           "results": []}


def vendor_session(email=VEMAIL, pw="Demo@Pmc2026"):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code} {r.text[:200]}")
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


@pytest.fixture(scope="module", autouse=True)
def seeded():
    cleanup()
    nf = str(DB.vendors.find_one({"email": VEMAIL})["_id"])
    other = str(DB.vendors.find_one({"email": {"$ne": VEMAIL}})["_id"])
    S["nf"] = nf
    DB.notices.insert_one({"notice_ref": REF, "title": f"TEST debrief {REF}", "is_published": True, "award_method": "l1", "created_at": now()})
    S["win"] = mk_bid(REF, 1, other, "awarded", 400000)
    S["lose"] = mk_bid(REF, 2, nf, "non_winner", 500000, QUAL_OK, emd_refund_due_at=now(days=14), technical_cleared_at=now(days=-1))
    S["nq"] = mk_bid(REF, 3, nf, "non_winner", 300000, QUAL_NQ)
    S["dq"] = mk_bid(REF, 4, nf, "technical_review", 350000, QUAL_DQ)
    S["prog"] = mk_bid(REF, 5, nf, "submitted", 450000)
    S["mine_awarded"] = mk_bid(REF, 6, nf, "awarded", 390000)
    ranked = [{"rank": 1, "bid_id": S["win"], "price_amount": 400000.0, "price_currency": "GBP", "status": "accounting_cleared", "compliance_flags": [], "compliant": True, "company_name": "TEST Co 1"},
              {"rank": 2, "bid_id": S["lose"], "price_amount": 500000.0, "price_currency": "GBP", "status": "accounting_cleared", "compliance_flags": ["late_doc"], "compliant": True}]
    DB.comparison_runs.insert_one({"notice_ref": REF, "run_at": now(), "result": {"ranked": ranked, "l1_winner": ranked[0]}})
    yield
    if os.environ.get("DBRF_KEEP") != "1":
        cleanup()


@pytest.fixture(scope="module")
def vs():
    return vendor_session()


# --- Debrief endpoint ---
class TestDebrief:
    def test_bad_id_404(self, vs):
        assert vs.get(f"{API}/bids/not-an-id/debrief").status_code == 404

    def test_other_vendor_bid_404(self, vs):
        assert vs.get(f"{API}/bids/{S['win']}/debrief").status_code == 404

    def test_unauth_401(self):
        assert requests.get(f"{API}/bids/{S['lose']}/debrief").status_code in (401, 403)

    def test_in_progress_409(self, vs):
        r = vs.get(f"{API}/bids/{S['prog']}/debrief")
        assert r.status_code == 409, r.text
        assert "decision" in r.json()["detail"]

    def test_non_winner_full(self, vs):
        r = vs.get(f"{API}/bids/{S['lose']}/debrief")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["bid_ref"] == f"{REF}-B2" and d["notice_ref"] == REF and d["notice_title"] == f"TEST debrief {REF}"
        assert d["status"] == "non_winner" and d["award_method"] == "l1" and d["qualification_status"] == "qualified"
        assert d["rank"] == {"position": 2, "of": 2, "your_price": 500000.0, "currency": "GBP", "compliance_flags": ["late_doc"]}
        assert d["awarded_price"] == 400000.0
        assert "L2 of 2" in d["summary_html"] and "400,000.00" in d["summary_html"] and "late_doc" in d["summary_html"]
        assert d["optional_summary"] == {"passed": 1, "total": 2, "required": 1}
        assert d["emd_refund_due_at"]
        c = d["criteria"]
        assert len(c) == 2
        assert c[0]["title"] == "ISO 9001" and c[0]["mandatory"] is True and c[0]["result"] == "pass"
        assert c[0]["proof_review"] == {"status": "accepted", "accepted": 2, "rejected_comments": []}
        assert c[1]["mandatory"] is False and c[1]["declared"] == 20 and c[1]["unit"] == "people" and c[1]["reason"] == "20 < 50"
        assert c[1]["proof_review"] == {"status": "rejected", "accepted": 1, "rejected_comments": ["Payroll proof is unreadable"]}
        assert "committee1@" not in r.text and "committee2@" not in r.text

    def test_not_qualified(self, vs):
        d = vs.get(f"{API}/bids/{S['nq']}/debrief").json()
        assert d["qualification_status"] == "not_qualified" and d["rank"] is None
        assert "ISO 9001: Answer is no" in d["summary_html"]
        assert "Optional criteria met: 0 of 2" in d["summary_html"]

    def test_disqualified_in_progress_status_allowed_and_escaped(self, vs):
        r = vs.get(f"{API}/bids/{S['dq']}/debrief")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["decision"] == "disqualified" and "disqualified" in d["summary_html"]
        assert "<script>" not in d["summary_html"] and "&lt;script&gt;" in d["summary_html"]

    def test_awarded_own_bid(self, vs):
        d = vs.get(f"{API}/bids/{S['mine_awarded']}/debrief").json()
        assert d["summary_html"] == "<p>Your bid was awarded.</p>" and d["awarded_price"] is None

    def test_mine_lists_non_winner(self, vs):
        rows = vs.get(f"{API}/bids/mine").json()
        ids = {r["id"]: r["status"] for r in rows if r.get("notice_ref") == REF}
        assert ids.get(S["lose"]) == "non_winner"


# --- Losing email: _flag_losing_emds_for_refund + _loss_reason ---
def test_flag_losing_emds_email(monkeypatch):
    sys.path.insert(0, "/app/backend")
    os.chdir("/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    import notify
    from routers import bids as bids_mod
    nf = S["nf"]
    DB.notices.insert_one({"notice_ref": REF2, "title": "TEST email", "created_at": now()})
    w = mk_bid(REF2, 1, "x", "awarded", 100.0)
    l = mk_bid(REF2, 2, nf, "accounting_cleared", 200.0, emd_paid_amount=50, emd_currency="GBP")
    DB.comparison_runs.insert_one({"notice_ref": REF2, "run_at": now(), "result": {"ranked": [
        {"rank": 1, "bid_id": w, "price_amount": 100.0, "price_currency": "GBP"},
        {"rank": 2, "bid_id": l, "price_amount": 200.0, "price_currency": "GBP"}]}})
    sent = []

    async def fake(to, subj, body, cta=None, url=None, *a, **k):
        sent.append((to, subj, body, cta, url))

    async def fake_role(*a, **k):
        return None
    monkeypatch.setattr(notify, "vendor_confirm", fake)
    monkeypatch.setattr(notify, "notify_role", fake_role, raising=False)

    async def run():
        from db import db as mdb
        n = await bids_mod._flag_losing_emds_for_refund(REF2, w, "TEST_admin@example.com")
        mdb.client.close() if hasattr(mdb, "client") else None
        return n
    n = asyncio.new_event_loop().run_until_complete(run())
    assert n == 1
    b = DB.bids.find_one({"_id": ObjectId(l)})
    assert b["status"] == "non_winner" and b["emd_refund_state"] == "pending_release"
    assert len(sent) == 1
    to, subj, body, cta, url = sent[0]
    assert cta == "Open your full debrief" and url.endswith(f"/vendor/bids/{l}/debrief")
    assert "L2 of 2" in body and "100.00" in body and "200.00" in body and "returned" in body


# --- Secret scanner ---
def _scan(*paths):
    return subprocess.run([sys.executable, SCAN, *paths], capture_output=True, text=True)


FAKE = {
    "resend": "RESEND=re_AbCdEfGh12_ZyXwVuTs9876\n",
    "stripe": "k = sk_live_" + "a1B2c3D4e5F6g7H8i9J0\n",
    "sk": "OPENAI=sk-" + "A" * 24 + "\n",
    "aws": "AKIA" + "ABCDEFGHIJKLMNOP" + "\n",
    "google": "AIza" + "B" * 35 + "\n",
    "gocspx": "GOCSPX-" + "c" * 24 + "\n",
    "github": "ghp_" + "d" * 36 + "\n",
    "pem": "-----BEGIN RSA PRIVATE KEY-----\nabc\n",
    "mongo": "MONGO=mongodb+srv://user:hunter22@cluster0.x.net/db\n",
    "assign": 'password = "Sup3rS3cretValue!"\n',
}


@pytest.mark.parametrize("kind", list(FAKE))
def test_scan_blocks_each_kind(tmp_path, kind):
    p = tmp_path / f"f_{kind}.py"
    p.write_text(FAKE[kind])
    r = _scan(str(p))
    assert r.returncode == 1, r.stdout
    assert "BLOCKED:" in r.stdout and str(p) in r.stdout
    secret_tail = FAKE[kind].strip().split("=")[-1].strip().strip('"')[-10:]
    assert secret_tail not in r.stdout  # secret value never printed


def test_scan_zip_env_pem_key(tmp_path):
    z = tmp_path / "b.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("app/.env", "X=1")
        zf.writestr("certs/server.pem", "x")
        zf.writestr("certs/a.key", "x")
        zf.writestr("src/ok.py", "print('hi')")
    r = _scan(str(z))
    assert r.returncode == 1
    for n in ("app/.env", "certs/server.pem", "certs/a.key"):
        assert f"BLOCKED: secret file in {n}" in r.stdout


def test_scan_zip_content(tmp_path):
    z = tmp_path / "c.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("src/config.py", FAKE["aws"])
    r = _scan(str(z))
    assert r.returncode == 1 and "BLOCKED: AWS access key in src/config.py" in r.stdout


def test_scan_clean(tmp_path):
    p = tmp_path / "ok.py"
    p.write_text('import os\nKEY = os.environ["RESEND_API_KEY"]\npassword = "${PASSWORD}"\n')
    r = _scan(str(p))
    assert r.returncode == 0 and "Secret scan passed." in r.stdout


def test_scan_real_v59l_bundles():
    d = "/app/frontend/public/downloads"
    r = _scan(f"{d}/pmc-backend-v59l.zip", f"{d}/pmc-frontend-v59l-prod-build.zip")
    assert r.returncode == 0, r.stdout[-2000:]
    assert "Secret scan passed." in r.stdout


# Known gaps (documented, expected to FAIL until fixed)
def test_scan_gap_prefixed_env_name(tmp_path):
    p = tmp_path / "g.py"
    p.write_text('ADMIN_PASSWORD = "Sup3rS3cretValue!"\nRESEND_API_KEY="abcdefghijklmnop"\n')
    r = _scan(str(p))
    assert r.returncode == 1, "UPPER_SNAKE prefixed names (ADMIN_PASSWORD, RESEND_API_KEY) are not matched due to \\b before keyword"


def test_scan_gap_env_variants_in_zip(tmp_path):
    z = tmp_path / "e.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("backend/.env.production", "X=1")
    r = _scan(str(z))
    assert r.returncode == 1, ".env.production / .env.local are not treated as secret files"
