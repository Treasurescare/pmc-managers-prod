"""v52cz rev9 — regressions:
1. PATCH /notices/{ref} is a true partial update (NoticePatchIn +
   exclude_unset): the Escrow routing picker can PATCH just
   `escrow_account_id` without tripping the full-NoticeIn required fields
   (was HTTP 422 "Field required" x4). Field-level validation still applies
   to keys that ARE sent.
2. Banks master: GB roster includes neobanks (Revolut, Wise); the public
   POST /masters/banks "+" affordance upserts and the row is listable.
"""
from __future__ import annotations
import os
import uuid
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": "adminsupport@pmcmanagers.com",
                     "password": "Admin@12345"}, timeout=30)
    if r.status_code != 200:
        r = s.post(f"{API}/admin/auth/login",
                   json={"email": "adminsupport@pmcmanagers.com",
                         "password": "Admin@123"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    s.headers.update({
        "Authorization": f"Bearer {data.get('token') or data.get('access_token')}",
        "X-CSRF-Token": data["csrf_token"],
        "Content-Type": "application/json",
    })
    return s


@pytest.fixture(scope="module")
def draft_notice(admin):
    tag = uuid.uuid4().hex[:6]
    r = admin.post(f"{API}/notices", json={
        "title": f"TEST rev9 partial patch {tag}",
        "description": "Draft notice used to verify partial PATCH semantics.",
        "document_type": "rfq",
        "category": "General",
        "delivery_country": "GB",
        "submission_deadline": "2026-12-31",
        "budget_amount": 1000,
        "is_published": False,
    }, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_partial_patch_escrow_account_only(admin, draft_notice):
    ref = draft_notice["notice_ref"]
    r = admin.patch(f"{API}/notices/{ref}",
                    json={"escrow_account_id": None}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == draft_notice["title"], "partial PATCH must not wipe title"
    assert body["description"] == draft_notice["description"]
    assert body["is_published"] is False, "unset is_published must not flip state"


def test_partial_patch_still_validates_sent_fields(admin, draft_notice):
    ref = draft_notice["notice_ref"]
    r = admin.patch(f"{API}/notices/{ref}", json={"title": "ab"}, timeout=30)
    assert r.status_code == 422, r.text
    r = admin.patch(f"{API}/notices/{ref}",
                    json={"budget_amount": -5}, timeout=30)
    assert r.status_code == 422, r.text


def test_gb_roster_has_neobanks():
    for name in ("Revolut", "Wise", "Monzo", "Starling"):
        r = requests.get(f"{API}/masters/banks",
                         params={"country_code": "GB", "q": name}, timeout=15)
        assert r.status_code == 200, r.text
        names = [b["name"] for b in r.json()]
        assert any(name.lower() in n.lower() for n in names), f"{name} missing: {names}"


def test_suggest_bank_adds_and_lists():
    tag = uuid.uuid4().hex[:6]
    name = f"TEST Suggest Bank {tag}"
    r = requests.post(f"{API}/masters/banks",
                      json={"country_code": "GB", "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "user_suggested"
    r2 = requests.get(f"{API}/masters/banks",
                      params={"country_code": "GB", "q": name}, timeout=15)
    assert any(b["name"] == name for b in r2.json()), r2.text
    # Idempotent — suggesting the same bank again must not duplicate it.
    r3 = requests.post(f"{API}/masters/banks",
                       json={"country_code": "GB", "name": name}, timeout=15)
    assert r3.status_code == 200, r3.text
    r4 = requests.get(f"{API}/masters/banks",
                      params={"country_code": "GB", "q": name}, timeout=15)
    assert sum(1 for b in r4.json() if b["name"] == name) == 1


def test_suggest_bank_rejects_bad_input():
    r = requests.post(f"{API}/masters/banks",
                      json={"country_code": "GBX", "name": "x"}, timeout=15)
    assert r.status_code == 422, r.text
