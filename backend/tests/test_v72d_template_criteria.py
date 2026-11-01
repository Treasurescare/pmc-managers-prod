# v72d: Supplier Tender Builder (template) criteria endpoints, submit-review gate, reviewer approve copies criteria + publishes; minor fixes (ai-check 502, declared formatting).
import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from bson import ObjectId
from fastapi import HTTPException
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
NAME = f"TEST-TPLC-{RID}"
DEMO_PW = "Demo@Pmc2026"
S = {}

MUST = {"id": "mpturn01", "title": "Average annual turnover", "category": "financial", "answer_type": "number",
        "operator": "gte", "threshold": 1000000, "unit": "USD", "proof": "Audited accounts", "proof_required": True,
        "kind": "must_pass", "consortium_rule": "lead"}
STAFF = {"id": "scstaff1", "title": "Qualified key staff", "answer_type": "number", "operator": "gte", "threshold": 5,
         "unit": "staff", "kind": "scored", "max_points": 10, "scoring": "auto", "full_points_at": 15}
DESC = ("Supply and installation of water treatment equipment. Bidders must show average annual turnover of at least "
        "USD 1,000,000 over the last 3 years with audited accounts, hold ISO 9001 certification, have at least 5 "
        "qualified key staff and submit a methodology.")


def _tpl(tv_id, status="draft", criteria=None):
    h = {"work_title": f"{NAME} water plant", "work_description": DESC, "budget_amount": 100000, "tender_value": 100000,
         "budget_currency": "USD", "product_category": "Heating, ventilation & air-conditioning (HVAC)"}
    d = {"name": NAME, "kind": "tender", "is_master": False, "header": h,
         "sections": [{"code": "sec-3", "kind": "section", "title": "Qualifying", "body": DESC, "order": 10}],
         "owner_vendor_id": tv_id, "owner_vendor_ref": "VEN-TEST01", "owner_company_name": "Test Supplier Co",
         "review_status": status, "created_at": datetime.now(timezone.utc).isoformat(), "fees_paid": {}}
    if criteria is not None:
        d["tender_criteria"] = criteria
    if status == "submitted":
        d["submitted_at"] = datetime.now(timezone.utc).isoformat()
    return str(DB.tender_templates.insert_one(d).inserted_id)


def _cleanup():
    ids = [str(d["_id"]) for d in DB.tender_templates.find({"name": NAME})]
    DB.notices.delete_many({"tender_template_id": {"$in": ids}})
    DB.tender_templates.delete_many({"name": NAME})


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
    S["tv_id"] = str(DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})["_id"])
    S["tid"] = _tpl(S["tv_id"])
    S["tid_nocrit"] = _tpl(S["tv_id"], status="submitted")  # legacy submitted without criteria
    yield
    _cleanup()


@pytest.fixture(scope="module")
def tv():
    return _login_vendor("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def nf():
    return _login_vendor("northfield@demo.pmcmanagers.com", DEMO_PW)


@pytest.fixture(scope="module")
def reviewer():
    return _login_staff("reviewerqa@pmcmanagers.com", "Reviewer@12345", "reviewer")


@pytest.fixture(scope="module")
def admin():
    return _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")


def _url(tid, suffix=""):
    return f"{API}/tender-criteria/template/{tid}/mine{suffix}"


class TestA_TemplateCriteria:
    def test_get_empty(self, tv):
        r = tv.get(_url(S["tid"]))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["criteria"] == [] and d["locked"] is False and d["ai_check"] is None

    def test_unauth_and_other_vendor(self, nf):
        assert requests.get(_url(S["tid"])).status_code in (401, 403)
        assert nf.get(_url(S["tid"])).status_code == 404
        assert nf.put(_url(S["tid"]), json={"criteria": [MUST]}).status_code == 404
        assert requests.get(_url("notanid")).status_code in (401, 403, 404)

    def test_bad_criterion_422(self, tv):
        bad = {**MUST, "unit": None}
        assert tv.put(_url(S["tid"]), json={"criteria": [bad]}).status_code == 422

    def test_duplicate_ids_422(self, tv):
        r = tv.put(_url(S["tid"]), json={"criteria": [MUST, {**STAFF, "id": MUST["id"]}]})
        assert r.status_code == 422, r.text
        assert tv.get(_url(S["tid"])).json()["criteria"] == []

    def test_submit_without_criteria_409(self, tv):
        r = tv.post(f"{API}/tender-templates/{S['tid']}/submit-review")
        assert r.status_code == 409, r.text
        assert "criteria" in r.json()["detail"].lower()

    def test_scored_only_still_409(self, tv):
        r = tv.put(_url(S["tid"]), json={"criteria": [STAFF]})
        assert r.status_code == 200, r.text
        r = tv.post(f"{API}/tender-templates/{S['tid']}/submit-review")
        assert r.status_code == 409, r.text

    def test_save_must_pass_persists(self, tv):
        r = tv.put(_url(S["tid"]), json={"criteria": [MUST, STAFF], "fx_rule": "Central bank rate"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert [c["id"] for c in d["criteria"]] == ["mpturn01", "scstaff1"] and d["fx_rule"] == "Central bank rate"
        g = tv.get(_url(S["tid"])).json()
        assert len(g["criteria"]) == 2 and g["criteria"][0]["threshold"] == 1000000
        doc = tv.get(f"{API}/tender-templates/{S['tid']}").json()
        assert len(doc.get("tender_criteria") or []) == 2  # builder sees count for the button label

    def test_builder_patch_keeps_criteria(self, tv):
        doc = DB.tender_templates.find_one({"_id": ObjectId(S["tid"])})
        r = tv.patch(f"{API}/tender-templates/{S['tid']}", json={"name": NAME, "kind": "tender", "header": doc["header"],
                                                                  "sections": doc["sections"]})
        assert r.status_code == 200, r.text
        assert len(DB.tender_templates.find_one({"_id": ObjectId(S["tid"])})["tender_criteria"]) == 2

    def test_ai_suggest(self, tv):
        r = tv.post(_url(S["tid"], "/ai-suggest"), timeout=180)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["criteria"], list)
        S["ai_found"] = len(d["criteria"])
        for c in d["criteria"]:
            assert c.get("title") and c.get("id")
        # suggest must not write a bogus notice
        assert DB.notices.find_one({"notice_ref": S["tid"]}) is None

    def test_submit_ok(self, tv):
        r = tv.post(f"{API}/tender-templates/{S['tid']}/submit-review")
        if r.status_code == 402:
            pytest.fail(f"fees gate blocked submit: {r.text}")
        assert r.status_code == 200, r.text
        assert r.json()["review_status"] == "submitted"

    def test_locked_after_submit(self, tv):
        assert tv.put(_url(S["tid"]), json={"criteria": [MUST]}).status_code == 409
        g = tv.get(_url(S["tid"]))
        assert g.status_code == 200, g.text
        assert g.json()["locked"] is True and len(g.json()["criteria"]) == 2

    def test_other_vendor_still_404_after_submit(self, nf):
        assert nf.get(_url(S["tid"])).status_code == 404

    def test_reviewer_approve_publishes_with_criteria(self, reviewer):
        r = reviewer.post(f"{API}/tender-templates/{S['tid']}/review/approve", json={"note": "ok"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_published"] is True and d["note"] is None
        n = DB.notices.find_one({"notice_ref": d["notice_ref"]})
        assert n["is_published"] is True and n.get("published_at")
        assert [c["id"] for c in n["tender_criteria"]] == ["mpturn01", "scstaff1"]
        pub = requests.get(f"{API}/tender-criteria/{d['notice_ref']}")
        assert pub.status_code == 200 and len(pub.json()["criteria"]) == 2

    def test_get_after_approve_owner_and_admin(self, tv, admin):
        g = tv.get(_url(S["tid"]))
        assert g.status_code == 200 and g.json()["locked"] is True
        a = admin.get(_url(S["tid"]))
        assert a.status_code == 200, a.text
        assert len(a.json()["criteria"]) == 2
        assert tv.put(_url(S["tid"]), json={"criteria": [MUST]}).status_code == 409

    def test_legacy_without_criteria_saved_as_draft(self, reviewer):
        r = reviewer.post(f"{API}/tender-templates/{S['tid_nocrit']}/review/approve", json={})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_published"] is False and "criteria" in (d["note"] or "")
        assert DB.notices.find_one({"notice_ref": d["notice_ref"]})["is_published"] is False


class TestB_MinorFixes:
    def test_ai_check_unparseable_502(self, monkeypatch):
        from routers import tender_criteria as tc, tender_pro
        ref = f"TEST-TPLC-N-{RID}"

        async def fake(*a, **k):
            return "Sorry, I cannot help with that."

        monkeypatch.setattr(tender_pro, "_llm_complete", fake)

        async def run():
            from db import db
            await db.notices.insert_one({"notice_ref": ref, "title": "t", "description": DESC, "tender_criteria": [MUST],
                                         "tender_template_id": "x", "is_published": False})
            try:
                await tc.ai_check(ref, {"email": "t@x", "id": "x", "role": "admin"})
                return None
            except HTTPException as e:
                return e.status_code
            finally:
                await db.notices.delete_many({"notice_ref": ref})
        assert asyncio.run(run()) == 502

    def test_declared_formatting(self):
        from routers.tender_criteria import evaluate
        q = evaluate([MUST], [{"criterion_id": "mpturn01", "value": 400000.0}],
                     [{"kind": "technical", "criterion_id": "mpturn01", "key": "k"}])
        txt = str(q)
        assert "Declared 400,000 USD" in txt, txt
