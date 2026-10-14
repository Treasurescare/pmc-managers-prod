"""v52cz rev5 — escrow registration: empty scaffold rows must not 422.

The form starts with one blank signatory ({name:"", email:""}) and one
blank bank row. Before rev5, sending them tripped EmailStr on
`signatories[0].email` and the draft could never be created. Now empty
emails coerce to None and completely blank rows are dropped before
persistence."""
from __future__ import annotations
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def _core_payload(**over):
    p = {
        "legal_name": "Rev5 Test Bank Ltd",
        "country": "IN",
        "registered_address": "100 MG Road, Mumbai, Maharashtra, 400001, India",
        "address_line1": "100 MG Road",
        "city": "Mumbai",
        "state_code": "MH",
        "state_name": "Maharashtra",
        "postal_code": "400001",
        "reg_number": "L17110MH1973PLC019786",
        "primary_contact_email": "ops.rev5@testbank.in",
        "signatories": [{"name": "", "designation": "", "email": "", "phone": ""}],
        "banking": [{"account_name": "", "account_number": "", "iban": None,
                     "swift": None, "currency": "USD", "institution_name": "",
                     "branch": None, "correspondent_bank": None,
                     "settlement_cutoff": None}],
    }
    p.update(over)
    return p


def test_register_with_blank_signatory_row_succeeds():
    r = requests.post(f"{API}/escrow-institutions/register",
                      json=_core_payload(), timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "draft" and d.get("magic_token")


def test_blank_rows_are_dropped_from_persisted_draft():
    r = requests.post(f"{API}/escrow-institutions/register",
                      json=_core_payload(primary_contact_email="ops.rev5b@testbank.in"),
                      timeout=15)
    assert r.status_code == 200, r.text
    token = r.json()["magic_token"]
    # Resume via magic link — the stored doc must have no empty scaffold rows.
    r = requests.get(f"{API}/escrow-institutions/resume/{token}", timeout=10)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["signatories"] == []
    assert doc["banking"] == []
    # Structured address pieces persisted.
    assert doc["address_line1"] == "100 MG Road"
    assert doc["state_code"] == "MH"
    assert doc["postal_code"] == "400001"


def test_partial_signatory_kept_with_none_email():
    """A row with a name but no email must survive (email=None), not 422."""
    p = _core_payload(
        primary_contact_email="ops.rev5c@testbank.in",
        signatories=[{"name": "Priya Nair", "designation": "Director", "email": ""}],
    )
    r = requests.post(f"{API}/escrow-institutions/register", json=p, timeout=15)
    assert r.status_code == 200, r.text
    token = r.json()["magic_token"]
    doc = requests.get(f"{API}/escrow-institutions/resume/{token}", timeout=10).json()
    assert len(doc["signatories"]) == 1
    assert doc["signatories"][0]["name"] == "Priya Nair"
    assert doc["signatories"][0]["email"] is None


def test_invalid_signatory_email_still_rejected():
    """Garbage (non-empty, non-email) must still fail — guard stays intact."""
    p = _core_payload(
        primary_contact_email="ops.rev5d@testbank.in",
        signatories=[{"name": "Bad", "email": "not-an-email"}],
    )
    r = requests.post(f"{API}/escrow-institutions/register", json=p, timeout=15)
    assert r.status_code == 422, r.text
