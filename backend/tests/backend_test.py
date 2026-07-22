"""End-to-end backend tests for PMC Managers Tender Management API.

Covers: health, public stats, auth (login/register/me), vendor profile submission,
admin approve, tender CRUD, bids (submit/duplicate/award), notifications, uploads.

Iteration 2 additions: KZ license reference & gating, Stripe payments checkout,
Google OAuth callback, CSV bid export, admin stats fees_collected.
"""
import io
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

# Direct pymongo helper for flipping registration_fee_paid without going through Stripe
from pymongo import MongoClient
from bson import ObjectId as _ObjectId

# Load backend env for mongo access
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv as _load_dotenv  # type: ignore
_load_dotenv("/app/backend/.env")

_MONGO = MongoClient(os.environ["MONGO_URL"])
_DB = _MONGO[os.environ["DB_NAME"]]


def _mark_fee_paid(user_id: str):
    _DB.users.update_one({"_id": _ObjectId(user_id)}, {"$set": {"registration_fee_paid": True}})


def _set_kz_licenses(user_id: str, licenses):
    _DB.users.update_one({"_id": _ObjectId(user_id)},
                         {"$set": {"vendor_profile.kz_licenses": licenses}})

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
        # Reset vendor@example.com to pending — prior iterations may have approved it
        _DB.users.update_one({"email": VENDOR_PENDING["email"]},
                             {"$set": {"vendor_status": "pending"}})
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
        # Iteration 2: registration fee gate — pre-flip fee_paid to allow full-decl submit
        _mark_fee_paid(CTX["new_vendor_id"])
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


# =========================================================================
# ITERATION 2 — new feature tests (KZ licenses, payments, google, CSV, i18n)
# =========================================================================

# ---------- KZ licenses reference ----------
class TestKZLicensesReference:
    def test_kz_licenses_endpoint(self):
        r = requests.get(f"{API}/reference/kz-licenses", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "licenses" in data and "category_map" in data
        for expected in ["Medical gas installation", "Electrical installation", "Construction (1st category)"]:
            assert expected in data["licenses"], f"missing {expected}"
        assert len(data["licenses"]) == 6
        # spot-check map
        assert data["category_map"]["Medical gas pipeline systems"] == ["Medical gas installation"]


# ---------- Fee gate on vendor profile ----------
class TestRegistrationFeeGate:
    def test_402_when_all_decls_true_and_fee_not_paid(self):
        # Register a fresh vendor (no fee paid)
        uniq = uuid.uuid4().hex[:8]
        creds = {"email": f"TEST_feegate_{uniq}@example.com", "password": "Vendor@123",
                 "name": "Fee Gate Vendor", "role": "vendor"}
        s = _session()
        r = s.post(f"{API}/auth/register", json=creds, timeout=15)
        assert r.status_code == 200
        vid = r.json()["id"]
        CTX["feegate_vendor_id"] = vid
        CTX["feegate_vendor_session"] = s

        payload = {
            "company_name": f"TEST_FG_{uniq}", "registered_address": "x", "country": "US",
            "registration_number": "R1", "legal_entity_type": "LLC",
            "contact_name": "c", "contact_title": "CEO", "contact_office_phone": "+1",
            "contact_email": "c@example.com",
            "signatory_name": "s", "signatory_title": "CEO",
            "bank_name": "b", "bank_account_number": "1", "bank_swift": "SW",
            "primary_sector": "General", "business_description": "d",
            "decl_conflict_of_interest": True, "decl_integrity": True, "decl_accuracy": True,
            "decl_data_consent": True, "decl_fee": True, "decl_notification": True,
        }
        rr = s.post(f"{API}/vendor/profile", json=payload, timeout=15)
        assert rr.status_code == 402, f"expected 402, got {rr.status_code}: {rr.text}"
        assert "registration fee" in rr.text.lower()

    def test_profile_submit_ok_after_fee_paid(self):
        vid = CTX["feegate_vendor_id"]
        _mark_fee_paid(vid)
        s = CTX["feegate_vendor_session"]
        payload = {
            "company_name": "TEST_FGPaid", "registered_address": "x", "country": "US",
            "registration_number": "R1", "legal_entity_type": "LLC",
            "contact_name": "c", "contact_title": "CEO", "contact_office_phone": "+1",
            "contact_email": "c@example.com",
            "signatory_name": "s", "signatory_title": "CEO",
            "bank_name": "b", "bank_account_number": "1", "bank_swift": "SW",
            "primary_sector": "General", "business_description": "d",
            "decl_conflict_of_interest": True, "decl_integrity": True, "decl_accuracy": True,
            "decl_data_consent": True, "decl_fee": True, "decl_notification": True,
        }
        rr = s.post(f"{API}/vendor/profile", json=payload, timeout=15)
        assert rr.status_code == 200, rr.text
        assert rr.json().get("vendor_status") == "pending"


# ---------- Payments (Stripe Flow B) ----------
class TestPayments:
    def test_checkout_returns_url_and_session(self):
        # Use a fresh vendor that has NOT paid
        uniq = uuid.uuid4().hex[:8]
        creds = {"email": f"TEST_pay_{uniq}@example.com", "password": "Vendor@123",
                 "name": "Pay Vendor", "role": "vendor"}
        s = _session()
        r = s.post(f"{API}/auth/register", json=creds, timeout=15)
        assert r.status_code == 200
        CTX["pay_vendor_id"] = r.json()["id"]
        CTX["pay_vendor_session"] = s

        r2 = s.post(f"{API}/payments/checkout",
                    json={"origin_url": "https://tender-hub-57.preview.emergentagent.com"},
                    timeout=25)
        assert r2.status_code == 200, f"checkout failed: {r2.status_code} {r2.text}"
        data = r2.json()
        assert "checkout_url" in data and "session_id" in data
        assert data["checkout_url"].startswith("http")
        CTX["pay_session_id"] = data["session_id"]

        # Verify payment_transactions record inserted with status=initiated
        rec = _DB.payment_transactions.find_one({"session_id": data["session_id"]})
        assert rec is not None, "payment_transactions record missing"
        assert rec["status"] == "initiated"
        assert rec["payment_status"] == "pending"
        assert rec["user_id"] == CTX["pay_vendor_id"]
        assert float(rec["amount"]) == 100.0

    def test_payment_status_returns_shape(self):
        sid = CTX["pay_session_id"]
        s = CTX["pay_vendor_session"]
        r = s.get(f"{API}/payments/status/{sid}", timeout=25)
        # Might return 200 with pending; endpoint is public per code (no auth dep) but let's just check status shape
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == sid
        assert "status" in d and "payment_status" in d

    def test_checkout_400_when_already_paid(self):
        # Mark the pay-vendor as already paid
        _mark_fee_paid(CTX["pay_vendor_id"])
        s = CTX["pay_vendor_session"]
        r = s.post(f"{API}/payments/checkout",
                   json={"origin_url": "https://tender-hub-57.preview.emergentagent.com"},
                   timeout=15)
        assert r.status_code == 400
        assert "already paid" in r.text.lower()


# ---------- KZ tender + license gating on bid ----------
class TestKZLicenseGate:
    def test_buyer_kz_tender_auto_attaches_licenses(self):
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        payload = {
            "title": f"TEST_KZ_Medgas_{uuid.uuid4().hex[:6]}",
            "description": "Medical gas pipeline works for hospital block A.",
            "category": "Medical gas pipeline systems",
            "budget_currency": "USD",
            "budget_amount": 250000,
            "submission_deadline": deadline,
            "delivery_country": "KZ",
            "delivery_location": "Astana, KZ",
            "required_licenses": [],  # server should auto-attach
        }
        r = s.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        assert "Medical gas installation" in (t.get("required_licenses") or []), t
        CTX["kz_tender_id"] = t["id"]

    def test_vendor_without_licenses_gets_403(self):
        # new_vendor_session vendor is approved but has empty kz_licenses (profile above set none)
        s = CTX["new_vendor_session"]
        r = s.post(f"{API}/bids", json={
            "tender_id": CTX["kz_tender_id"],
            "price_currency": "USD",
            "price_amount": 200000,
            "delivery_days": 90,
            "proposal": "We will do medical gas.",
        }, timeout=15)
        assert r.status_code == 403, r.text
        assert "missing required licenses" in r.text.lower()

    def test_vendor_with_licenses_can_bid(self):
        # Grant the license via direct DB write
        _set_kz_licenses(CTX["new_vendor_id"], ["Medical gas installation"])
        s = CTX["new_vendor_session"]
        r = s.post(f"{API}/bids", json={
            "tender_id": CTX["kz_tender_id"],
            "price_currency": "USD",
            "price_amount": 210000,
            "delivery_days": 88,
            "proposal": "Fully licensed medgas contractor.",
        }, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["status"] == "submitted"
        CTX["kz_bid_id"] = b["id"]


# ---------- CSV export ----------
class TestCSVExport:
    def test_owner_buyer_can_export(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders/{CTX['kz_tender_id']}/bids/export", timeout=15)
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "")
        text = r.text
        # Verify header row columns
        header = text.splitlines()[0]
        for col in ["Tender ID", "Tender Title", "Vendor Company", "Vendor Email",
                    "Currency", "Price", "Delivery Days", "Status", "Submitted At", "Proposal"]:
            assert col in header, f"missing column {col} in {header}"
        # Verify at least one data row (our KZ bid)
        assert len(text.splitlines()) >= 2

    def test_non_owner_buyer_gets_403(self):
        uniq = uuid.uuid4().hex[:8]
        creds = {"email": f"TEST_csv_buyer_{uniq}@example.com", "password": "Buyer@123",
                 "name": "csvbuyer", "role": "buyer"}
        s = _session()
        assert s.post(f"{API}/auth/register", json=creds, timeout=15).status_code == 200
        r = s.get(f"{API}/tenders/{CTX['kz_tender_id']}/bids/export", timeout=15)
        assert r.status_code == 403

    def test_admin_can_export(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/tenders/{CTX['kz_tender_id']}/bids/export", timeout=15)
        assert r.status_code == 200


# ---------- Google OAuth callback ----------
class TestGoogleCallback:
    def test_invalid_session_id_returns_401(self):
        r = requests.post(f"{API}/auth/google-callback",
                          json={"session_id": "invalid_session_totally_fake"}, timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


# ---------- Admin stats — fees_collected ----------
class TestAdminStatsFeesCollected:
    def test_admin_stats_has_fees_collected(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/admin/stats", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "fees_collected" in d
        assert isinstance(d["fees_collected"], int)


# =========================================================================
# ITERATION 3 (v1.2) — RFP / RFQ module tests
# =========================================================================


class TestRfpRfqBackend:
    """Verify document_type support on POST/GET /tenders and dynamic bid fields."""

    def test_create_rfp_returns_persisted_fields(self):
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        payload = {
            "document_type": "rfp",
            "title": f"TEST_RFP_{uuid.uuid4().hex[:6]}",
            "description": "Consulting services for hospital IT master plan.",
            "category": "Consulting",
            "submission_deadline": deadline,
            "budget_currency": "USD",
            "budget_amount": 150000,
            "delivery_location": "Astana",
            "scope_of_work": "Design and roadmap for hospital IT.",
            "expected_deliverables": "Final report + roadmap.",
            "evaluation_criteria": [
                {"name": "Technical", "weight": 60, "description": "Methodology"},
                {"name": "Commercial", "weight": 40, "description": "Price"},
            ],
            "evaluation_committee": [
                {"name": "Alia", "role": "CTO"},
                {"name": "Ivan", "role": "CFO"},
            ],
            "pre_bid_meeting_date": deadline,
            "bid_bond_amount": 5000,
        }
        r = s.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["document_type"] == "rfp"
        assert t["scope_of_work"] == "Design and roadmap for hospital IT."
        assert len(t["evaluation_criteria"]) == 2
        assert t["evaluation_criteria"][0]["weight"] == 60
        assert len(t["evaluation_committee"]) == 2
        CTX["rfp_tender_id"] = t["id"]

        # GET by id returns all fields
        r2 = s.get(f"{API}/tenders/{t['id']}", timeout=10)
        assert r2.status_code == 200
        got = r2.json()
        assert got["document_type"] == "rfp"
        assert got["scope_of_work"] == payload["scope_of_work"]
        assert len(got["evaluation_criteria"]) == 2

    def test_create_rfq_returns_persisted_fields(self):
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        payload = {
            "document_type": "rfq",
            "title": f"TEST_RFQ_{uuid.uuid4().hex[:6]}",
            "description": "Quotation for cabling supplies.",
            "category": "Supplies",
            "submission_deadline": deadline,
            "budget_currency": "USD",
            "budget_amount": 20000,
            "delivery_location": "Astana",
            "delivery_country": "KZ",
            "line_items": [
                {"item": "CAT6 cable", "qty": 500, "unit": "m", "target_unit_price": 2.5},
                {"item": "RJ45 connector", "qty": 200, "unit": "pcs", "target_unit_price": 0.4},
            ],
            "payment_terms": "30 days net",
            "delivery_date": "2026-06-01",
        }
        r = s.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["document_type"] == "rfq"
        assert len(t["line_items"]) == 2
        assert t["line_items"][0]["item"] == "CAT6 cable"
        assert t["payment_terms"] == "30 days net"
        assert t["delivery_date"] == "2026-06-01"
        CTX["rfq_tender_id"] = t["id"]

    def test_create_rfq_kz_auto_attaches_no_licenses_for_generic_category(self):
        # For "Supplies" category we do not expect KZ auto-attach — required_licenses stays empty
        s = CTX["buyer_session"]
        t = s.get(f"{API}/tenders/{CTX['rfq_tender_id']}", timeout=10).json()
        assert t.get("required_licenses") in (None, [], [""])

    def test_filter_tenders_by_document_type_rfp(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders?document_type=rfp", timeout=10)
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 1
        assert all(d.get("document_type") == "rfp" for d in docs)
        assert CTX["rfp_tender_id"] in [d["id"] for d in docs]

    def test_filter_tenders_by_document_type_rfq(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders?document_type=rfq", timeout=10)
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 1
        assert all(d.get("document_type") == "rfq" for d in docs)
        assert CTX["rfq_tender_id"] in [d["id"] for d in docs]

    def test_list_all_tenders_backcompat(self):
        # No filter — should include our RFP, RFQ, and legacy tenders
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders", timeout=10)
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()]
        assert CTX["rfp_tender_id"] in ids
        assert CTX["rfq_tender_id"] in ids

    def test_get_legacy_tender_still_works(self):
        # tender_id was created without document_type in TestTenders — must still return
        s = CTX["buyer_session"]
        r = s.get(f"{API}/tenders/{CTX['tender_id']}", timeout=10)
        assert r.status_code == 200
        got = r.json()
        # Either missing (legacy) or defaulted to "tender"
        assert got.get("document_type", "tender") in ("tender", None)

    def test_bid_on_rfq_with_line_item_prices(self):
        # approved vendor already granted "Medical gas installation" earlier — RFQ needs no licenses
        s = CTX["new_vendor_session"]
        payload = {
            "tender_id": CTX["rfq_tender_id"],
            "price_currency": "USD",
            "price_amount": 1330.0,  # 500*2.5 + 200*0.4 = 1330
            "delivery_days": 30,
            "proposal": "Full RFQ quotation.",
            "line_item_prices": [
                {"item": "CAT6 cable", "qty": 500, "unit": "m", "unit_price": 2.4, "subtotal": 1200.0},
                {"item": "RJ45 connector", "qty": 200, "unit": "pcs", "unit_price": 0.65, "subtotal": 130.0},
            ],
        }
        r = s.post(f"{API}/bids", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["status"] == "submitted"
        assert len(b.get("line_item_prices", [])) == 2
        assert b["line_item_prices"][0]["unit_price"] == 2.4
        CTX["rfq_bid_id"] = b["id"]

    def test_bid_on_rfp_with_technical_commercial_team(self):
        s = CTX["new_vendor_session"]
        payload = {
            "tender_id": CTX["rfp_tender_id"],
            "price_currency": "USD",
            "price_amount": 140000,
            "delivery_days": 90,
            "proposal": "Overall proposal summary.",
            "technical_proposal": "Deep technical write-up: phased delivery, team, methodology.",
            "commercial_proposal": "Payment 30/40/30. Total 140k USD.",
            "team_composition": "PM + 2 architects + 4 engineers.",
        }
        r = s.post(f"{API}/bids", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["status"] == "submitted"
        assert b.get("technical_proposal", "").startswith("Deep technical write-up")
        assert b.get("commercial_proposal", "").startswith("Payment 30/40/30")
        assert "PM" in b.get("team_composition", "")

    def test_kz_license_gate_still_enforced_on_rfp(self):
        """Create an RFP with delivery_country=KZ + required_licenses.
        A vendor without matching kz_licenses must get 403."""
        # 1) buyer creates KZ RFP requiring 'Electrical installation'
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        rfp_payload = {
            "document_type": "rfp",
            "title": f"TEST_KZ_RFP_{uuid.uuid4().hex[:6]}",
            "description": "Electrical works consulting.",
            "category": "Substation works (HT/LT)",  # maps to Electrical installation
            "submission_deadline": deadline,
            "budget_currency": "USD",
            "budget_amount": 90000,
            "delivery_country": "KZ",
            "delivery_location": "Astana",
            "scope_of_work": "HT/LT substation design",
            "evaluation_criteria": [
                {"name": "Technical", "weight": 70, "description": "Design"},
                {"name": "Commercial", "weight": 30, "description": "Price"},
            ],
        }
        r = s.post(f"{API}/tenders", json=rfp_payload, timeout=15)
        assert r.status_code == 200, r.text
        rfp = r.json()
        assert "Electrical installation" in (rfp.get("required_licenses") or [])
        kz_rfp_id = rfp["id"]

        # 2) Register a fresh approved vendor that does NOT have Electrical installation
        uniq = uuid.uuid4().hex[:8]
        creds = {"email": f"TEST_norfp_{uniq}@example.com", "password": "Vendor@123",
                 "name": "No License", "role": "vendor"}
        vs = _session()
        rr = vs.post(f"{API}/auth/register", json=creds, timeout=15)
        assert rr.status_code == 200
        new_vid = rr.json()["id"]
        # Mark fee-paid so admin can approve after profile submit; but faster to directly approve
        admin_s = CTX["admin_session"]
        admin_s.post(f"{API}/admin/vendors/{new_vid}/approve", timeout=10)

        r2 = vs.post(f"{API}/bids", json={
            "tender_id": kz_rfp_id,
            "price_currency": "USD",
            "price_amount": 80000,
            "delivery_days": 60,
            "proposal": "We'll do it.",
            "technical_proposal": "Yes",
        }, timeout=15)
        assert r2.status_code == 403
        assert "missing required licenses" in r2.text.lower()


# =========================================================================
# ITERATION 4 (v1.3) — RFP scoring & evaluation-weight server-side validation
# =========================================================================


class TestV13RfpScoring:
    """RFP bid scoring: POST /api/bids/{id}/score + weight validation."""

    def _register_and_approve_vendor(self, tag: str):
        """Helper: register a vendor, approve them, mark fee-paid."""
        uniq = uuid.uuid4().hex[:6]
        creds = {"email": f"TEST_v13_{tag}_{uniq}@example.com", "password": "Vendor@123",
                 "name": f"V13 {tag}", "role": "vendor"}
        vs = _session()
        r = vs.post(f"{API}/auth/register", json=creds, timeout=15)
        assert r.status_code == 200, r.text
        vid = r.json()["id"]
        # approve via admin
        admin = CTX["admin_session"]
        admin.post(f"{API}/admin/vendors/{vid}/approve", timeout=10)
        _mark_fee_paid(vid)
        # relogin so session cookie reflects role/approval
        vs2 = _session()
        _login(vs2, creds)
        return vs2, vid, creds

    def test_a_create_rfp_with_valid_weights(self):
        """Create an RFP with Technical=60 / Commercial=40 (sums to 100)."""
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        payload = {
            "document_type": "rfp",
            "title": f"TEST_V13_RFPScore_{uuid.uuid4().hex[:6]}",
            "description": "RFP for scoring test",
            "category": "Consulting & Advisory",
            "submission_deadline": deadline,
            "budget_currency": "USD",
            "budget_amount": 200000,
            "delivery_location": "Astana",
            "scope_of_work": "Master plan",
            "evaluation_criteria": [
                {"name": "Technical", "weight": 60, "description": "Methodology"},
                {"name": "Commercial", "weight": 40, "description": "Price"},
            ],
        }
        r = s.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        CTX["v13_rfp_id"] = r.json()["id"]

    def test_b_create_rfp_bad_weight_sum_returns_400(self):
        """Weights not summing to 100 must be rejected server-side."""
        s = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        payload = {
            "document_type": "rfp",
            "title": f"TEST_V13_BadWeight_{uuid.uuid4().hex[:6]}",
            "description": "should fail",
            "category": "Consulting & Advisory",
            "submission_deadline": deadline,
            "budget_currency": "USD",
            "evaluation_criteria": [
                {"name": "Technical", "weight": 70, "description": "x"},
                {"name": "Commercial", "weight": 40, "description": "y"},  # sums to 110
            ],
        }
        r = s.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        assert "weight" in r.text.lower()

    def test_c_submit_two_rfp_bids(self):
        """Two vendors submit RFP bids so we can score them."""
        vs1, vid1, _ = self._register_and_approve_vendor("v1")
        vs2, vid2, _ = self._register_and_approve_vendor("v2")
        CTX["v13_vs1"] = vs1
        CTX["v13_vs2"] = vs2
        CTX["v13_vid1"] = vid1
        CTX["v13_vid2"] = vid2

        rfp_id = CTX["v13_rfp_id"]
        # Vendor 1
        r1 = vs1.post(f"{API}/bids", json={
            "tender_id": rfp_id, "price_currency": "USD", "price_amount": 180000, "delivery_days": 90,
            "proposal": "V1 proposal",
            "technical_proposal": "V1 tech", "commercial_proposal": "V1 comm", "team_composition": "PM+3",
        }, timeout=15)
        assert r1.status_code == 200, r1.text
        CTX["v13_bid1"] = r1.json()["id"]
        # Vendor 2
        r2 = vs2.post(f"{API}/bids", json={
            "tender_id": rfp_id, "price_currency": "USD", "price_amount": 170000, "delivery_days": 100,
            "proposal": "V2 proposal",
            "technical_proposal": "V2 tech", "commercial_proposal": "V2 comm", "team_composition": "PM+2",
        }, timeout=15)
        assert r2.status_code == 200, r2.text
        CTX["v13_bid2"] = r2.json()["id"]

    def test_d_score_bid_as_buyer_returns_weighted_total(self):
        """Buyer scores bid1 with Technical=80, Commercial=70 → 60*.8 + 40*.7 = 76.0"""
        s = CTX["buyer_session"]
        r = s.post(f"{API}/bids/{CTX['v13_bid1']}/score",
                   json={"scores": {"Technical": 80, "Commercial": 70}, "notes": "Solid team"},
                   timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert abs(data["weighted_total"] - 76.0) < 0.01, f"expected 76.0 got {data['weighted_total']}"

    def test_e_scored_bid_persists_fields_on_get_bids(self):
        """GET /api/bids?tender_id=... now includes rfp_scores + rfp_weighted_total for scored bid."""
        s = CTX["buyer_session"]
        r = s.get(f"{API}/bids?tender_id={CTX['v13_rfp_id']}", timeout=10)
        assert r.status_code == 200, r.text
        bids = r.json()
        scored = [b for b in bids if b["id"] == CTX["v13_bid1"]]
        assert len(scored) == 1
        b = scored[0]
        assert "rfp_scores" in b and b["rfp_scores"]["Technical"] == 80
        assert "rfp_weighted_total" in b
        assert abs(b["rfp_weighted_total"] - 76.0) < 0.01

    def test_f_score_non_rfp_returns_400(self):
        """Scoring a plain-tender/RFQ bid returns 400."""
        s = CTX["buyer_session"]
        # Use rfq_bid_id from earlier tests (RFQ) — it's a bid on an RFQ tender
        rfq_bid = CTX.get("rfq_bid_id")
        assert rfq_bid, "prerequisite RFQ bid must exist"
        r = s.post(f"{API}/bids/{rfq_bid}/score", json={"scores": {"x": 50}}, timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"
        assert "rfp" in r.text.lower()

    def test_g_score_forbidden_for_non_owner_buyer(self):
        """Buyer who doesn't own the RFP tender gets 403."""
        uniq = uuid.uuid4().hex[:6]
        creds = {"email": f"TEST_v13_otherbuyer_{uniq}@example.com", "password": "Buyer@123",
                 "name": "Other Buyer", "role": "buyer"}
        s = _session()
        assert s.post(f"{API}/auth/register", json=creds, timeout=15).status_code == 200
        r = s.post(f"{API}/bids/{CTX['v13_bid1']}/score",
                   json={"scores": {"Technical": 50, "Commercial": 60}}, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"

    def test_h_admin_can_score_any_rfp_bid(self):
        """Admin can score even when they don't own the tender."""
        s = CTX["admin_session"]
        r = s.post(f"{API}/bids/{CTX['v13_bid2']}/score",
                   json={"scores": {"Technical": 90, "Commercial": 60}},
                   timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # 60*.9 + 40*.6 = 54 + 24 = 78
        assert abs(data["weighted_total"] - 78.0) < 0.01

    def test_i_score_not_found_bid_returns_404(self):
        s = CTX["admin_session"]
        fake_id = "652f0b3c1e5c2b6a1a000000"  # valid ObjectId shape, but no such bid
        r = s.post(f"{API}/bids/{fake_id}/score", json={"scores": {}}, timeout=10)
        assert r.status_code == 404

    def test_j_score_clamps_out_of_range(self):
        """Score above 100 is clamped to 100 in weighted total."""
        s = CTX["buyer_session"]
        # Score bid1 again with Technical=150 (clamped to 100), Commercial=0 → 60*1.0 + 40*0 = 60
        r = s.post(f"{API}/bids/{CTX['v13_bid1']}/score",
                   json={"scores": {"Technical": 150, "Commercial": 0}},
                   timeout=15)
        assert r.status_code == 200, r.text
        assert abs(r.json()["weighted_total"] - 60.0) < 0.01


# =========================================================================
# ITERATION 5 (v1.4) — Real-time tender feed
# =========================================================================


class TestV14TenderFeed:
    """GET /api/feed/tenders — auth-gated feed of open + awarded tenders."""

    def test_feed_requires_auth(self):
        r = requests.get(f"{API}/feed/tenders", timeout=10)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"

    def test_feed_returns_list_for_admin(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/feed/tenders", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        # We've created lots of tenders in prior tests
        assert len(data) >= 1
        # Field shape check for first item
        item = data[0]
        for k in ("id", "title", "description", "document_type", "category", "status",
                  "budget_currency", "budget_amount", "submission_deadline",
                  "delivery_country", "created_by_name", "created_at"):
            assert k in item, f"missing {k} in feed item: {item.keys()}"
        # description <= 220 chars
        assert len(item["description"] or "") <= 220
        # status must be open or awarded
        assert item["status"] in ("open", "awarded")
        # sorted by created_at desc — verify by pairwise compare (strings ISO sortable)
        for i in range(len(data) - 1):
            a = data[i].get("created_at") or ""
            b = data[i + 1].get("created_at") or ""
            assert a >= b, f"feed not sorted desc: {a} < {b}"

    def test_feed_returns_list_for_buyer(self):
        s = CTX["buyer_session"]
        r = s.get(f"{API}/feed/tenders", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_feed_returns_list_for_vendor(self):
        s = CTX["new_vendor_session"]
        r = s.get(f"{API}/feed/tenders", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_feed_limit_param_respected(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/feed/tenders?limit=5", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert len(data) <= 5

    def test_feed_limit_clamped_to_100(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/feed/tenders?limit=500", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert len(data) <= 100

    def test_feed_limit_min_clamped_to_1(self):
        s = CTX["admin_session"]
        r = s.get(f"{API}/feed/tenders?limit=0", timeout=10)
        assert r.status_code == 200
        data = r.json()
        # 0 must clamp to at least 1
        assert len(data) >= 1

    def test_feed_excludes_closed_tenders(self):
        """Any tender with status=closed must NOT appear in the feed."""
        s = CTX["admin_session"]
        r = s.get(f"{API}/feed/tenders?limit=100", timeout=10)
        assert r.status_code == 200
        statuses = {item["status"] for item in r.json()}
        assert statuses.issubset({"open", "awarded"}), f"unexpected statuses: {statuses}"

    def test_feed_reflects_new_tender_creation(self):
        """Create a tender and verify it appears at top of feed."""
        buyer = CTX["buyer_session"]
        deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        title = f"TEST_v14_FeedTop_{uuid.uuid4().hex[:6]}"
        r = buyer.post(f"{API}/tenders", json={
            "title": title,
            "description": "Feed liveness test tender." * 3,  # verify truncation works too
            "category": "Consulting & Advisory",
            "budget_currency": "USD",
            "budget_amount": 12345,
            "submission_deadline": deadline,
            "delivery_location": "Astana",
        }, timeout=15)
        assert r.status_code == 200
        new_id = r.json()["id"]

        # Now the admin fetches feed with limit=5 — the new tender should be within the first entries
        s = CTX["admin_session"]
        feed = s.get(f"{API}/feed/tenders?limit=5", timeout=10).json()
        top_ids = [it["id"] for it in feed]
        assert new_id in top_ids, f"new tender {new_id} not in top-5 feed ids: {top_ids}"

        # Verify description truncated to 220 chars max
        item = next(it for it in feed if it["id"] == new_id)
        assert len(item["description"]) <= 220
