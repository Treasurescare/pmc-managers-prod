# v66: Partner self-registration, partner_registration fee rule, waive/approve, Stripe payment request, apply_partner_payment.
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone

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
E_SELF = f"test_partner_self_{RID}@example.com"
E_WAIVE = f"test_partner_waive_{RID}@example.com"
PW = "PartnerPw@123"
S = {}
START = datetime.now(timezone.utc).isoformat()


def _admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    if r.json().get("access_token"):
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def _clear_reg_attempts():
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})


def _cleanup():
    ids = [str(a["_id"]) for a in DB.agents.find({"email": {"$regex": f"^test_partner.*{RID}"}})]
    DB.payment_transactions.delete_many({"agent_id": {"$in": ids}})
    DB.agents.delete_many({"email": {"$regex": f"^test_partner.*{RID}"}})
    DB.emd_masters.delete_many({"name": {"$regex": f"^TEST.*{RID}"}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    _clear_reg_attempts()
    if DB.agents.count_documents({}) == 0:  # don't let TEST runs burn real PT-xxxx codes
        DB.counters.delete_one({"name": "partner_code"})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = _admin()
    yield
    _cleanup()


def _register(email, name="TEST Partner", headers=None):
    return requests.post(f"{API}/agents/register", json={"email": email, "name": name}, headers=headers or {})


def _join_and_submit(email, country):
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
    body = {"entity_type": "individual", "legal_name": "TEST Partner", "country": country, "address_line1": "1 St",
            "city": "Nairobi", "postal_code": "00100", "primary_contact_phone": "+254 700000000",
            "banking": [{"account_name": "TEST", "account_number": "123456789"}],
            "documents": {k: doc for k in ("id_proof", "address_proof", "bank_proof")}}
    assert s.patch(f"{API}/agents/me/profile", json=body).status_code == 200
    r = s.post(f"{API}/agents/me/submit")
    assert r.status_code == 200, r.text
    return s, str(DB.agents.find_one({"email": email})["_id"])


def _apply(session_id):
    code = ("import asyncio,sys; sys.path.insert(0,'/app/backend'); "
            "from routers.agents import apply_partner_payment; "
            f"asyncio.run(apply_partner_payment({session_id!r}))")
    p = subprocess.run(["python", "-c", code], cwd="/app/backend", capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stderr[-2000:]


# --- self registration ---
def test_self_register_creates_invited_self():
    r = _register(E_SELF)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    a = DB.agents.find_one({"email": E_SELF})
    assert a and a["status"] == "invited" and a["source"] == "self" and a["invite_token"]
    S["tok1"] = a["invite_token"]
    assert requests.get(f"{API}/agents/join/{S['tok1']}").json()["email"] == E_SELF


def test_self_register_existing_invited_rotates_token():
    r = _register(E_SELF.upper())
    assert r.status_code == 200 and r.json()["ok"] is True
    assert DB.agents.count_documents({"email": E_SELF}) == 1
    new = DB.agents.find_one({"email": E_SELF})["invite_token"]
    assert new != S["tok1"]
    assert requests.get(f"{API}/agents/join/{S['tok1']}").status_code == 404


def test_self_register_invalid_payload_422():
    assert requests.post(f"{API}/agents/register", json={"email": "not-email", "name": "TEST"}).status_code == 422


def test_self_register_rate_limit_429():
    _clear_reg_attempts()
    codes = [_register(f"test_partner_rl{i}_{RID}@example.com").status_code for i in range(6)]
    assert codes[:5] == [200] * 5, codes
    assert codes[5] == 429, codes
    S["rl_spoof"] = _register(f"test_partner_rlx_{RID}@example.com", headers={"X-Forwarded-For": f"10.9.{RID[:1].isdigit() and 8 or 7}.1"}).status_code
    _clear_reg_attempts()


def test_rate_limit_xff_spoof_info():
    # informational: leftmost X-Forwarded-For is client-controlled
    print("spoofed XFF status after limit:", S.get("rl_spoof"))
    assert S.get("rl_spoof") == 429, f"Rate limit bypassable by spoofing X-Forwarded-For (got {S.get('rl_spoof')})"


# --- payment flow ---
def test_join_submit_self_partner():
    s, aid = _join_and_submit(E_SELF, "KE")
    S["p1"], S["aid1"] = s, aid
    assert s.get(f"{API}/agents/me").json()["status"] == "submitted"


def test_self_register_joined_not_duplicated():
    _clear_reg_attempts()
    r = _register(E_SELF)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert DB.agents.count_documents({"email": E_SELF}) == 1
    assert DB.agents.find_one({"email": E_SELF})["status"] == "submitted"


def test_approve_without_waive_409():
    r = S["admin"].post(f"{API}/admin/agents/{S['aid1']}/decision", json={"action": "approve"})
    assert r.status_code == 409 and "Waive" in r.json()["detail"]


def test_request_payment_no_rule_422():
    r = S["admin"].post(f"{API}/admin/agents/{S['aid1']}/decision", json={"action": "request_payment"})
    assert r.status_code == 422, r.text
    assert "Partner registration" in r.json()["detail"] and "KE" in r.json()["detail"]


def test_create_group_fee_rule():
    r = S["admin"].post(f"{API}/tender-pro/emd-masters", json={
        "name": f"TEST Partner fee East Africa {RID}", "kind": "partner_registration", "countries": ["KE", "TZ"],
        "currency": "USD", "slabs": [{"fee_type": "fixed", "fixed_amount": 49}]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["kind"] == "partner_registration" and sorted(d["countries"]) == ["KE", "TZ"]
    S["rule"] = d.get("id") or d.get("_id")


def test_request_payment_creates_checkout():
    r = S["admin"].post(f"{API}/admin/agents/{S['aid1']}/decision", json={"action": "request_payment"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "payment_pending" and "email_sent" in d
    p = d["payment"]
    assert p["amount"] == 49.0 and p["currency"] == "USD" and p["session_id"].startswith("cs_test")
    assert p["checkout_url"].startswith("https://")
    S["sess1"] = p["session_id"]
    tx = DB.payment_transactions.find_one({"session_id": p["session_id"]})
    assert tx and tx["purpose"] == "partner_fee" and tx["agent_id"] == S["aid1"]


def test_partner_sees_payment_and_refresh():
    me = S["p1"].get(f"{API}/agents/me").json()
    assert me["status"] == "payment_pending" and me["payment"]["amount"] == 49.0
    r = S["p1"].post(f"{API}/agents/me/payment/refresh")
    assert r.status_code == 200 and r.json()["status"] == "payment_pending"


def test_resend_payment_link():
    r = S["admin"].post(f"{API}/admin/agents/{S['aid1']}/decision", json={"action": "request_payment"})
    assert r.status_code == 200 and r.json()["status"] == "payment_pending"
    S["sess2"] = r.json()["payment"]["session_id"]
    assert S["sess2"] != S["sess1"]


def test_old_session_does_not_approve():
    _apply(S["sess1"])
    assert DB.agents.find_one({"email": E_SELF})["status"] == "payment_pending"


def test_apply_partner_payment_approves_idempotent():
    _apply(S["sess2"])
    a = DB.agents.find_one({"email": E_SELF})
    assert a["status"] == "approved" and a["payment"]["status"] == "paid"
    code = a.get("partner_code")
    assert code and code.startswith("PT-") and len(code) == 7
    _apply(S["sess2"])
    a2 = DB.agents.find_one({"email": E_SELF})
    assert a2["partner_code"] == code and a2["payment"]["paid_at"] == a["payment"]["paid_at"]
    S["code1"] = code
    me = S["p1"].get(f"{API}/agents/me").json()
    assert me["status"] == "approved" and me["partner_code"] == code


# --- waive path ---
def test_waive_approve_assigns_code():
    _clear_reg_attempts()
    assert _register(E_WAIVE).status_code == 200
    _, aid = _join_and_submit(E_WAIVE, "IN")
    r = S["admin"].post(f"{API}/admin/agents/{aid}/decision", json={"action": "approve", "waive_fee": True})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    a = DB.agents.find_one({"email": E_WAIVE})
    assert a["fee_waived"] is True and a["partner_code"].startswith("PT-") and a["partner_code"] != S["code1"]
    d = S["admin"].get(f"{API}/admin/agents/{aid}").json()
    assert d["partner_code"] == a["partner_code"] and d["fee_waived"] is True
