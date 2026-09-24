"""Bug Blitz v46m — verify /api/v1/reports/snapshot returns valid JSON with expected keys."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://tender-hub-57.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORDS = ["Admin@12345", "Admin@123"]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    token = None
    csrf = None
    last_err = None
    for pw in ADMIN_PASSWORDS:
        for path in ["/api/v1/admin/auth/login"]:
            try:
                r = s.post(f"{BASE_URL}{path}", json={"email": ADMIN_EMAIL, "password": pw}, timeout=15)
                if r.status_code == 200:
                    body = r.json()
                    token = body.get("access_token") or body.get("token")
                    csrf = body.get("csrf_token") or body.get("x_csrf_token") or body.get("csrf")
                    if not csrf:
                        # csrf often in Set-Cookie or header
                        csrf = r.headers.get("X-CSRF-Token")
                    if token:
                        break
                else:
                    last_err = f"{path} {pw} -> {r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_err = f"{path} {pw} -> {e}"
        if token:
            break
    if not token:
        pytest.skip(f"Admin login failed: {last_err}")
    headers = {"Authorization": f"Bearer {token}"}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    s.headers.update(headers)
    return s


def test_snapshot_returns_valid_json(admin_session):
    """(b) POST /api/v1/reports/snapshot must return valid JSON with ok/errors/files/generated_at keys."""
    r = admin_session.post(f"{BASE_URL}/api/v1/reports/snapshot", timeout=120)
    # Print for debug
    print(f"status={r.status_code}, content-type={r.headers.get('content-type')}")
    print(f"body preview: {r.text[:400]}")
    assert r.status_code == 200, f"snapshot returned {r.status_code}: {r.text[:400]}"
    assert "application/json" in r.headers.get("content-type", ""), "must be JSON content-type"
    body = r.json()  # must not throw
    assert "ok" in body
    assert "errors" in body and isinstance(body["errors"], list)
    assert "files" in body and isinstance(body["files"], list)
    assert "generated_at" in body


def test_snapshot_requires_auth():
    r = requests.post(f"{BASE_URL}/api/v1/reports/snapshot", timeout=15)
    assert r.status_code in (401, 403), f"unauth expected 401/403, got {r.status_code}"
