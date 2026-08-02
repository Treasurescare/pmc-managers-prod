"""Regression tests for Wave 7-8 features:
1. AI Audit Copilot endpoint
2. High-risk role MFA enforcement (staff login rejection)
3. GDPR vendor self-forget endpoint
4. Bids listing includes active_step field (matrix pipeline)
5. Per-tenant public endpoint
6. KYC stub endpoints (start + get by case_id)
"""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://tender-hub-57.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@123"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/staff/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
                     "active_role": "admin"})
    assert r.status_code == 200, r.text
    csrf = r.json()["csrf_token"]
    s.headers.update({"X-CSRF-Token": csrf})
    return s


@pytest.fixture(scope="module")
def ensure_tenants(admin_session):
    """Seed PMC-KZ-01 and DEMO-CORP if missing."""
    for code, name, color, kind in [
        ("PMC-KZ-01", "PMC Managers Kazakhstan", "#0b1e3f", "pmc"),
        ("DEMO-CORP", "Demo Corporate Client", "#3b0764", "corporate"),
    ]:
        # try public read first (works unauthenticated)
        r = requests.get(f"{BASE}/api/v1/tenants/public/{code}")
        if r.status_code == 200:
            continue
        # create via admin
        cr = admin_session.post(f"{BASE}/api/v1/tenants",
                                 json={"code": code, "name": name, "kind": kind,
                                       "country": "KZ", "branding_color": color,
                                       "is_active": True})
        assert cr.status_code in (200, 201, 409), cr.text
    return True


# ---------- 1. AI Audit Copilot ----------

class TestAuditCopilot:
    def test_copilot_endpoint_returns_verdict(self, admin_session):
        # find any bid to test on
        r = admin_session.get(f"{BASE}/api/v1/bids")
        assert r.status_code == 200, r.text
        bids = r.json()
        # need a bid past submitted stage — pick any that exists
        if not bids:
            pytest.skip("No bids seeded")
        bid_id = bids[0]["id"]
        cr = admin_session.post(f"{BASE}/api/v1/analytics/ai/audit-copilot/{bid_id}")
        assert cr.status_code == 200, cr.text
        data = cr.json()
        assert data["verdict"] in ("ok", "review")
        assert "flags" in data
        assert isinstance(data["flags"], list)
        assert "generated_at" in data
        assert "history_length" in data

    def test_copilot_404_on_bad_bid(self, admin_session):
        r = admin_session.post(f"{BASE}/api/v1/analytics/ai/audit-copilot/507f1f77bcf86cd799439011")
        assert r.status_code == 404


# ---------- 2. High-risk role MFA enforcement ----------

class TestHighRiskMFA:
    @pytest.mark.parametrize("email,password,role", [
        ("escrow@pmcmanagers.com", "Escrow@123", "escrow_agent"),
        ("legal@pmcmanagers.com", "Legal@123", "legal_counsel"),
        ("accounts@pmcmanagers.com", "Accts@123", "accounting"),
    ])
    def test_high_risk_rejected_without_mfa(self, email, password, role):
        r = requests.post(f"{BASE}/api/v1/staff/auth/login",
                          json={"email": email, "password": password, "active_role": role})
        assert r.status_code == 403, f"{role} should be 403 but was {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        assert "MFA is required" in detail
        assert role in detail

    def test_admin_role_unaffected(self):
        r = requests.post(f"{BASE}/api/v1/staff/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
                                "active_role": "admin"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["active_role"] == "admin"


# ---------- 3. GDPR vendor self-forget ----------

class TestGdprSelfForget:
    def _seed_vendor_direct(self):
        """Seed a vendor directly via motor — simpler than the registration path."""
        import asyncio, sys
        sys.path.insert(0, "/app/backend")
        from motor.motor_asyncio import AsyncIOMotorClient
        from security import hash_password
        email = f"test_gdpr_{uuid.uuid4().hex[:8]}@example.com"
        pw = "Vendor@123"

        async def _ins():
            c = AsyncIOMotorClient("mongodb://localhost:27017")
            db = c["pmc_tender_db"]
            await db.vendors.insert_one({
                "email": email, "company_name": "TEST GDPR Vendor",
                "password_hash": hash_password(pw),
                "is_active": True, "must_change_password": False,
                "vendor_ref": f"PMC-VEN-TEST-{uuid.uuid4().hex[:6]}",
                "tenant_id": "PMC-KZ-01",
            })
            c.close()
        asyncio.run(_ins())
        return email, pw

    def test_gdpr_self_forget_flow(self, admin_session):
        email, current_pw = self._seed_vendor_direct()
        # Vendor login
        vs = requests.Session()
        lr = vs.post(f"{BASE}/api/v1/vendor/auth/login",
                     json={"email": email, "password": current_pw})
        assert lr.status_code == 200, lr.text
        csrf = lr.json()["csrf_token"]
        vs.headers.update({"X-CSRF-Token": csrf})

        # Wrong password
        wr = vs.post(f"{BASE}/api/v1/vendor/gdpr-forget",
                     json={"password": "wrong-pw"})
        assert wr.status_code == 401

        # Correct password
        ok = vs.post(f"{BASE}/api/v1/vendor/gdpr-forget",
                     json={"password": current_pw})
        assert ok.status_code == 200, ok.text
        assert ok.json().get("ok") is True

        # Vendor should now be unable to log in (is_active=false)
        rr = requests.post(f"{BASE}/api/v1/vendor/auth/login",
                           json={"email": email, "password": current_pw})
        # Either 403 (disabled) or 401 (email changed)
        assert rr.status_code in (401, 403)


# ---------- 4. Bids listing has active_step ----------

class TestActiveStepMatrix:
    def test_bids_list_returns_active_step(self, admin_session):
        r = admin_session.get(f"{BASE}/api/v1/bids")
        assert r.status_code == 200, r.text
        bids = r.json()
        if not bids:
            pytest.skip("No bids to check active_step on")
        for b in bids[:5]:
            assert "active_step" in b, f"missing active_step in {b.get('bid_ref')}"
            step = b["active_step"]
            assert "role_code" in step
            assert "label" in step


# ---------- 5. Public tenant endpoint ----------

class TestPublicTenant:
    def test_demo_corp_public(self, ensure_tenants):
        r = requests.get(f"{BASE}/api/v1/tenants/public/DEMO-CORP")
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["code"] == "DEMO-CORP"
        assert t["name"]
        assert t["kind"] in ("corporate", "government", "pmc")
        assert "branding_color" in t

    def test_pmc_kz_public(self, ensure_tenants):
        r = requests.get(f"{BASE}/api/v1/tenants/public/PMC-KZ-01")
        assert r.status_code == 200, r.text
        assert r.json()["code"] == "PMC-KZ-01"

    def test_unknown_tenant_404(self):
        r = requests.get(f"{BASE}/api/v1/tenants/public/NOT-A-REAL-TENANT")
        assert r.status_code == 404


# ---------- 6. KYC stub ----------

class TestKycStub:
    def test_start_and_get_case(self, admin_session):
        # find any vendor
        r = admin_session.get(f"{BASE}/api/v1/vendors")
        if r.status_code != 200 or not r.json():
            pytest.skip("No vendors available")
        vendor = r.json()[0]
        vref = vendor.get("vendor_ref")
        if not vref:
            pytest.skip("No vendor_ref")
        cr = admin_session.post(f"{BASE}/api/v1/kyc/start",
                                 json={"vendor_ref": vref, "level": "basic"})
        assert cr.status_code == 200, cr.text
        data = cr.json()
        assert "case_id" in data
        assert "risk_score" in data
        assert data["status"] in ("clear", "review", "hit")
        assert isinstance(data["flags"], list)

        # Now fetch it
        gr = admin_session.get(f"{BASE}/api/v1/kyc/{data['case_id']}")
        assert gr.status_code == 200, gr.text
        got = gr.json()
        assert got["case_id"] == data["case_id"]
        assert got["vendor_ref"] == vref

    def test_kyc_case_not_found(self, admin_session):
        r = admin_session.get(f"{BASE}/api/v1/kyc/kyc_does_not_exist")
        assert r.status_code == 404
