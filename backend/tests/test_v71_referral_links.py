# v71: partner referral links (public partner lookup, tagged self-fill registrations), admin invite/resend email_error.
import time
import uuid

import pytest
import requests
from bson import ObjectId

import test_v69_partner_statements_login as t

RID = uuid.uuid4().hex[:6]
t.RID = RID
API = t.API
DB = t.DB
S = {}
SUP = {k: f"test_sup_{k}_{RID}@example.com" for k in ("ref", "bad", "lower", "pending")}


def _cleanup():
    t._cleanup()
    DB.agents.delete_many({"email": {"$regex": f"^test_.*{RID}@example.com$"}})
    DB.registrations.delete_many({"email": {"$regex": f"^test_.*{RID}@example.com$"}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = t._admin()
    t.S["admin"] = S["admin"]
    yield
    time.sleep(1)
    _cleanup()
    if DB.agents.count_documents({}) == 0:
        DB.counters.delete_one({"name": "partner_code"})


# --- setup approved partner ---
def test_setup_partner():
    s, aid, email = t._partner("ref")
    a = DB.agents.find_one({"_id": ObjectId(aid)})
    assert a["status"] == "approved" and a.get("partner_code", "").startswith("PT-")
    S.update(ps=s, aid=aid, code=a["partner_code"], name=a.get("legal_name") or a["name"])


# --- public partner lookup ---
def test_public_partner_ok():
    r = requests.get(f"{API}/public/partner/{S['code']}")
    assert r.status_code == 200, r.text
    assert r.json() == {"code": S["code"], "name": S["name"]}


def test_public_partner_lowercase():
    r = requests.get(f"{API}/public/partner/{S['code'].lower()}")
    assert r.status_code == 200 and r.json()["code"] == S["code"]


def test_public_partner_unknown_404():
    assert requests.get(f"{API}/public/partner/PT-ZZZZ{RID}").status_code == 404


def test_public_partner_not_approved_404():
    em = f"test_partner_pending_{RID}@example.com"
    DB.agents.insert_one({"email": em, "name": "TEST pending", "status": "pending_review", "partner_code": f"PT-P{RID}"})
    assert requests.get(f"{API}/public/partner/PT-P{RID}").status_code == 404


# --- registrations with partner_code ---
def _create(key, code):
    body = {"email": SUP[key], "company_name": f"TEST Ref {key} {RID}", "country": "IN", "data_processing_consent": True}
    if code is not None:
        body["partner_code"] = code
    r = requests.post(f"{API}/registrations", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_referral_registration_tagged():
    rid = _create("ref", S["code"])
    reg = DB.registrations.find_one({"_id": ObjectId(rid)})
    assert reg["partner_id"] == S["aid"] and reg["invited_by_partner_id"] == S["aid"]
    assert reg["partner_code"] == S["code"]
    assert reg["partner_access"] == "self_fill" and reg["partner_source"] == "link"
    assert reg["partner_claim_expires_at"] > reg["partner_invited_at"]
    S["rid"] = rid


def test_referral_lowercase_code_tagged():
    rid = _create("lower", S["code"].lower())
    assert DB.registrations.find_one({"_id": ObjectId(rid)}).get("partner_id") == S["aid"]


def test_invalid_code_untagged():
    rid = _create("bad", f"PT-BAD{RID}")
    reg = DB.registrations.find_one({"_id": ObjectId(rid)})
    for k in ("partner_id", "partner_code", "partner_access", "partner_source", "invited_by_partner_id"):
        assert k not in reg


def test_not_approved_code_untagged():
    rid = _create("pending", f"PT-P{RID}")
    assert "partner_id" not in DB.registrations.find_one({"_id": ObjectId(rid)})


def test_referral_in_partner_suppliers():
    r = S["ps"].get(f"{API}/agents/me/suppliers")
    assert r.status_code == 200
    rows = {x["id"]: x for x in r.json()["items"]}
    assert S["rid"] in rows
    assert rows[S["rid"]]["partner_access"] == "self_fill"
    assert rows[S["rid"]]["email"] == SUP["ref"]


def test_referral_resume_works_for_supplier():
    tok = DB.registrations.find_one({"_id": ObjectId(S["rid"])})["magic_token"]
    r = requests.get(f"{API}/registrations/resume/{tok}")
    assert r.status_code == 200, r.text
    assert "partner_id" not in r.json()


# --- admin invite/resend email_error ---
def test_admin_invite_email_error():
    em = f"test_partner_inv_{RID}@example.com"
    r = S["admin"].post(f"{API}/admin/agents/invite", json={"email": em, "name": "TEST Inv"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert "email_error" in d
    if not d["email_sent"]:
        assert isinstance(d["email_error"], str) and len(d["email_error"]) > 5, d
        print("invite email_error:", d["email_error"])
    else:
        assert d["email_error"] == ""
    S["inv"] = d["id"]


def test_admin_resend_email_error():
    r = S["admin"].post(f"{API}/admin/agents/{S['inv']}/resend")
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) >= {"email_sent", "email_error"}
    if not d["email_sent"]:
        assert len(d["email_error"]) > 5
        print("resend email_error:", d["email_error"])


def test_admin_resend_non_invited_409():
    assert S["admin"].post(f"{API}/admin/agents/{S['aid']}/resend").status_code == 409
