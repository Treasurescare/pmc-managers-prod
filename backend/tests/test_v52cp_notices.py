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
import uuid
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
    """v52cp — every notice must expose `delivery_country` so the public
    card can show it, and notices with an EMD config must additionally
    expose `emd_amount` + `emd_currency` so the EMD chip renders.
    v52cz rev3 — self-seed an EMD-configured notice first: the old version
    depended on whatever the last 20 notices happened to be, which broke
    once bulk regression seeds (no EMD) dominated the top of the list."""
    s, _ = _admin_session()
    from datetime import datetime, timedelta, timezone
    dl = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    payload = {
        "title": f"v52cp emd probe {uuid.uuid4().hex[:6]}",
        "description": "regression — emd exposure",
        "category": "Civil Works",
        "document_type": "tender",
        "budget_amount": 100000,
        "budget_currency": "USD",
        "delivery_country": "KZ",
        "submission_deadline": dl,
        "emd_config": {"percentage": 2.0, "currency": "USD"},
        "is_published": True,
    }
    r = s.post(f"{API}/notices", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    r = requests.get(f"{API}/notices", params={"limit": 20}, timeout=15)
    assert r.status_code == 200, r.text
    items = r.json().get("items") or r.json()
    assert isinstance(items, list) and items
    saw_emd = False
    for n in items:
        assert isinstance(n.get("delivery_country"), str) and n["delivery_country"], n
        cfg = n.get("emd_config") or {}
        if (cfg.get("fixed_amount") or 0) > 0 or (cfg.get("percentage") or 0) > 0:
            assert "emd_amount" in n and "emd_currency" in n, n
            saw_emd = True
    # Our freshly-seeded EMD notice must be inside the latest-20 window.
    assert saw_emd, "No seeded notice has an EMD config to validate against"


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


# ---- v52ct — new notice flow regression ----

def test_notice_create_rejects_zero_or_missing_budget():
    """v52ct — the backend must refuse budget_amount <= 0 regardless of what
    the frontend sends. Covers 'bid amount must not be zero' acceptance."""
    s, _ = _admin_session()
    base = {
        "title": "v52ct zero-budget notice",
        "description": "Zero budget should be rejected server-side.",
        "document_type": "tender",
        "category": "general",
        "delivery_country": "IN",
        "submission_deadline": "2030-01-01T00:00:00+00:00",
        "budget_currency": "USD",
        "is_published": False,
    }
    for bad in (0, 0.0, None):
        r = s.post(f"{API}/notices", json={**base, "budget_amount": bad}, timeout=15)
        assert r.status_code in (400, 422), f"budget_amount={bad!r} should be rejected: {r.status_code} {r.text}"


def test_notice_create_with_tender_template_prefill_round_trip():
    """v52ct — create a tender-builder template that carries category /
    country / currency / budget / EMD in its header, then create a notice
    whose fields come from that template. The public listing must then
    expose delivery_country, budget_amount+budget_currency and
    emd_amount+emd_currency so the Notice Board card renders them."""
    s, _ = _admin_session()
    tpl = s.post(f"{API}/tender-templates", json={
        "name": "v52ct template",
        "kind": "tender",
        "header": {
            "work_title": "v52ct work title",
            "work_description": "Scope sourced from the tender header for the v52ct regression.",
            "product_category": "Biogas Plant Construction",
            "delivery_country": "IN",
            "budget_currency": "INR",
            "budget_amount": 5000000,
            "emd_amount": 50000,
        },
        "sections": [],
    }, timeout=15).json()
    try:
        payload = {
            "title": "v52ct work title",
            "description": "Scope sourced from the tender header for the v52ct regression.",
            "document_type": "tender",
            "category": "Biogas Plant Construction",
            "delivery_country": "IN",
            "budget_currency": "INR",
            "budget_amount": 5000000,
            "submission_deadline": "2030-01-01T00:00:00+00:00",
            "emd_config": {"fixed_amount": 50000, "percentage": 0, "currency": "INR"},
            "tender_template_id": tpl["id"],
            "is_published": True,
        }
        r = s.post(f"{API}/notices", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        notice_ref = r.json()["notice_ref"]

        # Public GET must expose flat emd_amount/emd_currency AND the raw
        # budget/country so the public card can render them.
        pub = requests.get(f"{API}/notices", params={"limit": 50}, timeout=15).json()
        items = pub.get("items") or pub
        hit = next((n for n in items if n.get("notice_ref") == notice_ref), None)
        assert hit, f"created notice {notice_ref} not in public listing"
        assert hit["delivery_country"] == "IN"
        assert float(hit["budget_amount"]) == 5000000
        assert hit["budget_currency"] == "INR"
        assert float(hit["emd_amount"]) == 50000
        assert hit["emd_currency"] == "INR"
        assert hit["category"] == "Biogas Plant Construction"
        assert hit["tender_template_id"] == tpl["id"]
    finally:
        s.delete(f"{API}/tender-templates/{tpl['id']}", timeout=15)
        # v52cv — also delete the notice; leaving it published with a dangling
        # tender_template_id breaks the public Download pack ZIP (404).
        if r.ok and r.json().get("notice_ref"):
            s.delete(f"{API}/notices/{r.json()['notice_ref']}/admin", timeout=15)


def test_public_notice_card_zero_emd_shape_is_stable():
    """v52ct — a notice with no EMD config must still expose emd_amount
    (None) and emd_currency so the frontend `Number(n.emd_amount) > 0`
    guard works without undefined-key gymnastics."""
    s, _ = _admin_session()
    r = s.post(f"{API}/notices", json={
        "title": "v52ct no-emd notice",
        "description": "A notice that does not require any EMD.",
        "document_type": "rfq",
        "category": "general",
        "delivery_country": "IN",
        "submission_deadline": "2030-01-01T00:00:00+00:00",
        "budget_currency": "USD",
        "budget_amount": 100.0,
        "is_published": True,
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    ref = r.json()["notice_ref"]
    items = requests.get(f"{API}/notices", params={"limit": 50}, timeout=15).json()
    items = items.get("items") or items
    hit = next((n for n in items if n.get("notice_ref") == ref), None)
    assert hit, f"notice {ref} missing from public listing"
    assert "emd_amount" in hit and "emd_currency" in hit
    assert hit["emd_amount"] in (None, 0, 0.0)
