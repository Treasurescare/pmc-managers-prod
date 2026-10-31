# v70: partner public profile cards (photo + bio opt-in) on homepage highlights, admin hide, partner join -> unified login.
import os
import time
import uuid
from datetime import datetime, timezone

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
S = {}
START = datetime.now(timezone.utc).isoformat()
SUP = {k: f"test_sup_{k}_{RID}@example.com" for k in ("one", "two")}
THIS = datetime.now(timezone.utc).strftime("%Y-%m")
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82")
BIO = "TEST bio: I onboard verified steel suppliers across Pune."


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
    for c in ("partner_commissions", "partner_statements", "partner_photos"):
        DB[c].delete_many({"partner_id": {"$in": ids}})
    for r in DB.registrations.find({"email": {"$regex": f"^test_sup_.*{RID}"}}):
        DB.uploads.delete_many({"key": {"$regex": f"^registration-docs/{r['_id']}/"}})
        DB.partner_commissions.delete_many({"registration_id": str(r["_id"])})
    DB.registrations.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.vendors.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.agents.delete_many({"email": {"$regex": f"^test_partner.*{RID}"}})
    DB.uploads.delete_many({"key": {"$regex": f"TEST{RID}"}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = _admin()
    S["orig_board"] = DB.partner_commission_settings.find_one({"key": "leaderboard"})
    S["seq"] = (DB.counters.find_one({"name": "vendor_seq"}) or {}).get("value")
    yield
    if S["orig_board"]:
        DB.partner_commission_settings.replace_one({"key": "leaderboard"}, S["orig_board"])
    else:
        DB.partner_commission_settings.delete_one({"key": "leaderboard"})
    _cleanup()
    if S["seq"] is not None:
        DB.counters.update_one({"name": "vendor_seq"}, {"$set": {"value": S["seq"]}})
    if DB.agents.count_documents({}) == 0:
        DB.counters.delete_one({"name": "partner_code"})


def _join(tag):
    email = f"test_partner_{tag}_{RID}@example.com"
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})
    assert requests.post(f"{API}/agents/register", json={"email": email, "name": f"TEST Partner {tag}"}).status_code == 200
    tok = DB.agents.find_one({"email": email})["invite_token"]
    s = requests.Session()
    r = s.post(f"{API}/agents/join/{tok}", json={"password": PW})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s, email


def _partner(tag):
    s, email = _join(tag)
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


def _hl_mine(code):
    d = requests.get(f"{API}/public/partner-highlights").json()
    return d, [i for i in d["items"] if i["code"] == code]


# --- setup: partner A badge winner (1 approved supplier), partner B (1 invite, no badge), partner N not approved ---
def test_setup():
    S["pa"], S["aid_a"], S["email_a"] = _partner("a")
    S["pb"], S["aid_b"], S["email_b"] = _partner("b")
    S["pn"], S["email_n"] = _join("n")
    S["code_a"] = DB.agents.find_one({"_id": ObjectId(S["aid_a"])})["partner_code"]
    S["code_b"] = DB.agents.find_one({"_id": ObjectId(S["aid_b"])})["partner_code"]
    r = S["pa"].post(f"{API}/agents/me/suppliers", json={"company_name": f"TEST Supplier one {RID}", "email": SUP["one"], "mobile": "+91 9876543210"})
    assert r.status_code == 200, r.text
    rid1 = r.json()["id"]
    ctok = DB.registrations.find_one({"_id": ObjectId(rid1)})["partner_consent_token"]
    assert requests.post(f"{API}/supplier-invites/{ctok}", json={"decision": "self", "signer_name": "TEST Self", "consents": {"data_privacy": True}}).status_code == 200
    DB.registrations.update_one({"_id": ObjectId(rid1)}, {"$set": {"registered_address": "1 TEST Road", "country": "IN",
                                                                  "registration_number": f"TESTREG{RID}", "legal_entity_type": "Private Limited", "status": "submitted"}})
    assert S["admin"].post(f"{API}/registrations/{rid1}/decision", json={"action": "approve"}).status_code == 200
    DB.partner_commission_settings.update_one({"key": "leaderboard"}, {"$set": {"show_names": False}}, upsert=True)


# --- partner public-profile endpoints ---
def test_profile_default_empty():
    r = S["pa"].get(f"{API}/agents/me/public-profile")
    assert r.status_code == 200, r.text
    assert r.json().get("photo_url") is None and not r.json().get("show")


def test_non_approved_partner_403():
    pn = S["pn"]
    assert pn.get(f"{API}/agents/me/public-profile").status_code == 403
    assert pn.put(f"{API}/agents/me/public-profile", json={"bio": "x", "show": True}).status_code == 403
    assert pn.post(f"{API}/agents/me/public-photo", files={"file": ("a.png", PNG, "image/png")}).status_code == 403
    assert pn.get(f"{API}/agents/me/public-photo").status_code == 403


def test_unauth_401():
    assert requests.get(f"{API}/agents/me/public-profile").status_code in (401, 403)
    assert requests.get(f"{API}/agents/me/public-photo").status_code in (401, 403)


def test_put_requires_csrf():
    r = requests.put(f"{API}/agents/me/public-profile", cookies=S["pa"].cookies, json={"bio": "x", "show": True})
    assert r.status_code in (401, 403), r.status_code
    r = requests.post(f"{API}/agents/me/public-photo", cookies=S["pa"].cookies, files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code in (401, 403), r.status_code


def test_bio_too_long_422():
    assert S["pa"].put(f"{API}/agents/me/public-profile", json={"bio": "x" * 281, "show": True}).status_code == 422
    assert S["pa"].put(f"{API}/agents/me/public-profile", json={"bio": "x" * 280, "show": False}).status_code == 200


def test_highlights_no_optin_code_only():
    d, mine = _hl_mine(S["code_a"])
    assert d["month"] == THIS and len(mine) == 1, d
    it = mine[0]
    assert it["partner"] == S["code_a"]
    assert "bio" not in it and "photo_url" not in it
    assert not [i for i in d["items"] if i["code"] == S["code_b"]]


def test_photo_bad_type_422():
    r = S["pa"].post(f"{API}/agents/me/public-photo", files={"file": ("a.gif", b"GIF89a....", "image/gif")})
    assert r.status_code == 422, r.text
    r = S["pa"].post(f"{API}/agents/me/public-photo", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 422


def test_photo_too_big_413():
    r = S["pa"].post(f"{API}/agents/me/public-photo", files={"file": ("big.png", PNG + b"\x00" * (2 * 1024 * 1024 + 10), "image/png")})
    assert r.status_code == 413, r.text


def test_photo_upload_and_get():
    r = S["pa"].post(f"{API}/agents/me/public-photo", files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 200 and r.json() == {"ok": True}, r.text
    r = S["pa"].get(f"{API}/agents/me/public-photo")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/png") and r.content == PNG
    p = S["pa"].get(f"{API}/agents/me/public-profile").json()
    assert p["photo_url"] and p["photo_url"].startswith("/api/v1/agents/me/public-photo")
    # not opted in yet -> public photo 404
    assert requests.get(f"{API}/public/partner-photo/{S['code_a']}").status_code == 404


def test_optin_and_highlights_show_profile():
    r = S["pa"].put(f"{API}/agents/me/public-profile", json={"bio": f"  {BIO}  ", "show": True})
    assert r.status_code == 200 and r.json()["bio"] == BIO and r.json()["show"] is True
    g = S["pa"].get(f"{API}/agents/me/public-profile").json()
    assert g["bio"] == BIO and g["show"] is True and g.get("photo_at")
    d, mine = _hl_mine(S["code_a"])
    assert len(mine) == 1, d
    it = mine[0]
    assert it["partner"] == "TEST Partner a Ltd", it  # name even though show_names False
    assert it["bio"] == BIO
    assert it["photo_url"].startswith(f"/api/v1/public/partner-photo/{S['code_a']}")
    r = requests.get(BASE_URL + it["photo_url"])
    assert r.status_code == 200 and r.content == PNG and r.headers.get("x-content-type-options") == "nosniff"


def test_public_photo_unknown_404():
    assert requests.get(f"{API}/public/partner-photo/NOPE{RID}").status_code == 404
    assert requests.get(f"{API}/public/partner-photo/{S['code_b']}").status_code == 404


def test_admin_hide_requires_admin_and_csrf():
    u = f"{API}/admin/agents/{S['aid_a']}/public-profile/hide"
    assert requests.post(u, json={"hidden": True}).status_code in (401, 403)
    assert requests.post(u, cookies=S["admin"].cookies, json={"hidden": True}).status_code in (401, 403)
    assert S["pa"].post(u, json={"hidden": True}).status_code in (401, 403)
    assert S["admin"].post(f"{API}/admin/agents/{'0'*24}/public-profile/hide", json={"hidden": True}).status_code == 404


def test_admin_hide_and_restore():
    u = f"{API}/admin/agents/{S['aid_a']}/public-profile/hide"
    r = S["admin"].post(u, json={"hidden": True})
    assert r.status_code == 200 and r.json() == {"hidden": True}
    det = S["admin"].get(f"{API}/admin/agents/{S['aid_a']}").json()
    assert det["public_profile"]["hidden"] is True and det["public_profile"]["show"] is True
    _, mine = _hl_mine(S["code_a"])
    assert mine and mine[0]["partner"] == S["code_a"] and "bio" not in mine[0] and "photo_url" not in mine[0]
    assert requests.get(f"{API}/public/partner-photo/{S['code_a']}").status_code == 404
    # partner re-saving cannot clear the admin hide
    S["pa"].put(f"{API}/agents/me/public-profile", json={"bio": BIO, "show": True})
    assert S["pa"].get(f"{API}/agents/me/public-profile").json().get("hidden") is True
    assert requests.get(f"{API}/public/partner-photo/{S['code_a']}").status_code == 404
    r = S["admin"].post(u, json={"hidden": False})
    assert r.status_code == 200
    _, mine = _hl_mine(S["code_a"])
    assert mine[0]["partner"] == "TEST Partner a Ltd" and mine[0]["bio"] == BIO
    assert requests.get(f"{API}/public/partner-photo/{S['code_a']}").status_code == 200


def test_optout_removes():
    assert S["pa"].put(f"{API}/agents/me/public-profile", json={"bio": BIO, "show": False}).status_code == 200
    _, mine = _hl_mine(S["code_a"])
    assert mine[0]["partner"] == S["code_a"] and "bio" not in mine[0]
    assert requests.get(f"{API}/public/partner-photo/{S['code_a']}").status_code == 404
    # restore opt-in for UI tests if run afterwards
    S["pa"].put(f"{API}/agents/me/public-profile", json={"bio": BIO, "show": True})


# --- partner join sets password -> unified login ---
def test_join_password_login():
    for pw in (PW,):
        r = requests.post(f"{API}/agents/auth/login", json={"email": S["email_n"], "password": pw})
        assert r.status_code == 200 and r.json()["email"] == S["email_n"], r.text
    assert requests.post(f"{API}/agents/auth/login", json={"email": S["email_n"], "password": "Wrong@12345"}).status_code == 401
