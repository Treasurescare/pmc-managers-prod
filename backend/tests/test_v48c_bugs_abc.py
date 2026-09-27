"""v48c option E - Bugs A, B, C verification.
- BUG A: PDF template supports ?inline=true (default) and ?inline=false with proper Content-Disposition
- BUG B: admin list registrations (approved/rejected) returns rows with status set
- BUG C: /api/v1/vendor-ratings/admin/pending-count endpoint reachable
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PWD = "Admin@12345"


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD})
    if r.status_code != 200:
        r = s.post(f"{BASE_URL}/api/v1/admin/auth/login", json={"email": ADMIN_EMAIL, "password": "Admin@123"})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    csrf = data.get("csrf_token") or data.get("csrfToken")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


# ---------- BUG A ----------
class TestBugAPdfInline:
    def test_default_inline(self):
        r = requests.get(f"{BASE_URL}/api/v1/vendors/registration-template")
        assert r.status_code == 200
        cd = r.headers.get("Content-Disposition", "")
        assert cd.lower().startswith("inline"), f"expected inline, got {cd}"
        assert r.content[:8].startswith(b"%PDF-1."), "not a PDF"
        assert b"%%EOF" in r.content[-64:], "no EOF marker"
        assert len(r.content) > 3072

    def test_inline_true(self):
        r = requests.get(f"{BASE_URL}/api/v1/vendors/registration-template?inline=true")
        assert r.status_code == 200
        assert r.headers.get("Content-Disposition", "").lower().startswith("inline")
        assert r.content[:5] == b"%PDF-"

    def test_inline_false_attachment(self):
        r = requests.get(f"{BASE_URL}/api/v1/vendors/registration-template?inline=false")
        assert r.status_code == 200
        cd = r.headers.get("Content-Disposition", "")
        assert cd.lower().startswith("attachment"), f"expected attachment, got {cd}"
        assert r.content[:5] == b"%PDF-"
        assert b"%%EOF" in r.content[-64:]
        assert len(r.content) > 3072

    def test_pypdf_reads_pages(self):
        r = requests.get(f"{BASE_URL}/api/v1/vendors/registration-template?inline=false")
        assert r.status_code == 200
        try:
            from pypdf import PdfReader
        except ImportError:
            pytest.skip("pypdf not available")
        reader = PdfReader(io.BytesIO(r.content))
        assert len(reader.pages) >= 2


# ---------- BUG B ----------
class TestBugBApprovedList:
    def test_approved_list_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/v1/registrations?status=approved")
        assert r.status_code == 200, r.text[:200]
        items = r.json()
        assert isinstance(items, list)
        if items:
            row = items[0]
            assert row.get("status") == "approved"
            assert "id" in row

    def test_rejected_list_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/v1/registrations?status=rejected")
        assert r.status_code == 200, r.text[:200]
        items = r.json()
        assert isinstance(items, list)
        if items:
            assert items[0].get("status") == "rejected"


# ---------- BUG C ----------
class TestBugCPendingReviewCount:
    def test_admin_pending_count_endpoint(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/v1/vendor-ratings/admin/pending-count")
        assert r.status_code == 200, r.text[:200]
        j = r.json()
        assert "pending" in j
        assert isinstance(j["pending"], int)
        assert j["pending"] >= 0
