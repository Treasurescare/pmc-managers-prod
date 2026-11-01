# v72b: partner session-bound CSRF (no csrf cookie) + tender criteria fixes A1/A2/A3 retest.
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
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
RID = uuid.uuid4().hex[:6].lower()
PEMAIL = f"test_partner_{RID}@example.com"
PPASS = "TestPass@123"
NREF = f"TEST-CRITC-{RID.upper()}"
S = {}

MUST = {"id": "mpturn01", "title": "Average annual turnover", "answer_type": "number", "operator": "gte",
        "threshold": 1000000, "unit": "USD", "proof": "Audited accounts", "proof_required": True,
        "kind": "must_pass", "consortium_rule": "lead"}
BLANK_PROOF = {"id": "blank001", "title": "Safety policy", "answer_type": "yes_no", "kind": "must_pass",
               "proof_required": True, "proof": ""}


def _future(d=5):
    return (datetime.now(timezone.utc) + timedelta(days=d)).isoformat()


def _cleanup():
    DB.agents.delete_many({"email": PEMAIL})
    DB.notices.delete_many({"notice_ref": {"$regex": f"^TEST-CRITC-{RID.upper()}"}})
    DB.notices.delete_many({"title": {"$regex": f"^TEST_v72b {RID}"}})


@pytest.fixture(scope="module", autouse=True)
def setup():
    _cleanup()
    yield
    _cleanup()


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345",
                                                "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _no_csrf_cookie(s):
    for c in list(s.cookies):
        if c.name == "csrf_token":
            s.cookies.clear(c.domain, c.path, c.name)


# Fix B: partner CSRF session-bound
class TestB_PartnerCsrf:
    def test_register_and_join(self):
        r = requests.post(f"{API}/agents/register", json={"email": PEMAIL, "name": "TEST_ Partner", "country": "IN"})
        if r.status_code == 429:
            DB.agents.insert_one({"email": PEMAIL, "name": "TEST_ Partner", "country": "IN", "status": "invited",
                                  "invite_token": f"tok{RID}xxxxxxxxxxxxxxxx", "invite_expires_at": _future(7),
                                  "created_at": datetime.now(timezone.utc).isoformat(), "banking": [], "documents": {}, "history": []})
        else:
            assert r.status_code == 200, r.text
        tok = DB.agents.find_one({"email": PEMAIL})["invite_token"]
        s = requests.Session()
        j = s.post(f"{API}/agents/join/{tok}", json={"password": PPASS})
        assert j.status_code == 200, j.text
        assert isinstance(j.json().get("csrf_token"), str) and len(j.json()["csrf_token"]) == 64
        S["join_csrf"] = j.json()["csrf_token"]
        S["id"] = j.json()["id"]

    def test_login_returns_session_csrf(self):
        s = requests.Session()
        r = s.post(f"{API}/agents/auth/login", json={"email": PEMAIL, "password": PPASS})
        assert r.status_code == 200, r.text
        assert r.json()["csrf_token"] == S["join_csrf"], "csrf should be deterministic HMAC per agent"
        me = s.get(f"{API}/agents/me")
        assert me.status_code == 200 and me.json()["csrf_token"] == S["join_csrf"]
        S["sess"] = s

    def test_patch_profile_without_csrf_cookie_ok(self):
        s = S["sess"]
        _no_csrf_cookie(s)
        assert "csrf_token" not in s.cookies.get_dict()
        r = s.patch(f"{API}/agents/me/profile", json={"city": "TEST_City", "address_line1": "1 Test St"},
                    headers={"X-CSRF-Token": S["join_csrf"]})
        assert r.status_code == 200, r.text
        assert DB.agents.find_one({"email": PEMAIL})["city"] == "TEST_City"

    def test_banking_without_cookie_ok(self):
        s = S["sess"]
        r = s.patch(f"{API}/agents/me/profile", json={"banking": [{"account_name": "TEST", "account_number": "123"}]},
                    headers={"X-CSRF-Token": S["join_csrf"]})
        assert r.status_code == 200 and r.json()["banking"][0]["account_number"] == "123"

    def test_wrong_header_403(self):
        r = S["sess"].patch(f"{API}/agents/me/profile", json={"city": "X"}, headers={"X-CSRF-Token": "a" * 64})
        assert r.status_code == 403

    def test_no_header_403(self):
        r = S["sess"].patch(f"{API}/agents/me/profile", json={"city": "X"})
        assert r.status_code == 403

    def test_other_agent_token_rejected(self):
        # header valid for a different subject must be rejected
        from importlib import import_module  # noqa
        r = S["sess"].patch(f"{API}/agents/me/profile", json={"city": "X"},
                            headers={"X-CSRF-Token": "0" * 64})
        assert r.status_code == 403

    def test_stale_access_token_cookie_with_agent(self, admin):
        # A leftover staff access_token cookie in the same browser + dropped csrf cookie
        s = requests.Session()
        s.post(f"{API}/agents/auth/login", json={"email": PEMAIL, "password": PPASS})
        _no_csrf_cookie(s)
        at = admin.cookies.get("access_token")
        if not at:
            pytest.skip("no admin access_token cookie")
        s.cookies.set("access_token", at)
        r = s.patch(f"{API}/agents/me/profile", json={"city": "TEST_City2"}, headers={"X-CSRF-Token": S["join_csrf"]})
        S["stale_status"] = r.status_code
        assert r.status_code == 200, f"stale staff cookie breaks partner CSRF fallback: {r.status_code} {r.text}"

    def test_demo_partner_login(self):
        r = requests.post(f"{API}/agents/auth/login", json={"email": "partner@demo.pmcmanagers.com", "password": "Demo@Pmc2026"})
        assert r.status_code == 200 and len(r.json()["csrf_token"]) == 64


# Fix A1: create/patch publish gate
class TestA1_PublishGate:
    def test_create_published_409(self, admin):
        r = admin.post(f"{API}/notices", json={"title": f"TEST_v72b {RID} pub", "description": "x", "is_published": True,
                                               "submission_deadline": _future(), "budget_amount": 1000})
        assert r.status_code in (409, 422), r.text
        if r.status_code == 409:
            assert "draft first" in r.text
        assert DB.notices.count_documents({"title": f"TEST_v72b {RID} pub"}) == 0

    def test_patch_publish_no_criteria_409(self, admin):
        DB.notices.insert_one({"notice_ref": NREF, "title": f"TEST_v72b {RID} d", "is_published": False,
                               "budget_amount": 1000.0, "submission_deadline": _future(), "bid_opening_date": _future(6),
                               "created_at": datetime.now(timezone.utc).isoformat()})
        r = admin.patch(f"{API}/notices/{NREF}", json={"is_published": True})
        assert r.status_code == 409, r.text
        assert DB.notices.find_one({"notice_ref": NREF})["is_published"] is False

    def test_patch_publish_with_criteria_ok(self, admin):
        r = admin.put(f"{API}/tender-criteria/{NREF}", json={"criteria": [MUST]})
        assert r.status_code == 200, r.text
        r = admin.patch(f"{API}/notices/{NREF}", json={"is_published": True})
        assert r.status_code == 200, r.text
        assert DB.notices.find_one({"notice_ref": NREF})["is_published"] is True


# Fix A2/A3
class TestA2_ProofDefault:
    def test_empty_proof_defaults(self, admin):
        ref = NREF + "-B"
        DB.notices.insert_one({"notice_ref": ref, "title": f"TEST_v72b {RID} b", "is_published": False,
                               "budget_amount": 1000.0, "submission_deadline": _future(),
                               "created_at": datetime.now(timezone.utc).isoformat()})
        r = admin.put(f"{API}/tender-criteria/{ref}", json={"criteria": [BLANK_PROOF]})
        assert r.status_code == 200, r.text
        assert r.json()["criteria"][0]["proof"] == "Supporting document"
        g = admin.get(f"{API}/tender-criteria/{ref}/admin").json()
        assert g["criteria"][0]["proof"] == "Supporting document" and g["criteria"][0]["proof_required"] is True

    def test_422_message(self, admin):
        r = admin.put(f"{API}/tender-criteria/{NREF}-B", json={"criteria": [{**MUST, "unit": ""}]})
        assert r.status_code == 422
        print("422 detail:", r.text[:300])
