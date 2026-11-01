# v75: Criteria master library (items/sets), live-tender criteria editing (no bids vs bids), RBAC/CSRF
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = None
for line in open("/app/frontend/.env"):
    if line.startswith("REACT_APP_BACKEND_URL="):
        BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
API = f"{BASE_URL}/api/v1"
LIB = f"{API}/criteria-library"
RID = uuid.uuid4().hex[:6]
S = {"items": [], "sets": [], "notices": []}
MP = {"title": f"TEST_ turnover {RID}", "category": "financial", "answer_type": "number", "operator": "gte",
      "threshold": 1000, "unit": "USD", "kind": "must_pass"}
SC = {"title": f"TEST_ method {RID}", "answer_type": "text", "kind": "scored", "max_points": 10}


def _login(path, email, pw, role=None):
    s = requests.Session()
    body = {"email": email, "password": pw}
    if role:
        body["active_role"] = role
    r = s.post(f"{API}{path}", json=body)
    if r.status_code != 200:
        return None
    tok = r.json().get("csrf_token")
    if tok:
        s.headers["X-CSRF-Token"] = tok
    return s


@pytest.fixture(scope="module", autouse=True)
def setup():
    S["admin"] = _login("/staff/auth/login", "adminsupport@pmcmanagers.com", "Admin@12345", "admin")
    if not S["admin"]:
        pytest.skip("admin login failed")
    S["rev"] = _login("/staff/auth/login", "reviewerqa@pmcmanagers.com", "Reviewer@12345", "reviewer")
    S["vendor"] = _login("/vendor/auth/login", "testvendor@pmcmanagers.com", "Vendor@12345")
    backup = {n["notice_ref"]: n for n in DB.notices.find({"notice_ref": "DEMO-TND-001"},
                                                          {"notice_ref": 1, "tender_criteria": 1, "criteria_fx_rule": 1,
                                                           "consortium_allowed": 1, "consortium_max_members": 1})}
    yield
    for ref, n in backup.items():
        DB.notices.update_one({"notice_ref": ref}, {"$set": {"tender_criteria": n.get("tender_criteria") or [],
                                                             "criteria_fx_rule": n.get("criteria_fx_rule"),
                                                             "consortium_allowed": n.get("consortium_allowed", False),
                                                             "consortium_max_members": n.get("consortium_max_members")},
                                                    "$unset": {"criteria_ai_check": ""}})
    DB.criteria_master.delete_many({"title": {"$regex": "^TEST_"}})
    DB.criteria_sets.delete_many({"name": {"$regex": "^TEST_"}})
    for r in S["notices"]:
        DB.notices.delete_one({"notice_ref": r})


# --- Library read + auth
class TestLibraryRead:
    def test_anonymous_401(self):
        assert requests.get(LIB).status_code == 401

    def test_admin_reads_seeded(self):
        r = S["admin"].get(LIB)
        assert r.status_code == 200
        d = r.json()
        assert len([x for x in d["items"] if not x["title"].startswith("TEST_")]) >= 8
        assert all("_id" not in x and isinstance(x["id"], str) for x in d["items"])
        assert "sets" in d

    def test_vendor_can_read(self):
        if not S["vendor"]:
            pytest.skip("vendor login failed")
        assert S["vendor"].get(LIB).status_code == 200

    def test_templates_endpoint_has_sets(self):
        r = S["admin"].get(f"{API}/tender-criteria/templates")
        assert r.status_code == 200
        assert "sets" in r.json() and len(r.json()["templates"]) >= 8

    def test_templates_endpoint_anonymous(self):
        # informational: is the master library leaked via /templates anonymously?
        r = requests.get(f"{API}/tender-criteria/templates")
        print("anonymous /tender-criteria/templates ->", r.status_code)


# --- Library write RBAC/CSRF
class TestLibraryWrite:
    def test_vendor_forbidden(self):
        if not S["vendor"]:
            pytest.skip("vendor login failed")
        assert S["vendor"].post(f"{LIB}/items", json=MP).status_code in (401, 403)
        assert S["vendor"].post(f"{LIB}/sets", json={"name": f"TEST_v {RID}", "criteria": [MP]}).status_code in (401, 403)

    def test_no_csrf_rejected(self):
        s = requests.Session()
        s.cookies.update(S["admin"].cookies)
        r = s.post(f"{LIB}/items", json=MP)
        assert r.status_code == 403, r.text

    def test_admin_item_crud(self):
        r = S["admin"].post(f"{LIB}/items", json=MP)
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        S["items"].append(iid)
        assert any(x["id"] == iid for x in S["admin"].get(LIB).json()["items"])
        r = S["admin"].put(f"{LIB}/items/{iid}", json={**MP, "threshold": 2000})
        assert r.status_code == 200 and r.json()["threshold"] == 2000
        r = S["admin"].delete(f"{LIB}/items/{iid}")
        assert r.status_code == 200
        assert not any(x["id"] == iid for x in S["admin"].get(LIB).json()["items"])
        assert DB.criteria_master.find_one({"_id": ObjectId(iid)})["status"] == "archived"
        assert S["admin"].delete(f"{LIB}/items/{iid}").status_code == 404

    def test_bad_ids_404(self):
        assert S["admin"].put(f"{LIB}/items/xyz", json=MP).status_code == 404
        assert S["admin"].delete(f"{LIB}/sets/xyz").status_code == 404

    def test_invalid_item_422(self):
        assert S["admin"].post(f"{LIB}/items", json={**MP, "unit": ""}).status_code == 422

    def test_reviewer_item_and_set(self):
        if not S["rev"]:
            pytest.skip("reviewer login failed")
        r = S["rev"].post(f"{LIB}/items", json={**MP, "title": f"TEST_ rev {RID}"})
        assert r.status_code == 200, r.text
        r = S["rev"].post(f"{LIB}/sets", json={"name": f"TEST_ rev set {RID}", "criteria": [MP]})
        assert r.status_code == 200, r.text

    def test_set_crud_and_dup(self):
        name = f"TEST_ Standard construction {RID}"
        r = S["admin"].post(f"{LIB}/sets", json={"name": name, "criteria": [MP, SC]})
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        assert len(r.json()["criteria"]) == 2
        assert S["admin"].post(f"{LIB}/sets", json={"name": name, "criteria": [MP]}).status_code == 409
        tpl = S["admin"].get(f"{API}/tender-criteria/templates").json()
        assert any(s["id"] == sid for s in tpl["sets"])
        r = S["admin"].put(f"{LIB}/sets/{sid}", json={"name": name + " v2", "criteria": [MP]})
        assert r.status_code == 200 and len(r.json()["criteria"]) == 1
        assert S["admin"].delete(f"{LIB}/sets/{sid}").status_code == 200
        assert not any(s["id"] == sid for s in S["admin"].get(LIB).json()["sets"])

    def test_empty_set_422(self):
        assert S["admin"].post(f"{LIB}/sets", json={"name": f"TEST_ empty {RID}", "criteria": []}).status_code == 422


# --- Live tender criteria editing
class TestLiveCriteria:
    def test_live_no_bids_editable(self):
        r = S["admin"].get(f"{API}/tender-criteria/DEMO-TND-001/admin")
        assert r.status_code == 200
        d = r.json()
        assert d["locked"] is False and d.get("live_no_bids") is True

    def test_live_no_bids_zero_mustpass_422(self):
        r = S["admin"].put(f"{API}/tender-criteria/DEMO-TND-001", json={"criteria": [SC]})
        assert r.status_code == 422, r.text

    def test_live_no_bids_save_ok(self):
        r = S["admin"].put(f"{API}/tender-criteria/DEMO-TND-001", json={"criteria": [MP, SC]})
        assert r.status_code == 200, r.text
        assert len(r.json()["criteria"]) == 2
        pub = requests.get(f"{API}/tender-criteria/DEMO-TND-001").json()
        assert len(pub["criteria"]) == 2

    @pytest.mark.parametrize("ref", ["DEMO-TND-OPEN", "DEMO-TND-AWD"])
    def test_live_with_bids_locked(self, ref):
        d = S["admin"].get(f"{API}/tender-criteria/{ref}/admin").json()
        assert d["locked"] is True and not d.get("live_no_bids")
        r = S["admin"].put(f"{API}/tender-criteria/{ref}", json={"criteria": [MP]})
        assert r.status_code == 409, r.text
        assert "bids have already been received" in r.text.lower()

    def test_reviewer_cannot_save_notice_criteria(self):
        if not S["rev"]:
            pytest.skip("reviewer login failed")
        r = S["rev"].put(f"{API}/tender-criteria/DEMO-TND-001", json={"criteria": [MP]})
        print("reviewer PUT notice criteria ->", r.status_code)
        assert r.status_code in (401, 403)


# --- Draft notice publish after criteria
class TestDraftPublish:
    def test_draft_publish_requires_mustpass(self):
        p = {"title": f"TEST_ notice {RID}", "description": "TEST_ description of work long enough",
             "category": "Construction", "budget_amount": 50000,
             "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()}
        r = S["admin"].post(f"{API}/notices", json=p)
        assert r.status_code in (200, 201), r.text
        ref = r.json()["notice_ref"]
        S["notices"].append(ref)
        d = S["admin"].get(f"{API}/tender-criteria/{ref}/admin").json()
        assert d["locked"] is False and not d.get("live_no_bids")
        assert S["admin"].put(f"{API}/tender-criteria/{ref}", json={"criteria": [SC]}).status_code == 200
        r = S["admin"].post(f"{API}/notices/{ref}/publish")
        print("publish w/o must-pass/doc ->", r.status_code, r.text[:200])
        assert r.status_code >= 400
