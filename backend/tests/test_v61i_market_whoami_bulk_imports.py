# v61i — market whoami, admin bulk approve/reject, earlier catalogue imports list (owner-only)
# Requires: python tests/mkt_t180_seed.py create (TEST_ buyer org + vendor #2); clean afterwards.
import os
import uuid
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1/market"
_mongo = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
VID = "6ae1f245f1bb6cf576407a2a"
CREATED = {"listings": [], "imports": []}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for lid in CREATED["listings"]:
        _mongo.mkt_listings.delete_one({"_id": ObjectId(lid)})
    for iid in CREATED["imports"]:
        _mongo.mkt_imports.delete_one({"_id": iid})


def vlogin(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.text[:200]}")
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def alogin(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.text[:200]}")
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


@pytest.fixture(scope="module")
def v1():
    return vlogin("testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def v2():
    return vlogin("test_mkt_v2_t180@example.com", "Vendor@12345")


@pytest.fixture(scope="module")
def adm():
    return alogin("adminsupport@pmcmanagers.com", "Admin@12345")


@pytest.fixture(scope="module")
def buyer():
    return alogin("test_mkt_buyer_t180@example.com", "Buyer@12345")


def pending(v, title):
    r = v.post(f"{API}/listings", json={"title": title, "sale_modes": ["fixed"], "buy_now_price": 10, "category": "TEST_cat"})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    CREATED["listings"].append(lid)
    r = v.post(f"{API}/listings/{lid}/submit")
    assert r.status_code == 200, r.text
    return lid


# --- whoami ---
class TestWhoami:
    def test_anon(self):
        r = requests.get(f"{API}/whoami", allow_redirects=False)
        assert r.status_code == 200 and r.json() == {"kind": None}

    def test_vendor(self, v1):
        d = v1.get(f"{API}/whoami").json()
        assert d["kind"] == "supplier" and d["verified"] is True and d["name"]

    def test_admin(self, adm):
        assert adm.get(f"{API}/whoami").json()["kind"] == "staff"

    def test_buyer(self, buyer):
        d = buyer.get(f"{API}/whoami").json()
        assert d == {"kind": "buyer", "name": "TEST_MKT Buyer Org", "verified": True}

    def test_garbage_cookie(self):
        r = requests.get(f"{API}/whoami", cookies={"access_token": "x", "vendor_token": "y"}, allow_redirects=False)
        assert r.status_code == 200 and r.json()["kind"] is None


# --- bulk decision ---
class TestBulk:
    def test_auth(self, v1):
        body = {"ids": ["000000000000000000000000"], "action": "approve"}
        assert requests.post(f"{API}/admin/listings/bulk-decision", json=body).status_code in (401, 403)
        assert v1.post(f"{API}/admin/listings/bulk-decision", json=body).status_code in (401, 403)

    def test_validation(self, adm):
        assert adm.post(f"{API}/admin/listings/bulk-decision", json={"ids": [], "action": "approve"}).status_code == 422
        assert adm.post(f"{API}/admin/listings/bulk-decision", json={"ids": ["a"], "action": "nope"}).status_code == 422

    def test_approve_and_skip(self, v1, adm):
        a, b = pending(v1, "TEST_bulk_a"), pending(v1, "TEST_bulk_b")
        r = adm.post(f"{API}/admin/listings/bulk-decision",
                     json={"ids": [a, b, "bad", "000000000000000000000000"], "action": "approve", "waive_sale_fee": True, "notes": "TEST ok"})
        assert r.status_code == 200, r.text
        assert r.json()["decided"] == 2 and r.json()["skipped"] == 2
        for lid in (a, b):
            d = _mongo.mkt_listings.find_one({"_id": ObjectId(lid)})
            assert d["status"] == "live" and d["sale_fee_waived"] is True and d["review_notes"] == "TEST ok"
        # already live -> skipped
        r = adm.post(f"{API}/admin/listings/bulk-decision", json={"ids": [a], "action": "reject"})
        assert r.json()["decided"] == 0 and r.json()["skipped"] == 1
        assert _mongo.mkt_listings.find_one({"_id": ObjectId(a)})["status"] == "live"

    def test_reject(self, v1, adm):
        a, b = pending(v1, "TEST_bulk_r1"), pending(v1, "TEST_bulk_r2")
        r = adm.post(f"{API}/admin/listings/bulk-decision", json={"ids": [a, b], "action": "reject", "notes": "TEST photos"})
        assert r.json()["decided"] == 2
        assert {_mongo.mkt_listings.find_one({"_id": ObjectId(x)})["status"] for x in (a, b)} == {"rejected"}

    def test_buyer_org_admin_cannot_bulk_decide(self, v1, buyer):
        # buyer-org user holds role 'admin' in its own tenant; must not decide platform listings
        a = pending(v1, "TEST_bulk_buyer")
        r = buyer.post(f"{API}/admin/listings/bulk-decision", json={"ids": [a], "action": "approve"})
        st = _mongo.mkt_listings.find_one({"_id": ObjectId(a)})["status"]
        assert r.status_code in (401, 403) and st == "pending", f"buyer org got {r.status_code} {r.text[:120]}; status={st}"


# --- earlier imports ---
class TestImports:
    def test_list_owner_only(self, v1, v2):
        iid = f"TEST_{uuid.uuid4().hex[:10]}"
        _mongo.mkt_imports.insert_one({"_id": iid, "owner": VID, "file_name": "TEST_cat.pdf", "status": "done", "pages": 2,
                                       "products": [{"title": "TEST_p1"}, {"title": "TEST_p2"}], "created_at": "2026-01-10T00:00:00+00:00"})
        fid = f"TEST_{uuid.uuid4().hex[:10]}"
        _mongo.mkt_imports.insert_one({"_id": fid, "owner": VID, "file_name": "TEST_failed.pdf", "status": "failed", "created_at": "2026-01-10T00:00:00+00:00"})
        CREATED["imports"] += [iid, fid]
        items = v1.get(f"{API}/catalogue/imports").json()["items"]
        row = next((x for x in items if x["id"] == iid), None)
        assert row and row["products"] == 2 and row["file_name"] == "TEST_cat.pdf" and row["pages"] == 2
        assert all(x["id"] != fid for x in items)
        assert all(x["id"] != iid for x in v2.get(f"{API}/catalogue/imports").json()["items"])
        assert v2.get(f"{API}/catalogue/import/{iid}").status_code == 404
        g = v1.get(f"{API}/catalogue/import/{iid}").json()
        assert g["status"] == "done" and len(g["products"]) == 2

    def test_anon_and_admin(self, adm):
        assert requests.get(f"{API}/catalogue/imports").status_code == 401
        assert adm.get(f"{API}/catalogue/imports").status_code in (401, 403)
