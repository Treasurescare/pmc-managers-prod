"""v51x — Verify the three backend fixes called out in the review request:
  1. POST /api/v1/reverse-auctions/{aid}/start with 0 participants -> 400 with 'need at least 2 registered participants'
  2. POST /api/v1/reverse-auctions/{aid}/invite with 2 emails -> 200 w/ 'invited' list of {email, token}
  3. GET /api/v1/notices/admin/all -> 200 and each item includes created_by_email + created_at
"""
import os
import pytest
import requests
import uuid

def _read_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env() or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not configured"
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS_PRIMARY = "Admin@12345"
ADMIN_PASS_FALLBACK = "Admin@123"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS_PRIMARY})
    if r.status_code != 200:
        r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASS_FALLBACK})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    csrf = data.get("csrf_token") or data.get("csrfToken")
    assert token, f"no token in admin login response: {list(data.keys())}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


# ---- Reverse auctions preflight ------------------------------------------

@pytest.fixture(scope="module")
def draft_auction(admin_session):
    """Reuse an existing draft reverse auction if available; else create one."""
    r = admin_session.get(f"{BASE_URL}/api/v1/reverse-auctions")
    if r.status_code == 200:
        for a in r.json().get("items", []):
            if a.get("status") == "draft":
                aid = a.get("_id") or a.get("id")
                if aid:
                    return aid
    payload = {
        "title": f"TEST_v51x_{uuid.uuid4().hex[:8]}",
        "notice_ref": f"TEST-{uuid.uuid4().hex[:6]}",
        "starting_price": 100000,
        "floor_price": 80000,
        "currency": "INR",
        "duration_minutes": 15,
        "min_decrement": 100,
    }
    r = admin_session.post(f"{BASE_URL}/api/v1/reverse-auctions", json=payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"could not create draft auction: {r.status_code} {r.text[:200]}")
    aid = r.json().get("_id") or r.json().get("id") or r.json().get("auction_id")
    assert aid, f"no id returned: {r.json()}"
    return aid


def test_start_auction_zero_participants_returns_clear_400(admin_session, draft_auction):
    r = admin_session.post(f"{BASE_URL}/api/v1/reverse-auctions/{draft_auction}/start")
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    detail = (body.get("detail") or "").lower()
    assert "need at least 2 registered participants" in detail, \
        f"expected clear preflight msg; got: {body}"


def test_invite_two_vendors_returns_invited_list(admin_session, draft_auction):
    emails = ["vendor1@example.com", "vendor2@example.com"]
    r = admin_session.post(
        f"{BASE_URL}/api/v1/reverse-auctions/{draft_auction}/invite",
        json={"emails": emails, "note": "TEST_v51x"},
    )
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "invited" in body, f"no 'invited' key: {body}"
    invited = body["invited"]
    assert isinstance(invited, list) and len(invited) == 2
    for row in invited:
        assert "email" in row and "token" in row
        assert row["email"] in emails
        assert isinstance(row["token"], str) and len(row["token"]) > 10


# ---- Notices admin list includes created_by_email -------------------------

def test_notices_admin_all_includes_created_by_email(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/v1/notices/admin/all?limit=50")
    assert r.status_code == 200, f"got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "items" in body
    items = body["items"]
    assert isinstance(items, list)
    if not items:
        pytest.skip("no notices in system yet — cannot verify fields")
    for n in items[:10]:
        assert "created_by_email" in n, f"missing created_by_email: {list(n.keys())}"
        assert "created_at" in n, f"missing created_at: {list(n.keys())}"
        if n["created_by_email"] is not None:
            assert isinstance(n["created_by_email"], str)
