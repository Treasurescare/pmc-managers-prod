"""v52cp — regression tests for the Notices + Tender Builder bridge fixes.

Covers the user-reported bugs:
- 422 "sometimes" when saving a tender → empty section code/title must now
  be tolerated by Pydantic (`SectionBlock` relaxed).
- Public tender listing must expose `emd_amount` + `emd_currency` so the
  landing page card can render them.
- Primary document is no longer required at notice-create time.
"""
from __future__ import annotations
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                      "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"


def _admin_session() -> tuple[requests.Session, dict]:
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": "adminsupport@pmcmanagers.com",
                     "password": "Admin@12345"},
               timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    s.headers.update({
        "Authorization": f"Bearer {data['token']}",
        "X-CSRF-Token": data.get("csrf_token") or "",
    })
    # Ensure the csrf_token cookie is set for the double-submit check.
    if data.get("csrf_token") and not s.cookies.get("csrf_token"):
        s.cookies.set("csrf_token", data["csrf_token"])
    return s, data


def test_tender_template_accepts_blank_section_code_and_title():
    s, _ = _admin_session()
    payload = {
        "name": "v52cp smoke",
        "kind": "tender",
        "header": {"work_title": "x"},
        "sections": [
            {"code": "sec-1", "kind": "section", "title": "Filled"},
            {"code": "", "kind": "section", "title": ""},
            {"kind": "annexure"},
        ],
    }
    r = s.post(f"{API}/tender-templates", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    tid = r.json()["id"]
    s.delete(f"{API}/tender-templates/{tid}", timeout=15)


def test_tender_template_accepts_short_placeholder_name():
    s, _ = _admin_session()
    payload = {"name": "x", "kind": "tender", "sections": []}
    r = s.post(f"{API}/tender-templates", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    s.delete(f"{API}/tender-templates/{r.json()['id']}", timeout=15)


def test_public_notices_expose_emd_amount_and_country():
    r = requests.get(f"{API}/notices", params={"limit": 5}, timeout=15)
    assert r.status_code == 200, r.text
    items = r.json().get("items") or r.json()
    assert isinstance(items, list) and items
    for n in items:
        assert isinstance(n.get("delivery_country"), str) and n["delivery_country"], n
        assert "emd_amount" in n
        assert "emd_currency" in n


def test_notice_create_no_longer_requires_primary_document():
    s, _ = _admin_session()
    payload = {
        "title": "v52cp test notice (no doc)",
        "description": "This notice is created without an attached primary document.",
        "document_type": "tender",
        "category": "general",
        "delivery_country": "IN",
        "submission_deadline": "2030-01-01T00:00:00+00:00",
        "budget_currency": "USD",
        "budget_amount": 1000.0,
        "is_published": False,
    }
    r = s.post(f"{API}/notices", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    out = r.json()
    assert out.get("notice_ref")
    assert not out.get("primary_document")
