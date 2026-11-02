# v81: Challenge register PDF (auditors/lenders) + first published prices (tender fee flat, management fee stepped).
# Uses demo tender DEMO-TND-AWD; restores all data at teardown (ledger rows are append-only and stay).
import io
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from pypdf import PdfReader

sys.path.insert(0, "/app/backend")

BASE = os.environ.get("REACT_APP_BACKEND_URL") or [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0]
API = BASE.rstrip("/") + "/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
REF = "DEMO-TND-AWD"
KESTREL_BID = "6ae6a21837fa842ad33531cb"
NF_BID = "6ae6a21737fa842ad33531c5"
PW = "Demo@Pmc2026"
S = {}


def iso(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def _sess(path, email, pw, extra=None):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": email, "password": pw, **(extra or {})})
    assert r.status_code == 200, r.text
    j = r.json()
    tok = j.get("access_token") or j.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    if j.get("csrf_token"):
        s.headers["X-CSRF-Token"] = j["csrf_token"]
    return s


def pdf_text(content: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)


@pytest.fixture(scope="module", autouse=True)
def setup():
    S["orig_bid"] = DB.bids.find_one({"_id": ObjectId(NF_BID)}, {"status": 1, "awarded_at": 1})
    S["corr_before"] = [c["_id"] for c in DB.corrigenda.find({"notice_ref": REF}, {"_id": 1})]
    S["admin"] = _sess("admin/auth/login", "adminsupport@pmcmanagers.com", "Admin@12345")
    S["k"] = _sess("vendor/auth/login", "kestrel@demo.pmcmanagers.com", PW)
    S["c1"] = _sess("staff/auth/login", "committee1@demo.pmcmanagers.com", PW, {"active_role": "committee_member"})
    S["c2"] = _sess("staff/auth/login", "committee2@demo.pmcmanagers.com", PW, {"active_role": "committee_member"})
    yield
    DB.bid_challenges.delete_many({"notice_ref": REF})
    DB.corrigenda.delete_many({"notice_ref": REF, "_id": {"$nin": S["corr_before"]}})
    DB.notices.update_one({"notice_ref": REF}, {"$unset": {"standstill_days": "", "award_suspended": "", "award_suspended_at": "", "re_evaluation_required": ""}})
    ob = S["orig_bid"]
    DB.bids.update_one({"_id": ob["_id"]}, {"$set": {"status": ob["status"], "awarded_at": ob["awarded_at"]},
                                            "$unset": {"award_withdrawn_at": "", "award_withdrawn_reason": ""}})


# ---------- Published prices ----------
class TestPublicPricing:
    def test_public_pricing_exact(self):
        r = requests.get(f"{API}/fee-types/public/pricing")
        assert r.status_code == 200
        fees = {f["code"]: f for f in r.json()["fees"]}
        assert set(fees) == {"tender_fee", "tender_management"}, list(fees)
        exp = {"IN": ("INR", 1000), "GB": ("GBP", 500), "US": ("USD", 500), "MY": ("MYR", 500)}
        tf = fees["tender_fee"]["rules"]
        assert len(tf) == 4
        for rule in tf:
            c = rule["countries"][0]
            assert rule["currency"] == exp[c][0] and rule["slabs"][0]["fixed_amount"] == exp[c][1] and rule["progressive"] is False
        tm = fees["tender_management"]["rules"]
        assert len(tm) == 4 and {x["countries"][0] for x in tm} == set(exp)
        for rule in tm:
            assert rule["progressive"] is True and rule["currency"] == exp[rule["countries"][0]][0]
            s0, s1 = rule["slabs"]
            assert (s0["tender_value_min"], s0["tender_value_max"], s0["percentage"]) == (0, 5_000_000, 3.0)
            assert (s1["tender_value_min"], s1["tender_value_max"], s1["percentage"]) == (5_000_000, None, 2.0)

    def test_no_transaction_fee(self):
        txt = requests.get(f"{API}/fee-types/public/pricing").text.lower()
        assert "transaction" not in txt


class TestComputeAmount:
    def test_progressive(self):
        from routers._fees import compute_amount
        rule = DB.emd_masters.find_one({"kind": "tender_management", "countries": "IN"})
        assert compute_amount(rule, 4_000_000) == 120_000
        assert compute_amount(rule, 5_000_000) == 150_000
        assert compute_amount(rule, 12_000_000) == 290_000
        assert compute_amount(rule, 0) == 0
        assert compute_amount(rule, None) is None

    def test_non_progressive_unchanged(self):
        from routers._fees import compute_amount
        rule = dict(DB.emd_masters.find_one({"kind": "tender_management", "countries": "IN"}))
        rule["progressive"] = False
        assert compute_amount(rule, 12_000_000) == 240_000  # whole value at band rate 2%
        assert compute_amount(rule, 4_000_000) == 120_000
        tf = DB.emd_masters.find_one({"kind": "tender_fee", "countries": "IN"})
        assert compute_amount(tf, None) == 1000

    def test_tender_builder_fees_uses_stepped(self):
        import asyncio
        from routers import _fees
        async def run():
            return await _fees.upfront_quote("IN", "", 12_000_000), await _fees.tender_builder_fees("IN", {"header": {"tender_value": 12_000_000}})
        q, tb = asyncio.new_event_loop().run_until_complete(run())
        tm = [f for f in tb if f.get("code") == "tender_management" or f.get("fee_type") == "tender_management"]
        print("upfront:", q, "\nbuilder:", tb)
        assert tm and abs(float(tm[0]["amount"]) - 290_000) < 0.01


class TestSeedOneTime:
    def test_seed_does_not_overwrite(self):
        import subprocess
        import time
        rid = DB.emd_masters.find_one({"kind": "tender_fee", "countries": "GB"})["_id"]
        DB.emd_masters.update_one({"_id": rid}, {"$set": {"slabs.0.fixed_amount": 777}})
        try:
            subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True, capture_output=True)
            for _ in range(40):
                try:
                    if requests.get(f"{API}/fee-types/public/pricing", timeout=5).status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            assert DB.emd_masters.find_one({"_id": rid})["slabs"][0]["fixed_amount"] == 777
            assert DB.emd_masters.count_documents({"kind": {"$in": ["tender_fee", "tender_management"]}}) == 8
            gb = [r for f in requests.get(f"{API}/fee-types/public/pricing").json()["fees"] if f["code"] == "tender_fee"
                  for r in f["rules"] if r["countries"] == ["GB"]][0]
            assert gb["slabs"][0]["fixed_amount"] == 777
        finally:
            DB.emd_masters.update_one({"_id": rid}, {"$set": {"slabs.0.fixed_amount": 500}})


class TestAdminRuleProgressive:
    def test_edit_keeps_progressive(self):
        a = S["admin"]
        orig = DB.emd_masters.find_one({"kind": "tender_management", "countries": "IN"})
        keys = ["name", "country", "countries", "industry", "category", "kind", "categories", "currency", "slabs", "is_active", "progressive", "notes"]
        body = {k: orig.get(k) for k in keys}
        body["notes"] = "TEST_ edited"
        try:
            r = a.patch(f"{API}/tender-pro/emd-masters/{orig['_id']}", json=body)
            assert r.status_code == 200, r.text
            d = DB.emd_masters.find_one({"_id": orig["_id"]})
            assert d["progressive"] is True and d["notes"] == "TEST_ edited"
            assert [s["percentage"] for s in d["slabs"]] == [3.0, 2.0]
            lst = a.get(f"{API}/tender-pro/emd-masters", params={"kind": "tender_management"})
            assert lst.status_code == 200 and all(x.get("progressive") for x in lst.json())
        finally:
            DB.emd_masters.update_one({"_id": orig["_id"]}, {"$set": {k: orig.get(k) for k in keys}, "$unset": {"updated_at": ""}})

    def test_fee_types_flag(self):
        r = S["admin"].get(f"{API}/fee-types")
        assert r.status_code == 200
        on = sorted(x["code"] for x in r.json() if x.get("show_on_pricing"))
        assert on == ["tender_fee", "tender_management"], on


# ---------- Challenge register PDF ----------
def vote(who, cid, d):
    return S[who].post(f"{API}/bid-challenges/{cid}/vote", json={"decision": d, "comment": f"TEST_ reason {who} {d}"})


class TestRegisterPdf:
    def test_01_access(self):
        url = f"{API}/bid-challenges/notice/{REF}/register.pdf"
        assert requests.get(url).status_code in (401, 403)
        assert S["k"].get(url).status_code in (401, 403)
        cert = _sess("staff/auth/login", "legal@pmcmanagers.com", "Legal@123", {"active_role": "committee_member"})
        r = cert.get(url)
        print("non-committee committee_member:", r.status_code, r.text[:120])
        assert r.status_code == 403
        assert S["admin"].get(f"{API}/bid-challenges/notice/NOPE-XYZ/register.pdf").status_code == 404
        r = S["c1"].get(url)
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
        assert "No challenges were lodged" in pdf_text(r.content)

    def test_02_full_flow_pdf(self):
        k, a = S["k"], S["admin"]
        a.put(f"{API}/bid-challenges/notice/{REF}/standstill", json={"days": 12, "reason": "TEST_ Extend standstill for auditors"})
        # challenge 1: upheld -> meeting -> resolved confirm
        r = k.post(f"{API}/bid-challenges/mine/{KESTREL_BID}", json={"grounds": "evaluation", "details": "TEST_ Evaluation ignored our ISO 9001 certificate."})
        assert r.status_code == 200, r.text
        c1 = r.json()["id"]
        vote("c1", c1, "uphold"); vote("c2", c1, "dismiss")
        r = S["c1"].post(f"{API}/bid-challenges/{c1}/meeting", json={"scheduled_at": iso(days=2), "location": "TEST Board Room 7"})
        assert r.status_code == 200, r.text
        DB.bid_challenges.update_one({"_id": ObjectId(c1)}, {"$set": {"meeting.scheduled_at": iso(hours=-1)}})
        r = a.post(f"{API}/bid-challenges/{c1}/resolution", json={"outcome": "confirm_award", "minutes": "TEST_ Minutes award stands"})
        assert r.status_code == 200, r.text
        # challenge 2: dismissed -> appeal -> appeal dismissed
        r = k.post(f"{API}/bid-challenges/mine/{KESTREL_BID}", json={"grounds": "price", "details": "TEST_ Price comparison used the wrong currency."})
        assert r.status_code == 200, r.text
        c2 = r.json()["id"]
        vote("c1", c2, "dismiss"); vote("c2", c2, "dismiss")
        r = k.post(f"{API}/bid-challenges/mine/challenge/{c2}/appeal", json={"reason": "TEST_ Committee missed the FX evidence."})
        assert r.status_code == 200, r.text
        r = a.post(f"{API}/bid-challenges/{c2}/appeal-decision", json={"decision": "dismiss", "reason": "TEST_ Final senior dismissal"})
        assert r.status_code == 200, r.text
        refs = [DB.bid_challenges.find_one({"_id": ObjectId(x)})["challenge_ref"] for x in (c1, c2)]

        before = DB.audit_events.count_documents({"event_type": "bid_challenge.register_downloaded", "target_id": REF})
        r = a.get(f"{API}/bid-challenges/notice/{REF}/register.pdf")
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf")
        assert f"{REF}-challenge-register.pdf" in r.headers.get("content-disposition", "")
        t = pdf_text(r.content)
        flat = " ".join(t.split())
        open("/app/test_reports/pytest/register_pdf_text.txt", "w").write(t)
        checks = {
            "title": "Bid challenge register", "ref": REF, "standstill": "12 days", "contract": "Contract signing",
            "ch1": refs[0], "ch2": refs[1], "bidder": "kestrel@demo.pmcmanagers.com",
            "details1": "ISO 9001", "details2": "wrong currency", "voter1": "committee1@demo.pmcmanagers.com",
            "voter2": "committee2@demo.pmcmanagers.com", "vote_reason": "TEST_ reason c1 uphold", "uphold": "uphold",
            "outcome_upheld": "Upheld", "outcome_dismissed": "Dismissed", "place": "TEST Board Room 7",
            "invited": "northfield@demo.pmcmanagers.com", "resolution": "Award confirmed", "minutes": "Minutes award stands",
            "appeal_reason": "FX evidence", "appeal_dec": "Final senior dismissal", "decided_by": "adminsupport@pmcmanagers.com",
            "corr": "Standstill period changed from 10 to 12 days", "corr_reason": "Extend standstill for auditors",
            "ledger": "Audit ledger entries", "ev_lodged": "bid_challenge.lodged", "ev_vote": "bid_challenge.vote",
            "ev_meeting": "bid_challenge.meeting", "ev_resolved": "bid_challenge.resolved", "ev_appeal": "bid_challenge.appealed",
            "ev_appdec": "bid_challenge.appeal_decided", "ev_standstill": "bid_challenge.standstill_changed",
        }
        missing = [k_ for k_, v in checks.items() if v not in flat]
        assert not missing, f"Missing in PDF: {missing}"
        after = DB.audit_events.count_documents({"event_type": "bid_challenge.register_downloaded", "target_id": REF})
        assert after == before + 1
        ev = DB.audit_events.find_one({"event_type": "bid_challenge.register_downloaded", "target_id": REF}, sort=[("seq", -1)])
        assert ev.get("current_hash")

    def test_03_committee_member_on_tender_ok(self):
        r = S["c2"].get(f"{API}/bid-challenges/notice/{REF}/register.pdf")
        assert r.status_code == 200 and r.content[:4] == b"%PDF"
