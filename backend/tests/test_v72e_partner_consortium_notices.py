# v72e: Partner draft fix (resend/invite/admin edit), consortium settings + flow + bid, Stage 2 consortium rules, bidder result notices.
import os
import sys
import time
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
E2E, NOCONS = f"TEST-CONS-{RID}", f"TEST-NOCONS-{RID}"
DEMO_PW = "Demo@Pmc2026"
S = {}

TURN = {"id": "mpturn01", "title": "Average annual turnover", "answer_type": "number", "operator": "gte",
        "threshold": 1000000, "unit": "USD", "kind": "must_pass", "consortium_rule": "lead"}
ISO = {"id": "mpiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass", "consortium_rule": "each"}
YRS = {"id": "mpyrs001", "title": "Years in business", "answer_type": "number", "operator": "gte", "threshold": 3,
       "unit": "years", "kind": "must_pass", "consortium_rule": "each"}
STAFF = {"id": "scstaff1", "title": "Qualified key staff", "answer_type": "number", "operator": "gte", "threshold": 5,
         "unit": "staff", "kind": "scored", "max_points": 10, "scoring": "auto", "full_points_at": 15, "consortium_rule": "combined"}
CRIT = [TURN, ISO, YRS, STAFF]
AG = {k: f"test_{k}_{RID.lower()}@example.com" for k in ("inv", "draft", "appr", "rej", "clar")}


def _now(**kw):
    return (datetime.now(timezone.utc) + timedelta(**kw)).isoformat()


def _vid(email):
    return str(DB.vendors.find_one({"email": email})["_id"])


def _cleanup():
    for ref in (E2E, NOCONS):
        for coll in ("bids", "notices", "committees", "opening_records", "consortia"):
            DB[coll].delete_many({"notice_ref": ref})
        DB.notifications.delete_many({"related_notice_ref": ref})
    DB.uploads.delete_many({"key": {"$regex": f"TESTCN{RID}"}})
    DB.agents.delete_many({"email": {"$in": list(AG.values())}})


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
    S["orig_settings"] = DB.platform_settings.find_one({"_id": "consortium"})
    base = {"is_published": True, "kyc_bypass": True, "category": "", "budget_amount": 100000.0, "budget_currency": "USD",
            "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"}, "created_at": _now(),
            "submission_deadline": _now(days=3), "bid_opening_date": _now(days=4), "description": "TEST consortium tender"}
    DB.notices.insert_one({**base, "notice_ref": E2E, "title": f"TEST consortium {RID}", "tender_criteria": CRIT})
    DB.notices.insert_one({**base, "notice_ref": NOCONS, "title": f"TEST no consortium {RID}", "tender_criteria": [TURN]})
    c1 = str(DB.admin_users.find_one({"email": "committee1@demo.pmcmanagers.com"})["_id"])
    c2 = str(DB.admin_users.find_one({"email": "committee2@demo.pmcmanagers.com"})["_id"])
    DB.committees.insert_one({"notice_ref": E2E, "chairperson_id": c1, "member_ids": [c2], "status": "open", "quorum": 2,
                              "votes": [], "created_at": _now()})
    now = _now()
    for k, st in (("inv", "invited"), ("draft", "draft"), ("appr", "approved"), ("rej", "rejected"), ("clar", "needs_clarification")):
        r = DB.agents.insert_one({"email": AG[k], "name": f"TEST_{k}", "status": st, "invite_token": f"tok{k}{RID}",
                                  "invite_expires_at": _now(days=1), "created_at": now, "banking": [], "documents": {}, "history": []})
        S[f"ag_{k}"] = str(r.inserted_id)
    yield
    _cleanup()
    if S["orig_settings"]:
        DB.platform_settings.replace_one({"_id": "consortium"}, S["orig_settings"])
    else:
        DB.platform_settings.delete_one({"_id": "consortium"})


@pytest.fixture(scope="module")
def admin():
    return _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


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
def ks():
    return _login_vendor("kestrel@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def c1():
    return _login_staff("committee1@demo.pmcmanagers.com", DEMO_PW, "committee_member")


@pytest.fixture(scope="module")
def c2():
    return _login_staff("committee2@demo.pmcmanagers.com", DEMO_PW, "committee_member")


# ---- Partner draft fix ----
class TestA_Partners:
    def test_resend_invited_new_token(self, admin):
        r = admin.post(f"{API}/admin/agents/{S['ag_inv']}/resend")
        assert r.status_code == 200, r.text
        assert r.json()["kind"] == "invitation" and "email_sent" in r.json()
        assert DB.agents.find_one({"_id": ObjectId(S["ag_inv"])})["invite_token"] != f"tokinv{RID}"

    def test_resend_draft_and_clarify_reminder(self, admin):
        for k in ("draft", "clar"):
            r = admin.post(f"{API}/admin/agents/{S[f'ag_{k}']}/resend")
            assert r.status_code == 200, r.text
            assert r.json()["kind"] == "reminder"

    def test_resend_approved_409(self, admin):
        r = admin.post(f"{API}/admin/agents/{S['ag_appr']}/resend")
        assert r.status_code == 409 and "approved" in r.text

    def test_resend_without_csrf_403(self, admin):
        s = requests.Session()
        s.cookies.update(admin.cookies)
        assert s.post(f"{API}/admin/agents/{S['ag_draft']}/resend").status_code in (401, 403)

    def test_invite_existing_draft_returns_existing(self, admin):
        r = admin.post(f"{API}/admin/agents/invite", json={"email": AG["draft"].upper(), "name": "TEST again"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["existing"] is True and d["kind"] == "reminder" and d["id"] == S["ag_draft"]
        assert "invite_token" not in d and "password_hash" not in d
        assert DB.agents.count_documents({"email": AG["draft"]}) == 1

    def test_invite_existing_invited(self, admin):
        r = admin.post(f"{API}/admin/agents/invite", json={"email": AG["inv"], "name": "TEST again"})
        assert r.status_code == 200 and r.json()["kind"] == "invitation" and r.json()["existing"] is True

    def test_invite_existing_approved_409(self, admin):
        r = admin.post(f"{API}/admin/agents/invite", json={"email": AG["appr"], "name": "TEST again"})
        assert r.status_code == 409 and "already a partner" in r.text

    def test_admin_edit_draft(self, admin):
        body = {"legal_name": "TEST Partner Ltd", "entity_type": "company", "primary_contact_phone": "+44 1234",
                "country": "gb", "city": "London", "address_line1": "1 Road", "postal_code": "N1", "reg_number": "R123",
                "status": "approved", "email": "hack@x.com"}
        r = admin.patch(f"{API}/admin/agents/{S['ag_draft']}/profile", json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["legal_name"] == "TEST Partner Ltd" and d["country"] == "GB" and d["entity_type"] == "company"
        a = DB.agents.find_one({"_id": ObjectId(S["ag_draft"])})
        assert a["status"] == "draft" and a["email"] == AG["draft"]  # non-editable keys ignored
        assert a["history"][-1]["action"] == "admin_edit" and "city" in a["history"][-1]["fields"]

    def test_admin_edit_validation(self, admin):
        assert admin.patch(f"{API}/admin/agents/{S['ag_draft']}/profile", json={"entity_type": "trust"}).status_code == 422
        assert admin.patch(f"{API}/admin/agents/{S['ag_draft']}/profile", json={"foo": "bar"}).status_code == 422
        assert admin.patch(f"{API}/admin/agents/{S['ag_rej']}/profile", json={"city": "X"}).status_code == 409
        assert admin.patch(f"{API}/admin/agents/{'0' * 24}/profile", json={"city": "X"}).status_code == 404


# ---- Consortium settings + criteria fields ----
class TestB_Settings:
    def test_get_default(self):
        r = requests.get(f"{API}/consortia/settings")
        assert r.status_code == 200 and isinstance(r.json()["max_members_default"], int)

    def test_put_bounds(self, admin, tv):
        assert admin.put(f"{API}/consortia/settings", json={"max_members_default": 1}).status_code == 422
        assert admin.put(f"{API}/consortia/settings", json={"max_members_default": 21}).status_code == 422
        assert tv.put(f"{API}/consortia/settings", json={"max_members_default": 6}).status_code in (401, 403)
        r = admin.put(f"{API}/consortia/settings", json={"max_members_default": 7})
        assert r.status_code == 200
        assert requests.get(f"{API}/consortia/settings").json()["max_members_default"] == 7

    def test_criteria_consortium_fields(self, admin):
        live = admin.put(f"{API}/tender-criteria/{E2E}", json={"criteria": CRIT, "consortium_allowed": True})
        assert live.status_code == 409  # published tenders locked
        DB.notices.update_one({"notice_ref": E2E}, {"$set": {"is_published": False}})
        S["unpub"] = True
        assert admin.put(f"{API}/tender-criteria/{E2E}", json={"criteria": CRIT, "consortium_allowed": True,
                                                                "consortium_max_members": 1}).status_code == 422
        r = admin.put(f"{API}/tender-criteria/{E2E}", json={"criteria": CRIT, "consortium_allowed": True, "consortium_max_members": 3})
        assert r.status_code == 200, r.text
        g = admin.get(f"{API}/tender-criteria/{E2E}/admin").json()
        assert g["consortium_allowed"] is True and g["consortium_max_members"] == 3
        assert {c["id"]: c["consortium_rule"] for c in g["criteria"]}["scstaff1"] == "combined"
        DB.notices.update_one({"notice_ref": E2E}, {"$set": {"is_published": True}})
        pub = requests.get(f"{API}/tender-criteria/{E2E}").json()
        S["public_criteria"] = pub
        assert pub.get("consortium_allowed") is True and pub.get("consortium_max_members") == 3


# ---- Consortium flow ----
class TestC_Consortium:
    def test_create_not_allowed_409(self, nf):
        r = nf.post(f"{API}/consortia", json={"notice_ref": NOCONS, "name": "TEST team"})
        assert r.status_code == 409

    def test_create_and_dup(self, nf):
        r = nf.post(f"{API}/consortia", json={"notice_ref": E2E, "name": "TEST Team Alpha"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_lead"] is True and d["max_members"] == 3 and d["ready"] is False
        S["cid"] = d["id"]
        assert nf.post(f"{API}/consortia", json={"notice_ref": E2E, "name": "TEST again"}).status_code == 409

    def test_add_unknown_404(self, nf):
        r = nf.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "nobody_xyz@example.com", "share_pct": 10})
        assert r.status_code == 404

    def test_member_cannot_add(self, bw):
        r = bw.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "VEN-DEMO3", "share_pct": 10})
        assert r.status_code == 404  # not part of it yet

    def test_add_members_and_limit(self, nf):
        r = nf.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "brightwater@demo.pmcmanagers.com",
                                                                  "capability": "Medical", "share_pct": 30})
        assert r.status_code == 200, r.text
        r = nf.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "ven-demo3", "share_pct": 20})
        assert r.status_code == 200, r.text  # by supplier ref, case-insensitive
        assert len(r.json()["members"]) == 2
        r = nf.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "testvendor@pmcmanagers.com", "share_pct": 5})
        assert r.status_code == 409 and "at most 3" in r.text
        assert DB.notifications.count_documents({"related_notice_ref": E2E, "related_type": "consortium"}) == 2

    def test_dup_member_409(self, nf):
        r = nf.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "VEN-DEMO2", "share_pct": 5})
        assert r.status_code == 409

    def test_invited_member_cannot_bid_alone(self, bw):
        r = bw.post(f"{API}/bids", json=_bid_body(bw, 2000000, True, 5, 6))
        assert r.status_code == 409 and "consortium" in r.text.lower(), r.text

    def test_decline_and_sign_blocked(self, ks):
        r = ks.post(f"{API}/consortia/{S['cid']}/respond", json={"accept": False})
        assert r.status_code == 200, r.text
        assert ks.post(f"{API}/consortia/{S['cid']}/respond", json={"accept": True}).status_code == 409
        r = ks.post(f"{API}/consortia/{S['cid']}/agreement/sign", json={"signer_name": "Kes Trel", "consent": True})
        assert r.status_code == 409

    def test_remove_declined(self, nf):
        r = nf.delete(f"{API}/consortia/{S['cid']}/members/{_vid('kestrel@demo.pmcmanagers.com')}")
        assert r.status_code == 200 and len(r.json()["members"]) == 1

    def test_solo_bidder_cannot_join(self, nf, tv):
        S["solo"] = _submit(tv, _bid_body(tv, 400000, True, 5, 8))
        r = nf.post(f"{API}/consortia/{S['cid']}/members", json={"email_or_ref": "VEN-TEST01", "share_pct": 5})
        assert r.status_code == 409 and "alone" in r.text

    def test_accept_issues(self, bw):
        r = bw.post(f"{API}/consortia/{S['cid']}/respond", json={"accept": True})
        assert r.status_code == 200, r.text
        g = bw.get(f"{API}/consortia/mine", params={"notice_ref": E2E}).json()["items"][0]
        assert g["is_lead"] is False and g["ready"] is False
        assert any("100%" in i for i in g["issues"]) and any("escrow" in i for i in g["issues"])

    def test_terms_and_sign(self, nf, bw):
        bwid = _vid("brightwater@demo.pmcmanagers.com")
        assert bw.put(f"{API}/consortia/{S['cid']}/terms", json={"lead_share_pct": 70, "shares": {bwid: 30},
                                                                "escrow_mode": "shared", "deposit_mode": "lead_pays"}).status_code == 403
        assert nf.put(f"{API}/consortia/{S['cid']}/terms", json={"lead_share_pct": 70, "shares": {},
                                                                "escrow_mode": "bogus", "deposit_mode": "lead_pays"}).status_code == 422
        r = nf.put(f"{API}/consortia/{S['cid']}/terms", json={"lead_share_pct": 70, "shares": {bwid: 30},
                                                             "escrow_mode": "separate", "deposit_mode": "each_pays_share"})
        assert r.status_code == 200, r.text
        assert r.json()["issues"] == ["Upload the signed consortium agreement, or have every member sign the standard one"]
        assert nf.post(f"{API}/consortia/{S['cid']}/agreement/sign", json={"signer_name": "Nor Field", "consent": False}).status_code == 422
        assert nf.post(f"{API}/consortia/{S['cid']}/agreement/sign", json={"signer_name": "Nor Field", "consent": True}).status_code == 200
        r = bw.post(f"{API}/consortia/{S['cid']}/agreement/sign", json={"signer_name": "Bri Water", "consent": True})
        assert r.status_code == 200 and r.json()["ready"] is True, r.json()

    def test_terms_reset_signatures_then_upload(self, nf):
        bwid = _vid("brightwater@demo.pmcmanagers.com")
        r = nf.put(f"{API}/consortia/{S['cid']}/terms", json={"lead_share_pct": 70, "shares": {bwid: 30},
                                                             "escrow_mode": "shared", "deposit_mode": "lead_pays"})
        assert r.json()["agreement"]["signatures"] == [] and r.json()["ready"] is False
        assert nf.post(f"{API}/consortia/{S['cid']}/agreement/upload", json={"key": "nope", "filename": "a.pdf"}).status_code == 422
        key = _upload(nf, "agreement.pdf")
        r = nf.post(f"{API}/consortia/{S['cid']}/agreement/upload", json={"key": key, "filename": "agreement.pdf"})
        assert r.status_code == 200 and r.json()["ready"] is True, r.text


def _upload(s, name):
    key = f"bid-docs/TESTCN{RID}{uuid.uuid4().hex[:8]}_{name}"
    r = s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, b"%PDF-1.4 cn", "application/pdf")})
    assert r.status_code == 200, r.text
    return key


def _bid_body(s, turnover, iso, yrs, staff, members=None, cid=None, price=9000):
    now = _now()
    docs = [{"kind": "technical", "key": _upload(s, "t.pdf"), "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
            {"kind": "commercial", "key": _upload(s, "c.pdf"), "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]
    m = members or {}
    ans = [{"criterion_id": "mpturn01", "value": turnover},
           {"criterion_id": "mpiso001", "value": iso, "members": m.get("iso")},
           {"criterion_id": "mpyrs001", "value": yrs, "members": m.get("yrs")},
           {"criterion_id": "scstaff1", "value": staff, "members": m.get("staff")}]
    b = {"notice_ref": E2E, "price_amount": price, "price_currency": "USD", "technical_notes": "T", "commercial_notes": "C",
         "documents": docs, "criteria_answers": ans}
    if cid:
        b["consortium_id"] = cid
    return b


def _submit(s, body):
    r = s.post(f"{API}/bids", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ---- Consortium bid ----
class TestD_ConsortiumBid:
    def test_member_cannot_bid_for_consortium(self, bw):
        r = bw.post(f"{API}/bids", json=_bid_body(bw, 2000000, True, 5, 6, cid=S["cid"]))
        assert r.status_code == 403

    def test_missing_each_member_values_422(self, nf):
        r = nf.post(f"{API}/bids", json=_bid_body(nf, 2500000, True, 5, 6, cid=S["cid"]))
        assert r.status_code == 422 and "Brightwater" in r.text, r.text

    def test_wrong_notice_cid_on_nocons(self, nf):
        b = _bid_body(nf, 2500000, True, 5, 6, cid=S["cid"])
        b["notice_ref"] = NOCONS
        assert nf.post(f"{API}/bids", json=b).status_code in (409, 422)

    def test_submit_consortium_bid(self, nf):
        bwid = _vid("brightwater@demo.pmcmanagers.com")
        S["bwid"] = bwid
        body = _bid_body(nf, 2500000, True, 5, 6, cid=S["cid"],
                         members={"iso": {bwid: True}, "yrs": {bwid: 4}, "staff": {bwid: 6}})
        S["cbid"] = _submit(nf, body)
        b = DB.bids.find_one({"_id": ObjectId(S["cbid"])})
        assert b["consortium"]["id"] == S["cid"] and b["consortium"]["lead_share_pct"] == 70
        assert [m["vendor_id"] for m in b["consortium"]["members"]] == [bwid]
        c = DB.consortia.find_one({"_id": ObjectId(S["cid"])})
        assert c["status"] == "bid_submitted" and c["bid_id"] == S["cbid"]

    def test_locked_after_submit(self, nf, bw):
        assert nf.put(f"{API}/consortia/{S['cid']}/terms", json={"lead_share_pct": 100, "shares": {},
                                                                "escrow_mode": "shared", "deposit_mode": "lead_pays"}).status_code == 409
        r = bw.post(f"{API}/bids", json=_bid_body(bw, 2000000, True, 5, 6))
        assert r.status_code == 409


# ---- Pure evaluator rules ----
class TestE_EvaluateUnit:
    def test_rules(self):
        sys.path.insert(0, "/app/backend")
        from routers.tender_criteria import evaluate
        cons = {"members": [{"vendor_id": "m1", "company_name": "Member One"}, {"vendor_id": "m2", "company_name": "Member Two"}]}
        ans = [{"criterion_id": "mpturn01", "value": 2000000, "members": {"m1": 1, "m2": 1}},
               {"criterion_id": "mpiso001", "value": True, "members": {"m1": True, "m2": False}},
               {"criterion_id": "mpyrs001", "value": 5, "members": {"m1": 2, "m2": 4}},
               {"criterion_id": "scstaff1", "value": 3, "members": {"m1": 3, "m2": 4}}]
        q = evaluate(CRIT, ans, [], cons, "Leader Co")
        r = {x["criterion_id"]: x for x in q["results"]}
        assert r["mpturn01"]["result"] == "pass" and r["mpturn01"]["applies_to"] == "lead member"
        assert r["mpiso001"]["result"] == "fail" and "Member Two" in r["mpiso001"]["reason"] and "Member One" not in r["mpiso001"]["reason"]
        assert r["mpyrs001"]["result"] == "fail" and "Member One" in r["mpyrs001"]["reason"]
        assert r["scstaff1"]["value"] == 10 and r["scstaff1"]["points"] == 5.0 and r["scstaff1"]["applies_to"] == "all members combined"
        assert len(r["scstaff1"]["member_values"]) == 3
        assert q["system_status"] == "not_qualified"
        combined_yes = evaluate([{**ISO, "consortium_rule": "combined"}], [{"criterion_id": "mpiso001", "value": False, "members": {"m1": True}}],
                                [], cons, "L")
        assert combined_yes["system_status"] == "qualified"


# ---- Opening + notices ----
SIG = {"consent": True}


class TestF_OpeningNotices:
    def test_open_technical(self, c1, c2):
        DB.notices.update_one({"notice_ref": E2E}, {"$set": {"submission_deadline": _now(hours=-3), "bid_opening_date": _now(hours=-2)}})
        r = c1.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "technical", "signer_name": "Committee One", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is False, r.text
        r = c2.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "technical", "signer_name": "Committee Two", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is True, r.text
        assert r.json()["bids_opened"] == 2

    def test_consortium_qualification(self, c1):
        b = DB.bids.find_one({"_id": ObjectId(S["cbid"])})
        assert b["qualification"]["system_status"] == "qualified", b["qualification"]
        res = {x["criterion_id"]: x for x in b["qualification"]["results"]}
        assert res["scstaff1"]["value"] == 12 and res["scstaff1"]["points"] == 7.0
        assert res["mpyrs001"]["applies_to"] == "every member" and len(res["mpyrs001"]["member_values"]) == 2
        solo = DB.bids.find_one({"_id": ObjectId(S["solo"])})
        assert solo["qualification"]["system_status"] == "not_qualified"
        rows = c1.get(f"{API}/tender-criteria/{E2E}/qualification").json()["bids"]
        assert any(x.get("results") and any("applies_to" in r for r in x["results"]) for x in rows)

    def test_preliminary_notices(self, nf, bw, tv):
        for _ in range(20):
            if DB.bids.find_one({"_id": ObjectId(S["solo"]), "qualification_notices.0": {"$exists": True}}):
                break
            time.sleep(1)
        b = DB.bids.find_one({"_id": ObjectId(S["cbid"])})
        assert b["qualification_notices"][0]["kind"] == "preliminary"
        assert b["qualification_notices"][0]["qualified_count"] == 1 and b["qualification_notices"][0]["bids_total"] == 2
        for em in ("northfield@demo.pmcmanagers.com", "brightwater@demo.pmcmanagers.com", "testvendor@pmcmanagers.com"):
            assert DB.notifications.count_documents({"user_email": em, "related_notice_ref": E2E, "related_type": "criteria_result"}) == 1, em
        mine_bw = bw.get(f"{API}/tender-criteria/results/vendor/mine").json()["items"]
        assert any(x["bid_id"] == S["cbid"] and x["consortium"] == "TEST Team Alpha" for x in mine_bw)
        r = tv.get(f"{API}/tender-criteria/results/vendor/mine")
        mine_tv = [x for x in r.json()["items"] if x["notice_ref"] == E2E]
        assert len(mine_tv) == 1 and mine_tv[0]["bid_id"] == S["solo"]
        assert mine_tv[0]["notice"]["status"] == "not_qualified" and mine_tv[0]["notice"]["qualified_count"] == 1
        txt = r.text
        assert "Northfield" not in txt and "Brightwater" not in txt and "Team Alpha" not in txt

    def test_commercial_final_before_price(self, c1, c2):
        c1.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "commercial", "signer_name": "Committee One", **SIG})
        r = c2.post(f"{API}/bid-opening/{E2E}/approve", json={"stage": "commercial", "signer_name": "Committee Two", **SIG})
        assert r.status_code == 200 and r.json()["opened"] is True, r.text
        assert r.json()["bids_opened"] == 1
        b = DB.bids.find_one({"_id": ObjectId(S["cbid"])})
        fin = b["qualification_notices"][-1]
        assert fin["kind"] == "final" and fin["status"] == "qualified"
        assert fin["at"] <= b["commercial_unsealed_at"]
        assert b.get("price_amount") == 9000
        assert DB.notifications.count_documents({"user_email": "brightwater@demo.pmcmanagers.com", "related_notice_ref": E2E,
                                                 "related_type": "criteria_result"}) == 2

    def test_my_results_history(self, nf):
        items = [x for x in nf.get(f"{API}/tender-criteria/results/vendor/mine").json()["items"] if x["notice_ref"] == E2E]
        assert items[0]["history"] == ["preliminary", "final"] and items[0]["notice"]["kind"] == "final"


# ---- Withdrawn consortium bid should release members (regression probe) ----
WREF = f"TEST-CONSW-{RID}"


class TestG_WithdrawRelease:
    def test_withdraw_consortium_bid_releases_members(self, nf, bw):
        DB.notices.insert_one({"notice_ref": WREF, "title": "TEST withdraw", "is_published": True, "kyc_bypass": True,
                               "consortium_allowed": True, "budget_amount": 1000.0, "budget_currency": "USD",
                               "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"},
                               "submission_deadline": _now(days=3), "bid_opening_date": _now(days=4), "created_at": _now()})
        try:
            cid = nf.post(f"{API}/consortia", json={"notice_ref": WREF, "name": "TEST W team"}).json()["id"]
            bwid = _vid("brightwater@demo.pmcmanagers.com")
            nf.post(f"{API}/consortia/{cid}/members", json={"email_or_ref": "VEN-DEMO2", "share_pct": 40})
            bw.post(f"{API}/consortia/{cid}/respond", json={"accept": True})
            nf.put(f"{API}/consortia/{cid}/terms", json={"lead_share_pct": 60, "shares": {bwid: 40}, "escrow_mode": "shared", "deposit_mode": "lead_pays"})
            nf.post(f"{API}/consortia/{cid}/agreement/upload", json={"key": _upload(nf, "ag.pdf"), "filename": "ag.pdf"})
            body = _bid_body(nf, 1, True, 1, 1, cid=cid)
            body["notice_ref"], body["criteria_answers"] = WREF, []
            bid = _submit(nf, body)
            assert nf.post(f"{API}/bids/{bid}/withdraw").status_code == 200
            c = DB.consortia.find_one({"_id": ObjectId(cid)})
            S["withdraw_cons_status"] = c["status"]
            b2 = _bid_body(bw, 1, True, 1, 1)
            b2["notice_ref"], b2["criteria_answers"] = WREF, []
            r = bw.post(f"{API}/bids", json=b2)
            S["withdraw_member_solo"] = (r.status_code, r.text[:200])
            r2 = nf.post(f"{API}/consortia/{cid}/withdraw")
            S["withdraw_cons_after"] = (r2.status_code, r2.text[:200])
            assert r.status_code == 200 or r2.status_code == 200, f"members locked: cons={c['status']} solo={S['withdraw_member_solo']} withdraw={S['withdraw_cons_after']}"
        finally:
            for coll in ("bids", "notices", "consortia"):
                DB[coll].delete_many({"notice_ref": WREF})
            DB.notifications.delete_many({"related_notice_ref": WREF})
