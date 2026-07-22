"""End-to-end backend tests for PMC Managers Tender Management API.

Covers: health, public stats, auth (login/register/me), vendor profile submission,
admin approve, tender CRUD, bids (submit/duplicate/award), notifications, uploads.
"""
import io
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fallback for backend test container - read from frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@pmcmanagers.com", "password": "Admin@123"}
BUYER = {"email": "buyer@pmcmanagers.com", "password": "Buyer@123"}
VENDOR_PENDING = {"email": "vendor@example.com", "password": "Vendor@123"}


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, creds):
    r = session.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return r.json()


# -------- Shared context (order-preserving via module state) --------
CTX = {}


# ---------- Health / public ----------
class TestHealth:
    def test_health(self):
        r = requests.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_public_stats(self):
        r = requests.get(f"{API}/public/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("tenders_open", "vendors_approved", "total_tenders"):
            assert k in data
            assert isinstance(data[k], int)


# ---------- Auth ----------
class TestAuth:
    def test_admin_login_and_me(self):
        s = _session()
        user = _login(s, ADMIN)
        assert user["role"] == "admin"
        assert user["email"] == ADMIN["email"]
        # cookies set
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies
        r = s.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
        CTX["admin_session"] = s

    def test_buyer_login(self):
        s = _session()
        user = _login(s, BUYER)
        assert user["role"] == "buyer"
        CTX["buyer_session"] = s

    def test_vendor_pending_login(self):
        s = _session()
        user = _login(s, VENDOR_PENDING)
        assert user["role"] == "vendor"
        assert user["vendor_status"] == "pending"
        CTX["vendor_pending_session"] = s

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "wrongpass"}, timeout=10)
        assert r.status_code == 401

    def test_register_vendor_self(self):
        uniq = uuid.uuid4().hex[:8]
        creds = {
            "email": f"TEST_vendor_{uniq}@example.com",
            "password": "Vendor@123",
            "name": f"Test Vendor {uniq}",
            "role": "vendor",
        }
        s = _session()
        r = s.post(f"{API}/auth/register", json=creds, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["role"] == "vendor"
        assert data["vendor_status"] == "pending"
        # cookies set
        assert "access_token" in s.cookies
        CTX["new_vendor_session"] = s
        CTX["new_vendor_creds"] = creds
        CTX["new_vendor_id"] = data["id"]

    def test_register_buyer_self(self):
        uniq = uuid.uuid4().hex[:8]
        creds = {
            "email": f"TEST_buyer_{uniq}@example.com",
            "password": "Buyer@123",
            "name": f"Test Buyer {uniq}",
            "role": "buyer",
        }
        r = requests.post(f"{API}/auth/register", json=creds, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "buyer"

    def test_register_admin_blocked(self):
        uniq = uuid.uuid4().hex[:8]
        r = requests.post(
            f"{API}/auth/register",
            json={"email": f"TEST_admin_{uniq}@example.com", "password": "Admin@123", "name": "x", "role": "admin"},
            timeout=15,
        )
        assert r.status_code == 403


# ---------- Vendor profile + admin approval ----------
class TestVendorLifecycle:
    def test_vendor_submit_full_profile(self):
        s = CTX.get("new_vendor_session")
        assert s is not None, "prerequisite registration test must run first"
        payload = {
            "company_name": "TEST_Global Trading LLC",
            "trade_name": "GTL",
            "registered_address": "123 Astana Ave, Astana",
            "mailing_address": "PO Box 100, Astana",
            "country": "KZ",
            "country_id_label": "BIN",
            "registration_number": "BIN1234567890",
            "incorporation_date": "2015-06-01",
            "tax_id": "TIN-999",
            "legal_entity_type": "LLC",
            "website": "https://example.com",
            "employees_count": 42,
            "contact_name": "Alia Test",
            "contact_title": "CEO",
            "contact_office_phone": "+7 700 000 0000",
            "contact_mobile": "+7 700 111 1111",
            "contact_email": "alia@example.com",
            "signatory_name": "Alia Test",
            "signatory_title": "CEO",
            "signatory_contact": "+7 700 000 0000",
            "bank_name": "Halyk Bank",
            "bank_branch": "Astana",
            "bank_account_number": "KZ12345678901234567890",
            "bank_swift": "HSBKKZKX",
            "bank_address": "Astana",
            "primary_sector": "Construction",
            "business_description": "Full-service supplier of construction materials.",
            "operating_regions": ["KZ", "UZ"],
            "business_categories": ["Land survey & demarcation", "Topographic survey"],
            "previous_projects": [
                {"name": "Bridge A", "client": "Gov", "value": 1000000, "currency": "USD", "period": "2022"}
            ],
            "references": [
                {"name": "Ref One", "position": "Director", "phone": "+7", "email": "r@x.com", "company": "X"}
            ],
            "litigation_history": "None",
            "decl_conflict_of_interest": True,
            "decl_integrity": True,
            "decl_accuracy": True,
            "decl_data_consent": True,
            "decl_fee": True,
            "decl_notification": True,
            "signature_name": "Alia Test",
            "signature_title": "CEO",
            "signature_date": datetime.now(timezone.utc).date().isoformat(),
        }
        r = s.post(f"{API}/vendor/profile", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("vendor_status") == "pending"

    def test_vendor_get_profile(self):
        s = CTX["new_vendor_session"]
        r = s.get(f"{API}/vendor/profile", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["vendor_status"] == "pending"
        assert data["vendor_profile"]["company_name"] == "TEST_Global Trading LLC"

    def test_admin_sees_new_vendor(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/admin/vendors", timeout=10)
        assert r.status_code == 200
        vendors = r.json()
        ids = {v["id"] for v in vendors}
        assert CTX["new_vendor_id"] in ids

    def test_admin_approve_vendor(self):
        s = CTX["admin_session"]
        r = s.post(f"{API}/admin/vendors/{CTX['new_vendor_id']}/approve", timeout=10)
        assert r.status_code == 200
        # vendor login and check status
        vs = _session()
        me = _login(vs, CTX["new_vendor_creds"])
        assert me["vendor_status"] == "approved"
        CTX["new_vendor_session"] = vs  # refreshed

    def test_vendor_notifications_have_approval(self):
        s = CTX["new_vendor_session"]
        r = s.get(f"{API}/notifications", timeout=10)
        assert r.status_code == 200
        titles = [n["title"] for n in r.json()]
        assert any("approved" in t.lower() for t in titles), titles


# ---------- Tenders ----------
class TestTenders:
    def test_buyer_create_tender(self):
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        payload = {
            "title": f"TEST_Tender_{uuid.uuid4().hex[:6]}",
            "description": "Provide land survey services for campus site A.",
            "category": "Land survey & demarcation",
            "budget_currency": "USD",
            "budget_amount": 50000,
            "submission_deadline": deadline,
            "delivery_location": "Astana, KZ",
            "eligibility_criteria": "Licensed surveyors only",
            "attachments": [],
        }
        r = s.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["status"] == "open"
        assert "id" in t
        CTX["tender_id"] = t["id"]

    def test_buyer_list_mine(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders?mine=true", timeout=10)
        assert r.status_code == 200
        ids = [t["id"] for t in r.json()]
        assert CTX["tender_id"] in ids

    def test_get_tender_by_id(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders/{CTX['tender_id']}", timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == CTX["tender_id"]


# ---------- Bids ----------
class TestBids:
    def test_unapproved_vendor_cannot_bid(self):
        # vendor@example.com is pending
        s = CTX["vendor_pending_session"]
        payload = {
            "tender_id": CTX["tender_id"],
            "price_currency": "USD",
            "price_amount": 40000,
            "delivery_days": 60,
            "proposal": "We propose x.",
        }
        r = s.post(f"{API}/bids", json=payload, timeout=10)
        assert r.status_code == 403
        assert "not approved" in r.text.lower()

    def test_approved_vendor_can_bid(self):
        s = CTX["new_vendor_session"]  # now approved
        payload = {
            "tender_id": CTX["tender_id"],
            "price_currency": "USD",
            "price_amount": 45000,
            "delivery_days": 60,
            "proposal": "Comprehensive survey with modern GPS.",
        }
        r = s.post(f"{API}/bids", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["status"] == "submitted"
        CTX["bid_id"] = b["id"]

    def test_duplicate_bid_rejected(self):
        s = CTX["new_vendor_session"]
        payload = {
            "tender_id": CTX["tender_id"],
            "price_currency": "USD",
            "price_amount": 46000,
            "delivery_days": 55,
            "proposal": "Duplicate attempt",
        }
        r = s.post(f"{API}/bids", json=payload, timeout=10)
        assert r.status_code == 400

    def test_buyer_list_bids(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/bids?tender_id={CTX['tender_id']}", timeout=10)
        assert r.status_code == 200
        bids = r.json()
        assert any(b["id"] == CTX["bid_id"] for b in bids)

    def test_other_buyer_forbidden(self):
        # register another buyer, they shouldn't see bids on our tender
        uniq = uuid.uuid4().hex[:8]
        creds = {
            "email": f"TEST_buyer2_{uniq}@example.com",
            "password": "Buyer@123",
            "name": "Buyer 2",
            "role": "buyer",
        }
        s = _session()
        rr = s.post(f"{API}/auth/register", json=creds, timeout=15)
        assert rr.status_code == 200
        r = s.get(f"{API}/bids?tender_id={CTX['tender_id']}", timeout=10)
        assert r.status_code == 403

    def test_buyer_cannot_bid_own_tender(self):
        # buyers don't have role=vendor, POST /bids should 403 due to require_role("vendor")
        s = CTX["buyer_session"]
        r = s.post(f"{API}/bids", json={
            "tender_id": CTX["tender_id"],
            "price_currency": "USD",
            "price_amount": 30000,
            "delivery_days": 30,
            "proposal": "self bid"
        }, timeout=10)
        assert r.status_code == 403

    def test_award_bid(self):
        s = CTX["buyer_session"]
        r = s.post(f"{API}/bids/{CTX['bid_id']}/award", timeout=10)
        assert r.status_code == 200
        # confirm tender status
        t = s.get(f"{API}/tenders/{CTX['tender_id']}", timeout=10).json()
        assert t["status"] == "awarded"
        assert t["awarded_bid_id"] == CTX["bid_id"]
        # bid status via list
        bids = s.get(f"{API}/bids?tender_id={CTX['tender_id']}", timeout=10).json()
        awarded = [b for b in bids if b["id"] == CTX["bid_id"]][0]
        assert awarded["status"] == "awarded"


# ---------- Tender close permissions ----------
class TestTenderClose:
    def test_close_forbidden_for_non_owner(self):
        # New buyer must not close our tender
        uniq = uuid.uuid4().hex[:8]
        creds = {"email": f"TEST_buyer3_{uniq}@example.com", "password": "Buyer@123", "name": "b3", "role": "buyer"}
        s = _session()
        assert s.post(f"{API}/auth/register", json=creds, timeout=15).status_code == 200
        r = s.post(f"{API}/tenders/{CTX['tender_id']}/close", timeout=10)
        assert r.status_code == 403


# ---------- Uploads ----------
class TestUploads:
    def test_upload_small(self):
        s = CTX["admin_session"]
        files = {"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
        # need to remove Content-Type=application/json header for multipart
        headers = {k: v for k, v in s.headers.items() if k.lower() != "content-type"}
        r = requests.post(f"{API}/uploads", files=files, cookies=s.cookies, headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "test.txt"
        assert data["size"] == 11
        assert data["data"].startswith("data:text/plain;base64,")

    def test_upload_too_large(self):
        s = CTX["admin_session"]
        big = b"a" * (5 * 1024 * 1024 + 100)
        files = {"file": ("big.bin", io.BytesIO(big), "application/octet-stream")}
        headers = {k: v for k, v in s.headers.items() if k.lower() != "content-type"}
        r = requests.post(f"{API}/uploads", files=files, cookies=s.cookies, headers=headers, timeout=30)
        assert r.status_code == 413


# ---------- Admin stats / users ----------
class TestAdminEndpoints:
    def test_admin_stats(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/admin/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("users", "vendors_pending", "vendors_approved", "tenders_open", "tenders_total", "bids_total"):
            assert k in data
            assert isinstance(data[k], int)

    def test_admin_users(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/admin/users", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 3


# ---------- Notifications ----------
class TestNotifications:
    def test_mark_all_read(self):
        s = CTX["new_vendor_session"]
        r = s.post(f"{API}/notifications/mark-all-read", timeout=10)
        assert r.status_code == 200
        # verify all unread now 0
        notifs = s.get(f"{API}/notifications", timeout=10).json()
        assert all(n["read"] is True for n in notifs)
