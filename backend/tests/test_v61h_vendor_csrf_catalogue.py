# v61h — vendor session-bound CSRF (no csrf cookie), /staff/auth/csrf vendor refresh, admin/staff regression,
# catalogue import progress fields.
import os
import time
import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
VENDOR = {"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"}
ADMIN = {"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"}
STAFF = {"email": "legal@pmcmanagers.com", "password": "Legal@123", "active_role": "legal_counsel"}

_mongo = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED = {"listings": [], "categories": [], "imports": []}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for lid in CREATED["listings"]:
        _mongo.mkt_listings.delete_one({"_id": ObjectId(lid)})
    for cid in CREATED["categories"]:
        _mongo.categories.delete_one({"_id": ObjectId(cid), "source": "supplier"})
    for iid in CREATED["imports"]:
        _mongo.mkt_media.delete_many({"import_id": iid})
        _mongo.mkt_imports.delete_one({"_id": iid})


@pytest.fixture(scope="module")
def vendor_login():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json=VENDOR)
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code} {r.text[:200]}")
    data = r.json()
    vt = s.cookies.get("vendor_token")
    assert vt, "vendor_token cookie not set"
    assert data.get("csrf_token"), "login response lacks csrf_token"
    return {"vt": vt, "csrf": data["csrf_token"], "cookie_csrf": s.cookies.get("csrf_token")}


def _vendor_only(vt, csrf=None):
    h = {"Cookie": f"vendor_token={vt}", "Content-Type": "application/json"}
    if csrf is not None:
        h["X-CSRF-Token"] = csrf
    return h


# --- vendor CSRF without csrf cookie ---
class TestVendorCsrfNoCookie:
    def test_login_csrf_matches_cookie(self, vendor_login):
        assert vendor_login["cookie_csrf"] == vendor_login["csrf"]
        assert len(vendor_login["csrf"]) == 64  # HMAC-SHA256 hex

    def test_category_post_only_vendor_cookie(self, vendor_login):
        r = requests.post(f"{BASE_URL}/api/v1/market/categories",
                          headers=_vendor_only(vendor_login["vt"], vendor_login["csrf"]),
                          json={"name": f"TEST_cat_{int(time.time())}"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["created"] is True and d["name"].startswith("TEST_cat_")
        CREATED["categories"].append(d["id"])

    def test_listing_post_only_vendor_cookie_and_persist(self, vendor_login):
        r = requests.post(f"{BASE_URL}/api/v1/market/listings",
                          headers=_vendor_only(vendor_login["vt"], vendor_login["csrf"]),
                          json={"title": "TEST_csrf listing", "sale_modes": ["fixed"], "buy_now_price": 10})
        assert r.status_code == 200, r.text
        lid = r.json()["id"]
        CREATED["listings"].append(lid)
        assert r.json()["status"] == "draft"
        g = requests.get(f"{BASE_URL}/api/v1/market/mine", headers=_vendor_only(vendor_login["vt"]))
        assert g.status_code == 200
        assert lid in str(g.json())

    def test_wrong_header_403(self, vendor_login):
        r = requests.post(f"{BASE_URL}/api/v1/market/categories",
                          headers=_vendor_only(vendor_login["vt"], "0" * 64), json={"name": "TEST_cat_bad"})
        assert r.status_code == 403
        assert "csrf" in r.json()["detail"].lower()

    def test_missing_header_403(self, vendor_login):
        r = requests.post(f"{BASE_URL}/api/v1/market/categories",
                          headers=_vendor_only(vendor_login["vt"]), json={"name": "TEST_cat_bad"})
        assert r.status_code == 403

    def test_admin_session_token_not_valid_for_vendor(self, vendor_login):
        a = requests.post(f"{BASE_URL}/api/v1/admin/auth/login", json=ADMIN)
        assert a.status_code == 200
        r = requests.post(f"{BASE_URL}/api/v1/market/categories",
                          headers=_vendor_only(vendor_login["vt"], a.json()["csrf_token"]), json={"name": "TEST_cat_bad"})
        assert r.status_code == 403


# --- /staff/auth/csrf refresh ---
class TestCsrfRefresh:
    def test_refresh_with_vendor_cookie(self, vendor_login):
        r = requests.get(f"{BASE_URL}/api/v1/staff/auth/csrf", headers=_vendor_only(vendor_login["vt"]))
        assert r.status_code == 200, r.text
        assert r.json()["csrf_token"] == vendor_login["csrf"]
        assert "csrf_token=" in r.headers.get("set-cookie", "")

    def test_refresh_no_session_401(self):
        r = requests.get(f"{BASE_URL}/api/v1/staff/auth/csrf")
        assert r.status_code == 401

    def test_refresh_invalid_vendor_cookie_401(self):
        r = requests.get(f"{BASE_URL}/api/v1/staff/auth/csrf", headers={"Cookie": "vendor_token=garbage"})
        assert r.status_code == 401

    def test_refresh_admin_path(self):
        s = requests.Session()
        a = s.post(f"{BASE_URL}/api/v1/admin/auth/login", json=ADMIN)
        assert a.status_code == 200
        r = s.get(f"{BASE_URL}/api/v1/staff/auth/csrf")
        assert r.status_code == 200
        assert r.json()["csrf_token"] == a.json()["csrf_token"]


# --- regression: admin + staff ---
class TestRegression:
    def test_admin_post_no_csrf_cookie(self):
        s = requests.Session()
        a = s.post(f"{BASE_URL}/api/v1/admin/auth/login", json=ADMIN)
        assert a.status_code == 200
        at = s.cookies.get("access_token")
        h = {"Cookie": f"access_token={at}", "X-CSRF-Token": a.json()["csrf_token"]}
        r = requests.post(f"{BASE_URL}/api/v1/market/admin/listings/{'0'*24}/decision", headers=h, json={"action": "approve"})
        assert r.status_code == 409, r.text  # passed auth + CSRF, then business 409
        r2 = requests.post(f"{BASE_URL}/api/v1/market/admin/listings/{'0'*24}/decision",
                           headers={"Cookie": f"access_token={at}"}, json={"action": "approve"})
        assert r2.status_code == 403

    def test_admin_listings_get(self):
        s = requests.Session()
        assert s.post(f"{BASE_URL}/api/v1/admin/auth/login", json=ADMIN).status_code == 200
        r = s.get(f"{BASE_URL}/api/v1/market/admin/listings?status=all")
        assert r.status_code == 200 and "items" in r.json()

    def test_staff_login_and_refresh(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/staff/auth/login", json=STAFF)
        if r.status_code != 200:
            pytest.skip(f"staff login {r.status_code}: {r.text[:150]}")
        c = s.get(f"{BASE_URL}/api/v1/staff/auth/csrf")
        assert c.status_code == 200 and c.json()["csrf_token"]
        lo = s.post(f"{BASE_URL}/api/v1/staff/auth/logout", headers={"X-CSRF-Token": c.json()["csrf_token"]})
        assert lo.status_code in (200, 204), lo.text

    def test_vendor_logout_login(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json=VENDOR)
        assert r.status_code == 200
        assert s.get(f"{BASE_URL}/api/v1/vendor/auth/me").status_code == 200
        lo = s.post(f"{BASE_URL}/api/v1/vendor/auth/logout", headers={"X-CSRF-Token": r.json()["csrf_token"]})
        assert lo.status_code in (200, 204), lo.text
        assert s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json=VENDOR).status_code == 200


# --- catalogue import progress (real Gemini) ---
class TestCatalogueImport:
    def test_import_progress_fields(self, vendor_login):
        import fitz
        doc = fitz.open()
        for i in range(32):
            pg = doc.new_page()
            pg.insert_text((72, 100), f"TEST_ Product {i+1}: Steel Bolt M{i+6}", fontsize=20)
            pg.insert_text((72, 140), f"High tensile bolt, grade 8.8, length {20+i} mm. Unit: piece", fontsize=12)
        body = doc.tobytes()
        h = {"Cookie": f"vendor_token={vendor_login['vt']}", "X-CSRF-Token": vendor_login["csrf"]}
        r = requests.post(f"{BASE_URL}/api/v1/market/catalogue/import", headers=h,
                          files={"file": (f"TEST_cat_{int(time.time())}.pdf", body, "application/pdf")})
        if r.status_code == 402:
            pytest.skip(f"payment required: {r.text[:200]}")
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        CREATED["imports"].append(iid)
        seen_progress, d = [], {}
        for _ in range(60):
            time.sleep(4)
            d = requests.get(f"{BASE_URL}/api/v1/market/catalogue/import/{iid}", headers=h).json()
            seen_progress.append((d.get("pages_done"), d.get("found")))
            if d.get("status") != "reading":
                break
        print("progress", seen_progress)
        assert d["status"] == "done", d
        assert d["pages_total"] == 32 and d["pages_done"] == 32 and d["pages"] == 32
        assert any(p[0] in (15, 30) for p in seen_progress), seen_progress
        assert len(d["products"]) >= 1
        assert max(p["page"] for p in d["products"]) > 15, "pages after the first chunk not read"
