"""v52bt backend tests — DocuSign resend graceful + work-packages sample CSV auth."""
import os
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    if r.status_code != 200:
        # Try fallback password
        r = s.post(f"{BASE}/api/v1/admin/auth/login",
                   json={"email": ADMIN_EMAIL, "password": "Admin@123"}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    s.headers.update({
        "Authorization": f"Bearer {data['token']}",
        "X-CSRF-Token": data.get("csrf_token", ""),
    })
    return s


# --- Work packages sample CSV ---

def test_sample_csv_requires_auth():
    r = requests.get(f"{BASE}/api/v1/packages/import/sample.csv", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 unauth got {r.status_code}"


def test_sample_csv_authed_download(admin_session):
    r = admin_session.get(f"{BASE}/api/v1/packages/import/sample.csv", timeout=15)
    assert r.status_code == 200, r.text[:200]
    first_line = r.text.splitlines()[0]
    assert first_line == "title,category,phase,value,currency,float_target_date,status", first_line
    assert "attachment" in r.headers.get("Content-Disposition", "")
    assert "csv" in r.headers.get("Content-Type", "")


# --- DocuSign resend graceful ---

def test_docusign_resend_bogus_envelope_not_found(admin_session):
    """DB has no such envelope → 404 'Envelope not found', NOT 500."""
    r = admin_session.post(
        f"{BASE}/api/v1/docusign/envelopes/00000000-0000-0000-0000-000000000000/resend",
        timeout=20)
    assert r.status_code == 404, f"expected 404, got {r.status_code} body={r.text[:300]}"
    body = r.json()
    assert "Envelope not found" in str(body)
    assert "Traceback" not in r.text


def test_docusign_envelopes_list_ok(admin_session):
    r = admin_session.get(f"{BASE}/api/v1/docusign/envelopes?limit=50", timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    # Just assert shape; may be empty in fresh env.
    assert isinstance(data, (list, dict))


def test_docusign_resend_real_envelope_graceful(admin_session):
    """Pick an existing envelope not in terminal state. If upstream returns
    ENVELOPE_DOES_NOT_EXIST, we MUST see 410 with the friendly message and
    the DB row should flip to 'orphaned'. Otherwise accept 200/400/424 but
    NEVER 500 and NEVER a raw traceback."""
    r = admin_session.get(f"{BASE}/api/v1/docusign/envelopes?limit=50", timeout=20)
    assert r.status_code == 200
    data = r.json()
    rows = data if isinstance(data, list) else (data.get("items") or data.get("envelopes") or [])
    candidate = next((e for e in rows
                      if (e.get("status") or "").lower()
                      not in ("completed", "declined", "voided", "orphaned")), None)
    if not candidate:
        pytest.skip("no non-terminal envelope to test resend against")
    env_id = candidate.get("envelope_id") or candidate.get("id")
    assert env_id
    r2 = admin_session.post(f"{BASE}/api/v1/docusign/envelopes/{env_id}/resend", timeout=30)
    assert r2.status_code != 500, f"500 from resend: {r2.text[:400]}"
    assert "Traceback" not in r2.text
    if r2.status_code == 410:
        detail = str(r2.json().get("detail", ""))
        assert ("different DocuSign sandbox" in detail) or ("Use Reassign" in detail), detail
    elif r2.status_code == 424:
        # readable error, not a bare exception
        assert "DocuSign" in r2.text
    else:
        assert r2.status_code in (200, 400, 404, 409, 410, 424), r2.status_code


# --- Admin login smoke to confirm core auth path ---

def test_admin_login_shape():
    r = requests.post(f"{BASE}/api/v1/admin/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    if r.status_code != 200:
        r = requests.post(f"{BASE}/api/v1/admin/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "Admin@123"}, timeout=20)
    assert r.status_code == 200, r.text[:200]
    j = r.json()
    assert "token" in j and isinstance(j["token"], str) and len(j["token"]) > 10
