# v72g: consortium escrow payment split on release + admin result-notice delivery log / resend.
import uuid

import pytest
from bson import ObjectId

from test_v72e_partner_consortium_notices import API, DB, _login_staff, _login_vendor, _now

RID = uuid.uuid4().hex[:6].upper()
NREF = f"TEST-V72G-{RID}"
S = {}
SIG = lambda a: {"pmc": {"action": a, "signed_at": _now()}, "escrow_institution": {"action": a, "signed_at": _now()}}


def _cons(escrow_mode="shared", deposit_mode="lead_pays", lead=50.0, shares=(30.0, 20.0)):
    return {"id": "c" + RID, "name": f"TEST Team {RID}", "lead_share_pct": lead, "escrow_mode": escrow_mode,
            "deposit_mode": deposit_mode,
            "members": [{"vendor_id": f"m{i}{RID}", "company_name": f"TEST Member {i}", "email": f"test_m{i}_{RID.lower()}@example.com",
                         "vendor_ref": f"VEN-TM{i}", "share_pct": s} for i, s in enumerate(shares)]}


def _bid(tag, cons=None, status="awarded"):
    ref = f"TEST-BID-{RID}-{tag}"
    DB.bids.insert_one({"bid_ref": ref, "notice_ref": NREF, "vendor_id": "lead" + RID, "vendor_email": f"test_lead_{RID.lower()}@example.com",
                        "vendor_ref": "VEN-TLEAD", "company_name": "TEST Lead Co", "status": status, "consortium": cons,
                        "submitted_at": _now()})
    return ref


def _tx(bid_ref, amount=1000.0, action=None):
    r = DB.escrow_transactions.insert_one({"bid_ref": bid_ref, "notice_ref": NREF, "amount": amount, "currency": "USD",
                                           "status": "awaiting_signatures" if action else "received",
                                           "signatures": SIG(action) if action else {}, "audit_trail": [],
                                           "created_at": _now(), "created_by": "TEST"})
    return str(r.inserted_id)


@pytest.fixture(scope="module", autouse=True)
def setup():
    yield
    DB.bids.delete_many({"notice_ref": NREF})
    DB.escrow_transactions.delete_many({"notice_ref": NREF})
    DB.notifications.delete_many({"related_notice_ref": NREF})
    DB.notices.delete_many({"notice_ref": NREF})


@pytest.fixture(scope="module")
def admin():
    return _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


@pytest.fixture(scope="module")
def reviewer():
    return _login_staff("reviewerqa@pmcmanagers.com", "Reviewer@12345", "reviewer")


def _rel(admin, tid, action):
    return admin.post(f"{API}/escrow/transactions/{tid}/release", json={"action": action, "memo": "TEST"})


# ---- Split preview + release_to_contractor ----
class TestSplitContractor:
    def test_preview_before_release(self, admin):
        S["b1"] = _bid("C1", _cons(lead=33.33, shares=(33.33, 33.34)))
        S["t1"] = _tx(S["b1"], amount=1000.01, action="release_to_contractor")
        r = admin.get(f"{API}/escrow/transactions/{S['t1']}/consortium-split")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["recorded"] is False and d["applies"] is True
        c = d["preview"]["release_to_contractor"]
        assert round(sum(x["amount"] for x in c["lines"]), 2) == 1000.01
        v = d["preview"]["release_to_vendor"]
        assert len(v["lines"]) == 1 and v["lines"][0]["share_pct"] == 100 and v["lines"][0]["lead"]

    def test_release_records_split(self, admin):
        r = _rel(admin, S["t1"], "release_to_contractor")
        assert r.status_code == 200, r.text
        tx = DB.escrow_transactions.find_one({"_id": ObjectId(S["t1"])})
        sp = tx["consortium_split"]
        assert sp["action"] == "release_to_contractor" and sp["escrow_mode"] == "shared" and sp["total"] == 1000.01
        assert len(sp["lines"]) == 3 and sp["lines"][0]["lead"] is True
        assert round(sum(x["amount"] for x in sp["lines"]), 2) == 1000.01
        assert [x["amount"] for x in sp["lines"][1:]] == [333.30, 333.40]
        assert sp["lines"][0]["amount"] == 333.31  # remainder to lead
        for x in sp["lines"]:
            assert x["status"] == "pending_payout" and x["currency"] == "USD" and "shared escrow" in x["route"]
            assert x["email"] and x["vendor_id"] and x["company"]
        assert any(e.get("event") == "consortium_split" for e in tx["audit_trail"])

    def test_get_after_release(self, admin):
        d = admin.get(f"{API}/escrow/transactions/{S['t1']}/consortium-split").json()
        assert d["recorded"] is True and len(d["lines"]) == 3

    def test_second_release_409_split_once(self, admin):
        r = _rel(admin, S["t1"], "release_to_contractor")
        assert r.status_code == 409
        tx = DB.escrow_transactions.find_one({"_id": ObjectId(S["t1"])})
        assert sum(1 for e in tx["audit_trail"] if e.get("event") == "consortium_split") == 1

    def test_mark_paid(self, admin):
        u = f"{API}/escrow/transactions/{S['t1']}/consortium-split"
        assert admin.post(f"{u}/1/paid", json={"reference": "ab"}).status_code == 422
        assert admin.post(f"{u}/9/paid", json={"reference": "WIRE-1"}).status_code == 404
        assert admin.post(f"{u}/-1/paid", json={"reference": "WIRE-1"}).status_code == 404
        r = admin.post(f"{u}/1/paid", json={"reference": "  WIRE-TEST-1 "})
        assert r.status_code == 200, r.text
        ln = r.json()["lines"][1]
        assert ln["status"] == "paid" and ln["paid_ref"] == "WIRE-TEST-1" and ln["paid_by"]
        assert admin.post(f"{u}/1/paid", json={"reference": "WIRE-TEST-2"}).status_code == 409
        tx = DB.escrow_transactions.find_one({"_id": ObjectId(S["t1"])})
        assert tx["consortium_split"]["lines"][1]["status"] == "paid" and tx["consortium_split"]["lines"][0]["status"] == "pending_payout"

    def test_list_splits(self, admin):
        r = admin.get(f"{API}/escrow/consortium-splits")
        assert r.status_code == 200
        assert any(i["tid"] == S["t1"] and i["bid_ref"] == S["b1"] for i in r.json()["items"])


# ---- Refund modes / forfeit / separate / non-consortium ----
class TestSplitModes:
    def test_refund_lead_pays(self, admin):
        b = _bid("R1", _cons(deposit_mode="lead_pays"), status="rejected")
        t = _tx(b, 500, "release_to_vendor")
        assert _rel(admin, t, "release_to_vendor").status_code == 200
        sp = DB.escrow_transactions.find_one({"_id": ObjectId(t)})["consortium_split"]
        assert len(sp["lines"]) == 1 and sp["lines"][0]["lead"] and sp["lines"][0]["amount"] == 500 and sp["lines"][0]["share_pct"] == 100

    def test_refund_each_pays_separate(self, admin):
        b = _bid("R2", _cons(escrow_mode="separate", deposit_mode="each_pays_share"), status="rejected")
        t = _tx(b, 500, "release_to_vendor")
        assert _rel(admin, t, "release_to_vendor").status_code == 200
        sp = DB.escrow_transactions.find_one({"_id": ObjectId(t)})["consortium_split"]
        assert [x["amount"] for x in sp["lines"]] == [250, 150, 100]
        assert sp["escrow_mode"] == "separate" and all("own escrow account" in x["route"] for x in sp["lines"])

    def test_forfeit_no_split(self, admin):
        b = _bid("F1", _cons(), status="rejected")
        t = _tx(b, 500, "forfeit")
        assert _rel(admin, t, "forfeit").status_code == 200
        assert "consortium_split" not in DB.escrow_transactions.find_one({"_id": ObjectId(t)})

    def test_non_consortium(self, admin):
        b = _bid("N1", None)
        t = _tx(b, 500, "release_to_contractor")
        d = admin.get(f"{API}/escrow/transactions/{t}/consortium-split").json()
        assert d == {"recorded": False, "applies": False}
        assert _rel(admin, t, "release_to_contractor").status_code == 200
        assert "consortium_split" not in DB.escrow_transactions.find_one({"_id": ObjectId(t)})
        assert admin.post(f"{API}/escrow/transactions/{t}/consortium-split/0/paid", json={"reference": "WIRE-1"}).status_code == 404

    def test_bad_tid_and_rbac(self, admin, reviewer):
        assert admin.get(f"{API}/escrow/transactions/{'0' * 24}/consortium-split").status_code == 404
        assert admin.get(f"{API}/escrow/transactions/bad/consortium-split").status_code == 404
        assert reviewer.get(f"{API}/escrow/transactions/{S['t1']}/consortium-split").status_code == 403
        assert reviewer.post(f"{API}/escrow/transactions/{S['t1']}/consortium-split/2/paid", json={"reference": "WIRE-1"}).status_code == 403

    def test_leave_ui_fixture(self):
        # pending consortium tx for UI check (preview) — cleaned with notice_ref
        S["ui_bid"] = _bid("UI", _cons())
        S["ui_tx"] = _tx(S["ui_bid"], 900)
        open("/tmp/v72g_ui.txt", "w").write(f"{S['ui_tx']} {S['t1']} {NREF}")


# ---- Result notices admin ----
class TestResultNotices:
    def test_seed_and_list(self, admin, reviewer):
        b = DB.bids.find_one({"bid_ref": S["b1"]})
        S["nbid"] = str(b["_id"])
        DB.bids.update_one({"_id": b["_id"]}, {"$set": {"qualification_notices": [
            {"kind": "preliminary", "at": _now(), "status": "qualified", "subject": "[PMC] TEST subj", "body": "<p>TEST body</p>",
             "emails": [{"to": "testvendor@pmcmanagers.com", "sent": False}, {"to": "test_x@example.com", "sent": True}]},
            {"kind": "final", "at": _now(), "status": "qualified", "emails": [{"to": "testvendor@pmcmanagers.com", "sent": False}]}]}})
        for s in (admin, reviewer):
            r = s.get(f"{API}/tender-criteria/{NREF}/result-notices")
            assert r.status_code == 200, r.text
            it = [i for i in r.json()["items"] if i["bid_id"] == S["nbid"]][0]
            assert it["consortium"] and [n["idx"] for n in it["notices"]] == [0, 1]
            assert it["notices"][0]["emails"][0]["to"] == "testvendor@pmcmanagers.com" and "body" not in it["notices"][0]

    def test_resend_errors(self, admin, reviewer):
        u = f"{API}/tender-criteria/{NREF}/result-notices/resend"
        assert admin.post(u, json={"bid_id": S["nbid"], "idx": 0, "email": "nobody@example.com"}).status_code == 422
        assert admin.post(u, json={"bid_id": S["nbid"], "idx": 5, "email": "testvendor@pmcmanagers.com"}).status_code == 404
        assert admin.post(u, json={"bid_id": "bad", "idx": 0, "email": "testvendor@pmcmanagers.com"}).status_code == 404
        assert admin.post(u, json={"bid_id": S["nbid"], "idx": 1, "email": "testvendor@pmcmanagers.com"}).status_code == 409
        assert reviewer.post(u, json={"bid_id": S["nbid"], "idx": 0, "email": "testvendor@pmcmanagers.com"}).status_code == 403

    def test_resend_ok(self, admin):
        r = admin.post(f"{API}/tender-criteria/{NREF}/result-notices/resend",
                       json={"bid_id": S["nbid"], "idx": 0, "email": "TestVendor@pmcmanagers.com"})
        S["resend_status"] = r.status_code
        assert r.status_code == 200, r.text
        row = DB.bids.find_one({"_id": ObjectId(S["nbid"])})["qualification_notices"][0]["emails"][0]
        assert row["resend_count"] == 1 and row["resent_at"] and row["resent_by"]
        if r.json()["ok"]:
            assert row["sent"] is True and row["last_error"] is None
        else:
            assert row["sent"] is False and row["last_error"] and r.json()["error"]

    def test_vendor_mine_stripped(self):
        v = _login_vendor("testvendor@pmcmanagers.com", "Vendor@12345")
        vid = str(DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})["_id"])
        DB.bids.update_one({"_id": ObjectId(S["nbid"])}, {"$set": {"vendor_id": vid}})
        r = v.get(f"{API}/tender-criteria/results/vendor/mine")
        assert r.status_code == 200
        it = [i for i in r.json()["items"] if i["bid_id"] == S["nbid"]][0]
        assert not {"emails", "body", "subject"} & set(it["notice"]) and it["history"] == ["preliminary", "final"]
