"""v51z backend verification — participant_count + invite auto_send fallback."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    csrf = data.get("csrf_token") or data.get("csrf")
    s.headers.update({
        "Authorization": f"Bearer {tok}",
        "X-CSRF-Token": csrf or "",
        "Content-Type": "application/json",
    })
    return s


# --- participant_count on list -----------------------------------------
def test_list_reverse_auctions_has_participant_count(admin_session):
    r = admin_session.get(f"{BASE}/api/v1/reverse-auctions", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body["items"] if isinstance(body, dict) else body
    assert isinstance(rows, list) and len(rows) > 0, "need at least one auction row"
    for row in rows:
        assert "participant_count" in row, f"missing participant_count: {row}"
        assert isinstance(row["participant_count"], int)
        assert row["participant_count"] >= 0


# --- invite autosend with NO template_id falls back to default ---------
def test_invite_auto_send_without_template_id_succeeds(admin_session):
    rows = admin_session.get(f"{BASE}/api/v1/reverse-auctions").json()["items"]
    draft = next((r for r in rows if r.get("status") != "closed"), rows[0])
    aid = draft.get("id") or draft.get("_id") or draft.get("aid")
    body = {"emails": ["testv51z@example.com"], "auto_send": True,
            "origin_url": "https://preview.test"}
    r = admin_session.post(f"{BASE}/api/v1/reverse-auctions/{aid}/invite",
                           json=body, timeout=20)
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data.get("count") == 1
    assert "auto_sent" in data and data["auto_sent"] >= 0


# --- explicit bogus template_id must still 404 -------------------------
def test_invite_auto_send_bogus_template_id_404(admin_session):
    rows = admin_session.get(f"{BASE}/api/v1/reverse-auctions").json()["items"]
    aid = (rows[0].get("id") or rows[0].get("_id") or rows[0].get("aid"))
    body = {"emails": ["x@y.com"], "auto_send": True,
            "template_id": "507f1f77bcf86cd799439011",
            "origin_url": "https://preview.test"}
    r = admin_session.post(f"{BASE}/api/v1/reverse-auctions/{aid}/invite",
                           json=body, timeout=15)
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"
    assert "template" in (r.json().get("detail") or "").lower()
