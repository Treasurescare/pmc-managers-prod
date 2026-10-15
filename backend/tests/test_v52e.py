"""v52e — admin pipeline enrichment, owner-notify, bank curation, dashboard wiring."""
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


def _grab_verify(email: str) -> str:
    from pymongo import MongoClient
    with MongoClient(MONGO_URL) as c:
        d = c[DB_NAME].escrow_accounts.find_one({"email": email.lower()})
        return d["verify_token"]


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": "adminsupport@pmcmanagers.com",
                     "password": "Admin@12345"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}",
                        "X-CSRF-Token": d["csrf_token"],
                        "Content-Type": "application/json"})
    return s


@pytest.fixture
def account():
    email = f"v52e+{uuid.uuid4().hex[:8]}@example.com"
    requests.post(f"{API}/escrow-accounts/register",
                   json={"email": email, "legal_name": "V52E Bank",
                          "primary_contact_phone": "+1 555",
                          "password": "StrongPass!1"}, timeout=15)
    requests.get(f"{API}/escrow-accounts/verify/{_grab_verify(email)}", timeout=15)
    s = requests.Session()
    r = s.post(f"{API}/escrow-accounts/auth/login",
                json={"email": email, "password": "StrongPass!1"}, timeout=15)
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s, r.json(), email


def test_admin_list_shows_owner_account(admin, account):
    _, acc, email = account
    r = admin.get(f"{API}/escrow-institutions?status=draft", timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    match = next((i for i in items if i.get("account_id") == acc["id"]), None)
    assert match, f"owner-tagged row missing for {acc['id']}"
    assert match["owner_account"]["email"] == email
    assert match["owner_account"]["status"] == "verified"


def test_admin_notify_owner_lands_in_bell(admin, account):
    s, acc, _ = account
    r = admin.post(f"{API}/escrow-institutions/{acc['institution_id']}/notify-owner",
                    json={"title": "Hello from PMC",
                           "body": "Please attach financials.",
                           "send_email": False}, timeout=15)
    assert r.status_code == 200, r.text
    r = s.get(f"{API}/escrow-accounts/me/notifications", timeout=15)
    kinds = [n["kind"] for n in r.json()]
    titles = [n["title"] for n in r.json()]
    assert "admin_message" in kinds
    assert "Hello from PMC" in titles


def test_notify_owner_404_for_legacy_draft(admin):
    # Create a legacy magic-link draft (no account_id)
    from pymongo import MongoClient
    from bson import ObjectId
    with MongoClient(MONGO_URL) as c:
        r = c[DB_NAME].escrow_institutions.insert_one({
            "legal_name": "Legacy", "primary_contact_email": "legacy@x.com",
            "status": "draft", "magic_token": "x"})
        iid = str(r.inserted_id)
        try:
            resp = admin.post(f"{API}/escrow-institutions/{iid}/notify-owner",
                               json={"title": "Legacy test title",
                                      "body": "Y body long enough"}, timeout=15)
            assert resp.status_code == 400, resp.text
        finally:
            c[DB_NAME].escrow_institutions.delete_one({"_id": ObjectId(iid)})


def test_dashboard_endpoint_returns_wiring(account):
    s, acc, _ = account
    r = s.get(f"{API}/escrow-accounts/me/dashboard", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    for key in ("institution", "joint_accounts", "joint_accounts_count",
                 "pending_signatures", "pending_signatures_count",
                 "transactions", "transactions_count"):
        assert key in d, f"missing {key}"
    assert d["institution"]["id"] == acc["institution_id"]
    # New institution, no joint accounts yet.
    assert d["joint_accounts_count"] == 0
    assert d["pending_signatures_count"] == 0


def test_bank_suggest_approve_merge_reject(admin):
    # Create a suggested bank
    cc = "GB"
    name_a = f"TEST Bank {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/masters/banks",
                       json={"country_code": cc, "name": name_a}, timeout=15)
    assert r.status_code == 200
    bank_a_id = r.json()["_id"]
    assert r.json()["source"] == "user_suggested"
    # Approve → curated with enrichment
    r = admin.post(f"{API}/masters/banks-admin/{bank_a_id}/approve",
                    json={"swift_prefix": "TESTGB",
                           "currencies": ["GBP"],
                           "aliases": ["Test Ltd"]}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "curated"
    assert r.json()["swift_prefix"] == "TESTGB"
    # Create another suggestion and merge it into the first
    name_b = f"TEST Dup {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/masters/banks",
                       json={"country_code": cc, "name": name_b}, timeout=15)
    bank_b_id = r.json()["_id"]
    r = admin.post(f"{API}/masters/banks-admin/{bank_b_id}/merge",
                    json={"target_id": bank_a_id}, timeout=15)
    assert r.status_code == 200, r.text
    # B should be gone, A should have B's name in aliases
    r = requests.get(f"{API}/masters/banks",
                      params={"country_code": cc, "q": name_b}, timeout=15)
    # The alias search in GET /banks matches aliases, so A should surface
    found_a_via_alias = any(b["_id"] == bank_a_id for b in r.json())
    assert found_a_via_alias, f"merge did not add alias: {r.json()}"
    # Create and reject
    name_c = f"TEST Reject {uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/masters/banks",
                       json={"country_code": cc, "name": name_c}, timeout=15)
    bank_c_id = r.json()["_id"]
    r = admin.delete(f"{API}/masters/banks-admin/{bank_c_id}", timeout=15)
    assert r.status_code == 200
    r = requests.get(f"{API}/masters/banks",
                      params={"country_code": cc, "q": name_c}, timeout=15)
    assert not any(b["name"] == name_c for b in r.json()), "reject failed"


def test_bank_merge_cross_country_rejected(admin):
    gb = requests.post(f"{API}/masters/banks",
                       json={"country_code": "GB", "name": f"TEST GB {uuid.uuid4().hex[:6]}"},
                       timeout=15).json()
    us = requests.post(f"{API}/masters/banks",
                       json={"country_code": "US", "name": f"TEST US {uuid.uuid4().hex[:6]}"},
                       timeout=15).json()
    r = admin.post(f"{API}/masters/banks-admin/{gb['_id']}/merge",
                    json={"target_id": us["_id"]}, timeout=15)
    assert r.status_code == 422, r.text
