# v71: Partner self-register stores country; join keeps country; submit 422 lists missing docs; submit succeeds once complete.
import os
import uuid

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
RID = uuid.uuid4().hex[:6]
EMAIL = f"test_ctry_{RID}@example.com"
EMAIL_NC = f"test_ctry_nc_{RID}@example.com"
PW = "AgentPw@123"
S = {}


def _cleanup():
    DB.agents.delete_many({"email": {"$regex": f"^test_ctry.*{RID}"}})
    DB.agents.delete_many({"email": "test_ctry_partner@example.com"})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    DB.uploads.delete_many({"key": {"$regex": f"^agent-docs/.*TEST{RID}"}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    yield
    _cleanup()


# --- register stores country ---
def test_register_with_country_stores_uppercase():
    r = requests.post(f"{API}/agents/register", json={"email": EMAIL.upper(), "name": "TEST Ctry Partner", "country": "ae"})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    a = DB.agents.find_one({"email": EMAIL})
    assert a and a["country"] == "AE" and a["status"] == "invited" and a["source"] == "self"
    S["token"] = a["invite_token"]


def test_register_without_country_backcompat():
    r = requests.post(f"{API}/agents/register", json={"email": EMAIL_NC, "name": "TEST NC"})
    assert r.status_code == 200, r.text
    assert DB.agents.find_one({"email": EMAIL_NC})["country"] is None


def test_register_invalid_country_len_422():
    r = requests.post(f"{API}/agents/register", json={"email": f"test_ctry_bad_{RID}@example.com", "name": "TEST Bad", "country": "X"})
    assert r.status_code == 422


def test_reregister_invited_keeps_existing_country():
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}})
    r = requests.post(f"{API}/agents/register", json={"email": EMAIL, "name": "TEST Ctry Partner", "country": "IN"})
    assert r.status_code == 200
    a = DB.agents.find_one({"email": EMAIL})
    assert a["country"] == "AE"
    S["token"] = a["invite_token"]


def test_reregister_invited_fills_missing_country():
    r = requests.post(f"{API}/agents/register", json={"email": EMAIL_NC, "name": "TEST NC", "country": "GB"})
    assert r.status_code == 200
    assert DB.agents.find_one({"email": EMAIL_NC})["country"] == "GB"


# --- join keeps country; /me returns it ---
def test_join_and_me_has_country():
    s = requests.Session()
    r = s.post(f"{API}/agents/join/{S['token']}", json={"password": PW})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    S["agent"] = s
    me = s.get(f"{API}/agents/me").json()
    assert me["country"] == "AE" and me["status"] == "draft" and me["legal_name"] == "TEST Ctry Partner"


# --- submit errors list docs ---
def test_submit_missing_lists_docs():
    r = S["agent"].post(f"{API}/agents/me/submit")
    assert r.status_code == 422
    det = r.json()["detail"]
    assert "Still missing" in det and "document: bank proof" in det and "document: id proof" in det
    assert "country" not in det.replace("Still missing", "")


def _upload(slot):
    pre = S["agent"].post(f"{API}/uploads/presign", json={"file_name": f"TEST{RID}_{slot}.pdf", "scope": "agent-docs"}).json()
    r = S["agent"].post(f"{API}/uploads/direct", data={"key": pre["key"]},
                        files={"file": (f"TEST{RID}_{slot}.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert r.status_code == 200, r.text
    return {"key": pre["key"], "filename": f"TEST{RID}_{slot}.pdf"}


def test_complete_profile_and_submit():
    s = S["agent"]
    r = s.patch(f"{API}/agents/me/profile", json={"entity_type": "individual", "address_line1": "1 Test St", "city": "Dubai",
                                                   "primary_contact_phone": "+971500000000",
                                                   "banking": [{"account_name": "TEST", "account_number": "123456"}]})
    assert r.status_code == 200, r.text
    docs = {d: _upload(d) for d in ("id_proof", "address_proof")}
    s.patch(f"{API}/agents/me/profile", json={"documents": docs})
    det = s.post(f"{API}/agents/me/submit").json()["detail"]
    assert "document: bank proof" in det and "id proof" not in det and "signed agent agreement" in det
    docs["bank_proof"] = _upload("bank_proof")
    assert s.patch(f"{API}/agents/me/profile", json={"documents": docs}).status_code == 200
    keys = requests.get(f"{API}/agents/agreement").json()["consent_keys"]
    assert s.post(f"{API}/agents/me/agreement", json={"signer_name": "TEST Ctry", "consents": {k: True for k in keys}}).status_code == 200
    r = s.post(f"{API}/agents/me/submit")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "submitted"
    assert DB.agents.find_one({"email": EMAIL})["status"] == "submitted"
