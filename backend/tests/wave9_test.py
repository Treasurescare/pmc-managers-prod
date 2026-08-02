"""Wave 9 regression tests:
1. Admin vendor invite + verify + password set flow
2. Registration template upload/download
3. Notice creation with primary/attachment document upload
4. Permissions Matrix GET/PUT/reset + server-side enforcement (403)
5. Committee with external_invitees + external accept flow + designation
"""
import io
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = os.environ.get("PMC_TEST_ADMIN_EMAIL", "adminsupport@pmcmanagers.com")
ADMIN_PASSWORD = os.environ.get("PMC_TEST_ADMIN_PASSWORD", "Admin@123")


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/staff/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "active_role": "admin"})
    assert r.status_code == 200, r.text
    csrf = r.json()["csrf_token"]
    s.headers.update({"X-CSRF-Token": csrf})
    # Reset permissions matrix to defaults so state-polluted runs from curl smoke
    # tests don't break the default-row-count assertion.
    s.post(f"{BASE}/api/v1/permissions/reset")
    return s


@pytest.fixture(scope="module")
def reviewer_session(admin):
    """Create a fresh reviewer-only staff for RBAC 403 test."""
    email = f"TEST_reviewer_{uuid.uuid4().hex[:6]}@example.com"
    r = admin.post(f"{BASE}/api/v1/staff", json={
        "email": email, "name": "Test Reviewer",
        "password": "Reviewer@123", "roles": ["reviewer"],
        "hierarchy_level": 2,
    })
    assert r.status_code in (200, 201, 409), r.text
    s = requests.Session()
    lr = s.post(f"{BASE}/api/v1/staff/auth/login",
                json={"email": email, "password": "Reviewer@123", "active_role": "reviewer"})
    assert lr.status_code == 200, lr.text
    s.headers.update({"X-CSRF-Token": lr.json()["csrf_token"]})
    return s


# ============ Vendor invite flow ============

class TestVendorInvite:
    _state = {}

    def test_invite_creates_stub_and_returns_verify_url(self, admin):
        email = f"TEST_vendor_{uuid.uuid4().hex[:6]}@example.com"
        r = admin.post(f"{BASE}/api/v1/vendors/invite",
                       json={"email": email, "company_name": "Acme Test Ltd"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["vendor_ref"].startswith("PMC-SUP-")
        assert data["email"] == email
        assert "/vendor/verify/" in data["verify_url"]
        TestVendorInvite._state["vendor_ref"] = data["vendor_ref"]
        TestVendorInvite._state["email"] = email
        TestVendorInvite._state["token"] = data["verify_url"].rsplit("/", 1)[-1]

    def test_verify_token_returns_stub_info(self):
        tok = TestVendorInvite._state["token"]
        r = requests.get(f"{BASE}/api/v1/vendors/verify/{tok}")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["vendor_ref"] == TestVendorInvite._state["vendor_ref"]
        assert d["email_verified"] == False

    def test_verify_bad_token_404(self):
        r = requests.get(f"{BASE}/api/v1/vendors/verify/not-a-real-token")
        assert r.status_code == 404

    def test_set_password_activates_and_vendor_can_login(self):
        tok = TestVendorInvite._state["token"]
        r = requests.post(f"{BASE}/api/v1/vendors/verify/{tok}/complete",
                          json={"password": "Vendor@123"})
        assert r.status_code == 200, r.text
        assert r.json().get("ok") == True

        s = requests.Session()
        lr = s.post(f"{BASE}/api/v1/vendor/auth/login",
                    json={"email": TestVendorInvite._state["email"], "password": "Vendor@123"})
        assert lr.status_code == 200, f"vendor login failed: {lr.status_code} {lr.text}"

    def test_token_reuse_rejected(self):
        tok = TestVendorInvite._state["token"]
        r = requests.post(f"{BASE}/api/v1/vendors/verify/{tok}/complete",
                          json={"password": "Vendor@123"})
        assert r.status_code in (400, 404)


# ============ Registration template ============

class TestRegistrationTemplate:
    def test_upload_and_download_pdf(self, admin):
        pdf_bytes = b"%PDF-1.4\n% test template\n"
        files = {"file": ("blank_reg_form.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        r = admin.post(f"{BASE}/api/v1/vendors/registration-template", files=files)
        assert r.status_code == 200, r.text
        assert r.json()["file_name"] == "blank_reg_form.pdf"

        meta = requests.get(f"{BASE}/api/v1/vendors/registration-template/meta")
        assert meta.status_code == 200 and meta.json()["available"] == True

        dl = requests.get(f"{BASE}/api/v1/vendors/registration-template")
        assert dl.status_code == 200
        assert dl.content == pdf_bytes
        assert "pdf" in dl.headers.get("content-type", "").lower()


# ============ Permissions Matrix ============

class TestPermissionsMatrix:
    def test_get_defaults(self, admin):
        r = admin.get(f"{BASE}/api/v1/permissions")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["scope"] == "notices"
        rows = data["rows"]
        assert len(rows) == 9
        roles = {row["role"] for row in rows}
        expected = {"admin", "escrow_agent", "certifier", "legal_counsel", "accounting",
                    "committee_member", "auditor", "support", "reviewer"}
        assert expected == roles

    def test_put_and_persist(self, admin):
        # flip legal_counsel.modify → False (was True by default)
        r = admin.get(f"{BASE}/api/v1/permissions")
        rows = r.json()["rows"]
        for row in rows:
            if row["role"] == "legal_counsel":
                row["modify"] = False
        pr = admin.put(f"{BASE}/api/v1/permissions", json={"rows": rows})
        assert pr.status_code == 200, pr.text

        r2 = admin.get(f"{BASE}/api/v1/permissions")
        legal = next(x for x in r2.json()["rows"] if x["role"] == "legal_counsel")
        assert legal["modify"] == False

    def test_reset(self, admin):
        r = admin.post(f"{BASE}/api/v1/permissions/reset")
        assert r.status_code == 200
        rows = r.json()["rows"]
        assert len(rows) == 9

    def test_reviewer_cannot_create_notice_403(self, reviewer_session):
        r = reviewer_session.post(f"{BASE}/api/v1/notices", json={
            "title": "TEST_reviewer_notice",
            "document_type": "tender",
            "category": "general",
            "description": "should be blocked",
            "budget_currency": "KZT",
            "budget_amount": 1000,
            "delivery_country": "KZ",
            "submission_deadline": "2030-12-31T23:59:59Z",
            "is_published": False,
        })
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        assert "Permissions Matrix" in r.text


# ============ Notices with documents ============

class TestNoticeDocument:
    def test_create_notice_and_upload_primary_plus_attachment(self, admin):
        payload = {
            "title": f"TEST_notice_{uuid.uuid4().hex[:6]}",
            "document_type": "tender",
            "category": "general",
            "description": "wave9 test",
            "budget_currency": "KZT",
            "budget_amount": 500000,
            "delivery_country": "KZ",
            "submission_deadline": "2030-12-31T23:59:59Z",
            "is_published": False,
        }
        r = admin.post(f"{BASE}/api/v1/notices", json=payload)
        assert r.status_code == 200, r.text
        notice_ref = r.json()["notice_ref"]

        # Upload primary
        files = {"file": ("tender.pdf", io.BytesIO(b"%PDF-1.4 test tender"), "application/pdf")}
        r1 = admin.post(f"{BASE}/api/v1/notices/{notice_ref}/document",
                        data={"kind": "primary"}, files=files)
        assert r1.status_code == 200, r1.text
        assert r1.json()["kind"] == "primary"

        # Upload attachment
        files2 = {"file": ("annex1.txt", io.BytesIO(b"annex content"), "text/plain")}
        r2 = admin.post(f"{BASE}/api/v1/notices/{notice_ref}/document",
                        data={"kind": "attachment"}, files=files2)
        assert r2.status_code == 200, r2.text

        # Verify persistence via admin GET
        g = admin.get(f"{BASE}/api/v1/notices/{notice_ref}/admin")
        assert g.status_code == 200
        d = g.json()
        assert d.get("primary_document", {}).get("file_name") == "tender.pdf"
        assert len(d.get("attachments") or []) >= 1


# ============ Committee external invitees ============

class TestCommitteeExternal:
    def test_create_committee_with_external_and_accept_flow(self, admin):
        # Create a notice to attach committee to
        payload = {
            "title": f"TEST_committee_notice_{uuid.uuid4().hex[:6]}",
            "document_type": "tender", "category": "general",
            "description": "committee target",
            "budget_currency": "KZT", "budget_amount": 100000,
            "delivery_country": "KZ",
            "submission_deadline": "2030-12-31T23:59:59Z",
            "is_published": True,
        }
        nr = admin.post(f"{BASE}/api/v1/notices", json=payload)
        assert nr.status_code == 200, nr.text
        notice_ref = nr.json()["notice_ref"]

        # Get admin's staff list to pick chair + members
        sl = admin.get(f"{BASE}/api/v1/staff")
        assert sl.status_code == 200
        staff = sl.json()
        # Chair must be admin role
        chair = next(s for s in staff if "admin" in (s.get("roles") or [s.get("role")]))
        members = [s["id"] for s in staff[:3]]
        # dedupe
        if chair["id"] in members:
            members = [m for m in members if m != chair["id"]]
        if not members:
            members = [chair["id"]]

        ext_email = f"TEST_ext_{uuid.uuid4().hex[:6]}@example.com"
        cr = admin.post(f"{BASE}/api/v1/committees", json={
            "notice_ref": notice_ref,
            "chairperson_id": chair["id"],
            "member_ids": members,
            "quorum": 1,
            "external_invitees": [
                {"email": ext_email, "name": "Jane External",
                 "designation": "Independent Advisor"}
            ],
        })
        assert cr.status_code == 200, cr.text
        committee = cr.json()
        assert len(committee.get("external_invitees") or []) == 1
        inv = committee["external_invitees"][0]
        assert inv["designation"] == "Independent Advisor"
        token = inv["accept_token"]

        # PUBLIC meta lookup
        meta = requests.get(f"{BASE}/api/v1/committees/external/{token}")
        assert meta.status_code == 200, meta.text
        m = meta.json()
        assert m["notice_ref"] == notice_ref
        assert m["invitee"]["email"] == ext_email.lower()
        assert m["invitee"]["status"] == "invited"

        # PUBLIC accept
        dec = requests.post(f"{BASE}/api/v1/committees/external/{token}/decision",
                            json={"decision": "accepted"})
        assert dec.status_code == 200, dec.text
        assert dec.json()["decision"] == "accepted"

        # Verify status flipped in list
        lc = admin.get(f"{BASE}/api/v1/committees")
        assert lc.status_code == 200
        found = None
        for c in lc.json():
            for i in c.get("external_invitees") or []:
                if i.get("accept_token") == token:
                    found = i
                    break
            if found:
                break
        assert found and found["status"] == "accepted"

    def test_invalid_decision_400(self):
        r = requests.post(f"{BASE}/api/v1/committees/external/whatever/decision",
                          json={"decision": "meh"})
        assert r.status_code == 400
