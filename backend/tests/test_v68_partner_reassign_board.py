# v68: partner self-fill mode, mode switch, admin reassign supplier, leaderboard, partner code lifecycle stamping.
import os
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
RID = uuid.uuid4().hex[:6]
PW = "PartnerPw@123"
VPW = "VendorPw@12345"
S = {}
START = datetime.now(timezone.utc).isoformat()
SUP = {k: f"test_sup_{k}_{RID}@example.com" for k in ("one", "two", "three")}
NOTICE = f"TEST-NTC-{RID}"
KEYS = ["partner_help", "my_review", "data_privacy", "confidentiality", "my_responsibility", "can_revoke"]


def _admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    if r.json().get("access_token"):
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def _cleanup():
    ids = [str(a["_id"]) for a in DB.agents.find({"email": {"$regex": f"^test_partner.*{RID}"}})]
    DB.partner_commissions.delete_many({"partner_id": {"$in": ids}})
    for r in DB.registrations.find({"email": {"$regex": f"^test_sup_.*{RID}"}}):
        DB.uploads.delete_many({"key": {"$regex": f"^registration-docs/{r['_id']}/"}})
        DB.partner_commissions.delete_many({"registration_id": str(r["_id"])})
    DB.registrations.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.vendors.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.agents.delete_many({"email": {"$regex": f"^test_partner.*{RID}"}})
    DB.bids.delete_many({"notice_ref": NOTICE})
    DB.notices.delete_many({"notice_ref": NOTICE})
    DB.uploads.delete_many({"key": {"$regex": f"^bid-docs/TEST{RID}"}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = _admin()
    S["orig_settings"] = DB.partner_commission_settings.find_one({"key": "default"})
    S["orig_board"] = DB.partner_commission_settings.find_one({"key": "leaderboard"})
    S["seq"] = {n: (DB.counters.find_one({"name": n}) or {}).get("value") for n in ("vendor_seq", "bid_seq")}
    yield
    for key in ("default", "leaderboard"):
        orig = S["orig_settings"] if key == "default" else S["orig_board"]
        if orig:
            DB.partner_commission_settings.replace_one({"key": key}, orig)
        else:
            DB.partner_commission_settings.delete_one({"key": key})
    _cleanup()
    for n, v in S["seq"].items():
        if v is not None:
            DB.counters.update_one({"name": n}, {"$set": {"value": v}})
    if DB.agents.count_documents({}) == 0:
        DB.counters.delete_one({"name": "partner_code"})


def _partner(tag, approve=True):
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
    if approve:
        r = S["admin"].post(f"{API}/admin/agents/{aid}/decision", json={"action": "approve", "waive_fee": True})
        assert r.status_code == 200, r.text
    return s, aid


def _invite(s, key):
    r = s.post(f"{API}/agents/me/suppliers", json={"company_name": f"TEST Supplier {key} {RID}", "email": SUP[key], "mobile": "+91 9876543210"})
    assert r.status_code == 200, r.text
    reg = DB.registrations.find_one({"_id": ObjectId(r.json()["id"])})
    return r.json()["id"], reg["partner_consent_token"], reg["magic_token"]


def _approve(rid):
    DB.registrations.update_one({"_id": ObjectId(rid)}, {"$set": {
        "registered_address": "1 TEST Road", "country": "IN", "registration_number": f"TESTREG{RID}{rid[-4:]}",
        "legal_entity_type": "Private Limited", "status": "submitted"}})
    r = S["admin"].post(f"{API}/registrations/{rid}/decision", json={"action": "approve"})
    assert r.status_code == 200, r.text
    return DB.registrations.find_one({"_id": ObjectId(rid)})["vendor_ref"]


# --- setup ---
def test_setup():
    S["pa"], S["aid_a"] = _partner("a")
    S["pb"], S["aid_b"] = _partner("b")
    S["pc"], S["aid_c"] = _partner("c", approve=False)
    S["code_a"] = DB.agents.find_one({"_id": ObjectId(S["aid_a"])})["partner_code"]
    S["code_b"] = DB.agents.find_one({"_id": ObjectId(S["aid_b"])})["partner_code"]
    r = S["admin"].put(f"{API}/admin/partner-commission/settings",
                       json={"currency": "USD", "onboarding_amount": 20, "deal_type": "percent", "deal_value": 1})
    assert r.status_code == 200


# --- self-fill consent ---
def test_self_fill_consent():
    S["rid1"], ctok, S["magic1"] = _invite(S["pa"], "one")
    url = f"{API}/supplier-invites/{ctok}"
    assert requests.post(url, json={"decision": "self", "signer_name": "ab", "consents": {"data_privacy": True}}).status_code == 422
    assert requests.post(url, json={"decision": "self", "signer_name": "TEST Self Signer", "consents": {}}).status_code == 422
    r = requests.post(url, json={"decision": "self", "signer_name": "TEST Self Signer", "consents": {"data_privacy": True}})
    assert r.status_code == 200, r.text
    assert r.json() == {"partner_access": "self_fill", "resume_path": f"/register/resume?token={S['magic1']}"}
    assert requests.post(url, json={"decision": "self", "signer_name": "TEST Self Signer", "consents": {"data_privacy": True}}).status_code == 409
    assert S["pa"].post(f"{API}/agents/me/suppliers/{S['rid1']}/edit-link").status_code == 403
    d = requests.get(f"{API}/registrations/resume/{S['magic1']}").json()
    assert d["partner"]["access"] == "self_fill" and d["partner"]["code"] == S["code_a"]


# --- mode switching ---
def test_mode_switch():
    u = f"{API}/registrations/{S['rid1']}/partner-access/mode"
    assert requests.post(f"{u}?token=wrong{RID}", json={"mode": "partner", "signer_name": "TEST X"}).status_code == 404
    assert requests.post(f"{u}?token={S['magic1']}", json={"mode": "partner"}).status_code == 422
    r = requests.post(f"{u}?token={S['magic1']}", json={"mode": "partner", "signer_name": "TEST Grant Signer"})
    assert r.status_code == 200 and r.json()["partner_access"] == "granted"
    r = S["pa"].post(f"{API}/agents/me/suppliers/{S['rid1']}/edit-link")
    assert r.status_code == 200, r.text
    ptok = r.json()["path"].split("token=")[1].split("&")[0]
    assert S["pa"].get(f"{API}/registrations/resume/{ptok}").status_code == 200
    r = requests.post(f"{u}?token={S['magic1']}", json={"mode": "self"})
    assert r.status_code == 200 and r.json()["partner_access"] == "self_fill"
    assert S["pa"].get(f"{API}/registrations/resume/{ptok}").status_code == 404
    assert S["pa"].patch(f"{API}/registrations/{S['rid1']}?token={ptok}", json={"trade_name": "x"}).status_code == 404
    # idempotent
    assert requests.post(f"{u}?token={S['magic1']}", json={"mode": "self"}).json()["partner_access"] == "self_fill"


# --- approval of self_fill ---
def test_self_fill_approval_commission_and_vendor_fields():
    S["vref1"] = _approve(S["rid1"])
    rows = list(DB.partner_commissions.find({"registration_id": S["rid1"]}))
    assert len(rows) == 1 and rows[0]["partner_id"] == S["aid_a"] and rows[0]["amount"] == 20
    v = DB.vendors.find_one({"email": SUP["one"]})
    assert v["partner_code"] == S["code_a"] and v["partner_id"] == S["aid_a"] and "TEST Partner a" in v["partner_name"]
    u = f"{API}/registrations/{S['rid1']}/partner-access/mode?token={S['magic1']}"
    assert requests.post(u, json={"mode": "partner", "signer_name": "TEST Late"}).status_code == 409
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_a']}/commissions",
                        json={"vendor_ref": S["vref1"], "deal_ref": f"TEST-D1-{RID}", "business_amount": 1000})
    assert r.status_code == 200 and r.json()["amount"] == 10 and r.json()["partner_id"] == S["aid_a"]


# --- reassign validations ---
def test_reassign_validations():
    u = f"{API}/admin/partner-suppliers/{S['rid1']}/reassign"
    assert S["admin"].post(u, json={"partner_id": S["aid_c"], "note": "TEST move to unapproved"}).status_code == 422
    assert S["admin"].post(u, json={"partner_id": S["aid_a"], "note": "TEST same partner"}).status_code == 409
    assert S["admin"].post(u, json={"partner_id": S["aid_b"], "note": "abc"}).status_code == 422
    assert requests.post(u, cookies=S["admin"].cookies, json={"partner_id": S["aid_b"], "note": "TEST nocsrf"}).status_code in (401, 403)
    assert S["pa"].post(u, json={"partner_id": S["aid_b"], "note": "TEST partner tries"}).status_code in (401, 403)
    assert S["admin"].post(f"{API}/admin/partner-suppliers/{'0'*24}/reassign", json={"partner_id": S["aid_b"], "note": "TEST missing"}).status_code == 404


# --- reassign approved supplier ---
def test_reassign_approved():
    r = S["admin"].post(f"{API}/admin/partner-suppliers/{S['rid1']}/reassign", json={"partner_id": S["aid_b"], "note": "TEST geographic split"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["reconsent_sent"] is False and d["history"]["from"]["code"] == S["code_a"] and d["history"]["to"]["code"] == S["code_b"]
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid1"])})
    assert reg["partner_id"] == S["aid_b"] and reg["partner_access"] == "self_fill" and len(reg["partner_history"]) == 1
    v = DB.vendors.find_one({"email": SUP["one"]})
    assert v["partner_code"] == S["code_b"] and v["partner_id"] == S["aid_b"] and v["partner_history"][0]["note"] == "TEST geographic split"
    w = S["admin"].get(f"{API}/admin/agents/{S['aid_b']}/wallet").json()
    sup = [x for x in w["suppliers"] if x["id"] == S["rid1"]][0]
    assert sup["history"][0]["note"] == "TEST geographic split"
    k = S["admin"].get(f"{API}/vendors/{S['vref1']}/kpi")
    assert k.status_code == 200, k.text
    assert k.json()["partner_code"] == S["code_b"] and len(k.json()["partner_history"]) == 1


def test_commission_after_reassign():
    old = list(DB.partner_commissions.find({"registration_id": S["rid1"]}))
    assert len(old) == 2 and all(c["partner_id"] == S["aid_a"] and c["partner_code"] == S["code_a"] for c in old)
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_a']}/commissions",
                        json={"vendor_ref": S["vref1"], "deal_ref": f"TEST-D2-{RID}", "business_amount": 1000})
    assert r.status_code == 422
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_b']}/commissions",
                        json={"vendor_ref": S["vref1"], "deal_ref": f"TEST-D3-{RID}", "business_amount": 2000})
    assert r.status_code == 200 and r.json()["partner_id"] == S["aid_b"] and r.json()["amount"] == 20
    wa = S["pa"].get(f"{API}/agents/me/wallet").json()
    assert wa["totals"]["USD"]["due"] == 30


# --- reassign draft (granted) -> re-consent ---
def test_reassign_draft_reconsent():
    S["rid2"], ctok, magic2 = _invite(S["pa"], "two")
    assert requests.post(f"{API}/supplier-invites/{ctok}", json={"decision": "accept", "signer_name": "TEST Signer",
                                                                 "consents": {k: True for k in KEYS}}).status_code == 200
    ptok = S["pa"].post(f"{API}/agents/me/suppliers/{S['rid2']}/edit-link").json()["path"].split("token=")[1].split("&")[0]
    r = S["admin"].post(f"{API}/admin/partner-suppliers/{S['rid2']}/reassign", json={"partner_id": S["aid_b"], "note": "TEST reorganisation"})
    assert r.status_code == 200 and r.json()["reconsent_sent"] is True
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid2"])})
    assert reg["partner_access"] == "awaiting_consent" and reg["partner_id"] == S["aid_b"] and reg["partner_edit_token"] is None
    assert reg["partner_consent_token"] and reg["partner_consent_token"] != ctok
    assert S["pa"].get(f"{API}/registrations/resume/{ptok}").status_code == 404
    info = requests.get(f"{API}/supplier-invites/{reg['partner_consent_token']}").json()
    assert info["partner_code"] == S["code_b"] and info["partner_access"] == "awaiting_consent"
    # old (used) token: 409 already responded — informational
    print("old consent token after reassign:", requests.get(f"{API}/supplier-invites/{ctok}").status_code)
    assert S["pb"].get(f"{API}/agents/me/suppliers").status_code == 200
    assert any(i["id"] == S["rid2"] for i in S["pb"].get(f"{API}/agents/me/suppliers").json()["items"])
    assert not any(i["id"] == S["rid2"] for i in S["pa"].get(f"{API}/agents/me/suppliers").json()["items"])
    # new partner accept works
    r = requests.post(f"{API}/supplier-invites/{reg['partner_consent_token']}", json={"decision": "accept", "signer_name": "TEST Signer",
                                                                                    "consents": {k: True for k in KEYS}})
    assert r.status_code == 200 and r.json()["partner_access"] == "granted"
    assert S["pb"].post(f"{API}/agents/me/suppliers/{S['rid2']}/edit-link").status_code == 200


# --- leaderboard ---
def test_leaderboard_partner_view():
    S["rid3"], _, _ = _invite(S["pa"], "three")
    assert S["pc"].get(f"{API}/agents/me/leaderboard").status_code == 403
    r = S["pa"].get(f"{API}/agents/me/leaderboard")
    assert r.status_code == 200, r.text
    d = r.json()
    print("partner A board me:", d["me"], "partners", d["partners"])
    assert d["month"] == datetime.now(timezone.utc).strftime("%Y-%m") and d["show_names"] is False
    # credit stays with the partner who invited/onboarded, even after a reassign
    assert d["me"]["is_me"] and d["me"]["invites"] == 3 and d["me"]["approved"] == 1
    assert "TEST Partner a" in d["me"]["label"]
    others = [x for x in d["rows"] if not x["is_me"]]
    assert all(x["label"] == x["code"] for x in others)
    assert all("id" not in x and "name" not in x for x in d["rows"])
    rb = S["pb"].get(f"{API}/agents/me/leaderboard").json()["me"]
    print("partner B board me:", rb)
    assert rb["approved"] == 0 and rb["invites"] == 0 and d["me"]["rank"] < rb["rank"]


def test_leaderboard_admin_and_show_names():
    assert requests.get(f"{API}/admin/partners/leaderboard").status_code in (401, 403)
    r = S["admin"].get(f"{API}/admin/partners/leaderboard")
    assert r.status_code == 200
    rows = r.json()["rows"]
    ranks = [x["rank"] for x in rows]
    assert ranks == sorted(ranks)
    a = [x for x in rows if x["id"] == S["aid_a"]][0]
    assert a["approved"] == 1 and "TEST Partner a" in a["name"]
    assert S["pa"].put(f"{API}/admin/partners/leaderboard", json={"show_names": True}).status_code in (401, 403)
    r = S["admin"].put(f"{API}/admin/partners/leaderboard", json={"show_names": True})
    assert r.status_code == 200 and r.json()["show_names"] is True
    d = S["pa"].get(f"{API}/agents/me/leaderboard").json()
    rowb = [x for x in d["rows"] if x["code"] == S["code_b"]]
    assert d["show_names"] is True and rowb and "TEST Partner b" in rowb[0]["label"]
    S["admin"].put(f"{API}/admin/partners/leaderboard", json={"show_names": False})
    assert S["admin"].get(f"{API}/admin/partners/leaderboard").json()["show_names"] is False


# --- lifecycle: vendor profile + bid stamping ---
def test_vendor_profile_and_bid_stamp():
    import bcrypt as _b
    DB.vendors.update_one({"email": SUP["one"]}, {"$set": {"password_hash": _b.hashpw(VPW.encode(), _b.gensalt()).decode(),
                                                           "must_change_password": False, "kyc_status": "verified"}})
    vs = requests.Session()
    r = vs.post(f"{API}/vendor/auth/login", json={"email": SUP["one"], "password": VPW})
    assert r.status_code == 200, r.text
    vs.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    vid = r.json()["id"]
    p = vs.get(f"{API}/vendor/profile")
    assert p.status_code == 200 and p.json()["partner_code"] == S["code_b"] and "TEST Partner b" in p.json()["partner_name"]
    DB.notices.insert_one({"notice_ref": NOTICE, "title": f"TEST notice {RID}", "is_published": True, "kyc_bypass": True,
                           "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
                           "budget_amount": 0, "emd_config": {}, "created_at": START})
    docs = []
    for kind in ("technical", "commercial"):
        key = f"bid-docs/TEST{RID}/{kind}.pdf"
        DB.uploads.insert_one({"key": key, "sealed": True, "owner_vendor_id": vid, "created_at": START})
        docs.append({"kind": kind, "key": key, "filename": f"{kind}.pdf", "size_bytes": 10, "uploaded_at": START})
    r = vs.post(f"{API}/bids", json={"notice_ref": NOTICE, "price_amount": 1000, "price_currency": "USD", "documents": docs})
    print("bid create:", r.status_code, r.text[:300])
    assert r.status_code in (200, 201), r.text
    b = DB.bids.find_one({"notice_ref": NOTICE})
    assert b["partner_code"] == S["code_b"] and b["partner_id"] == S["aid_b"]
    a = S["admin"].get(f"{API}/bids/admin/{b['_id']}")
    assert a.status_code == 200 and a.json().get("partner_code") == S["code_b"]
