"""PMC v2 backend regression test suite."""
import io
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://tender-hub-57.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api/v1"

ADMIN_EMAIL = "admin@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---------- Public: notices ----------
class TestPublicNotices:
    def test_list_notices_published(self):
        r = requests.get(f"{API}/notices", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["total"] >= 3, f"expected >=3 seeded notices, got {data['total']}"
        for it in data["items"]:
            assert "notice_ref" in it and it["notice_ref"].startswith("PMC-NOT-")
            assert "title" in it and "document_type" in it

    def test_filter_by_document_type(self):
        for dt in ("tender", "rfp", "rfq"):
            r = requests.get(f"{API}/notices?document_type={dt}", timeout=15)
            assert r.status_code == 200
            for it in r.json()["items"]:
                assert it["document_type"] == dt

    def test_filter_by_country_kz(self):
        r = requests.get(f"{API}/notices?country=KZ", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 3
        for it in items:
            assert it["delivery_country"] == "KZ"
            # KZ notices should carry required_licenses (may be empty list)
            assert "required_licenses" in it

    def test_get_notice_detail(self):
        items = requests.get(f"{API}/notices", timeout=15).json()["items"]
        ref = items[0]["notice_ref"]
        r = requests.get(f"{API}/notices/{ref}", timeout=15)
        assert r.status_code == 200
        assert r.json()["notice_ref"] == ref

    def test_get_notice_404(self):
        r = requests.get(f"{API}/notices/PMC-NOT-9999-9999", timeout=15)
        assert r.status_code == 404


# ---------- Public: meta ----------
class TestPublicMeta:
    def test_public_stats(self):
        r = requests.get(f"{API}/meta/public/stats", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["notices_published"] >= 3
        assert d["packages_total"] >= 30
        assert "suppliers_approved" in d

    def test_kz_licenses(self):
        r = requests.get(f"{API}/meta/kz-licenses", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["licenses"]) == 6, f"expected 6 licenses, got {len(d['licenses'])}"
        assert "category_map" in d

    def test_countries(self):
        r = requests.get(f"{API}/meta/countries", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d) == 30
        assert d[0]["code"] == "KZ"


# ---------- Registration flow ----------
class TestRegistrationFlow:
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    state = {}

    def test_01_create_draft(self):
        r = requests.post(f"{API}/registrations", json={
            "email": self.email, "company_name": "TEST_Co", "country": "KZ"
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d and "magic_token" in d and "resume_url" in d
        TestRegistrationFlow.state["id"] = d["id"]
        TestRegistrationFlow.state["token"] = d["magic_token"]

    def test_02_duplicate_returns_same(self):
        r = requests.post(f"{API}/registrations", json={
            "email": self.email, "company_name": "TEST_Co", "country": "KZ"
        }, timeout=15)
        assert r.status_code == 200
        assert r.json()["magic_token"] == self.state["token"]
        assert r.json()["id"] == self.state["id"]

    def test_03_resume_valid(self):
        r = requests.get(f"{API}/registrations/resume/{self.state['token']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == self.email

    def test_04_resume_invalid(self):
        r = requests.get(f"{API}/registrations/resume/bad_token_xxx", timeout=15)
        assert r.status_code == 404

    def test_05_patch_wrong_token(self):
        r = requests.patch(f"{API}/registrations/{self.state['id']}?token=wrong",
                           json={"contact_name": "X"}, timeout=15)
        assert r.status_code == 404

    def test_06_patch_valid(self):
        payload = {
            "contact_name": "Test Person",
            "bank_name": "TestBank",
            "primary_sector": "Construction",
            "kz_licenses": ["Medical gas installation"],
        }
        r = requests.patch(f"{API}/registrations/{self.state['id']}?token={self.state['token']}",
                           json=payload, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["contact_name"] == "Test Person"

    def test_07_submit_missing_declarations(self):
        r = requests.post(f"{API}/registrations/{self.state['id']}/submit?token={self.state['token']}", timeout=15)
        assert r.status_code == 400
        assert "declarations" in r.text.lower() or "signature" in r.text.lower()

    def test_08_submit_missing_signature(self):
        # set all decls but omit signature
        payload = {"decl_conflict_of_interest": True, "decl_integrity": True,
                   "decl_accuracy": True, "decl_data_consent": True,
                   "decl_fee": True, "decl_notification": True}
        r = requests.patch(f"{API}/registrations/{self.state['id']}?token={self.state['token']}",
                           json=payload, timeout=15)
        assert r.status_code == 200
        r2 = requests.post(f"{API}/registrations/{self.state['id']}/submit?token={self.state['token']}", timeout=15)
        assert r2.status_code == 400
        assert "signature" in r2.text.lower()

    def test_09_submit_success(self):
        payload = {"signature_name": "Test User", "signature_title": "CEO",
                   "signature_date": "2026-01-15"}
        r = requests.patch(f"{API}/registrations/{self.state['id']}?token={self.state['token']}",
                           json=payload, timeout=15)
        assert r.status_code == 200
        r2 = requests.post(f"{API}/registrations/{self.state['id']}/submit?token={self.state['token']}", timeout=15)
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "submitted"

    def test_10_status_by_token(self):
        r = requests.get(f"{API}/registrations/status/{self.state['token']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "submitted"

    def test_11_status_wrong_token(self):
        r = requests.get(f"{API}/registrations/status/bad_token_yyy", timeout=15)
        assert r.status_code == 404


# ---------- Admin auth ----------
class TestAdminAuth:
    def test_login_success(self, admin_session):
        r = admin_session.get(f"{API}/admin/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_login_invalid(self):
        r = requests.post(f"{API}/admin/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "wrongpass123"}, timeout=15)
        assert r.status_code == 401

    def test_me_without_token(self):
        r = requests.get(f"{API}/admin/auth/me", timeout=15)
        assert r.status_code == 401


# ---------- Admin queue + decision ----------
class TestAdminDecisions:
    def test_list_submitted(self, admin_session):
        r = admin_session.get(f"{API}/registrations?status=submitted", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def _make_submitted(self, admin_session):
        email = f"decide_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/registrations",
                         json={"email": email, "company_name": "TEST_Dec", "country": "KZ"}, timeout=15)
        d = r.json()
        rid, tok = d["id"], d["magic_token"]
        payload = {"decl_conflict_of_interest": True, "decl_integrity": True,
                   "decl_accuracy": True, "decl_data_consent": True,
                   "decl_fee": True, "decl_notification": True,
                   "signature_name": "X", "signature_title": "Y", "signature_date": "2026-01-15",
                   "contact_name": "Z"}
        requests.patch(f"{API}/registrations/{rid}?token={tok}", json=payload, timeout=15)
        requests.post(f"{API}/registrations/{rid}/submit?token={tok}", timeout=15)
        return rid, tok, email

    def test_reject_requires_notes(self, admin_session):
        rid, _, _ = self._make_submitted(admin_session)
        r = admin_session.post(f"{API}/registrations/{rid}/decision",
                               json={"action": "reject"}, timeout=15)
        assert r.status_code == 400

    def test_clarify_requires_notes(self, admin_session):
        rid, _, _ = self._make_submitted(admin_session)
        r = admin_session.post(f"{API}/registrations/{rid}/decision",
                               json={"action": "clarify"}, timeout=15)
        assert r.status_code == 400

    def test_approve_creates_vendor(self, admin_session):
        rid, _, _ = self._make_submitted(admin_session)
        r = admin_session.post(f"{API}/registrations/{rid}/decision",
                               json={"action": "approve", "notes": "ok"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_clarify_flow(self, admin_session):
        rid, tok, _ = self._make_submitted(admin_session)
        r = admin_session.post(f"{API}/registrations/{rid}/decision",
                               json={"action": "clarify", "notes": "please add bank"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "needs_clarification"


# ---------- Admin notices ----------
class TestAdminNotices:
    def test_create_notice_auto_license(self, admin_session):
        payload = {
            "title": f"TEST_Notice_{uuid.uuid4().hex[:6]}",
            "description": "TEST description for auto-license attach behaviour on KZ delivery.",
            "document_type": "tender",
            "category": "Medical gas pipeline systems",
            "delivery_country": "KZ",
            "submission_deadline": "2026-12-31T14:00:00Z",
            "is_published": False,
        }
        r = admin_session.post(f"{API}/notices", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["notice_ref"].startswith("PMC-NOT-")
        assert "Medical gas installation" in d.get("required_licenses", [])
        # not visible on public list because unpublished
        ref = d["notice_ref"]
        r2 = requests.get(f"{API}/notices/{ref}", timeout=15)
        assert r2.status_code == 404
        # publish
        r3 = admin_session.post(f"{API}/notices/{ref}/publish", timeout=15)
        assert r3.status_code == 200
        r4 = requests.get(f"{API}/notices/{ref}", timeout=15)
        assert r4.status_code == 200


# ---------- Packages ----------
class TestPackages:
    def test_list_30_seeded(self, admin_session):
        r = admin_session.get(f"{API}/packages", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 30, f"expected >=30 packages, got {d['total']}"

    def test_requires_auth(self):
        r = requests.get(f"{API}/packages", timeout=15)
        assert r.status_code == 401

    def test_status_move(self, admin_session):
        d = admin_session.get(f"{API}/packages", timeout=15).json()
        pkg = d["items"][0]
        pid = pkg["id"]
        r = admin_session.post(f"{API}/packages/{pid}/status",
                               json={"status": "scoping"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "scoping"

    def test_status_invalid(self, admin_session):
        d = admin_session.get(f"{API}/packages", timeout=15).json()
        pid = d["items"][0]["id"]
        r = admin_session.post(f"{API}/packages/{pid}/status",
                               json={"status": "not_a_status"}, timeout=15)
        assert r.status_code == 400

    def test_csv_import(self, admin_session):
        csv_body = (
            "title,category,phase,value,currency,float_target_date,status\n"
            "TEST_Pkg_A,Medical gas pipeline systems,Phase 1,100000,USD,2026-06-01,backlog\n"
            "TEST_Pkg_B,Hostel bathrooms & plumbing,Phase 2,50000,USD,2026-07-01,scoping\n"
            ",MissingTitle,,,,,\n"  # invalid row
        )
        files = {"file": ("test.csv", csv_body, "text/csv")}
        r = admin_session.post(f"{API}/packages/import", files=files, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["created"] == 2
        assert d["skipped"] == 1


# ---------- Audit ----------
class TestAudit:
    def test_list_events(self, admin_session):
        r = admin_session.get(f"{API}/audit-events", timeout=15)
        assert r.status_code == 200
        events = r.json()
        assert isinstance(events, list)
        if events:
            e = events[0]
            for k in ("seq", "event_type", "previous_hash", "current_hash"):
                assert k in e, f"missing {k}"

    def test_verify_chain(self, admin_session):
        r = admin_session.get(f"{API}/audit-events/verify", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert "events_checked" in d
