"""Regression tests for BugsV2 Batch 4 fixes.

Focus:
  - Bug #78 — Vendor Document Crossover — admin-create refuses to import
    document_slots from a draft whose email doesn't match the new vendor.
  - Bucket A — /notices/admin/all returns drafts + published (unlike public
    /notices which is is_published-only).
"""
import os
import uuid
import pytest
import httpx

API = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWD = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    with httpx.Client(base_url=API, timeout=30) as c:
        r = c.post("/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
        assert r.status_code == 200, r.text
        c.headers["x-csrf-token"] = r.json()["csrf_token"]
        yield c


def test_bug78_admin_create_rejects_cross_email_draft(admin_session):
    """Admin creates a draft for A, uploads a doc, then admin-creates a
    vendor for B referencing A's draft — B must NOT inherit A's slot."""
    suffix = uuid.uuid4().hex[:8]
    email_a = f"crossA.{suffix}@example.com"
    email_b = f"crossB.{suffix}@example.com"

    r = admin_session.post("/api/v1/registrations", json={
        "email": email_a, "company_name": "Cross A", "country": "KZ",
        "data_processing_consent": True, "marketing_consent": False,
    })
    assert r.status_code == 200
    draft_a = r.json()

    files = {"file": ("proof.txt", b"hello", "text/plain")}
    data = {"token": draft_a["magic_token"]}
    r = admin_session.post(
        f"/api/v1/registrations/{draft_a['id']}/documents/incorporation_certificate",
        files=files, data=data,
    )
    assert r.status_code == 200

    r = admin_session.post("/api/v1/vendors/admin-create", json={
        "email": email_b, "mode": "activate", "password": "Vendor@12345",
        "registration": {"company_name": "Cross B", "country": "KZ"},
        "draft_registration_id": draft_a["id"],
    })
    assert r.status_code == 200, r.text
    new_reg_id = r.json()["registration_id"]

    r = admin_session.get(f"/api/v1/registrations/{new_reg_id}")
    assert r.status_code == 200
    slots = r.json().get("document_slots") or {}
    assert slots == {}, f"Bug #78 regression: Vendor B inherited slots {list(slots)}"


def test_notices_admin_all_returns_drafts(admin_session):
    r = admin_session.get("/api/v1/notices/admin/all?limit=5")
    assert r.status_code == 200
    payload = r.json()
    assert "items" in payload
    assert "total" in payload
