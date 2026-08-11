"""PMC v2 — Wave 1 backend regression tests.

Covers: staff auth (multi-role), vendor auth, notice+emd, bid, Stripe checkout,
sequential pipeline (escrow→admin→certifier→legal→accounting), committee,
inspections, tasks, chat, masters.
"""
import os
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL",
                          "https://tender-hub-57.preview.pmcmanagers.com").rstrip("/")
API = f"{BASE_URL}/api/v1"

OWNER_EMAIL = os.environ.get("PMC_TEST_OWNER_EMAIL", "kannan@emeraldcorporates.com")
OWNER_PASSWORD = os.environ.get("PMC_TEST_OWNER_PASSWORD", "Admin@123")
STAFF_CREDS = [
    ("escrow@pmcmanagers.com",    os.environ.get("PMC_TEST_ESCROW_PW",    "Escrow@123"),  "escrow_agent"),
    ("certifier@pmcmanagers.com", os.environ.get("PMC_TEST_CERTIFIER_PW", "Certify@123"), "certifier"),
    ("legal@pmcmanagers.com",     os.environ.get("PMC_TEST_LEGAL_PW",     "Legal@123"),   "legal_counsel"),
    ("accounts@pmcmanagers.com",  os.environ.get("PMC_TEST_ACCTS_PW",     "Accts@123"),   "accounting"),
    ("committee@pmcmanagers.com", os.environ.get("PMC_TEST_COMMITTEE_PW", "Bid@1234"),    "committee_member"),
]


# ---------- Helpers ----------

def _staff_login(email: str, password: str, active_role: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login",
               json={"email": email, "password": password, "active_role": active_role},
               timeout=15)
    assert r.status_code == 200, f"staff login failed {email}/{active_role}: {r.status_code} {r.text}"
    body = r.json()
    csrf = body.get("csrf_token") or s.cookies.get("csrf_token")
    assert csrf, "no csrf_token"
    s.headers.update({"X-CSRF-Token": csrf})
    s._me = body  # attach for tests
    return s


def _admin_session() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"owner login failed: {r.text}"
    body = r.json()
    csrf = body.get("csrf_token") or s.cookies.get("csrf_token")
    s.headers.update({"Authorization": f"Bearer {body['token']}", "X-CSRF-Token": csrf})
    s._me = body
    return s


# Shared state across the pipeline test class
STATE: dict = {}


@pytest.fixture(scope="session")
def admin_session():
    return _admin_session()


@pytest.fixture(scope="session")
def mongo_db():
    """Direct DB access — needed to seed a known-password vendor and to mark EMD paid."""
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "pmc_tender_db")
    client = MongoClient(mongo_url)
    return client[db_name]


# ============================================================
#  1. Staff auth — 9 roles, 6 seeded accounts
# ============================================================
class TestStaffAuth:
    def test_list_roles_returns_nine(self):
        r = requests.get(f"{API}/staff/roles", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "roles" in d
        assert len(d["roles"]) == 9, f"expected 9 roles, got {len(d['roles'])}"
        for expected in ["admin", "reviewer", "escrow_agent", "certifier",
                         "legal_counsel", "accounting", "committee_member",
                         "auditor", "support"]:
            assert expected in d["roles"], f"missing role {expected}"

    def test_owner_login_as_admin(self):
        s = _staff_login(OWNER_EMAIL, OWNER_PASSWORD, "admin")
        me = s._me
        assert me["email"] == OWNER_EMAIL
        assert me["active_role"] == "admin"
        assert "admin" in me["roles"]

    @pytest.mark.parametrize("email,pw,role", STAFF_CREDS)
    def test_seeded_staff_login(self, email, pw, role):
        s = _staff_login(email, pw, role)
        me = s._me
        assert me["email"] == email
        assert me["active_role"] == role
        assert role in me["roles"]

    def test_login_wrong_role_denied(self):
        # escrow user cannot log in as certifier
        r = requests.post(f"{API}/staff/auth/login", json={
            "email": "escrow@pmcmanagers.com", "password": "Escrow@123",
            "active_role": "certifier"}, timeout=15)
        assert r.status_code == 403

    def test_login_bad_password(self):
        r = requests.post(f"{API}/staff/auth/login", json={
            "email": OWNER_EMAIL, "password": "wrongpass",
            "active_role": "admin"}, timeout=15)
        assert r.status_code == 401


# ============================================================
#  2. Notice creation with EMD config
# ============================================================
class TestNoticeWithEMD:
    def test_create_notice_with_emd(self, admin_session):
        payload = {
            "title": f"TEST_Wave1_{uuid.uuid4().hex[:6]}",
            "description": "Wave1 pipeline test notice with EMD config.",
            "document_type": "tender",
            "category": "Modular operation theatres (OTs)",
            "delivery_country": "KZ",
            "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            "budget_currency": "USD",
            "budget_amount": 1000000,
            "emd_config": {"fixed_amount": 500.0, "percentage": 1.0, "currency": "USD"},
            "is_published": True,
        }
        r = admin_session.post(f"{API}/notices", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        ref = d["notice_ref"]
        assert ref.startswith("PMC-NOT-")
        assert d.get("emd_config", {}).get("fixed_amount") == 500.0
        # Publish if not already
        if not d.get("is_published"):
            admin_session.post(f"{API}/notices/{ref}/publish", timeout=15)
        STATE["notice_ref"] = ref
        STATE["budget"] = 1000000


# ============================================================
#  3. Vendor auth — seed vendor doc directly with known bcrypt hash
# ============================================================
class TestVendorAuth:
    def test_seed_and_login_vendor(self, mongo_db):
        # Insert a fresh vendor with a known password via the backend's bcrypt helper
        import bcrypt
        # NOTE: backend lowercases email on login lookup — store lowercase.
        email = f"test_vendor_{uuid.uuid4().hex[:8]}@example.com"
        pw = "VendorPw@123"
        hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        vref = f"PMC-VND-TEST-{uuid.uuid4().hex[:6]}"
        res = mongo_db.vendors.insert_one({
            "email": email, "password_hash": hashed,
            "company_name": "TEST_Wave1_Vendor",
            "vendor_ref": vref,
            "must_change_password": True,
            "is_active": True,
            "tenant_id": "PMC-KZ-01",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        STATE["vendor_id"] = str(res.inserted_id)
        STATE["vendor_email"] = email
        STATE["vendor_pw"] = pw
        STATE["vendor_ref"] = vref

        # Login
        s = requests.Session()
        r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": pw}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == email
        assert body["must_change_password"] is True
        csrf = body.get("csrf_token")
        assert csrf
        s.headers.update({"X-CSRF-Token": csrf})
        STATE["vendor_session"] = s

    def test_change_password_flow(self):
        s = STATE["vendor_session"]
        new_pw = "NewVendPw@456"
        r = s.post(f"{API}/vendor/auth/change-password", json={
            "current_password": STATE["vendor_pw"], "new_password": new_pw}, timeout=15)
        assert r.status_code == 200, r.text
        # Re-login with new password
        s2 = requests.Session()
        r2 = s2.post(f"{API}/vendor/auth/login",
                     json={"email": STATE["vendor_email"], "password": new_pw}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["must_change_password"] == False
        STATE["vendor_pw"] = new_pw
        csrf = r2.json().get("csrf_token")
        s2.headers.update({"X-CSRF-Token": csrf})
        STATE["vendor_session"] = s2

    def test_bad_password_rejected(self):
        r = requests.post(f"{API}/vendor/auth/login",
                          json={"email": STATE["vendor_email"], "password": "wrongxx"}, timeout=15)
        assert r.status_code == 401


# ============================================================
#  4. Bid creation, EMD computation, Stripe checkout
# ============================================================
class TestBidAndPayment:
    def test_create_bid_computes_emd(self):
        s = STATE["vendor_session"]
        r = s.post(f"{API}/bids", json={
            "notice_ref": STATE["notice_ref"],
            "price_amount": 950000,
            "price_currency": "USD",
            "documents": [],
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # EMD due = 500 + 1% * 1,000,000 = 10,500
        assert d["emd_due_amount"] == pytest.approx(10500.0)
        assert d["status"] == "emd_pending"
        STATE["bid_id"] = d["id"]
        STATE["bid_ref"] = d["bid_ref"]

    def test_stripe_checkout_returns_url(self):
        s = STATE["vendor_session"]
        r = s.post(f"{API}/payments/emd/checkout", json={
            "bid_id": STATE["bid_id"],
            "origin_url": BASE_URL,
        }, timeout=30)
        # Stripe test key sk_test_managed may or may not work in sandbox;
        # accept both success and provisioning-related failure but log.
        if r.status_code != 200:
            pytest.skip(f"Stripe checkout unavailable in sandbox: {r.status_code} {r.text}")
        d = r.json()
        assert "checkout_url" in d and d["checkout_url"].startswith("http")
        assert "session_id" in d
        STATE["session_id"] = d["session_id"]

    def test_payment_transaction_row_created(self, mongo_db):
        if "session_id" not in STATE:
            pytest.skip("Stripe checkout skipped")
        rec = mongo_db.payment_transactions.find_one({"session_id": STATE["session_id"]})
        assert rec is not None
        assert rec["status"] == "initiated"
        assert rec["bid_id"] == STATE["bid_id"]
        assert rec["amount"] == pytest.approx(10500.0)

    def test_bypass_advance_to_emd_paid(self, mongo_db):
        """Directly move the bid to emd_paid to test the rest of the pipeline
        (avoiding an actual Stripe payment)."""
        from bson import ObjectId
        mongo_db.bids.update_one(
            {"_id": ObjectId(STATE["bid_id"])},
            {"$set": {"status": "emd_paid",
                      "emd_paid_amount": 10500.0,
                      "emd_paid_at": datetime.now(timezone.utc).isoformat()}},
        )
        bid = mongo_db.bids.find_one({"_id": ObjectId(STATE["bid_id"])})
        assert bid["status"] == "emd_paid"


# ============================================================
#  5. Sequential approval pipeline
# ============================================================
class TestPipeline:
    def test_escrow_accepts(self):
        s = _staff_login("escrow@pmcmanagers.com", "Escrow@123", "escrow_agent")
        r = s.post(f"{API}/bids/{STATE['bid_id']}/decision",
                   json={"action": "accept", "role": "escrow_agent"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "escrow_accepted"

    def test_admin_flags(self, admin_session):
        # admin_session already logged in via /admin/auth (role='admin')
        r = admin_session.post(f"{API}/bids/{STATE['bid_id']}/decision",
                               json={"action": "accept", "role": "admin"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "admin_flagged"

    def test_assign_certifier(self, admin_session, mongo_db):
        cert = mongo_db.admin_users.find_one({"email": "certifier@pmcmanagers.com"})
        cid = str(cert["_id"])
        STATE["certifier_id"] = cid
        r = admin_session.post(
            f"{API}/bids/{STATE['bid_id']}/assign-certifier?certifier_id={cid}", timeout=15)
        assert r.status_code == 200, r.text

    def test_certifier_clears(self):
        s = _staff_login("certifier@pmcmanagers.com", "Certify@123", "certifier")
        r = s.post(f"{API}/bids/{STATE['bid_id']}/decision",
                   json={"action": "accept", "role": "certifier"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "certifier_cleared"

    def test_legal_clears(self):
        s = _staff_login("legal@pmcmanagers.com", "Legal@123", "legal_counsel")
        r = s.post(f"{API}/bids/{STATE['bid_id']}/decision",
                   json={"action": "accept", "role": "legal_counsel"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "legal_cleared"

    def test_accounting_clears(self):
        s = _staff_login("accounts@pmcmanagers.com", "Accts@123", "accounting")
        r = s.post(f"{API}/bids/{STATE['bid_id']}/decision",
                   json={"action": "accept", "role": "accounting"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "accounting_cleared"

    def test_role_mismatch_denied(self):
        # legal user trying to act as accounting
        s = _staff_login("legal@pmcmanagers.com", "Legal@123", "legal_counsel")
        r = s.post(f"{API}/bids/{STATE['bid_id']}/decision",
                   json={"action": "accept", "role": "accounting"}, timeout=15)
        assert r.status_code == 403


# ============================================================
#  6. Committee — create, vote, close awarded
# ============================================================
class TestCommittee:
    def test_form_committee(self, admin_session, mongo_db):
        chair = mongo_db.admin_users.find_one({"email": "committee@pmcmanagers.com"})
        legal = mongo_db.admin_users.find_one({"email": "legal@pmcmanagers.com"})
        accts = mongo_db.admin_users.find_one({"email": "accounts@pmcmanagers.com"})
        STATE["chair_id"] = str(chair["_id"])
        r = admin_session.post(f"{API}/committees", json={
            "notice_ref": STATE["notice_ref"],
            "chairperson_id": str(chair["_id"]),
            "member_ids": [str(legal["_id"]), str(accts["_id"])],
            "quorum": 2,
        }, timeout=15)
        assert r.status_code == 200, r.text
        STATE["committee_id"] = r.json()["id"]

    def test_vote_cast_by_chair(self):
        s = _staff_login("committee@pmcmanagers.com", "Bid@1234", "committee_member")
        r = s.post(f"{API}/committees/vote", json={
            "committee_id": STATE["committee_id"],
            "bid_id": STATE["bid_id"],
            "vote": "approve", "remarks": "Looks good",
        }, timeout=15)
        assert r.status_code == 200, r.text

    def test_close_awarded(self, admin_session):
        r = admin_session.post(f"{API}/committees/close", json={
            "committee_id": STATE["committee_id"],
            "decision": "closed_awarded",
            "awarded_bid_id": STATE["bid_id"],
            "remarks": "Award to test vendor",
        }, timeout=15)
        assert r.status_code == 200, r.text

    def test_bid_marked_awarded(self, mongo_db):
        from bson import ObjectId
        b = mongo_db.bids.find_one({"_id": ObjectId(STATE["bid_id"])})
        assert b["status"] == "awarded"


# ============================================================
#  7. Inspections
# ============================================================
class TestInspections:
    def test_admin_assigns_inspection(self, admin_session):
        r = admin_session.post(f"{API}/inspections", json={
            "notice_ref": STATE["notice_ref"],
            "bid_id": STATE["bid_id"],
            "certifier_id": STATE["certifier_id"],
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "location": "Astana Site A",
            "notes": "Verify OT prefab area",
        }, timeout=15)
        assert r.status_code == 200, r.text
        STATE["inspection_id"] = r.json()["id"]

    def test_certifier_lists_mine(self):
        s = _staff_login("certifier@pmcmanagers.com", "Certify@123", "certifier")
        r = s.get(f"{API}/inspections?certifier_id=me", timeout=15)
        assert r.status_code == 200
        ids = [i["id"] for i in r.json()]
        assert STATE["inspection_id"] in ids

    def test_certifier_updates_and_adds_media(self):
        s = _staff_login("certifier@pmcmanagers.com", "Certify@123", "certifier")
        r = s.patch(f"{API}/inspections/{STATE['inspection_id']}",
                    json={"status": "completed", "result": "pass",
                          "report_summary": "All clear."}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "completed"

        # Add a media reference (dummy — uploads not tested end-to-end here)
        r2 = s.post(f"{API}/inspections/{STATE['inspection_id']}/media",
                    json={"kind": "photo", "key": "test/photo1.jpg",
                          "filename": "photo1.jpg",
                          "content_type": "image/jpeg", "size_bytes": 1234}, timeout=15)
        assert r2.status_code == 200, r2.text


# ============================================================
#  8. CRM Tasks
# ============================================================
class TestTasks:
    def test_create_task_and_followup(self, admin_session):
        r = admin_session.post(f"{API}/tasks", json={
            "title": f"TEST_Task_{uuid.uuid4().hex[:6]}",
            "description": "Test task",
            "assignee_id": admin_session._me["id"],
            "priority": "high",
        }, timeout=15)
        assert r.status_code == 200, r.text
        tid = r.json()["id"]

        # Followup — endpoint uses task_id in path, but model requires task_id in body too
        r2 = admin_session.post(f"{API}/tasks/{tid}/followups", json={
            "task_id": tid, "message": "Followup one", "attachments": [],
        }, timeout=15)
        assert r2.status_code == 200, r2.text

        r3 = admin_session.get(f"{API}/tasks?assignee_id=me", timeout=15)
        assert r3.status_code == 200
        assert any(t["id"] == tid for t in r3.json())


# ============================================================
#  9. Chat
# ============================================================
class TestChat:
    def test_post_get_delete_message(self, admin_session):
        r = admin_session.post(f"{API}/chat/messages", json={
            "context_type": "bid", "context_id": STATE["bid_id"], "body": "hello"
        }, timeout=15)
        assert r.status_code == 200, r.text
        mid = r.json()["id"]

        r2 = admin_session.get(
            f"{API}/chat/messages?context_type=bid&context_id={STATE['bid_id']}",
            timeout=15)
        assert r2.status_code == 200
        assert any(m["id"] == mid for m in r2.json())

        r3 = admin_session.delete(f"{API}/chat/messages/{mid}", timeout=15)
        assert r3.status_code == 200


# ============================================================
#  10. Masters
# ============================================================
class TestMasters:
    def test_create_company_role_matrix(self, admin_session):
        code = f"TEST{uuid.uuid4().hex[:4].upper()}"
        r = admin_session.post(f"{API}/masters/companies", json={
            "name": f"TEST_Co_{code}", "code": code, "country": "KZ",
        }, timeout=15)
        assert r.status_code == 200, r.text

        rcode = f"TESTROLE_{uuid.uuid4().hex[:4]}"
        r2 = admin_session.post(f"{API}/masters/roles", json={
            "code": rcode, "label": "Test Role", "permissions": ["bid.read"],
        }, timeout=15)
        assert r2.status_code == 200, r2.text

        r3 = admin_session.post(f"{API}/masters/approval-matrices", json={
            "name": f"TEST_Matrix_{uuid.uuid4().hex[:4]}",
            "applies_to": "bid",
            "steps": [
                {"order": 1, "role_code": "escrow_agent",
                 "action_label": "Escrow", "sla_hours": 24, "required": True},
                {"order": 2, "role_code": "admin",
                 "action_label": "Admin flag", "sla_hours": 24, "required": True},
            ],
        }, timeout=15)
        assert r3.status_code == 200, r3.text

        # Listings
        assert admin_session.get(f"{API}/masters/companies", timeout=15).status_code == 200
        assert admin_session.get(f"{API}/masters/roles", timeout=15).status_code == 200
        assert admin_session.get(f"{API}/masters/approval-matrices",
                                 timeout=15).status_code == 200
