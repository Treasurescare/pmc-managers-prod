# v72f: retest of iteration_151 fixes — withdraw releases consortium, each+lte team value, no signature tokens,
# remove-member 404, terms share validation, KYC gate for members, per-recipient email log in result notices.
import asyncio
import sys
import uuid

import pytest
from bson import ObjectId

from test_v72e_partner_consortium_notices import (API, DB, DEMO_PW, YRS, _bid_body, _login_staff, _login_vendor,
                                                  _now, _submit, _upload, _vid)

RID = uuid.uuid4().hex[:6].upper()
REF, KREF, NREF = f"TEST-V72F-{RID}", f"TEST-V72FK-{RID}", f"TEST-V72FN-{RID}"
S = {}


def _notice(ref, **extra):
    DB.notices.insert_one({"notice_ref": ref, "title": f"TEST v72f {ref}", "is_published": True, "kyc_bypass": True,
                           "consortium_allowed": True, "budget_amount": 1000.0, "budget_currency": "USD",
                           "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"},
                           "submission_deadline": _now(days=3), "bid_opening_date": _now(days=4), "created_at": _now(), **extra})


@pytest.fixture(scope="module", autouse=True)
def setup():
    _notice(REF)
    _notice(KREF, kyc_bypass=False)
    _notice(NREF)
    S["ks_kyc"] = DB.vendors.find_one({"email": "kestrel@demo.pmcmanagers.com"}, {"kyc_status": 1, "kyc": 1})
    yield
    for ref in (REF, KREF, NREF):
        for coll in ("bids", "notices", "consortia"):
            DB[coll].delete_many({"notice_ref": ref})
        DB.notifications.delete_many({"related_notice_ref": ref})
    DB.uploads.delete_many({"key": {"$regex": "TESTCN"}})
    k = S["ks_kyc"]
    DB.vendors.update_one({"_id": k["_id"]}, {"$set": {"kyc_status": k.get("kyc_status")}})


@pytest.fixture(scope="module")
def nf():
    return _login_vendor("northfield@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def bw():
    return _login_vendor("brightwater@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def ks():
    return _login_vendor("kestrel@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def admin():
    return _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


def _body(s, cid=None):
    b = _bid_body(s, 1, True, 1, 1, cid=cid)
    b["notice_ref"], b["criteria_answers"] = REF, []
    return b


# ---- Withdraw releases consortium (HIGH fix) ----
class TestWithdrawRelease:
    def test_build_and_bid(self, nf, bw):
        r = nf.post(f"{API}/consortia", json={"notice_ref": REF, "name": "TEST F team"})
        assert r.status_code == 200, r.text
        S["cid"] = cid = r.json()["id"]
        S["bwid"] = bwid = _vid("brightwater@demo.pmcmanagers.com")
        assert nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": "VEN-DEMO2", "share_pct": 40}).status_code == 200
        assert bw.post(f"{API}/consortia/{cid}/respond", json={"accept": True}).status_code == 200
        r = nf.put(f"{API}/consortia/{cid}/terms", json={"lead_share_pct": 60, "shares": {bwid: 40}, "escrow_mode": "shared", "deposit_mode": "lead_pays"})
        assert r.status_code == 200, r.text
        assert nf.post(f"{API}/consortia/{cid}/agreement/sign", json={"consent": True, "signer_name": "NF Signer"}).status_code == 200
        assert bw.post(f"{API}/consortia/{cid}/agreement/sign", json={"consent": True, "signer_name": "BW Signer"}).status_code == 200
        S["bid1"] = _submit(nf, _body(nf, cid))
        c = DB.consortia.find_one({"_id": ObjectId(cid)})
        assert c["status"] == "bid_submitted" and c["bid_id"] == S["bid1"]

    def test_no_tokens_in_views(self, nf, bw, admin):
        r = admin.get(f"{API}/consortia/admin/by-notice/{REF}")
        assert r.status_code == 200, r.text
        assert r.json()["items"] and '"token"' not in r.text, r.text[:400]
        for s in (nf, bw):
            r = s.get(f"{API}/consortia/mine", params={"notice_ref": REF})
            assert r.status_code == 200 and "NF Signer" in r.text and '"token"' not in r.text, r.text[:300]
        # bid snapshot visible to lead (probe)
        r = nf.get(f"{API}/bids/{S['bid1']}")
        S["bid_view_has_token"] = (r.status_code, '"token"' in r.text)

    def test_withdraw_returns_to_forming(self, nf):
        assert nf.post(f"{API}/bids/{S['bid1']}/withdraw").status_code == 200
        c = DB.consortia.find_one({"_id": ObjectId(S["cid"])})
        assert c["status"] == "forming" and "bid_id" not in c

    def test_member_still_blocked_while_forming(self, bw):
        r = bw.post(f"{API}/bids", json=_body(bw))
        assert r.status_code == 409

    def test_lead_can_rebid_via_consortium(self, nf):
        r = nf.post(f"{API}/bids", json=_body(nf, S["cid"]))
        assert r.status_code == 200, r.text
        S["bid2"] = r.json()["id"]
        c = DB.consortia.find_one({"_id": ObjectId(S["cid"])})
        assert c["status"] == "bid_submitted" and c["bid_id"] == S["bid2"]
        assert nf.post(f"{API}/bids/{S['bid2']}/withdraw").status_code == 200

    def test_lead_withdraws_consortium_then_member_bids_alone(self, nf, bw):
        r = nf.post(f"{API}/consortia/{S['cid']}/withdraw")
        assert r.status_code == 200, r.text
        r = bw.post(f"{API}/bids", json=_body(bw))
        assert r.status_code == 200, r.text
        r = nf.post(f"{API}/bids", json=_body(nf))
        assert r.status_code == 200, r.text


# ---- members endpoints: 404, 422, KYC ----
class TestMembersValidation:
    def test_remove_non_member_404_and_terms_unknown_422(self, nf, bw):
        r = nf.post(f"{API}/consortia", json={"notice_ref": NREF, "name": "TEST N team"})
        assert r.status_code == 200, r.text
        cid = S["ncid"] = r.json()["id"]
        r = nf.delete(f"{API}/consortia/{cid}/members/{'0' * 24}")
        assert r.status_code == 404, r.text
        nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": "VEN-DEMO2", "share_pct": 40})
        r = nf.put(f"{API}/consortia/{cid}/terms", json={"lead_share_pct": 60, "shares": {"ffffffffffffffffffffffff": 40},
                                                         "escrow_mode": "shared", "deposit_mode": "lead_pays"})
        assert r.status_code == 422, r.text
        r = nf.delete(f"{API}/consortia/{cid}/members/{S['bwid']}")
        assert r.status_code == 200 and not r.json()["members"], r.text

    def test_kyc_gate(self, nf):
        DB.vendors.update_one({"email": "kestrel@demo.pmcmanagers.com"}, {"$set": {"kyc_status": "pending"}})
        r = nf.post(f"{API}/consortia", json={"notice_ref": KREF, "name": "TEST K team"})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        r = nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": "VEN-DEMO3", "share_pct": 40})
        assert r.status_code == 409 and "KYC" in r.text, r.text
        r = nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": "VEN-DEMO2", "share_pct": 40})
        assert r.status_code == 200, r.text
        # bypass notice allows unverified supplier
        ncid = S["ncid"]
        r = nf.post(f"{API}/consortia/{ncid}/members", json={"email_or_ref": "VEN-DEMO3", "share_pct": 40})
        assert r.status_code == 200, r.text


# ---- Pure evaluator: each + lte ----
class TestTeamValue:
    def test_each_lte_uses_max(self):
        sys.path.insert(0, "/app/backend")
        from routers.tender_criteria import evaluate
        cons = {"members": [{"vendor_id": "m1", "company_name": "M1"}, {"vendor_id": "m2", "company_name": "M2"}]}
        crit = [{**YRS, "id": "lte1", "operator": "lte", "threshold": 10, "consortium_rule": "each"}]
        q = evaluate(crit, [{"criterion_id": "lte1", "value": 3, "members": {"m1": 8, "m2": 5}}], [], cons, "L")
        assert q["results"][0]["value"] == 8 and q["results"][0]["result"] == "pass"
        q = evaluate(crit, [{"criterion_id": "lte1", "value": 3, "members": {"m1": 12, "m2": 5}}], [], cons, "L")
        assert q["results"][0]["value"] == 12 and q["results"][0]["result"] == "fail"
        gte = [{**YRS, "id": "g1", "operator": "gte", "threshold": 1, "consortium_rule": "each"}]
        assert evaluate(gte, [{"criterion_id": "g1", "value": 3, "members": {"m1": 8, "m2": 5}}], [], cons, "L")["results"][0]["value"] == 3


# ---- send_result_notices email log + my_results strip ----
class TestNoticeEmails:
    def test_emails_logged_and_stripped(self, bw):
        sys.path.insert(0, "/app/backend")
        import emails
        from routers import tender_criteria as tc
        b = DB.bids.find_one({"notice_ref": REF, "vendor_id": S["bwid"], "status": {"$ne": "withdrawn"}})
        DB.bids.update_one({"_id": b["_id"]}, {"$set": {"qualification": {"system_status": "qualified", "results": []}}})
        calls = []

        async def fake(to, subject, html, *a, **k):
            calls.append(to)
            return to.startswith("brightwater")
        orig = emails.send_email
        emails.send_email = fake
        try:
            sent = asyncio.run(tc.send_result_notices(REF, False))
        finally:
            emails.send_email = orig
        assert sent >= 1 and "brightwater@demo.pmcmanagers.com" in calls
        b = DB.bids.find_one({"_id": b["_id"]})
        assert b["qualification_notices"][-1]["emails"] == [{"to": "brightwater@demo.pmcmanagers.com", "sent": True}]
        r = bw.get(f"{API}/tender-criteria/results/vendor/mine")
        items = [x for x in r.json()["items"] if x["notice_ref"] == REF]
        assert items and "emails" not in items[0]["notice"] and items[0]["notice"]["qualified_count"] >= 1


def test_report_probe():
    print("PROBE", S.get("bid_view_has_token"))
