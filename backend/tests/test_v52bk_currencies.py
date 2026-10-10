"""v52bk — Currency master CRUD + public endpoint."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1"

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    if r.status_code != 200:
        r = s.post(f"{API}/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": "Admin@123"}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    j = r.json()
    tok = j.get("token") or j.get("access_token")
    csrf = j.get("csrf_token") or j.get("csrf")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


def test_public_currencies_list():
    r = requests.get(f"{API}/masters/currencies/public", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 25, f"only {len(data)}"
    codes = {c["code"] for c in data}
    for req in ("USD", "EUR", "KZT", "INR", "GBP", "JPY"):
        assert req in codes, f"{req} missing"
    for c in data:
        assert len(c["code"]) == 3
        assert "name" in c
        assert "_id" not in c  # ObjectId not leaked


def test_admin_currencies_list(admin_session):
    r = admin_session.get(f"{API}/masters/currencies" , timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) >= 25


def test_admin_create_duplicate_and_delete(admin_session):
    # ensure USD exists -> duplicate 409
    r = admin_session.post(f"{API}/masters/currencies",
                      json={"code": "USD", "name": "US Dollar", "symbol": "$", "decimals": 2},
                      timeout=15)
    assert r.status_code == 409, f"expected 409 got {r.status_code} {r.text}"

    # create a fresh test code
    r = admin_session.post(f"{API}/masters/currencies",
                      json={"code": "TST", "name": "TEST_Currency", "symbol": "T$", "decimals": 2},
                      timeout=15)
    # Could succeed or 409 if left from prior run - fetch id
    if r.status_code == 409:
        # fetch id
        rows = admin_session.get(f"{API}/masters/currencies?include_inactive=true",
                                 timeout=15).json()
        row = next((x for x in rows if x["code"] == "TST"), None)
        assert row, "TST not found despite 409"
        cid = row["id"]
    else:
        assert r.status_code == 200, r.text
        cid = r.json()["id"]

    # delete (soft-deactivate)
    rd = admin_session.delete(f"{API}/masters/currencies/{cid}", timeout=15)
    assert rd.status_code == 200, rd.text
    body = rd.json()
    assert body.get("ok") is True
    assert body.get("deactivated") is True

    # verify not in public list
    pub = requests.get(f"{API}/masters/currencies/public", timeout=15).json()
    assert all(c["code"] != "TST" for c in pub)


def test_notice_detail_public_access():
    """Smoke: /notices/<ref> page html does not force a redirect to /login server-side."""
    r = requests.get(f"{BASE}/notices/PMC-NOT-2026-0001", timeout=15, allow_redirects=False)
    assert r.status_code in (200, 304), r.status_code
