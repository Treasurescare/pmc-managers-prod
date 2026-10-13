"""v52co — business_categories accepts List[Any] (structured {code,title} or legacy strings).

Verifies registration draft create → PATCH with structured list → GET round-trip.
"""
from __future__ import annotations
import os
import uuid
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def _create_draft():
    email = f"TEST_bcat_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/registrations",
                      json={"email": email, "company_name": "TEST BCat Co", "country": "BD",
                            "data_processing_consent": True}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "id" in body and "magic_token" in body, body
    return body["id"], body["magic_token"]


def test_business_categories_structured_roundtrip():
    rid, token = _create_draft()
    payload = {"business_categories": [
        {"code": "26131507", "title": "Solar power plants"},
        {"code": "15111502", "title": "Methane"},
    ]}
    r = requests.patch(f"{API}/registrations/{rid}", params={"token": token},
                       json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    bcats = body.get("business_categories") or []
    assert len(bcats) == 2, bcats
    codes = {b["code"] for b in bcats}
    assert codes == {"26131507", "15111502"}

    # GET via resume to confirm persistence
    r2 = requests.get(f"{API}/registrations/resume/{token}", timeout=15)
    assert r2.status_code == 200
    bcats2 = r2.json().get("business_categories") or []
    assert len(bcats2) == 2
    assert {b["code"] for b in bcats2} == {"26131507", "15111502"}


def test_business_categories_legacy_strings_still_work():
    rid, token = _create_draft()
    r = requests.patch(f"{API}/registrations/{rid}", params={"token": token},
                       json={"business_categories": ["Solar", "Biogas"]}, timeout=15)
    assert r.status_code == 200, r.text
    bcats = r.json().get("business_categories") or []
    assert bcats == ["Solar", "Biogas"]


def test_bd_country_persists():
    """BD country must persist (used by SectionD KZ-gate)."""
    rid, token = _create_draft()
    r = requests.get(f"{API}/registrations/resume/{token}", timeout=15)
    assert r.status_code == 200
    assert (r.json().get("country") or "").upper() == "BD"
