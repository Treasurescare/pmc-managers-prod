# v78: Award-to-L1 one-click endpoint + tender tracker (/tender-tracker, /tender-tracker/live)
# Run with -n 0 (module fixture not xdist-safe). Seeds TEST_AWL1-* notices directly in Mongo (committee incl. admin user), cleans at module teardown (AWL1_KEEP=1 keeps).
import os
import uuid
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
REF = f"TEST_AWL1-{TAG}"          # main l1 award scenario
REF_W = f"TEST_AWL1W-{TAG}"       # weighted
REF_NC = f"TEST_AWL1NC-{TAG}"     # commercial not opened
REF_ST = f"TEST_AWL1ST-{TAG}"     # L1 bid at legal_cleared
REF_NM = f"TEST_AWL1NM-{TAG}"     # admin not a committee member
REF_NOC = f"TEST_AWL1NOC-{TAG}"   # no compliant L1
REF_TR = f"TEST_AWL1TR-{TAG}"     # tracker skipped-state scenario
REFS = [REF, REF_W, REF_NC, REF_ST, REF_NM, REF_NOC, REF_TR]
KEEP = os.environ.get("AWL1_KEEP") == "1"
S = {}


def now(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def cleanup():
    q = {"notice_ref": {"$regex": "^TEST_AWL1"}}
    for c in ("bids", "notices", "committees", "opening_records", "comparison_runs", "awards", "purchase_orders", "contracts", "award_documents"):
        DB[c].delete_many(q)
    DB.notifications.delete_many({"$or": [{"related_notice_ref": {"$regex": "^TEST_AWL1"}}, {"title": {"$regex": "TEST_AWL1"}}, {"body": {"$regex": "TEST_AWL1"}}]})


def mk_notice(ref, **kw):
    d = {"notice_ref": ref, "title": f"TEST award L1 {ref}", "is_published": True, "category": "", "budget_amount": 1000000.0,
         "budget_currency": "GBP", "created_at": now(), "published_at": now(days=-10), "submission_deadline": now(days=-2),
         "bid_opening_date": now(days=-1), "description": "TEST", "tenant_id": "PMC-KZ-01", "award_method": "l1",
         "tender_criteria": [{"id": "c1", "title": "Turnover", "answer_type": "yes_no", "kind": "must_pass"}],
         "technical_opened_at": now(days=-1), "commercial_opened_at": now(hours=-2)}
    d.update(kw)
    DB.notices.insert_one(d)


def mk_bid(ref, n, price, status, docs=True, tech=True):
    b = {"notice_ref": ref, "bid_ref": f"{ref}-B{n}", "company_name": f"TEST Co {n}", "vendor_email": f"test{n}@example.com",
         "vendor_ref": f"VEN-TEST{n}", "price_amount": price, "price_currency": "GBP", "status": status, "created_at": now(days=-3),
         "documents": [{"kind": "technical", "key": "x", "filename": "t.pdf"}, {"kind": "commercial", "key": "y", "filename": "p.pdf"}] if docs else [],
         "workflow_history": []}
    if tech:
        b["technical_cleared_at"] = now(days=-1)
    return str(DB.bids.insert_one(b).inserted_id)


def mk_committee(ref, members):
    DB.committees.insert_one({"notice_ref": ref, "chairperson_id": members[0], "member_ids": members[1:], "status": "open",
                              "quorum": 1, "votes": [], "created_at": now()})


@pytest.fixture(scope="module", autouse=True)
def seeded():
    cleanup()
    admin_id = str(DB.admin_users.find_one({"email": "adminsupport@pmcmanagers.com"})["_id"])
    other = DB.admin_users.find_one({"email": {"$ne": "adminsupport@pmcmanagers.com"}})
    other_id = str(other["_id"])
    for r in (REF, REF_W, REF_NC, REF_ST, REF_NOC):
        mk_committee(r, [other_id, admin_id])
    mk_committee(REF_NM, [other_id])
    mk_notice(REF)
    S["l1"] = mk_bid(REF, 1, 500000, "accounting_cleared")
    S["l2"] = mk_bid(REF, 2, 600000, "accounting_cleared")
    mk_bid(REF, 3, 450000, "accounting_cleared", tech=False)  # cheaper but not technically cleared -> ineligible
    mk_notice(REF_W, award_method="weighted"); mk_bid(REF_W, 1, 500000, "accounting_cleared")
    mk_notice(REF_NC, commercial_opened_at=None); mk_bid(REF_NC, 1, 500000, "accounting_cleared")
    mk_notice(REF_ST); mk_bid(REF_ST, 1, 500000, "legal_cleared"); mk_bid(REF_ST, 2, 700000, "accounting_cleared")
    mk_notice(REF_NM); mk_bid(REF_NM, 1, 500000, "accounting_cleared")
    mk_notice(REF_NOC); mk_bid(REF_NOC, 1, 500000, "accounting_cleared", docs=False)
    # tracker: criteria done, deadline future (bids not done), technical opened -> bids should be "skipped"
    mk_notice(REF_TR, submission_deadline=now(days=3), commercial_opened_at=None); mk_bid(REF_TR, 1, 1000, "submitted")
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345", "active_role": "admin"})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    S["admin"] = s
    yield
    if not KEEP:
        cleanup()


def award(ref, notes=None):
    return S["admin"].post(f"{API}/comparison/l1/{ref}/award", json={"notes": notes})


# --- Award to L1 guards
class TestA_AwardGuards:
    def test_anon_401(self):
        assert requests.post(f"{API}/comparison/l1/{REF}/award", json={}).status_code in (401, 403)

    def test_not_member_403(self):
        r = award(REF_NM)
        assert r.status_code == 403, r.text

    def test_unknown_404(self):
        assert award("TEST_AWL1-NOPE").status_code == 404

    def test_weighted_409(self):
        r = award(REF_W)
        assert r.status_code == 409 and "weighted" in r.json()["detail"].lower(), r.text

    def test_commercial_not_open_409(self):
        r = award(REF_NC)
        assert r.status_code == 409 and "not open" in r.json()["detail"].lower(), r.text

    def test_no_compliant_409(self):
        r = award(REF_NOC)
        assert r.status_code == 409 and "compliant" in r.json()["detail"].lower(), r.text

    def test_stage_not_cleared_409(self):
        r = award(REF_ST)
        assert r.status_code == 409 and "legal_cleared" in r.json()["detail"], r.text
        assert DB.bids.count_documents({"notice_ref": REF_ST, "status": "awarded"}) == 0

    def test_notes_too_long_422(self):
        assert award(REF, "x" * 1001).status_code == 422


# --- Award to L1 success path
class TestB_AwardSuccess:
    def test_award_success(self):
        r = award(REF, "TEST note")
        assert r.status_code == 200, r.text
        assert r.json() == {"awarded": f"{REF}-B1", "company_name": "TEST Co 1"}
        b = DB.bids.find_one({"_id": ObjectId(S["l1"])})
        assert b["status"] == "awarded"
        h = b["workflow_history"][-1]
        assert h["action"] == "award" and h["role"] == "committee" and h["to_status"] == "awarded" and "TEST note" in h["notes"]
        assert DB.audit_events.find_one({"event_type": "comparison.l1_award", "target_id": REF}) is not None
        assert DB.bids.find_one({"_id": ObjectId(S["l2"])})["status"] != "awarded"

    def test_latest_l1_shows_awarded(self):
        d = S["admin"].get(f"{API}/comparison/l1/{REF}/latest").json()
        statuses = {x["bid_ref"]: x["status"] for x in d["result"]["ranked"]}
        assert statuses.get(f"{REF}-B1") == "awarded", f"latest run not refreshed after award: {statuses}"

    def test_already_awarded_409(self):
        r = award(REF)
        assert r.status_code == 409 and "already" in r.json()["detail"].lower(), r.text


# --- Tender tracker
class TestC_Tracker:
    def test_anon_401(self):
        assert requests.get(f"{API}/tender-tracker/live").status_code == 401
        assert requests.get(f"{API}/tender-tracker", params={"refs": REF}).status_code == 401

    def test_refs_awarded_all_done(self):
        d = S["admin"].get(f"{API}/tender-tracker", params={"refs": f"{REF},{REF_TR}"}).json()
        t = d[REF]
        assert [s["key"] for s in t["stages"]] == ["criteria", "bids", "opening", "proof", "price", "l1", "award"]
        assert t["done"] == 7 and t["current"] is None
        assert all(s["state"] == "done" for s in t["stages"])

    def test_skipped_state(self):
        t = S["admin"].get(f"{API}/tender-tracker", params={"refs": REF_TR}).json()[REF_TR]
        st = {s["key"]: s["state"] for s in t["stages"]}
        assert st["criteria"] == "done" and st["bids"] == "skipped" and st["opening"] == "done" and st["proof"] == "done"
        assert st["price"] == "current" and t["current"] == "price" and st["l1"] == "todo" and st["award"] == "todo"

    def test_live_lists_in_progress_only(self):
        r = S["admin"].get(f"{API}/tender-tracker/live")
        assert r.status_code == 200
        rows = r.json()["tenders"]
        for row in rows:
            assert set(["notice_ref", "title", "deadline", "stages", "current", "done"]) <= set(row)
            assert row["current"] is not None and row["done"] < 7
        refs = [x["notice_ref"] for x in rows]
        assert REF not in refs  # fully done excluded
        print("live count", len(rows), "published", DB.notices.count_documents({"is_published": True, "deleted_at": None}))
        assert REF_TR in refs, "in-progress TEST notice missing from live list (limit 40 applied before filtering?)"
