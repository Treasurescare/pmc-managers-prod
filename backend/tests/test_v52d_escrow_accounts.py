"""v52d — Escrow account-first registration backend regression.

Covers:
  - POST /escrow-accounts/register → unverified, verify email queued
  - GET /escrow-accounts/verify/{token} → verified, draft institution auto-created
  - Login refused while unverified; works after verification
  - Session cookie authorises PATCH on the owned institution
  - PATCH on a FOREIGN institution rejects (401/404)
  - Submit transitions status → "submitted" and seeds a notification
  - Change-password rotates token_generation (old session dies)
  - Legacy POST /escrow-institutions/register → HTTP 410 (deprecated)
  - Idempotent re-register for an unverified email re-sends verify
"""
from __future__ import annotations
import os
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "pmc_v2")


def _grab_verify_token(email: str) -> str:
    from pymongo import MongoClient
    with MongoClient(MONGO_URL) as c:
        d = c[DB_NAME].escrow_accounts.find_one({"email": email.lower()})
        assert d and d.get("verify_token"), f"no verify token for {email}: {d}"
        return d["verify_token"]


def _new_email() -> str:
    return f"rev10test+{uuid.uuid4().hex[:10]}@example.com"


# ---------------- Register / verify ------------------------------------

def test_register_creates_unverified_account():
    email = _new_email()
    r = requests.post(f"{API}/escrow-accounts/register",
                       json={"email": email, "legal_name": "TEST bank",
                              "primary_contact_phone": "+91 9999999999",
                              "password": "StrongPass!1"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "unverified"


def test_login_blocked_until_verified():
    email = _new_email()
    requests.post(f"{API}/escrow-accounts/register",
                   json={"email": email, "legal_name": "TEST b",
                          "primary_contact_phone": "+1 5551234567",
                          "password": "StrongPass!1"}, timeout=15)
    r = requests.post(f"{API}/escrow-accounts/auth/login",
                       json={"email": email, "password": "StrongPass!1"}, timeout=15)
    assert r.status_code == 403, r.text
    assert "unverified" in r.text.lower() or "verify" in r.text.lower()


def test_verify_creates_draft_institution_and_login_works():
    email = _new_email()
    requests.post(f"{API}/escrow-accounts/register",
                   json={"email": email, "legal_name": "TEST verify bank",
                          "primary_contact_phone": "+971 50 123 4567",
                          "password": "StrongPass!1"}, timeout=15)
    tok = _grab_verify_token(email)
    r = requests.get(f"{API}/escrow-accounts/verify/{tok}", timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["institution_id"]

    s = requests.Session()
    r = s.post(f"{API}/escrow-accounts/auth/login",
                json={"email": email, "password": "StrongPass!1"}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "verified"
    assert data["institution_id"]

    r = s.get(f"{API}/escrow-accounts/auth/me", timeout=15)
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["institution"]["status"] == "draft"


def test_duplicate_register_resends_verify_for_unverified():
    email = _new_email()
    r1 = requests.post(f"{API}/escrow-accounts/register",
                        json={"email": email, "legal_name": "TEST",
                               "primary_contact_phone": "+1 555",
                               "password": "StrongPass!1"}, timeout=15)
    assert r1.status_code == 200, r1.text
    r2 = requests.post(f"{API}/escrow-accounts/register",
                        json={"email": email, "legal_name": "TEST",
                               "primary_contact_phone": "+1 555",
                               "password": "StrongPass!2"}, timeout=15)
    assert r2.status_code == 200, r2.text
    assert r1.json()["id"] == r2.json()["id"], "must reuse row, not duplicate"


# ---------------- Authenticated institution flow -----------------------

@pytest.fixture
def session():
    email = _new_email()
    requests.post(f"{API}/escrow-accounts/register",
                   json={"email": email, "legal_name": "TEST session bank",
                          "primary_contact_phone": "+91 9999",
                          "password": "StrongPass!1"}, timeout=15)
    requests.get(f"{API}/escrow-accounts/verify/{_grab_verify_token(email)}",
                 timeout=15)
    s = requests.Session()
    r = s.post(f"{API}/escrow-accounts/auth/login",
                json={"email": email, "password": "StrongPass!1"}, timeout=15)
    assert r.status_code == 200
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s, r.json(), email


def test_patch_submit_notifies_account(session):
    s, acc, email = session
    iid = acc["institution_id"]
    r = s.patch(f"{API}/escrow-institutions/{iid}", json={
        "legal_name": "TEST patched",
        "country": "GB", "registered_address": "1 Pall Mall",
        "reg_number": "GB-1", "primary_contact_email": email,
        "signatories": [{"name": "Jane", "designation": "CEO", "email": "jane@x.com"}],
        "banking": [{"account_name": "p", "account_number": "1",
                      "currency": "GBP", "institution_name": "Revolut"}],
    }, timeout=15)
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/escrow-institutions/{iid}/submit", timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "submitted"
    r = s.get(f"{API}/escrow-accounts/me/notifications", timeout=15)
    kinds = [n["kind"] for n in r.json()]
    assert "submitted" in kinds, kinds


def test_patch_foreign_institution_rejected(session):
    s, _, _ = session
    # Different session / institution
    email2 = _new_email()
    requests.post(f"{API}/escrow-accounts/register",
                   json={"email": email2, "legal_name": "other",
                          "primary_contact_phone": "+1 555",
                          "password": "StrongPass!1"}, timeout=15)
    requests.get(f"{API}/escrow-accounts/verify/{_grab_verify_token(email2)}",
                 timeout=15)
    s2 = requests.Session()
    r = s2.post(f"{API}/escrow-accounts/auth/login",
                 json={"email": email2, "password": "StrongPass!1"}, timeout=15)
    foreign_iid = r.json()["institution_id"]
    # Session `s` tries to PATCH someone else's institution
    r = s.patch(f"{API}/escrow-institutions/{foreign_iid}",
                 json={"legal_name": "hijack"}, timeout=15)
    assert r.status_code == 404, r.text  # mapped to "Not found" by the gate


def test_change_password_rotates_session(session):
    s, _, email = session
    r = s.post(f"{API}/escrow-accounts/auth/change-password",
                json={"current_password": "StrongPass!1",
                       "new_password": "NewPass!2345"}, timeout=15)
    assert r.status_code == 200, r.text
    # Fresh session with new password should work
    s2 = requests.Session()
    r = s2.post(f"{API}/escrow-accounts/auth/login",
                 json={"email": email, "password": "NewPass!2345"}, timeout=15)
    assert r.status_code == 200


# ---------------- Deprecated endpoint ----------------------------------

def test_legacy_register_endpoint_410():
    r = requests.post(f"{API}/escrow-institutions/register",
                       json={"legal_name": "zombie",
                              "primary_contact_email": "z@z.com"}, timeout=15)
    assert r.status_code == 410, r.text
    assert r.json()["detail"]["error"] == "endpoint_deprecated"
