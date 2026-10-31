# v67: Partner-led supplier onboarding (invite → consent → partner fills → supplier submits/revokes) + commission wallet.
import os
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
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
API = f"{BASE_URL}/api/v1"
RID = uuid.uuid4().hex[:6]
PW = "PartnerPw@123"
S = {}
START = datetime.now(timezone.utc).isoformat()
SUP = {k: f"test_sup_{k}_{RID}@example.com" for k in ("one", "two", "three", "self")}


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
    regs = list(DB.registrations.find({"email": {"$regex": f"^test_sup_.*{RID}"}}))
    for r in regs:
        DB.uploads.delete_many({"key": {"$regex": f"^registration-docs/{r['_id']}/"}})
    DB.registrations.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.vendors.delete_many({"email": {"$regex": f"^test_sup_.*{RID}"}})
    DB.agents.delete_many({"email": {"$regex": f"^test_partner.*{RID}"}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": RID}})
    DB.agent_login_attempts.delete_many({"identifier": {"$regex": "^reg:"}, "at": {"$gte": START}})


@pytest.fixture(scope="module", autouse=True)
def _mod():
    _cleanup()
    S["admin"] = _admin()
    S["orig_settings"] = DB.partner_commission_settings.find_one({"key": "default"})
    S["vseq"] = (DB.counters.find_one({"name": "vendor_seq"}) or {}).get("value")
    yield
    if S.get("orig_settings"):
        DB.partner_commission_settings.replace_one({"key": "default"}, S["orig_settings"])
    else:
        DB.partner_commission_settings.delete_one({"key": "default"})
    _cleanup()
    if S.get("vseq") is not None:  # don't let TEST approvals burn real vendor refs
        DB.counters.update_one({"name": "vendor_seq"}, {"$set": {"value": S["vseq"]}})
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


def _invite(s, key, company=None):
    return s.post(f"{API}/agents/me/suppliers", json={"company_name": company or f"TEST Supplier {key} {RID}",
                                                      "email": SUP[key], "mobile": "+91 9876543210"})


def _consent_body(name="TEST Supplier Signer"):
    keys = ["partner_help", "my_review", "data_privacy", "confidentiality", "my_responsibility", "can_revoke"]
    return {"decision": "accept", "signer_name": name, "consents": {k: True for k in keys}}


def _fill_required(rid):
    DB.registrations.update_one({"_id": ObjectId(rid)}, {"$set": {
        "registered_address": "1 TEST Road", "country": "IN", "registration_number": f"TESTREG{RID}",
        "legal_entity_type": "Private Limited", "status": "submitted"}})


# --- partners setup ---
def test_setup_partners():
    S["pa"], S["aid_a"] = _partner("a")
    S["pb"], S["aid_b"] = _partner("b")
    S["pc"], S["aid_c"] = _partner("c", approve=False)
    assert S["pa"].get(f"{API}/agents/me").json()["status"] == "approved"


def test_non_approved_partner_403():
    assert S["pc"].get(f"{API}/agents/me/suppliers").status_code == 403
    assert _invite(S["pc"], "three").status_code == 403


# --- invite + duplicates ---
def test_invite_supplier_creates_awaiting_consent():
    r = _invite(S["pa"], "one")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["partner_access"] == "awaiting_consent" and d["status"] == "draft" and d["email"] == SUP["one"]
    assert "email_sent" in d
    S["rid1"] = d["id"]
    reg = DB.registrations.find_one({"_id": ObjectId(d["id"])})
    assert reg["partner_id"] == S["aid_a"] and reg["partner_code"].startswith("PT-")
    S["ctok1"], S["magic1"] = reg["partner_consent_token"], reg["magic_token"]
    items = S["pa"].get(f"{API}/agents/me/suppliers").json()["items"]
    assert any(i["id"] == S["rid1"] for i in items)


def test_invite_without_csrf_403():
    r = requests.post(f"{API}/agents/me/suppliers", cookies=S["pa"].cookies,
                      json={"company_name": "TEST x", "email": SUP["three"], "mobile": "+91 9876543210"})
    assert r.status_code == 403


def test_dup_same_partner_409():
    r = _invite(S["pa"], "one")
    assert r.status_code == 409 and "already invited" in r.json()["detail"]


def test_dup_other_partner_claimed_409():
    r = _invite(S["pb"], "one", company=f"TEST Other {RID}")
    assert r.status_code == 409 and "Another partner" in r.json()["detail"]


def test_dup_existing_vendor_409():
    v = DB.vendors.find_one({}, {"email": 1})
    if not v:
        pytest.skip("no vendors")
    r = S["pa"].post(f"{API}/agents/me/suppliers", json={"company_name": f"TEST v {RID}", "email": v["email"], "mobile": "+91 9876543210"})
    assert r.status_code == 409 and "registered PMC supplier" in r.json()["detail"]


def test_dup_self_started_409():
    DB.registrations.insert_one({"email": SUP["self"], "company_name": f"TEST Self {RID}", "status": "draft", "magic_token": f"x{RID}", "created_at": START})
    r = _invite(S["pa"], "self")
    assert r.status_code == 409 and "already started" in r.json()["detail"]


# --- before consent ---
def test_before_consent_blocks():
    assert requests.get(f"{API}/registrations/resume/{S['magic1']}").status_code == 403
    assert S["pa"].post(f"{API}/agents/me/suppliers/{S['rid1']}/edit-link").status_code == 403
    r = S["pa"].post(f"{API}/agents/me/suppliers/{S['rid1']}/resend")
    assert r.status_code == 200
    S["ctok1"] = DB.registrations.find_one({"_id": ObjectId(S["rid1"])})["partner_consent_token"]


# --- consent ---
def test_invite_info_public():
    r = requests.get(f"{API}/supplier-invites/{S['ctok1']}")
    assert r.status_code == 200
    d = r.json()
    assert d["partner_code"].startswith("PT-") and "TEST Partner a" in d["partner_name"]
    assert len(d["consents"]) == 6 and d["partner_access"] == "awaiting_consent"
    assert requests.get(f"{API}/supplier-invites/bogus{RID}").status_code == 404


def test_consent_validation_422():
    b = _consent_body("ab")
    assert requests.post(f"{API}/supplier-invites/{S['ctok1']}", json=b).status_code == 422
    b = _consent_body()
    b["consents"].pop("can_revoke")
    assert requests.post(f"{API}/supplier-invites/{S['ctok1']}", json=b).status_code == 422


def test_consent_accept():
    r = requests.post(f"{API}/supplier-invites/{S['ctok1']}", json=_consent_body())
    assert r.status_code == 200, r.text
    assert r.json()["partner_access"] == "granted"
    assert r.json()["resume_path"] == f"/register/resume?token={S['magic1']}"
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid1"])})
    assert reg["partner_consent"]["signer_name"] == "TEST Supplier Signer" and reg["email_verified_at"]


def test_consent_second_response_409():
    r = requests.post(f"{API}/supplier-invites/{S['ctok1']}", json=_consent_body())
    print("second consent response:", r.status_code, r.text[:150])
    assert r.status_code == 409, f"expected 409, got {r.status_code} (token nulled after accept)"


# --- partner editing ---
def test_partner_edit_link_and_resume():
    r = S["pa"].post(f"{API}/agents/me/suppliers/{S['rid1']}/edit-link")
    assert r.status_code == 200, r.text
    path = r.json()["path"]
    assert path.startswith("/register/resume?token=") and path.endswith("&from=partner")
    S["ptok1"] = path.split("token=")[1].split("&")[0]
    assert S["ptok1"] != S["magic1"]
    r = S["pa"].get(f"{API}/registrations/resume/{S['ptok1']}")
    assert r.status_code == 200 and r.json()["editor"] == "partner"
    assert "magic_token" not in r.json() and "partner_edit_token" not in r.json()
    assert requests.get(f"{API}/registrations/resume/{S['ptok1']}").status_code == 404
    # other partner's cookie must not work
    assert S["pb"].get(f"{API}/registrations/resume/{S['ptok1']}").status_code == 404


def test_partner_patch_strips_decl_signature():
    body = {"trade_name": f"TEST Trade {RID}", "website": "https://example.com", "decl_integrity": True,
            "decl_accuracy": True, "signature_name": "Partner Forged", "signature_date": "2026-01-01"}
    r = S["pa"].patch(f"{API}/registrations/{S['rid1']}?token={S['ptok1']}", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["editor"] == "partner"
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid1"])})
    assert reg["trade_name"] == f"TEST Trade {RID}"
    assert not reg.get("decl_integrity") and not reg.get("signature_name")
    assert "trade_name" in reg["partner_fields"] and "website" in reg["partner_fields"]
    assert not any(f.startswith(("decl_", "signature_")) for f in reg["partner_fields"])
    assert len(reg["partner_edits"]) >= 1


def test_partner_patch_without_cookie_404():
    r = requests.patch(f"{API}/registrations/{S['rid1']}?token={S['ptok1']}", json={"trade_name": "x"})
    assert r.status_code == 404


def test_partner_upload_doc_logged():
    r = S["pa"].post(f"{API}/registrations/{S['rid1']}/documents/tin_proof", data={"token": S["ptok1"]},
                     files={"file": ("tin.pdf", b"%PDF-1.4 tin", "application/pdf")})
    assert r.status_code == 200, r.text
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid1"])})
    assert "document:tin_proof" in reg["partner_fields"] and reg["document_slots"]["tin_proof"]


def test_supplier_sees_partner_fields():
    r = requests.get(f"{API}/registrations/resume/{S['magic1']}")
    assert r.status_code == 200
    d = r.json()
    assert d["editor"] == "supplier"
    assert "trade_name" in d["partner"]["fields"] and "document:tin_proof" in d["partner"]["fields"]
    assert d["partner"]["access"] == "granted" and d["partner"]["code"].startswith("PT-")


def test_partner_cannot_submit():
    r = S["pa"].post(f"{API}/registrations/{S['rid1']}/submit?token={S['ptok1']}")
    assert r.status_code == 404


def test_send_for_review():
    r = S["pa"].post(f"{API}/agents/me/suppliers/{S['rid1']}/send-for-review")
    assert r.status_code == 200 and r.json()["partner_stage"] == "ready_for_review"
    row = [i for i in S["pa"].get(f"{API}/agents/me/suppliers").json()["items"] if i["id"] == S["rid1"]][0]
    assert row["partner_stage"] == "ready_for_review" and row["edits"] >= 2


# --- supplier two: consent then revoke ---
def test_revoke_flow():
    r = _invite(S["pa"], "two")
    assert r.status_code == 200
    S["rid2"] = r.json()["id"]
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid2"])})
    S["magic2"] = reg["magic_token"]
    assert requests.post(f"{API}/supplier-invites/{reg['partner_consent_token']}", json=_consent_body()).status_code == 200
    ptok = S["pa"].post(f"{API}/agents/me/suppliers/{S['rid2']}/edit-link").json()["path"].split("token=")[1].split("&")[0]
    assert S["pa"].get(f"{API}/registrations/resume/{ptok}").status_code == 200
    assert requests.post(f"{API}/registrations/{S['rid2']}/partner-access/revoke?token=wrong").status_code == 404
    r = requests.post(f"{API}/registrations/{S['rid2']}/partner-access/revoke?token={S['magic2']}")
    assert r.status_code == 200 and r.json()["partner_access"] == "revoked"
    assert S["pa"].get(f"{API}/registrations/resume/{ptok}").status_code == 404
    assert S["pa"].patch(f"{API}/registrations/{S['rid2']}?token={ptok}", json={"trade_name": "x"}).status_code == 404
    assert S["pa"].post(f"{API}/agents/me/suppliers/{S['rid2']}/edit-link").status_code == 403
    assert requests.get(f"{API}/registrations/resume/{S['magic2']}").json()["partner"]["access"] == "revoked"


def test_decline_flow():
    r = _invite(S["pb"], "three")
    assert r.status_code == 200, r.text
    S["rid3"] = r.json()["id"]
    tok = DB.registrations.find_one({"_id": ObjectId(S["rid3"])})["partner_consent_token"]
    r = requests.post(f"{API}/supplier-invites/{tok}", json={"decision": "decline"})
    assert r.status_code == 200 and r.json()["partner_access"] == "declined"
    reg = DB.registrations.find_one({"_id": ObjectId(S["rid3"])})
    assert reg["status"] == "withdrawn" and reg["partner_access"] == "declined"


# --- commission settings ---
def test_commission_settings_get_put():
    assert S["admin"].get(f"{API}/admin/partner-commission/settings").status_code == 200
    r = S["admin"].put(f"{API}/admin/partner-commission/settings",
                       json={"currency": "usd", "onboarding_amount": 25, "deal_type": "percent", "deal_value": 2.5})
    assert r.status_code == 200, r.text
    g = S["admin"].get(f"{API}/admin/partner-commission/settings").json()
    assert g["currency"] == "USD" and g["onboarding_amount"] == 25 and g["deal_type"] == "percent" and g["deal_value"] == 2.5
    assert S["admin"].put(f"{API}/admin/partner-commission/settings", json={"onboarding_amount": -1}).status_code == 422


def test_partner_override_and_clear():
    r = S["admin"].put(f"{API}/admin/agents/{S['aid_b']}/commission",
                       json={"rule": {"currency": "EUR", "onboarding_amount": 10, "deal_type": "fixed", "deal_value": 40}})
    assert r.status_code == 200 and r.json()["commission"]["currency"] == "EUR"
    w = S["admin"].get(f"{API}/admin/agents/{S['aid_b']}/wallet").json()
    assert w["rule"]["source"] == "partner" and w["rule"]["deal_type"] == "fixed"
    S["admin"].put(f"{API}/admin/agents/{S['aid_a']}/commission",
                   json={"rule": {"currency": "EUR", "onboarding_amount": 1, "deal_type": "fixed", "deal_value": 1}})
    r = S["admin"].put(f"{API}/admin/agents/{S['aid_a']}/commission", json={"rule": None})
    assert r.status_code == 200 and r.json()["commission"] is None
    assert S["admin"].get(f"{API}/admin/agents/{S['aid_a']}/wallet").json()["rule"]["source"] == "default"


# --- approval accrues onboarding ---
def test_approve_creates_onboarding_commission():
    _fill_required(S["rid1"])
    r = S["admin"].post(f"{API}/registrations/{S['rid1']}/decision", json={"action": "approve"})
    assert r.status_code == 200, r.text
    rows = list(DB.partner_commissions.find({"registration_id": S["rid1"]}))
    assert len(rows) == 1 and rows[0]["kind"] == "onboarding" and rows[0]["status"] == "due"
    assert rows[0]["amount"] == 25 and rows[0]["currency"] == "USD" and rows[0]["partner_id"] == S["aid_a"]
    S["vref1"] = DB.registrations.find_one({"_id": ObjectId(S["rid1"])})["vendor_ref"]
    S["cid_onb"] = str(rows[0]["_id"])
    assert S["admin"].post(f"{API}/registrations/{S['rid1']}/decision", json={"action": "approve"}).status_code == 409
    assert DB.partner_commissions.count_documents({"registration_id": S["rid1"]}) == 1


def test_approve_revoked_no_commission():
    _fill_required(S["rid2"])
    r = S["admin"].post(f"{API}/registrations/{S['rid2']}/decision", json={"action": "approve"})
    assert r.status_code == 200, r.text
    assert DB.partner_commissions.count_documents({"registration_id": S["rid2"]}) == 0
    S["vref2"] = DB.registrations.find_one({"_id": ObjectId(S["rid2"])})["vendor_ref"]


# --- deal commissions ---
def test_deal_commission_percent():
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_a']}/commissions",
                        json={"vendor_ref": S["vref1"], "deal_ref": f"TEST-DEAL-{RID}", "business_amount": 10000})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["amount"] == 250 and d["kind"] == "deal" and d["status"] == "due" and "%" in d["basis"]
    S["cid_deal"] = d["id"]


def test_deal_commission_wrong_partner_rejected():
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_b']}/commissions",
                        json={"vendor_ref": S["vref1"], "deal_ref": "TEST-X", "business_amount": 1000})
    assert r.status_code in (400, 404, 409, 422)


def test_deal_commission_revoked_supplier_info():
    # informational: supplier who REMOVED partner access — partner can still get deal commission?
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_a']}/commissions",
                        json={"vendor_ref": S["vref2"], "deal_ref": "TEST-REV", "business_amount": 1000})
    print("deal for revoked supplier:", r.status_code, r.text[:200])
    if r.status_code == 200:
        DB.partner_commissions.delete_one({"_id": ObjectId(r.json()["id"])})


def test_deal_commission_fixed_override():
    # partner B override fixed 40 EUR: needs a supplier onboarded by B — reassign rid1 temporarily is invasive; verify compute via A override
    S["admin"].put(f"{API}/admin/agents/{S['aid_a']}/commission",
                   json={"rule": {"currency": "EUR", "onboarding_amount": 5, "deal_type": "fixed", "deal_value": 40}})
    r = S["admin"].post(f"{API}/admin/agents/{S['aid_a']}/commissions",
                        json={"vendor_ref": S["vref1"], "deal_ref": f"TEST-FIX-{RID}", "business_amount": 0})
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 40 and r.json()["currency"] == "EUR" and r.json()["basis"] == "Fixed deal fee"
    S["cid_fixed"] = r.json()["id"]
    S["admin"].put(f"{API}/admin/agents/{S['aid_a']}/commission", json={"rule": None})


# --- wallets / payouts / settle ---
def test_wallets_and_payout():
    w = S["admin"].get(f"{API}/admin/agents/{S['aid_a']}/wallet").json()
    assert w["totals"]["USD"]["due"] == 275 and w["totals"]["EUR"]["due"] == 40
    assert len(w["items"]) == 3 and len(w["suppliers"]) == 2
    pw = S["pa"].get(f"{API}/agents/me/wallet")
    assert pw.status_code == 200
    pd = pw.json()
    assert pd["totals"]["USD"]["due"] == 275
    assert all("settled_by" not in i and "created_by" not in i for i in pd["items"])
    r = S["pa"].post(f"{API}/agents/me/wallet/request-payout")
    assert r.status_code == 200 and "USD 275.00" in r.json()["due"]
    assert S["pb"].post(f"{API}/agents/me/wallet/request-payout").status_code == 409


def test_settle_paid_void_and_409():
    r = S["admin"].post(f"{API}/admin/partner-commissions/{S['cid_onb']}", json={"action": "paid", "reference": "TEST-UTR-1"})
    assert r.status_code == 200 and r.json()["status"] == "paid" and r.json()["paid_on"]
    assert S["admin"].post(f"{API}/admin/partner-commissions/{S['cid_onb']}", json={"action": "void", "reference": "TEST"}).status_code == 409
    r = S["admin"].post(f"{API}/admin/partner-commissions/{S['cid_fixed']}", json={"action": "void", "reference": "TEST void"})
    assert r.status_code == 200 and r.json()["status"] == "void"
    assert S["admin"].post(f"{API}/admin/partner-commissions/{S['cid_deal']}", json={"action": "paid", "reference": "x"}).status_code == 422
    w = S["pa"].get(f"{API}/agents/me/wallet").json()
    assert w["totals"]["USD"] == {"due": 250, "paid": 25} and "EUR" not in w["totals"]
    S["admin"].post(f"{API}/admin/partner-commissions/{S['cid_deal']}", json={"action": "paid", "reference": "TEST-UTR-2"})
    assert S["pa"].post(f"{API}/agents/me/wallet/request-payout").status_code == 409


def test_admin_endpoints_require_admin():
    assert requests.get(f"{API}/admin/partner-commission/settings").status_code in (401, 403)
    assert S["pa"].get(f"{API}/admin/agents/{S['aid_a']}/wallet").status_code in (401, 403)
