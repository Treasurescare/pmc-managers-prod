# v69: partner password reset (portal=partner), partner monthly statement PDFs, admin send, cron, badges, public highlights.
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
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
ENV = {k: v.strip('"') for k, v in (l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))}
DB = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]
API = f"{BASE_URL}/api/v1"
RID = uuid.uuid4().hex[:6]
PW = "PartnerPw@123"
NEWPW = "NewPartnerPw@456"
S = {}
START = datetime.now(timezone.utc).isoformat()
SUP = {k: f"test_sup_{k}_{RID}@example.com" for k in ("one", "two", "three")}
NOW = datetime.now(timezone.utc)
THIS = NOW.strftime("%Y-%m")
PREV = f"{NOW.year - (NOW.month == 1)}-{12 if NOW.month == 1 else NOW.month - 1:02d}"
CRON_ID = f"test-cron-{RID}"


def _admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    if r.json().get("access_token"):
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def _ids():
    return [str(a["_id"]) for a in DB.agents.find({"email": {"$regex": f"^test_partner.*{RID}"}})]


def _cleanup():
    ids = _ids()
    DB.partner_commissions.delete_many({"partner_id": {"$in": ids}})
    DB.partner_statements.delete_many({"partner_id": {"$in": ids}})
    for r in DB.registrations.find({"email": {"$regex": f"^test_sup_.*{RID}"}}):
        DB.uploads.delete_many({"key": {"$regex": f"^registration-docs/{r['_id']}/"}})
        DB.partner_commissions.delete_many({"registration_id": str(r["_id"])})
    DB.registrations.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.vendors.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.agents.delete_many({"email": {"$regex": f"^test_partner.*{RID}"}})
    DB.uploads.delete_many({"key": {"$regex": f"TEST{RID}"}})
    DB.cron_runs.delete_many({"run_id": {"$regex": RID}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = _admin()
    S["orig_board"] = DB.partner_commission_settings.find_one({"key": "leaderboard"})
    S["seq"] = {n: (DB.counters.find_one({"name": n}) or {}).get("value") for n in ("vendor_seq",)}
    S["stmt_before"] = {d["_id"] for d in DB.partner_statements.find({}, {"_id": 1})}
    yield
    if S["orig_board"]:
        DB.partner_commission_settings.replace_one({"key": "leaderboard"}, S["orig_board"])
    else:
        DB.partner_commission_settings.delete_one({"key": "leaderboard"})
    time.sleep(3)  # let background statement tasks finish before cleaning
    _cleanup()
    for n, v in S["seq"].items():
        if v is not None:
            DB.counters.update_one({"name": n}, {"$set": {"value": v}})
    if DB.agents.count_documents({}) == 0:
        DB.counters.delete_one({"name": "partner_code"})


def _partner(tag):
    email = f"test_partner_{tag}_{RID}@example.com"
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})
    assert requests.post(f"{API}/agents/register", json={"email": email, "name": f"TEST Partner {tag}"}).status_code == 200
    tok = DB.agents.find_one({"email": email})["invite_token"]
    s = requests.Session()
    r = s.post(f"{API}/agents/join/{tok}", json={"password": PW})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    keys = requests.get(f"{API}/agents/agreement").json()["consent_keys"]
    assert s.post(f"{API}/agents/me/agreement", json={"signer_name": "TEST Partner", "consents": {k: True for k in keys}}).status_code == 200
    pre = s.post(f"{API}/uploads/presign", json={"file_name": f"TEST{RID}.pdf", "scope": "agent-docs"}).json()
    assert s.post(f"{API}/uploads/direct", data={"key": pre["key"]},
                  files={"file": (f"TEST{RID}.pdf", b"%PDF-1.4 t", "application/pdf")}).status_code == 200
    doc = {"key": pre["key"], "file_name": "x.pdf"}
    body = {"entity_type": "individual", "legal_name": f"TEST Partner {tag} Ltd", "country": "IN", "address_line1": "1 St",
            "city": "Pune", "postal_code": "411001", "primary_contact_phone": "+91 9000000000",
            "banking": [{"account_name": "TEST", "account_number": "123456789"}],
            "documents": {k: doc for k in ("id_proof", "address_proof", "bank_proof")}}
    assert s.patch(f"{API}/agents/me/profile", json=body).status_code == 200
    assert s.post(f"{API}/agents/me/submit").status_code == 200
    aid = str(DB.agents.find_one({"email": email})["_id"])
    r = S["admin"].post(f"{API}/admin/agents/{aid}/decision", json={"action": "approve", "waive_fee": True})
    assert r.status_code == 200, r.text
    return s, aid, email


def _invite(s, key):
    r = s.post(f"{API}/agents/me/suppliers", json={"company_name": f"TEST Supplier {key} {RID}", "email": SUP[key], "mobile": "+91 9876543210"})
    assert r.status_code == 200, r.text
    reg = DB.registrations.find_one({"_id": ObjectId(r.json()["id"])})
    return r.json()["id"], reg["partner_consent_token"]


# --- setup: partner A (2 invites, 1 approved), partner B (1 invite), partner C (for reset) ---
def test_setup():
    S["pa"], S["aid_a"], S["email_a"] = _partner("a")
    S["pb"], S["aid_b"], S["email_b"] = _partner("b")
    S["pc"], S["aid_c"], S["email_c"] = _partner("c")
    S["code_a"] = DB.agents.find_one({"_id": ObjectId(S["aid_a"])})["partner_code"]
    rid1, ctok = _invite(S["pa"], "one")
    _invite(S["pa"], "two")
    _invite(S["pb"], "three")
    r = requests.post(f"{API}/supplier-invites/{ctok}", json={"decision": "self", "signer_name": "TEST Self Signer", "consents": {"data_privacy": True}})
    assert r.status_code == 200, r.text
    DB.registrations.update_one({"_id": ObjectId(rid1)}, {"$set": {
        "registered_address": "1 TEST Road", "country": "IN", "registration_number": f"TESTREG{RID}",
        "legal_entity_type": "Private Limited", "status": "submitted"}})
    r = S["admin"].post(f"{API}/registrations/{rid1}/decision", json={"action": "approve"})
    assert r.status_code == 200, r.text
    S["rid1"] = rid1


# --- badges ---
def test_badges_partner_a():
    r = S["pa"].get(f"{API}/agents/me/badges")
    assert r.status_code == 200, r.text
    d = r.json()
    keys = {b["key"] for b in d["this_month"]}
    assert {"top_partner", "most_invites", "rising_star"} <= keys, d
    assert d["month"] == THIS and d["last"] == PREV and isinstance(d["last_month"], list)
    assert all(b["label"] for b in d["this_month"])


def test_badges_partner_b_none():
    d = S["pb"].get(f"{API}/agents/me/badges").json()
    assert d["this_month"] == [], d


def test_badges_requires_partner():
    assert requests.get(f"{API}/agents/me/badges").status_code in (401, 403)


# --- public highlights ---
def test_public_highlights_codes():
    DB.partner_commission_settings.update_one({"key": "leaderboard"}, {"$set": {"show_names": False}}, upsert=True)
    r = requests.get(f"{API}/public/partner-highlights")
    assert r.status_code == 200
    d = r.json()
    mine = [i for i in d["items"] if i["partner"] == S["code_a"]]
    if d["month"] == THIS:
        assert d["live"] is True
        assert {b for i in mine for b in i["badges"]} >= {"top_partner", "most_invites", "rising_star"}, d
        assert len(mine) == 1, "badges merged into one card per partner"
    for i in d["items"]:
        assert "TEST Partner" not in (i["partner"] or "")


def test_public_highlights_names():
    DB.partner_commission_settings.update_one({"key": "leaderboard"}, {"$set": {"show_names": True}}, upsert=True)
    d = requests.get(f"{API}/public/partner-highlights").json()
    if d["month"] == THIS:
        assert any(i["partner"] == "TEST Partner a Ltd" for i in d["items"]), d


# --- statements ---
def test_my_statement_pdf():
    r = S["pa"].get(f"{API}/agents/me/statement.pdf", params={"month": THIS})
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("application/pdf") and r.content[:4] == b"%PDF"
    assert THIS in r.headers.get("content-disposition", "")
    r = S["pa"].get(f"{API}/agents/me/statement.pdf")  # default prev month
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and PREV in r.headers.get("content-disposition", "")


def test_statement_bad_month():
    assert S["pa"].get(f"{API}/agents/me/statement.pdf", params={"month": "2026-1"}).status_code == 422
    assert S["admin"].get(f"{API}/admin/agents/{S['aid_a']}/statement.pdf", params={"month": "bad"}).status_code == 422


def test_statement_requires_auth():
    assert requests.get(f"{API}/agents/me/statement.pdf").status_code in (401, 403)
    assert requests.get(f"{API}/admin/agents/{S['aid_a']}/statement.pdf").status_code in (401, 403)


def test_admin_statement_pdf():
    r = S["admin"].get(f"{API}/admin/agents/{S['aid_a']}/statement.pdf", params={"month": THIS})
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert S["admin"].get(f"{API}/admin/agents/{'0'*24}/statement.pdf").status_code == 404


def test_admin_send_statements():
    assert requests.post(f"{API}/admin/partners/statements/send", cookies=S["admin"].cookies, json={"month": THIS}).status_code in (401, 403)
    assert S["admin"].post(f"{API}/admin/partners/statements/send", json={"month": "2026/01"}).status_code == 422
    r = S["admin"].post(f"{API}/admin/partners/statements/send", json={"month": THIS, "resend": False})
    assert r.status_code == 200 and r.json() == {"queued": True, "month": THIS}
    ids = [S["aid_a"], S["aid_b"], S["aid_c"]]
    for _ in range(30):
        if DB.partner_statements.count_documents({"partner_id": {"$in": ids}, "month": THIS}) == 3:
            break
        time.sleep(1)
    rows = list(DB.partner_statements.find({"partner_id": {"$in": ids}, "month": THIS}))
    assert len(rows) == 3, rows
    assert all("sent_at" in x and "email_ok" in x for x in rows)
    first = {x["partner_id"]: x["sent_at"] for x in rows}
    # non-resend skips only successfully emailed rows (example.com emails fail, so they are retried)
    DB.partner_statements.update_many({"partner_id": {"$in": ids}, "month": THIS}, {"$set": {"email_ok": True}})
    S["admin"].post(f"{API}/admin/partners/statements/send", json={"month": THIS})
    time.sleep(4)
    assert {x["partner_id"]: x["sent_at"] for x in DB.partner_statements.find({"partner_id": {"$in": ids}, "month": THIS})} == first
    S["admin"].post(f"{API}/admin/partners/statements/send", json={"month": THIS, "resend": True})
    for _ in range(30):
        cur = {x["partner_id"]: x["sent_at"] for x in DB.partner_statements.find({"partner_id": {"$in": ids}, "month": THIS})}
        if all(cur[k] != first[k] for k in first):
            break
        time.sleep(1)
    assert all(cur[k] != first[k] for k in first)
    assert DB.partner_statements.count_documents({"partner_id": {"$in": ids}, "month": THIS}) == 3


# --- cron ---
def test_cron_auth_and_idempotency():
    u = f"{API}/cron/partner-monthly-statements"
    assert requests.post(u).status_code == 401
    assert requests.post(u, headers={"Authorization": "Bearer wrong"}).status_code == 401
    h = {"Authorization": f"Bearer {ENV['WEBHOOK_CRON_SECRET']}", "X-Webhook-Id": CRON_ID}
    r = requests.post(u, headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    r = requests.post(u, headers=h)
    assert r.status_code == 200 and r.json().get("duplicate") is True
    assert DB.cron_runs.count_documents({"run_id": CRON_ID}) == 1
    ids = [S["aid_a"], S["aid_b"], S["aid_c"]]
    for _ in range(30):
        if DB.partner_statements.count_documents({"partner_id": {"$in": ids}, "month": PREV}) == 3:
            break
        time.sleep(1)
    assert DB.partner_statements.count_documents({"partner_id": {"$in": ids}, "month": PREV}) == 3


# --- partner password reset ---
def test_partner_reset_request_stores_jti():
    r = requests.post(f"{API}/auth/password-reset/request", json={"email": S["email_c"], "portal": "partner"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    a = DB.agents.find_one({"_id": ObjectId(S["aid_c"])})
    assert a.get("pwd_reset_jti"), a.keys()
    S["jti"] = a["pwd_reset_jti"]
    S["gen0"] = a.get("token_generation", 0)
    # unknown partner email -> same shape
    r = requests.post(f"{API}/auth/password-reset/request", json={"email": f"test_partner_none_{RID}@example.com", "portal": "partner"})
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_partner_reset_verify_confirm_login():
    now = datetime.now(timezone.utc)
    tok = jwt.encode({"sub": S["aid_c"], "email": S["email_c"], "portal": "partner", "jti": S["jti"], "type": "pwd_reset",
                      "iat": now, "exp": now + timedelta(minutes=30)}, ENV["JWT_SECRET"], algorithm="HS256")
    r = requests.post(f"{API}/auth/password-reset/verify", json={"token": tok})
    assert r.status_code == 200 and r.json()["portal"] == "partner" and r.json()["email"] == S["email_c"]
    r = requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": NEWPW})
    assert r.status_code == 200, r.text
    a = DB.agents.find_one({"_id": ObjectId(S["aid_c"])})
    assert a.get("token_generation", 0) == S["gen0"] + 1 and "pwd_reset_jti" not in a
    # replay rejected
    assert requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": NEWPW}).status_code == 400
    # old session invalidated by token_generation bump
    assert S["pc"].get(f"{API}/agents/me").status_code == 401
    assert requests.post(f"{API}/agents/auth/login", json={"email": S["email_c"], "password": PW}).status_code == 401
    r = requests.post(f"{API}/agents/auth/login", json={"email": S["email_c"], "password": NEWPW})
    assert r.status_code == 200 and r.json()["email"] == S["email_c"]
