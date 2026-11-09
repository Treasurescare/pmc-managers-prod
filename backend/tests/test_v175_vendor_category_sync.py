# v175 — Vendor category sync: admin full-profile edit -> top-level business_categories, UNSPSC picker requests, bid gate
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
from security import hash_password  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
SUF = uuid.uuid4().hex[:6].upper()
VREF = f"TEST-VCS-{SUF}"
VEMAIL = f"test_vcs_{SUF.lower()}@example.com"
VPASS = "Vendor@12345"
NREF = f"TEST-WIND-{SUF}"
CAT = "Wind generators"


@pytest.fixture(scope="module", autouse=True)
def seed():
    vid = mdb.vendors.insert_one({
        "vendor_ref": VREF, "email": VEMAIL, "company_name": "TEST_ Wind Co", "country": "KZ",
        "tenant_id": "PMC-KZ-01", "password_hash": hash_password(VPASS), "status": "active",
        "kyc_status": "verified", "is_active": True, "business_categories": ["Construction"],
        "profile": {"country": "KZ", "business_categories": ["Construction"]},
        "created_at": datetime.now(timezone.utc).isoformat()}).inserted_id
    mdb.notices.insert_one({
        "notice_ref": NREF, "title": "TEST_ Wind generator supply", "category": CAT, "tenant_id": "PMC-KZ-01",
        "delivery_country": "KZ", "currency": "USD", "budget_amount": 1000, "is_published": True,
        "document_type": "tender", "status": "published",
        "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()})
    yield vid
    mdb.vendors.delete_one({"_id": vid})
    mdb.notices.delete_one({"notice_ref": NREF})
    mdb.vendor_category_requests.delete_many({"vendor_ref": VREF})
    mdb.bids.delete_many({"notice_ref": NREF})
    mdb.messages.delete_many({"to_vendor_ref": VREF})
    mdb.notifications.delete_many({"user_ref": VREF})


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token") or ""
    return s


@pytest.fixture(scope="module")
def vendor():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": VEMAIL, "password": VPASS})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token") or ""
    return s


def _bid(vendor):
    # price 0 -> passes category gate then fails price validation (no bid row is created)
    return vendor.post(f"{API}/bids", json={"notice_ref": NREF, "price_amount": 0, "currency": "USD", "documents": []})


def _is_cat_block(r):
    return r.status_code == 403 and "category_not_registered" in r.text


class TestCategorySync:
    def test_before_admin_edit_bid_blocked(self, vendor):
        r = _bid(vendor)
        assert _is_cat_block(r), f"{r.status_code} {r.text[:300]}"
        ci = vendor.post(f"{API}/notices/{NREF}/category-interest")
        assert ci.status_code == 200 and ci.json()["registered"] is False

    def test_admin_full_edit_syncs_dict_category(self, admin, vendor):
        r = admin.patch(f"{API}/vendors/admin/{VREF}/full", json={
            "company_name": "TEST_ Wind Co", "profile": {"business_categories": [
                "Construction", {"code": "26111603", "title": CAT}]}})
        assert r.status_code == 200, r.text
        d = mdb.vendors.find_one({"vendor_ref": VREF})
        assert d["business_categories"] == ["Construction", CAT]
        mine = vendor.get(f"{API}/vendor/categories/mine").json()
        assert CAT in mine["approved"]

    def test_after_admin_edit_bid_passes_gate(self, vendor):
        r = _bid(vendor)
        assert not _is_cat_block(r), r.text[:300]
        assert r.status_code in (400, 422), f"{r.status_code} {r.text[:300]}"
        ci = vendor.post(f"{API}/notices/{NREF}/category-interest")
        assert ci.status_code == 200 and ci.json()["registered"] is True

    def test_vendor_me_has_categories(self, vendor):
        r = vendor.get(f"{API}/vendor/auth/me")
        assert r.status_code == 200
        assert CAT in (r.json().get("business_categories") or [])

    def test_request_already_approved_409(self, vendor):
        r = vendor.post(f"{API}/vendor/categories/request", json={"category_code": "26111603", "category_name": "wind GENERATORS"})
        assert r.status_code == 409


class TestUnspscRequestFlow:
    def test_reset_categories(self, admin):
        mdb.vendors.update_one({"vendor_ref": VREF}, {"$set": {"business_categories": ["Construction"],
                                                               "profile.business_categories": ["Construction"]}})

    def test_unspsc_search_public(self):
        r = requests.get(f"{API}/masters/unspsc/public/search", params={"q": "wind generators", "limit": 30})
        assert r.status_code == 200
        assert any(x["code"] == "26111603" and x["title_en"] == CAT for x in r.json())

    def test_request_unspsc_and_dup(self, vendor):
        r = vendor.post(f"{API}/vendor/categories/request", json={"category_code": "26111603", "category_name": CAT})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending" and r.json()["category_code"] == "26111603"
        mine = vendor.get(f"{API}/vendor/categories/mine").json()
        assert any(p["category_code"] == "26111603" for p in mine["pending"])
        dup = vendor.post(f"{API}/vendor/categories/request", json={"category_code": "26111603", "category_name": CAT})
        assert dup.status_code == 409

    def test_unknown_code_rejected(self, vendor):
        r = vendor.post(f"{API}/vendor/categories/request", json={"category_code": "99999999", "category_name": "TEST_ Bogus"})
        assert r.status_code == 400
        # code exists but title mismatch -> rejected too
        r = vendor.post(f"{API}/vendor/categories/request", json={"category_code": "26111604", "category_name": "TEST_ Wrong title"})
        assert r.status_code == 400

    def test_admin_removal_in_section_d_not_synced(self, admin):
        """Admin removes a category from Section D -> top-level list still keeps it (union merge). Informational."""
        mdb.vendors.update_one({"vendor_ref": VREF}, {"$set": {"business_categories": ["Construction", "TEST_Old"]}})
        r = admin.patch(f"{API}/vendors/admin/{VREF}/full", json={"profile": {"business_categories": ["Construction"]}})
        assert r.status_code == 200
        top = mdb.vendors.find_one({"vendor_ref": VREF})["business_categories"]
        mdb.vendors.update_one({"vendor_ref": VREF}, {"$set": {"business_categories": ["Construction"]}})
        print("top-level after removal:", top)
        assert "TEST_Old" not in top, f"removed category still bid-eligible: {top}"

    def test_master_category_still_requestable(self, vendor):
        c = mdb.categories.find_one({"is_active": True, "name": {"$nin": ["Construction", CAT]}})
        r = vendor.post(f"{API}/vendor/categories/request", json={"category_code": c["code"], "category_name": c["name"]})
        assert r.status_code == 200, r.text
        mdb.vendor_category_requests.delete_one({"vendor_ref": VREF, "category_code": c["code"]})

    def test_admin_approve_then_bid(self, admin, vendor):
        req = mdb.vendor_category_requests.find_one({"vendor_ref": VREF, "category_code": "26111603", "status": "pending"})
        assert req
        if req.get("payment_status") == "unpaid":
            mdb.vendor_category_requests.update_one({"_id": req["_id"]}, {"$set": {"payment_status": "paid"}})
        r = admin.post(f"{API}/vendors/category-requests/{req['_id']}/approve", json={"notes": "TEST_"})
        assert r.status_code == 200, r.text
        assert CAT in vendor.get(f"{API}/vendor/categories/mine").json()["approved"]
        b = _bid(vendor)
        assert not _is_cat_block(b), b.text[:300]


class TestTestvendorAdminEdit:
    def test_testvendor_full_edit_reachable(self, admin):
        """testvendor (seeded in preview) — admin full-edit must find it (tenant scoping)."""
        v = mdb.vendors.find_one({"email": "testvendor@pmcmanagers.com"}, {"vendor_ref": 1, "tenant_id": 1})
        if not v:
            pytest.skip("no testvendor")
        r = admin.patch(f"{API}/vendors/admin/{v['vendor_ref']}/full", json={})
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]} tenant_id={v.get('tenant_id')}"
