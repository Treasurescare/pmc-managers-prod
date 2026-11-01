# v74: Criteria-in-Tender-Builder (template criteria endpoints) + carry-over of criteria into notice on create_notice
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
API = f"{BASE_URL}/api/v1"
RID = uuid.uuid4().hex[:6]
S = {"tpls": [], "notices": []}

CRIT = {"id": "c1", "title": "TEST_ Min turnover", "category": "financial", "answer_type": "number",
        "operator": "gte", "threshold": 1000000, "unit": "USD", "kind": "must_pass"}


def _future(days=20):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture(scope="module", autouse=True)
def setup():
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345", "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code} {r.text[:200]}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    S["admin"] = s
    yield
    for t in S["tpls"]:
        DB.tender_templates.delete_one({"_id": ObjectId(t)})
    for n in S["notices"]:
        DB.notices.delete_one({"notice_ref": n})


def _new_tpl():
    r = S["admin"].post(f"{API}/tender-templates", json={"name": f"TEST_builder_{RID}", "header": {"work_title": f"TEST_ work {RID}"}})
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    S["tpls"].append(tid)
    return tid


def _notice_payload(tid, **kw):
    p = {"title": f"TEST_ notice {RID}", "description": "TEST_ description of work long enough",
         "category": "Construction", "submission_deadline": _future(), "budget_amount": 50000,
         "tender_template_id": tid}
    p.update(kw)
    return p


# Template criteria (builder) GET/PUT
class TestTemplateCriteria:
    def test_get_empty(self):
        tid = _new_tpl()
        S["tid"] = tid
        r = S["admin"].get(f"{API}/tender-criteria/template/{tid}/mine")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["criteria"] == [] and d["locked"] is False and d["notice_ref"] == tid

    def test_save_and_persist(self):
        tid = S["tid"]
        r = S["admin"].put(f"{API}/tender-criteria/template/{tid}/mine", json={"criteria": [CRIT]})
        assert r.status_code == 200, r.text
        assert len(r.json()["criteria"]) == 1
        g = S["admin"].get(f"{API}/tender-criteria/template/{tid}/mine").json()
        assert g["criteria"][0]["title"] == CRIT["title"] and g["criteria"][0]["kind"] == "must_pass"
        t = S["admin"].get(f"{API}/tender-templates/{tid}").json()
        assert len(t.get("tender_criteria") or []) == 1

    def test_bad_id_404(self):
        r = S["admin"].get(f"{API}/tender-criteria/template/000000000000000000000000/mine")
        assert r.status_code == 404

    def test_unauth(self):
        r = requests.get(f"{API}/tender-criteria/template/{S['tid']}/mine")
        assert r.status_code in (401, 403)


# create_notice copies criteria from template
class TestNoticeCarryOver:
    def test_create_copies_criteria(self):
        r = S["admin"].post(f"{API}/notices", json=_notice_payload(S["tid"]))
        assert r.status_code == 200, r.text
        d = r.json()
        S["notices"].append(d["notice_ref"])
        assert len(d.get("tender_criteria") or []) == 1
        assert d["tender_criteria"][0]["title"] == CRIT["title"]
        dbn = DB.notices.find_one({"notice_ref": d["notice_ref"]})
        assert dbn["tender_criteria"][0]["kind"] == "must_pass"
        assert dbn.get("is_published") is False

    def test_payload_criteria_wins(self):
        own = dict(CRIT, id="x1", title="TEST_ Own criterion")
        r = S["admin"].post(f"{API}/notices", json=_notice_payload(S["tid"], tender_criteria=[own]))
        assert r.status_code == 200, r.text
        d = r.json()
        S["notices"].append(d["notice_ref"])
        assert [c["title"] for c in d["tender_criteria"]] == ["TEST_ Own criterion"]

    def test_template_without_criteria(self):
        tid = _new_tpl()
        r = S["admin"].post(f"{API}/notices", json=_notice_payload(tid))
        assert r.status_code == 200, r.text
        d = r.json()
        S["notices"].append(d["notice_ref"])
        assert not d.get("tender_criteria")

    def test_invalid_template_id_ok(self):
        r = S["admin"].post(f"{API}/notices", json=_notice_payload("not-an-objectid"))
        assert r.status_code == 200, r.text
        S["notices"].append(r.json()["notice_ref"])
        assert not r.json().get("tender_criteria")

    def test_notice_criteria_endpoint_sees_copy(self):
        ref = S["notices"][0]
        r = S["admin"].get(f"{API}/tender-criteria/{ref}/admin")
        assert r.status_code == 200, r.text
        assert len(r.json()["criteria"]) == 1
