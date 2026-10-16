"""v54a — Escrow payment entries + institution-portal + DocuSign tests.

Covers:
- /api/v1/escrow/signatory-pool (admin + reviewer) returns pmc_officers AND
  institutions, with primary_contact_email + signatories[] (incl. fallback).
- Admin payment-entries CRUD + sign + void.
- Institution-portal (escrow_accounts) /me/transactions/{tid} 200 vs 403.
- Institution-portal payment entry create + sign.
- PATCH /escrow/accounts/{aid} accepts institution_id.
- POST /escrow/transactions/{tid}/docusign — same-email → 400, missing
  officers → 400, no DocuSign SDK/config → 503 is acceptable.
"""
import os
import secrets

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api/v1"

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORDS = ["Admin@12345", "Admin@123"]

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")


# ---------------- Fixtures ----------------


@pytest.fixture(scope="module")
def mongo():
    assert MONGO_URL and DB_NAME, "MONGO_URL / DB_NAME must be in backend .env"
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    last = None
    for pw in ADMIN_PASSWORDS:
        r = s.post(f"{API}/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": pw})
        last = r
        if r.status_code == 200:
            data = r.json()
            token = data.get("token") or data.get("access_token")
            csrf = data.get("csrf_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
            if csrf:
                s.headers.update({"X-CSRF-Token": csrf})
            return s
    pytest.skip(f"Admin login failed: {last.status_code if last else '-'} {last.text[:200] if last else ''}")


@pytest.fixture(scope="module")
def existing_tx(mongo):
    """Grab any existing escrow transaction we can test against, or create a
    minimal synthetic one with an escrow_account_snapshot carrying both
    officers so sign/role tests make sense."""
    tx = mongo.escrow_transactions.find_one(
        {"escrow_account_snapshot.pmc_officer.email": {"$exists": True},
         "escrow_account_snapshot.escrow_officer.email": {"$exists": True}})
    if tx:
        return tx
    # Build a synthetic tx referencing an existing escrow account if any.
    acc = mongo.escrow_accounts.find_one({"escrow_officer.email": {"$exists": True}})
    pmc = (acc or {}).get("pmc_officer") or {"email": ADMIN_EMAIL, "name": "PMC Admin"}
    esc = (acc or {}).get("escrow_officer") or {
        "email": f"TEST_{secrets.token_hex(4)}@example.com", "name": "Inst Officer"}
    doc = {
        "bid_ref": f"TEST_BID_{secrets.token_hex(3)}",
        "notice_ref": "TEST_NOTICE",
        "amount": 1000.0,
        "currency": "USD",
        "status": "received",
        "escrow_account_id": str(acc["_id"]) if acc else None,
        "escrow_account_snapshot": {
            "name": "TEST escrow account",
            "institution": "TEST Bank",
            "account_no": "1234",
            "pmc_officer": pmc,
            "escrow_officer": esc,
        },
        "created_at": "2026-01-01T00:00:00+00:00",
        "signatures": {},
    }
    r = mongo.escrow_transactions.insert_one(doc)
    doc["_id"] = r.inserted_id
    return doc


# ---------------- 1. signatory-pool ----------------


class TestSignatoryPool:
    def test_pool_admin_returns_both_arrays(self, admin_session):
        r = admin_session.get(f"{API}/escrow/signatory-pool")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "pmc_officers" in data, "pmc_officers missing (previous fall-through bug?)"
        assert "institutions" in data, "institutions missing (previous fall-through bug?)"
        assert isinstance(data["pmc_officers"], list)
        assert isinstance(data["institutions"], list)

    def test_pool_institutions_have_primary_contact_and_signatories(self, admin_session):
        r = admin_session.get(f"{API}/escrow/signatory-pool")
        data = r.json()
        if not data["institutions"]:
            pytest.skip("No approved institutions seeded")
        for inst in data["institutions"]:
            assert "primary_contact_email" in inst
            assert "signatories" in inst
            assert isinstance(inst["signatories"], list)
        # At least one institution should surface primary contact as fallback
        # when sigs are otherwise empty.
        any_with_pce = [i for i in data["institutions"] if i.get("primary_contact_email")]
        assert any_with_pce, "At least one institution should expose primary_contact_email"


# ---------------- 2. Admin payment-entries CRUD ----------------


class TestAdminPaymentEntries:
    created_id = None

    def test_create_requires_admin(self, existing_tx):
        # Anonymous (no auth) should be 401/403
        r = requests.post(f"{API}/escrow/payment-entries", json={
            "transaction_id": str(existing_tx["_id"]),
            "direction": "in", "kind": "emd_in", "amount": 1.0, "currency": "USD",
        })
        assert r.status_code in (401, 403), r.text

    def test_create_payment_entry(self, admin_session, existing_tx):
        payload = {
            "transaction_id": str(existing_tx["_id"]),
            "direction": "in", "kind": "emd_in",
            "amount": 500.0, "currency": "USD",
            "bank_reference": "TEST_UTR_1",
            "notes": "pytest v54a",
        }
        r = admin_session.post(f"{API}/escrow/payment-entries", json=payload)
        assert r.status_code == 200, r.text
        pe = r.json()
        assert pe["direction"] == "in"
        assert pe["kind"] == "emd_in"
        assert pe["amount"] == 500.0
        assert pe["currency"] == "USD"
        assert pe["status"] == "pending_signatures"
        assert "id" in pe
        TestAdminPaymentEntries.created_id = pe["id"]

    def test_list_payment_entries(self, admin_session, existing_tx):
        r = admin_session.get(
            f"{API}/escrow/transactions/{existing_tx['_id']}/payment-entries")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "transaction" in data
        assert any(p["id"] == TestAdminPaymentEntries.created_id
                   for p in data["items"])

    def test_sign_requires_officer_email_match(self, admin_session):
        """Admin signing — only succeeds if admin's email matches pmc_officer
        or escrow_officer on the snapshot. Our admin (adminsupport@) likely
        does NOT match, so expect 403."""
        peid = TestAdminPaymentEntries.created_id
        assert peid
        r = admin_session.post(
            f"{API}/escrow/payment-entries/{peid}/sign",
            json={"action": "approve"})
        # Either 200 (admin happens to be pmc officer) or 403 — both valid.
        assert r.status_code in (200, 403), r.text
        if r.status_code == 403:
            assert "officer" in r.text.lower() or "registered" in r.text.lower()

    def test_sign_as_pmc_officer_emulated(self, admin_session, mongo, existing_tx):
        """Patch the snapshot's pmc officer to our admin email so we can
        exercise the happy path and verify status stays pending_signatures
        (only one side signed)."""
        tid = str(existing_tx["_id"])
        mongo.escrow_transactions.update_one(
            {"_id": existing_tx["_id"]},
            {"$set": {"escrow_account_snapshot.pmc_officer": {
                "email": ADMIN_EMAIL, "name": "Admin", "role": "pmc"}}})
        # Create a fresh PE under the patched snapshot
        r = admin_session.post(f"{API}/escrow/payment-entries", json={
            "transaction_id": tid, "direction": "in", "kind": "emd_in",
            "amount": 10.0, "currency": "USD"})
        assert r.status_code == 200, r.text
        pe = r.json()
        # Patch escrow_account_snapshot on the PE too (admin side read from PE)
        mongo.escrow_payment_entries.update_one(
            {"_id": ObjectId(pe["id"])},
            {"$set": {"escrow_account_snapshot.pmc_officer": {
                "email": ADMIN_EMAIL, "name": "Admin", "role": "pmc"}}})
        r = admin_session.post(
            f"{API}/escrow/payment-entries/{pe['id']}/sign",
            json={"action": "approve"})
        assert r.status_code == 200, r.text
        signed = r.json()
        assert signed["signatures"]["pmc"]["email"].lower() == ADMIN_EMAIL
        # One side only — status should still be pending_signatures
        assert signed["status"] == "pending_signatures"

    def test_void_blocks_further_sign(self, admin_session, existing_tx):
        # Create a fresh PE to void
        r = admin_session.post(f"{API}/escrow/payment-entries", json={
            "transaction_id": str(existing_tx["_id"]),
            "direction": "out", "kind": "fee_out",
            "amount": 5.0, "currency": "USD"})
        assert r.status_code == 200
        peid = r.json()["id"]
        rv = admin_session.post(f"{API}/escrow/payment-entries/{peid}/void")
        assert rv.status_code == 200, rv.text
        assert rv.json()["status"] == "void"
        # Subsequent sign should 409
        rs = admin_session.post(
            f"{API}/escrow/payment-entries/{peid}/sign",
            json={"action": "approve"})
        assert rs.status_code == 409, rs.text


# ---------------- 3. PATCH account accepts institution_id ----------------


class TestAccountPatchInstitutionId:
    def test_patch_accepts_institution_id(self, admin_session, mongo):
        acc = mongo.escrow_accounts.find_one({})
        if not acc:
            pytest.skip("No escrow account to patch")
        inst = mongo.escrow_institutions.find_one({"status": "approved"})
        if not inst:
            pytest.skip("No approved institution to bind")
        r = admin_session.patch(
            f"{API}/escrow/accounts/{acc['_id']}",
            json={"institution_id": str(inst["_id"])})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("institution_id") == str(inst["_id"])


# ---------------- 4. Institution portal — scoped endpoints ----------------


@pytest.fixture(scope="module")
def institution_session(mongo):
    """Register a fresh escrow account, verify via token from Mongo, log in."""
    s = requests.Session()
    email = f"test_v54a_{secrets.token_hex(4)}@example.com"
    r = s.post(f"{API}/escrow-accounts/register", json={
        "email": email, "legal_name": "TEST Inst v54a",
        "primary_contact_phone": "+91 9999999999",
        "password": "Test@12345"})
    assert r.status_code == 200, r.text
    row = mongo.escrow_accounts.find_one({"email": email.lower()})
    assert row is not None, f"register succeeded but account missing for {email}"
    token = row.get("verify_token")
    rv = s.get(f"{API}/escrow-accounts/verify/{token}")
    assert rv.status_code == 200, rv.text
    rl = s.post(f"{API}/escrow-accounts/auth/login",
                 json={"email": email, "password": "Test@12345"})
    assert rl.status_code == 200, rl.text
    csrf = rl.json().get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    yield {"session": s, "email": email.lower()}
    mongo.escrow_accounts.delete_one({"email": email.lower()})


class TestInstitutionPortal:
    def test_get_tx_403_when_not_owner(self, institution_session, existing_tx):
        """A freshly-registered account that is NOT a signatory on the tx's
        escrow_account_snapshot must get 403."""
        s = institution_session["session"]
        r = s.get(f"{API}/escrow-accounts/me/transactions/{existing_tx['_id']}")
        assert r.status_code in (403, 404), r.text
        # 403 is the required contract; 404 only if transaction accidentally
        # has no snapshot — not our case because fixture ensures officers.
        if r.status_code == 404:
            pytest.fail("Expected 403 (not owner), got 404")

    def test_get_tx_200_when_signatory_match(
            self, institution_session, existing_tx, mongo):
        """Patch the institution's signatories[] to include an email that
        matches the tx snapshot's escrow_officer, then GET succeeds."""
        s = institution_session["session"]
        acc = mongo.escrow_accounts.find_one({"email": institution_session["email"]})
        iid = acc.get("institution_id")
        esc_email = ((existing_tx.get("escrow_account_snapshot") or {})
                     .get("escrow_officer") or {}).get("email")
        if not (iid and esc_email):
            pytest.skip("No institution_id or esc_email")
        mongo.escrow_institutions.update_one(
            {"_id": ObjectId(iid)},
            {"$set": {"signatories": [{"email": esc_email, "name": "Inst",
                                        "designation": "Signatory"}]}})
        r = s.get(f"{API}/escrow-accounts/me/transactions/{existing_tx['_id']}")
        assert r.status_code == 200, r.text
        tx = r.json()
        assert tx["id"] == str(existing_tx["_id"])
        assert "payment_entries" in tx
        assert "docusign_envelope" in tx

    def test_create_payment_entry_from_institution(
            self, institution_session, existing_tx):
        s = institution_session["session"]
        r = s.post(
            f"{API}/escrow-accounts/me/transactions/{existing_tx['_id']}/payment-entries",
            json={"direction": "in", "kind": "emd_in", "amount": 7.5,
                   "currency": "USD", "notes": "pytest inst"})
        assert r.status_code == 200, r.text
        pe = r.json()
        assert pe["created_by_role"] == "institution"
        assert pe["status"] == "pending_signatures"
        # escrow_institution signature NOT yet attached (placeholder empty)
        assert not (pe.get("signatures") or {}).get("escrow_institution")

    def test_sign_payment_entry_finalises_when_pmc_approved(
            self, institution_session, existing_tx, admin_session, mongo):
        """Create PE from admin, pre-approve as pmc side (patch snapshot so
        admin is pmc_officer), then institution signs → fully_signed."""
        tid = str(existing_tx["_id"])
        # Make admin the pmc officer on snapshot
        mongo.escrow_transactions.update_one(
            {"_id": existing_tx["_id"]},
            {"$set": {"escrow_account_snapshot.pmc_officer": {
                "email": ADMIN_EMAIL, "name": "Admin", "role": "pmc"}}})
        rc = admin_session.post(f"{API}/escrow/payment-entries", json={
            "transaction_id": tid, "direction": "in", "kind": "emd_in",
            "amount": 42.0, "currency": "USD"})
        assert rc.status_code == 200, rc.text
        peid = rc.json()["id"]
        mongo.escrow_payment_entries.update_one(
            {"_id": ObjectId(peid)},
            {"$set": {"escrow_account_snapshot.pmc_officer": {
                "email": ADMIN_EMAIL, "name": "Admin", "role": "pmc"}}})
        rs = admin_session.post(
            f"{API}/escrow/payment-entries/{peid}/sign",
            json={"action": "approve"})
        assert rs.status_code == 200
        assert rs.json()["status"] == "pending_signatures"
        # Institution signs
        inst = institution_session["session"]
        rsi = inst.post(f"{API}/escrow-accounts/me/payment-entries/{peid}/sign",
                        json={"action": "approve"})
        assert rsi.status_code == 200, rsi.text
        assert rsi.json()["status"] == "fully_signed"


# ---------------- 5. DocuSign envelope on transaction ----------------


class TestDocuSignEnvelope:
    def test_same_email_rejected_400(self, admin_session, mongo, existing_tx):
        tid = str(existing_tx["_id"])
        mongo.escrow_transactions.update_one(
            {"_id": existing_tx["_id"]},
            {"$set": {
                "escrow_account_snapshot.pmc_officer":
                    {"email": "same@example.com", "name": "A", "role": "pmc"},
                "escrow_account_snapshot.escrow_officer":
                    {"email": "same@example.com", "name": "B", "role": "escrow_institution"},
                "status": "received",
            }})
        r = admin_session.post(f"{API}/escrow/transactions/{tid}/docusign")
        assert r.status_code == 400, r.text
        assert "same email" in r.text.lower() or "independent" in r.text.lower() \
            or "different" in r.text.lower() or "two" in r.text.lower()

    def test_happy_path_or_503_fallback(self, admin_session, mongo, existing_tx):
        tid = str(existing_tx["_id"])
        mongo.escrow_transactions.update_one(
            {"_id": existing_tx["_id"]},
            {"$set": {
                "escrow_account_snapshot.pmc_officer":
                    {"email": "pmc@example.com", "name": "PMC", "role": "pmc"},
                "escrow_account_snapshot.escrow_officer":
                    {"email": "inst@example.com", "name": "Inst", "role": "escrow_institution"},
                "status": "received",
            }})
        r = admin_session.post(f"{API}/escrow/transactions/{tid}/docusign")
        # 200 (DocuSign configured) or 503 (SDK missing / no private key)
        # or 502 (DocuSign API call error) are all acceptable envs.
        # 200 (DocuSign fully configured), 502 (upstream API err),
        # 503 (SDK missing), or 424 (DocuSign auth/consent missing in env)
        # are all acceptable fallbacks per the review brief.
        assert r.status_code in (200, 424, 502, 503), r.text
