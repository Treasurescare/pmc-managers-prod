# v80: Public pricing from fee types (show_on_pricing) + Bid Challenge module (standstill, committee vote,
# resolution meeting, appeal, contract-signing gates). Uses demo tender DEMO-TND-AWD; restores data at teardown.
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

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


def admin_s():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    j = r.json()
    tok = j.get("access_token") or j.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    s.headers["X-CSRF-Token"] = j.get("csrf_token", "")
    return s


def vendor_s(email):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    j = r.json()
    if j.get("csrf_token"):
        s.headers["X-CSRF-Token"] = j["csrf_token"]
    tok = j.get("access_token") or j.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


def staff_s(email):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": PW, "active_role": "committee_member"})
    assert r.status_code == 200, r.text
    j = r.json()
    tok = j.get("access_token") or j.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    s.headers["X-CSRF-Token"] = j.get("csrf_token", "")
    return s


@pytest.fixture(scope="module", autouse=True)
def setup():
    S["orig_bid"] = DB.bids.find_one({"_id": ObjectId(NF_BID)}, {"status": 1, "awarded_at": 1})
    S["orig_notice"] = DB.notices.find_one({"notice_ref": REF}, {"standstill_days": 1, "award_suspended": 1, "re_evaluation_required": 1})
    S["corr_before"] = [c["_id"] for c in DB.corrigenda.find({"notice_ref": REF}, {"_id": 1})]
    S["ft"] = DB.fee_types.find_one({"code": "registration"})
    S["admin"] = admin_s()
    S["k"] = vendor_s("kestrel@demo.pmcmanagers.com")
    S["nf"] = vendor_s("northfield@demo.pmcmanagers.com")
    S["c1"] = staff_s("committee1@demo.pmcmanagers.com")
    S["c2"] = staff_s("committee2@demo.pmcmanagers.com")
    yield
    DB.bid_challenges.delete_many({"notice_ref": REF})
    DB.corrigenda.delete_many({"notice_ref": REF, "_id": {"$nin": S["corr_before"]}})
    DB.notices.update_one({"notice_ref": REF}, {"$unset": {"standstill_days": "", "award_suspended": "", "award_suspended_at": "", "re_evaluation_required": ""}})
    ob = S["orig_bid"]
    DB.bids.update_one({"_id": ob["_id"]}, {"$set": {"status": ob["status"], "awarded_at": ob["awarded_at"]},
                                            "$unset": {"award_withdrawn_at": "", "award_withdrawn_reason": ""}})
    DB.fee_types.update_one({"_id": S["ft"]["_id"]}, {"$set": {"show_on_pricing": bool(S["ft"].get("show_on_pricing"))}})


def ft_payload(ft, show):
    keys = ["name", "timing", "calc", "amount_mode", "category_scope", "billing", "used_in_tender_builder",
            "country_scope", "countries", "categories", "is_active", "description"]
    p = {k: ft.get(k) for k in keys if ft.get(k) is not None}
    p["show_on_pricing"] = show
    return p


# ---------- Pricing ----------
class TestPricing:
    def test_tick_and_public(self):
        a = S["admin"]
        r = a.patch(f"{API}/fee-types/{S['ft']['_id']}", json=ft_payload(S["ft"], True))
        assert r.status_code == 200, r.text
        assert r.json()["show_on_pricing"] is True
        p = requests.get(f"{API}/fee-types/public/pricing")
        assert p.status_code == 200
        fees = p.json()["fees"]
        codes = [f["code"] for f in fees]
        assert "registration" in codes
        assert "emd" not in codes  # unticked
        reg = [f for f in fees if f["code"] == "registration"][0]
        assert reg["rules"] and reg["rules"][0]["currency"] == "KZT"
        assert reg["rules"][0]["countries"] == ["KZ"]
        assert reg["rules"][0]["slabs"][0]["fixed_amount"] == 15000.0

    def test_untick_removes(self):
        r = S["admin"].patch(f"{API}/fee-types/{S['ft']['_id']}", json=ft_payload(S["ft"], False))
        assert r.status_code == 200
        codes = [f["code"] for f in requests.get(f"{API}/fee-types/public/pricing").json()["fees"]]
        assert "registration" not in codes


# ---------- Standstill + contract gates ----------
class TestStandstill:
    def test_list(self):
        r = S["admin"].get(f"{API}/bid-challenges")
        assert r.status_code == 200, r.text
        t = [x for x in r.json()["tenders"] if x["notice_ref"] == REF]
        assert t, "DEMO-TND-AWD missing from tenders"
        t = t[0]
        assert t["days"] == 10 and t["running"] is True
        assert t["ends_at"].startswith("2026-11-11")
        assert "standstill" in (t["contract_block"] or "").lower()

    def test_list_vendor_forbidden(self):
        assert S["k"].get(f"{API}/bid-challenges").status_code in (401, 403)

    def test_contract_gates(self):
        a = S["admin"]
        r = a.post(f"{API}/contracts", json={"notice_ref": REF, "bid_id": NF_BID, "vendor_id": "6ae6a2145b8d447ffcaf5a03",
                                             "title": "TEST_contract", "value": 1, "start_date": "2026-12-01", "end_date": "2027-12-01"})
        assert r.status_code == 409, r.text
        assert "standstill" in r.json()["detail"].lower()
        r = a.post(f"{API}/docusign/awards/{NF_BID}/contract/envelope", json={"signer_name": "TEST Signer", "signer_email": "test_signer@example.com"})
        assert r.status_code == 409, r.text
        r = S["nf"].post(f"{API}/docusign/mine/awards/{NF_BID}/contract/envelope", json={"signer_name": "TEST Signer", "signer_email": "test_signer@example.com"})
        assert r.status_code == 409, r.text

    def test_change_standstill(self):
        a = S["admin"]
        r = a.put(f"{API}/bid-challenges/notice/{REF}/standstill", json={"days": 12, "reason": "TEST_ extend for review"})
        assert r.status_code == 200, r.text
        assert r.json()["days"] == 12 and r.json()["ends_at"].startswith("2026-11-13")
        c = DB.corrigenda.find_one({"notice_ref": REF, "title": "Standstill period changed from 10 to 12 days"})
        assert c and c["field_amendments"][0] == {"field_key": "standstill_days", "before": 10, "after": 12}
        assert DB.notices.find_one({"notice_ref": REF})["standstill_days"] == 12
        r = a.put(f"{API}/bid-challenges/notice/{REF}/standstill", json={"days": 12, "reason": "TEST_ same"})
        assert r.status_code == 409
        r = S["c1"].put(f"{API}/bid-challenges/notice/{REF}/standstill", json={"days": 14, "reason": "TEST_ staff"})
        assert r.status_code == 403
        r = a.put(f"{API}/bid-challenges/notice/{REF}/standstill", json={"days": 10, "reason": "TEST_ revert"})
        assert r.status_code == 200


# ---------- Challenge lifecycle ----------
def lodge(details="TEST_ The evaluation ignored our ISO certificate entirely."):
    return S["k"].post(f"{API}/bid-challenges/mine/{KESTREL_BID}", json={"grounds": "evaluation", "details": details})


def vote(who, cid, d):
    return S[who].post(f"{API}/bid-challenges/{cid}/vote", json={"decision": d, "comment": f"TEST_ {d}"})


class TestLifecycle:
    def test_01_lodge_rules(self):
        st = S["k"].get(f"{API}/bid-challenges/mine/{KESTREL_BID}")
        assert st.status_code == 200 and st.json()["can_lodge"] is True
        assert lodge("short").status_code == 422
        assert S["k"].get(f"{API}/bid-challenges/mine/{NF_BID}").status_code == 404
        nf = S["nf"].get(f"{API}/bid-challenges/mine/{NF_BID}").json()
        assert nf["can_lodge"] is False and "awarded" in nf["why_not"].lower()
        assert S["nf"].post(f"{API}/bid-challenges/mine/{NF_BID}", json={"grounds": "price", "details": "x" * 30}).status_code == 409
        r = lodge()
        assert r.status_code == 200, r.text
        S["cid1"] = r.json()["id"]
        assert r.json()["status"] == "lodged"
        r2 = lodge()
        assert r2.status_code == 409

    def test_02_vote_upheld_tie(self):
        cid = S["cid1"]
        assert vote("admin", cid, "uphold").status_code == 403  # admin not on committee
        lst = S["c1"].get(f"{API}/bid-challenges").json()["challenges"]
        row = [x for x in lst if x["id"] == cid][0]
        assert row["i_can_vote"] is True and row["committee_size"] == 2
        assert vote("c1", cid, "uphold").json()["status"] == "under_review"
        assert vote("c1", cid, "dismiss").status_code == 409
        r = vote("c2", cid, "dismiss")
        assert r.json()["status"] == "upheld"
        assert DB.notices.find_one({"notice_ref": REF})["award_suspended"] is True
        v = S["k"].get(f"{API}/bid-challenges/mine/{KESTREL_BID}").json()["challenges"][0]
        assert "votes" not in v and v["committee_votes"] == {"uphold": 1, "dismiss": 1}
        r = S["admin"].post(f"{API}/contracts", json={"notice_ref": REF, "bid_id": NF_BID, "vendor_id": "x", "title": "T", "value": 1,
                                                      "start_date": "2026-12-01", "end_date": "2027-01-01"})
        assert r.status_code == 409 and "suspended" in r.json()["detail"].lower()

    def test_03_meeting_and_confirm(self):
        cid = S["cid1"]
        r = S["c1"].post(f"{API}/bid-challenges/{cid}/meeting", json={"scheduled_at": iso(days=-1), "location": "Room 1"})
        assert r.status_code == 422
        r = S["c1"].post(f"{API}/bid-challenges/{cid}/meeting", json={"scheduled_at": iso(days=2), "location": "Board Room"})
        assert r.status_code == 200, r.text
        m = r.json()["meeting"]
        assert r.json()["status"] == "meeting_scheduled"
        for e in ["committee1@demo.pmcmanagers.com", "committee2@demo.pmcmanagers.com",
                  "kestrel@demo.pmcmanagers.com", "northfield@demo.pmcmanagers.com"]:
            assert e in m["attendees"]
        S["attendees"] = m["attendees"]
        res = {"outcome": "confirm_award", "minutes": "TEST_ Meeting agreed the award stands."}
        assert S["admin"].post(f"{API}/bid-challenges/{cid}/resolution", json=res).status_code == 409
        DB.bid_challenges.update_one({"_id": ObjectId(cid)}, {"$set": {"meeting.scheduled_at": iso(hours=-1)}})
        assert S["c1"].post(f"{API}/bid-challenges/{cid}/resolution", json=res).status_code == 403
        r = S["admin"].post(f"{API}/bid-challenges/{cid}/resolution", json=res)
        assert r.status_code == 200 and r.json()["status"] == "resolved"
        assert DB.notices.find_one({"notice_ref": REF})["award_suspended"] is False
        t = [x for x in S["admin"].get(f"{API}/bid-challenges").json()["tenders"] if x["notice_ref"] == REF][0]
        assert "standstill" in t["contract_block"].lower()

    def test_04_vendor_view_leak(self):
        v = S["k"].get(f"{API}/bid-challenges/mine/{KESTREL_BID}").json()["challenges"][0]
        blob = str(v)
        S["leak"] = [e for e in ("committee1@demo", "committee2@demo") if e in blob]
        print("VENDOR VIEW LEAK:", S["leak"], v.get("meeting"))

    def test_05_dismiss_appeal_dismiss(self):
        r = lodge()
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        vote("c1", cid, "dismiss")
        r = vote("c2", cid, "dismiss")
        assert r.json()["status"] == "dismissed"
        dl = datetime.fromisoformat(r.json()["appeal_deadline"])
        assert timedelta(days=4, hours=23) < dl - datetime.now(timezone.utc) <= timedelta(days=5)
        k = S["k"]
        assert k.post(f"{API}/bid-challenges/mine/challenge/{cid}/appeal", json={"reason": "short"}).status_code == 422
        assert S["nf"].post(f"{API}/bid-challenges/mine/challenge/{cid}/appeal", json={"reason": "x" * 30}).status_code == 404
        r = k.post(f"{API}/bid-challenges/mine/challenge/{cid}/appeal", json={"reason": "TEST_ The committee missed key evidence."})
        assert r.status_code == 200 and r.json()["status"] == "appealed"
        assert k.post(f"{API}/bid-challenges/mine/challenge/{cid}/appeal", json={"reason": "TEST_ again again again again"}).status_code == 409
        row = [x for x in S["admin"].get(f"{API}/bid-challenges").json()["challenges"] if x["id"] == cid][0]
        assert row["i_can_decide_appeal"] is True
        d = {"decision": "dismiss", "reason": "TEST_ final dismissal"}
        assert S["c1"].post(f"{API}/bid-challenges/{cid}/appeal-decision", json=d).status_code == 403
        r = S["admin"].post(f"{API}/bid-challenges/{cid}/appeal-decision", json=d)
        assert r.status_code == 200 and r.json()["status"] == "closed"
        assert S["admin"].post(f"{API}/bid-challenges/{cid}/appeal-decision", json=d).status_code == 409

    def test_06_dismiss_appeal_uphold(self):
        cid = lodge().json()["id"]
        vote("c1", cid, "dismiss")
        vote("c2", cid, "dismiss")
        # contract blocked inside appeal window (independently of standstill)
        S["k"].post(f"{API}/bid-challenges/mine/challenge/{cid}/appeal", json={"reason": "TEST_ appeal for uphold path"})
        r = S["admin"].post(f"{API}/bid-challenges/{cid}/appeal-decision", json={"decision": "uphold", "reason": "TEST_ appeal upheld"})
        assert r.status_code == 200 and r.json()["status"] == "upheld"
        assert DB.notices.find_one({"notice_ref": REF})["award_suspended"] is True
        S["cid3"] = cid

    def test_07_re_evaluate(self):
        cid = S["cid3"]
        S["c1"].post(f"{API}/bid-challenges/{cid}/meeting", json={"scheduled_at": iso(days=1), "location": "Video call"})
        DB.bid_challenges.update_one({"_id": ObjectId(cid)}, {"$set": {"meeting.scheduled_at": iso(hours=-1)}})
        r = S["admin"].post(f"{API}/bid-challenges/{cid}/resolution", json={"outcome": "re_evaluate", "minutes": "TEST_ Re-evaluate all bids."})
        assert r.status_code == 200, r.text
        b = DB.bids.find_one({"_id": ObjectId(NF_BID)})
        assert b["status"] == "accounting_cleared" and "awarded_at" not in b
        n = DB.notices.find_one({"notice_ref": REF})
        assert n["re_evaluation_required"] is True and n["award_suspended"] is False
        r = S["admin"].post(f"{API}/contracts", json={"notice_ref": REF, "bid_id": NF_BID, "vendor_id": "x", "title": "T", "value": 1,
                                                      "start_date": "2026-12-01", "end_date": "2027-01-01"})
        assert r.status_code == 400  # no longer awarded

    def test_08_dismissed_window_blocks_after_standstill(self):
        # restore award, move standstill to past, dismissed challenge inside appeal window must still block
        ob = S["orig_bid"]
        DB.bids.update_one({"_id": ob["_id"]}, {"$set": {"status": "awarded", "awarded_at": iso(days=-20)}})
        DB.bid_challenges.insert_one({"challenge_ref": "CH-TEST", "notice_ref": REF, "vendor_id": "x", "status": "dismissed",
                                      "appeal_deadline": iso(days=3), "votes": {}, "created_at": iso()})
        r = S["admin"].post(f"{API}/docusign/awards/{NF_BID}/contract/envelope", json={"signer_name": "TEST Signer", "signer_email": "test_signer@example.com"})
        assert r.status_code == 409 and "appeal window" in r.json()["detail"]
        DB.bid_challenges.update_one({"challenge_ref": "CH-TEST"}, {"$set": {"appeal_deadline": iso(days=-1)}})
        t = [x for x in S["admin"].get(f"{API}/bid-challenges").json()["tenders"] if x["notice_ref"] == REF][0]
        assert t["contract_block"] is None and t["running"] is False
        # standstill ended -> change rejected
        r = S["admin"].put(f"{API}/bid-challenges/notice/{REF}/standstill", json={"days": 30, "reason": "TEST_ after end"})
        print("change after standstill ended:", r.status_code, r.text[:150])
        DB.bids.update_one({"_id": ob["_id"]}, {"$set": {"awarded_at": ob["awarded_at"]}})
