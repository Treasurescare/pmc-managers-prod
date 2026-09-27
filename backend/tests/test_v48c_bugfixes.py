"""v48c bug-fix backend regression tests.

Covers:
  BUG 5 — Reverse auction start with <2 participants must return 400.
  BUG 6 — Meeting create + add-invitees must include 'invites_sent' field.
"""
import os
import datetime
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except FileNotFoundError:
        pass
    return ""


BASE_URL = _load_backend_url()
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    if r.status_code != 200:
        # Try fallback password variant
        r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": "Admin@123"})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    csrf = data.get("csrf_token") or data.get("csrf")
    assert token, f"no token in login response: {data}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


# ---------------- BUG 5: reverse auction start guard ----------------
class TestReverseAuctionStartGuard:
    def test_start_with_less_than_2_participants_returns_400(self, admin_session):
        # Find a notice to attach an auction to
        nr = admin_session.get(f"{BASE_URL}/api/v1/notices?limit=1")
        assert nr.status_code == 200, nr.text[:200]
        notices = nr.json().get("items") or []
        if not notices:
            pytest.skip("no notices available to create draft auction")
        notice_ref = notices[0].get("notice_ref") or notices[0].get("ref")

        payload = {
            "notice_ref": notice_ref,
            "title": "TEST_v48c auction guard",
            "currency": "USD",
            "starting_price": 100000,
            "floor_price": 80000,
            "min_decrement": 500,
            "duration_minutes": 15,
            "anti_snipe_seconds": 60,
        }
        cr = admin_session.post(f"{BASE_URL}/api/v1/reverse-auctions", json=payload)
        assert cr.status_code in (200, 201), f"create failed {cr.status_code}: {cr.text[:300]}"
        aid = cr.json().get("id") or cr.json().get("_id")
        assert aid, cr.json()

        # Immediately attempt start with 0 participants
        sr = admin_session.post(f"{BASE_URL}/api/v1/reverse-auctions/{aid}/start")
        assert sr.status_code == 400, f"expected 400, got {sr.status_code}: {sr.text[:300]}"
        detail = (sr.json().get("detail") or "").lower()
        assert "2" in detail and "participant" in detail, \
            f"error message missing required guard text: {detail}"


# ---------------- BUG 6: meeting invite email dispatch ----------------
class TestMeetingInvitesField:
    def test_create_meeting_includes_invites_sent(self, admin_session):
        future = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat()
        payload = {
            "subject": "TEST_v48c Test Invite Email",
            "scheduled_at": future,
            "duration_min": 45,
            "provider": "jitsi",
            "is_internal": True,
            "invitees": [
                {"email": "meetings-qa@example.com", "name": "QA Tester", "role": "attendee"}
            ],
        }
        r = admin_session.post(f"{BASE_URL}/api/v1/meetings", json=payload)
        assert r.status_code in (200, 201), f"{r.status_code}: {r.text[:300]}"
        d = r.json()
        assert "invites_sent" in d, f"'invites_sent' missing in create response: {list(d.keys())}"
        assert isinstance(d["invites_sent"], int)
        mid = d.get("id") or d.get("_id")
        assert mid

        # Add invitees
        ar = admin_session.post(
            f"{BASE_URL}/api/v1/meetings/{mid}/invitees",
            json=[{"email": "meetings-qa2@example.com", "name": "QA Two", "role": "attendee"}],
        )
        assert ar.status_code == 200, f"{ar.status_code}: {ar.text[:300]}"
        ad = ar.json()
        assert "invites_sent" in ad, f"'invites_sent' missing in add-invitees response: {list(ad.keys())}"
        assert isinstance(ad["invites_sent"], int)
