"""v52cz rev7 — regression:
1. POST /register with an email that already has an escrow institution must
   409 with a clear "already registered" message.
2. Bank master has substantially expanded roster (incl. neobanks).
"""
from __future__ import annotations
import os
import uuid
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def test_register_rejects_duplicate_email():
    tag = uuid.uuid4().hex[:6]
    email = f"dup.{tag}@test.io"
    r = requests.post(f"{API}/escrow-institutions/register",
                      json={"legal_name": "Dup Bank 1",
                            "primary_contact_email": email,
                            "country": "IN"}, timeout=15)
    assert r.status_code == 200, r.text
    r2 = requests.post(f"{API}/escrow-institutions/register",
                       json={"legal_name": "Dup Bank 2",
                             "primary_contact_email": email,
                             "country": "GB"}, timeout=15)
    assert r2.status_code == 409, r2.text
    body = r2.json()
    detail = body.get("detail") or {}
    # FastAPI wraps dict details inside "detail"
    if isinstance(detail, dict):
        assert detail.get("error") == "escrow_email_already_registered"
        assert "already registered" in detail.get("message", "")


def test_banks_master_expanded_rosters():
    for cc, min_count in (("IN", 25), ("GB", 15), ("US", 15)):
        r = requests.get(f"{API}/masters/banks",
                         params={"country_code": cc, "limit": 200}, timeout=10)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert len(rows) >= min_count, f"{cc}: only {len(rows)} banks"


def test_banks_master_has_neobanks():
    # Pick a known neobank from the UK roster — case-insensitive search.
    r = requests.get(f"{API}/masters/banks",
                     params={"country_code": "GB", "q": "Monzo"}, timeout=10)
    names = [b["name"] for b in r.json()]
    assert any("Monzo" in n for n in names), names
    r = requests.get(f"{API}/masters/banks",
                     params={"country_code": "US", "q": "Chime"}, timeout=10)
    names = [b["name"] for b in r.json()]
    assert any("Chime" in n for n in names), names
