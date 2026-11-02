# v165 — UNSPSC search fix (word-boundary + synonyms), category UNSPSC suggestions/approve
import os
import time
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"


def _mongo():
    env = {}
    for line in open("/app/backend/.env"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v.strip('"')
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


def pub(q, limit=30):
    t = time.time()
    r = requests.get(f"{API}/masters/unspsc/public/search", params={"q": q, "limit": limit})
    return r, time.time() - t


# --- Public search: word boundary + synonyms
class TestPublicSearch:
    def test_wind(self):
        r, dt = pub("wind")
        assert r.status_code == 200
        titles = [d["title_en"] for d in r.json()]
        print("wind", dt, titles[:10])
        low = [t.lower() for t in titles]
        assert not any("winding" in t or "windows" in t or "windshield" in t for t in low[:10]), titles[:10]
        assert any("wind power plants" in t for t in low)
        assert any("wind generator" in t for t in low)
        assert any("onshore" in t for t in low) or any("offshore" in t for t in low)
        assert dt < 1.5

    def test_solar(self):
        r, dt = pub("solar")
        low = [d["title_en"].lower() for d in r.json()]
        print("solar", dt, low[:10])
        assert any("solar power plants" in t for t in low)
        assert any("photovoltaic module" in t for t in low)
        assert dt < 1.5

    def test_biomass(self):
        r, dt = pub("biomass")
        low = [d["title_en"].lower() for d in r.json()]
        print("biomass", dt, low[:10])
        assert any("biomass production" in t for t in low)
        assert any("biofuel" in t for t in low)

    @pytest.mark.parametrize("q", ["renewable", "renewable energy"])
    def test_renewable(self, q):
        r, dt = pub(q)
        low = [d["title_en"].lower() for d in r.json()]
        print(q, dt, low[:15])
        assert r.status_code == 200 and low
        for kw in ("solar", "wind", "hydro", "geothermal"):
            assert any(kw in t for t in low), f"{q} missing {kw}"
        assert dt < 1.5

    def test_hydro(self):
        r, dt = pub("hydro")
        low = [d["title_en"].lower() for d in r.json()]
        print("hydro", dt, low[:10])
        assert any("hydro power plants" in t for t in low)

    @pytest.mark.parametrize("q,kw", [("concrete", "concrete"), ("cement", "cement"), ("medical", "medical")])
    def test_generic(self, q, kw):
        r, dt = pub(q)
        rows = r.json()
        print(q, dt, [d["title_en"] for d in rows[:5]])
        assert len(rows) >= 5
        assert kw in rows[0]["title_en"].lower()
        assert all(d["level"] in ("commodity", "class") for d in rows)
        assert dt < 1.5

    def test_numeric_prefix(self):
        r, _ = pub("2610")
        rows = r.json()
        assert rows and all(d["code"].lstrip("0").startswith("2610") for d in rows)

    def test_levels_and_shape(self):
        r, _ = pub("solar")
        for d in r.json():
            assert set(d.keys()) == {"code", "title_en", "level"}
            assert d["level"] in ("commodity", "class")


# --- Admin search ranked
class TestAdminSearch:
    def test_admin_wind(self, admin):
        r = admin.get(f"{API}/masters/unspsc/search", params={"q": "wind", "limit": 20})
        assert r.status_code == 200
        low = [d["title_en"].lower() for d in r.json()]
        print("admin wind", low[:10])
        assert not any("winding" in t or "windows" in t for t in low[:10])
        assert any("wind" in t for t in low[:3])


# --- Category UNSPSC suggestions + approval
class TestCategorySuggestions:
    def test_suggestions_admin(self, admin):
        r = admin.get(f"{API}/masters/categories/unspsc-suggestions")
        assert r.status_code == 200
        data = r.json()
        print("count", len(data))
        for c in data:
            print(c["name"], [s["code"] + ":" + s["title"] for s in c["suggestions"]])
        assert len(data) == 18
        for c in data:
            assert "id" in c and "name" in c and len(c["suggestions"]) <= 3

    def test_suggestions_noauth(self):
        r = requests.get(f"{API}/masters/categories/unspsc-suggestions")
        assert r.status_code in (401, 403)

    def test_approve_noauth(self):
        r = requests.post(f"{API}/masters/categories/000000000000000000000000/approve-unspsc", json={"unspsc_code": "26101500"})
        assert r.status_code in (401, 403)

    def test_approve_unknown_code(self, admin):
        cid = admin.get(f"{API}/masters/categories/unspsc-suggestions").json()[0]["id"]
        r = admin.post(f"{API}/masters/categories/{cid}/approve-unspsc", json={"unspsc_code": "99999999"})
        assert r.status_code == 422

    def test_approve_invalid_id(self, admin):
        r = admin.post(f"{API}/masters/categories/not-an-id/approve-unspsc", json={"unspsc_code": "26101500"})
        print("invalid id", r.status_code)
        assert r.status_code in (400, 404, 422)

    def test_approve_and_revert(self, admin):
        db = _mongo()
        rows = admin.get(f"{API}/masters/categories/unspsc-suggestions").json()
        c = next(x for x in rows if x["suggestions"])
        code = c["suggestions"][0]["code"]
        try:
            r = admin.post(f"{API}/masters/categories/{c['id']}/approve-unspsc", json={"unspsc_code": code})
            assert r.status_code == 200, r.text
            doc = db.categories.find_one({"_id": ObjectId(c["id"])})
            assert doc["unspsc_code"] == code and doc.get("unspsc_title")
            assert db.audit_events.find_one({"event_type": "category.unspsc_approved", "target_id": c["id"]})
            after = admin.get(f"{API}/masters/categories/unspsc-suggestions").json()
            assert c["id"] not in [x["id"] for x in after]
            assert len(after) == len(rows) - 1
        finally:
            db.categories.update_one({"_id": ObjectId(c["id"])}, {"$set": {"unspsc_code": None}, "$unset": {"unspsc_title": ""}})
        assert len(admin.get(f"{API}/masters/categories/unspsc-suggestions").json()) == len(rows)


# --- Supplier registration Section C/D save with UNSPSC pick (regression for 422 extra inputs)
class TestRegistrationUnspsc:
    def test_section_c_d_save(self):
        db = _mongo()
        email = f"test_v165_{int(time.time())}@example.com"
        r = requests.post(f"{API}/registrations", json={"email": email, "company_name": "TEST_V165 Co", "data_processing_consent": True})
        assert r.status_code == 200, r.text
        rid, tok = r.json()["id"], r.json()["magic_token"]
        try:
            body = {"primary_unspsc_code": "26131509", "primary_unspsc_title": "Wind power plants",
                    "business_categories": [{"code": "26131509", "title": "Wind power plants"}]}
            p = requests.patch(f"{API}/registrations/{rid}", params={"token": tok}, json=body)
            assert p.status_code == 200, p.text
            g = requests.get(f"{API}/registrations/resume/{tok}").json()
            assert g["primary_unspsc_code"] == "26131509"
            assert g["primary_unspsc_title"] == "Wind power plants"
            assert g["business_categories"][0]["code"] == "26131509"
        finally:
            db.registrations.delete_one({"_id": ObjectId(rid)})
