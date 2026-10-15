"""v52f — chart aggregation, signatory invite, PDF statement."""
from __future__ import annotations
import os
import uuid
import requests
import pytest
from pymongo import MongoClient
from bson import ObjectId

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "pmc_v2")


def _grab_verify(email):
    with MongoClient(MONGO_URL) as c:
        return c[DB_NAME].escrow_accounts.find_one({"email": email.lower()})["verify_token"]


@pytest.fixture
def account():
    email = f"v52f+{uuid.uuid4().hex[:8]}@example.com"
    requests.post(f"{API}/escrow-accounts/register",
                   json={"email": email, "legal_name": "V52F Bank",
                          "primary_contact_phone": "+1 555",
                          "password": "StrongPass!1"}, timeout=15)
    requests.get(f"{API}/escrow-accounts/verify/{_grab_verify(email)}", timeout=15)
    s = requests.Session()
    r = s.post(f"{API}/escrow-accounts/auth/login",
                json={"email": email, "password": "StrongPass!1"}, timeout=15)
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s, r.json(), email


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": "adminsupport@pmcmanagers.com",
                     "password": "Admin@12345"}, timeout=30)
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}",
                        "X-CSRF-Token": d["csrf_token"],
                        "Content-Type": "application/json"})
    return s


def test_my_chart_12_months_empty_data(account):
    s, _, _ = account
    r = s.get(f"{API}/escrow-accounts/me/chart", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["series"]) == 12
    assert isinstance(d["accounts"], list)
    assert all("volume_by_currency" in m for m in d["series"])


def test_my_chart_custom_months_clamped(account):
    s, _, _ = account
    r = s.get(f"{API}/escrow-accounts/me/chart?months=36", timeout=15)
    d = r.json()
    assert len(d["series"]) == 24  # clamped to 24


def test_invite_signatory_blocked_until_approved(account):
    s, _, _ = account
    r = s.post(f"{API}/escrow-accounts/me/signatories/invite",
                json={"name": "Jane", "designation": "Director",
                       "email": "jane@example.com"}, timeout=15)
    assert r.status_code == 403, r.text
    assert "not_approved" in r.text or "approve" in r.text.lower()


def test_invite_signatory_after_approval(account):
    s, acc, _ = account
    with MongoClient(MONGO_URL) as c:
        c[DB_NAME].escrow_institutions.update_one(
            {"_id": ObjectId(acc["institution_id"])},
            {"$set": {"status": "approved"}})
    r = s.post(f"{API}/escrow-accounts/me/signatories/invite",
                json={"name": "Jane D", "designation": "Director",
                       "email": f"jane+{uuid.uuid4().hex[:6]}@example.com"},
                timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["signatory"]["name"] == "Jane D"
    # duplicate rejected
    r2 = s.post(f"{API}/escrow-accounts/me/signatories/invite",
                 json={"name": "Dup person", "designation": "Dir",
                        "email": r.json()["signatory"]["email"]}, timeout=15)
    assert r2.status_code == 409


def test_statement_pdf_rejects_foreign_account(account):
    s, _, _ = account
    r = s.get(f"{API}/escrow-accounts/me/joint-accounts/{ObjectId()}/statement.pdf",
                timeout=15)
    assert r.status_code == 403


def test_statement_pdf_renders_for_own_account(account):
    s, acc, email = account
    # Seed a joint account owned by this institution's primary email, plus one tx.
    with MongoClient(MONGO_URL) as c:
        c[DB_NAME].escrow_institutions.update_one(
            {"_id": ObjectId(acc["institution_id"])},
            {"$set": {"status": "approved",
                       "signatories": [{"name": "You", "designation": "CEO",
                                          "email": email}]}})
        ja = c[DB_NAME].escrow_accounts.insert_one({
            "name": "TEST JA", "account_no": "999",
            "currency": "USD", "balance": 50000,
            "escrow_officer": {"email": email}})
        c[DB_NAME].escrow_transactions.insert_one({
            "escrow_account_id": str(ja.inserted_id),
            "bid_ref": "PMC-BID-TEST", "vendor_ref": "V-1",
            "amount": 1000, "currency": "USD", "status": "received",
            "created_at": "2026-10-01T00:00:00+00:00"})
    r = s.get(f"{API}/escrow-accounts/me/joint-accounts/{ja.inserted_id}/statement.pdf",
                timeout=20)
    assert r.status_code == 200, r.text[:200]
    assert r.content.startswith(b"%PDF"), "not a PDF"
    assert len(r.content) > 1500


def test_admin_chart_all_approved(admin):
    r = admin.get(f"{API}/escrow/admin/chart", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "series" in d and len(d["series"]) == 12
    assert "all_approved" in d
    assert "institutions" in d


def test_admin_chart_filtered_subset(admin):
    # Pick first approved institution id, filter by it
    r = admin.get(f"{API}/escrow/admin/chart", timeout=15)
    all_app = r.json()["all_approved"]
    if not all_app:
        pytest.skip("no approved institutions yet")
    first_id = all_app[0]["id"]
    r = admin.get(f"{API}/escrow/admin/chart",
                    params={"institution_ids": first_id}, timeout=15)
    assert r.status_code == 200
    assert len(r.json()["institutions"]) == 1
    assert r.json()["institutions"][0]["id"] == first_id
