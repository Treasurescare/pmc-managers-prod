# v65: Onboarding agents — admin invite, join via token, login/lockout, profile/docs/agreement/submit, admin decisions, file access.
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
EMAIL = f"test_agent_{RID}@example.com"
EMAIL2 = f"test_agent_co_{RID}@example.com"
PW = "AgentPw@123"
S = {}


def _admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    if r.json().get("access_token"):
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/agents/auth/login", json={"email": email, "password": pw})
    if r.status_code == 200:
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s, r


def _cleanup():
    ids = [a["_id"] for a in DB.agents.find({"email": {"$regex": f"^test_agent.*{RID}"}})]
    DB.agents.delete_many({"_id": {"$in": ids}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    DB.uploads.delete_many({"key": {"$regex": f"^agent-docs/.*TEST{RID}"}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = _admin()
    yield
    _cleanup()


# --- admin invite ---
def test_invite_creates_invited_agent():
    r = S["admin"].post(f"{API}/admin/agents/invite", json={"email": EMAIL, "name": "TEST Agent One"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "invited" and d["email"] == EMAIL and "email_sent" in d
    assert "invite_token" not in d and "password_hash" not in d
    S["aid"] = d["id"]
    S["token"] = DB.agents.find_one({"email": EMAIL})["invite_token"]


def test_invite_duplicate_409():
    r = S["admin"].post(f"{API}/admin/agents/invite", json={"email": EMAIL.upper(), "name": "TEST Dup"})
    assert r.status_code == 409


def test_invite_requires_admin_csrf():
    r = requests.post(f"{API}/admin/agents/invite", json={"email": f"x{RID}@example.com", "name": "TEST x"})
    assert r.status_code in (401, 403)


def test_resend_rotates_token():
    old = S["token"]
    r = S["admin"].post(f"{API}/admin/agents/{S['aid']}/resend")
    assert r.status_code == 200 and "email_sent" in r.json()
    new = DB.agents.find_one({"email": EMAIL})["invite_token"]
    assert new != old
    assert requests.get(f"{API}/agents/join/{old}").status_code == 404
    S["token"] = new


def test_list_and_detail():
    r = S["admin"].get(f"{API}/admin/agents")
    assert r.status_code == 200
    assert any(i["id"] == S["aid"] for i in r.json()["items"])
    r = S["admin"].get(f"{API}/admin/agents/{S['aid']}")
    assert r.status_code == 200 and r.json()["email"] == EMAIL


def test_detail_invalid_id():
    r = S["admin"].get(f"{API}/admin/agents/not-an-objectid")
    assert r.status_code in (400, 404, 422), f"got {r.status_code}"


# --- join ---
def test_join_info_and_invalid():
    r = requests.get(f"{API}/agents/join/{S['token']}")
    assert r.status_code == 200 and r.json()["email"] == EMAIL and r.json()["name"] == "TEST Agent One"
    assert requests.get(f"{API}/agents/join/bogus{RID}").status_code == 404


def test_invited_cannot_login():
    _, r = _login(EMAIL, PW)
    assert r.status_code == 401


def test_join_short_password_422():
    r = requests.post(f"{API}/agents/join/{S['token']}", json={"password": "short"})
    assert r.status_code == 422


def test_join_sets_cookie_and_draft():
    s = requests.Session()
    r = s.post(f"{API}/agents/join/{S['token']}", json={"password": PW})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "draft" and d["csrf_token"]
    sc = r.headers.get("set-cookie", "")
    assert "agent_token=" in sc and "HttpOnly" in sc
    assert DB.agents.find_one({"email": EMAIL})["password_hash"].startswith("$2")
    s.headers["X-CSRF-Token"] = d["csrf_token"]
    me = s.get(f"{API}/agents/me")
    assert me.status_code == 200 and me.json()["status"] == "draft"
    S["agent"] = s
    # token cannot be reused
    assert requests.post(f"{API}/agents/join/{S['token']}", json={"password": PW}).status_code == 404


# --- login ---
def test_login_wrong_password_then_lockout():
    # use distinct email identifier so lockout doesn't block main agent
    s = requests.Session()
    bad_email = f"test_agent_lock_{RID}@example.com"
    codes = [s.post(f"{API}/agents/auth/login", json={"email": bad_email, "password": "nope12345"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5, codes
    assert codes[5] == 429, codes


def test_login_ok_and_logout():
    s, r = _login(EMAIL, PW)
    assert r.status_code == 200, r.text
    assert s.get(f"{API}/agents/me").status_code == 200
    r = s.post(f"{API}/agents/auth/logout")
    assert r.status_code == 200
    assert s.get(f"{API}/agents/me").status_code == 401


# --- profile ---
def test_profile_patch_requires_csrf():
    s = requests.Session()
    s.cookies.update(S["agent"].cookies)
    s.cookies.set("csrf_token", None)
    r = requests.patch(f"{API}/agents/me/profile", json={"city": "X"},
                       cookies={"agent_token": S["agent"].cookies.get("agent_token")})
    assert r.status_code == 403


def test_profile_rejects_email_change_and_filters_docs():
    a = S["agent"]
    r = a.patch(f"{API}/agents/me/profile", json={"primary_contact_email": f"other{RID}@example.com"})
    assert r.status_code == 422
    r = a.patch(f"{API}/agents/me/profile", json={"status": "approved", "documents": {
        "id_proof": {"key": "agent-docs/x"}, "bad": {"key": "vendor-docs/y"}, "str": "agent-docs/z"}})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "draft"
    assert set(d["documents"].keys()) == {"id_proof"}


def test_submit_missing_422_lists():
    r = S["agent"].post(f"{API}/agents/me/submit")
    assert r.status_code == 422
    det = r.json()["detail"]
    assert "country" in det and "bank account" in det and "signed agent agreement" in det and "address proof" in det


def test_upload_and_view_own_doc():
    files = {"file": (f"TEST{RID}_id.pdf", b"%PDF-1.4 test", "application/pdf")}
    pre = S["agent"].post(f"{API}/uploads/presign", json={"file_name": f"TEST{RID}_id.pdf", "scope": "agent-docs"}).json()
    assert pre["key"].startswith("agent-docs/")
    r = S["agent"].post(f"{API}/uploads/direct", data={"key": pre["key"]}, files=files)
    assert r.status_code == 200
    S["doc_key"] = pre["key"]
    r = S["agent"].get(f"{API}/uploads/files/{pre['key']}")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert requests.get(f"{API}/uploads/files/{pre['key']}").status_code == 401


def test_agreement_requires_all_consents():
    keys = requests.get(f"{API}/agents/agreement").json()["consent_keys"]
    assert len(keys) == 6
    c = {k: True for k in keys}
    c[keys[3]] = False
    r = S["agent"].post(f"{API}/agents/me/agreement", json={"signer_name": "TEST Agent One", "consents": c})
    assert r.status_code == 422
    r = S["agent"].post(f"{API}/agents/me/agreement", json={"signer_name": "TEST Agent One", "consents": {k: True for k in keys}})
    assert r.status_code == 200 and r.json()["agreement"]["signer_name"] == "TEST Agent One"


def _complete(s, key, company=False):
    doc = {"key": key, "file_name": "x.pdf"}
    docs = {k: doc for k in ["id_proof", "address_proof", "bank_proof"]}
    body = {"entity_type": "company" if company else "individual", "legal_name": "TEST Agent One", "country": "IN",
            "address_line1": "1 Test St", "city": "Mumbai", "state_code": "MH", "postal_code": "400001",
            "primary_contact_phone": "+91 9999999999",
            "banking": [{"account_name": "TEST Agent", "account_number": "123456789", "bank_name": "HDFC"}], "documents": docs}
    return s.patch(f"{API}/agents/me/profile", json=body)


def test_submit_success_then_locked():
    r = _complete(S["agent"], S["doc_key"])
    assert r.status_code == 200
    r = S["agent"].post(f"{API}/agents/me/submit")
    assert r.status_code == 200 and r.json()["status"] == "submitted", r.text
    assert S["agent"].patch(f"{API}/agents/me/profile", json={"city": "Pune"}).status_code == 409
    assert S["agent"].post(f"{API}/agents/me/submit").status_code == 409


# --- admin decisions ---
def test_clarify_needs_note_then_edit_again():
    ad = S["admin"]
    assert ad.post(f"{API}/admin/agents/{S['aid']}/decision", json={"action": "clarify"}).status_code == 422
    r = ad.post(f"{API}/admin/agents/{S['aid']}/decision", json={"action": "clarify", "note": "TEST fix your address"})
    assert r.status_code == 200 and r.json()["status"] == "needs_clarification"
    me = S["agent"].get(f"{API}/agents/me").json()
    assert me["status"] == "needs_clarification"
    assert any(h.get("note") == "TEST fix your address" for h in me["history"])
    assert S["agent"].patch(f"{API}/agents/me/profile", json={"city": "Pune"}).status_code == 200
    assert S["agent"].post(f"{API}/agents/me/submit").status_code == 200


def test_approve_only_submitted_and_reject_note():
    ad = S["admin"]
    assert ad.post(f"{API}/admin/agents/{S['aid']}/decision", json={"action": "suspend"}).status_code == 409
    r = ad.post(f"{API}/admin/agents/{S['aid']}/decision", json={"action": "approve"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert ad.post(f"{API}/admin/agents/{S['aid']}/decision", json={"action": "approve"}).status_code == 409


def test_suspend_revokes_session_and_blocks_login():
    ad = S["admin"]
    assert S["agent"].get(f"{API}/agents/me").status_code == 200
    r = ad.post(f"{API}/admin/agents/{S['aid']}/decision", json={"action": "suspend", "note": "TEST"})
    assert r.status_code == 200 and r.json()["status"] == "suspended"
    assert S["agent"].get(f"{API}/agents/me").status_code == 401
    _, r = _login(EMAIL, PW)
    assert r.status_code == 403


def test_company_requires_extra_docs_and_reject():
    ad = S["admin"]
    r = ad.post(f"{API}/admin/agents/invite", json={"email": EMAIL2, "name": "TEST Agent Co"})
    assert r.status_code == 200
    aid = r.json()["id"]
    tok = DB.agents.find_one({"email": EMAIL2})["invite_token"]
    s = requests.Session()
    r = s.post(f"{API}/agents/join/{tok}", json={"password": PW})
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    keys = requests.get(f"{API}/agents/agreement").json()["consent_keys"]
    s.post(f"{API}/agents/me/agreement", json={"signer_name": "TEST Agent Co", "consents": {k: True for k in keys}})
    _complete(s, S["doc_key"], company=True)
    r = s.post(f"{API}/agents/me/submit")
    assert r.status_code == 422
    det = r.json()["detail"]
    assert "incorporation certificate" in det and "tax registration" in det and "authority letter" in det and "registration number" in det
    # reject requires submitted; verify reject needs note via direct DB status set
    DB.agents.update_one({"email": EMAIL2}, {"$set": {"status": "submitted"}})
    assert ad.post(f"{API}/admin/agents/{aid}/decision", json={"action": "reject"}).status_code == 422
    assert ad.post(f"{API}/admin/agents/{aid}/decision", json={"action": "reject", "note": "TEST no"}).status_code == 200
    _, r = _login(EMAIL2, PW)
    assert r.status_code == 401
