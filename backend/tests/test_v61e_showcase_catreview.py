# v61e — Home showcase (/market/showcase), admin home adverts CRUD, supplier category review queue, authz
# Cleanup: deletes only the TEST_ adverts / categories / listings created here (by id) via Mongo at module teardown.
import asyncio
import io
import os
import secrets
from datetime import datetime, timedelta, timezone

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
V1 = f"{BASE_URL}/api/v1"
TAG = secrets.token_hex(3)
CREATED = {"ads": [], "cats": [], "listings": [], "media": []}


def _login(path, email, pw):
    s = requests.Session()
    r = s.post(f"{V1}/{path}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def iso(delta_h):
    return (datetime.now(timezone.utc) + timedelta(hours=delta_h)).isoformat()


@pytest.fixture(scope="module")
def admin():
    return _login("admin", "adminsupport@pmcmanagers.com", "Admin@12345")


@pytest.fixture(scope="module")
def vendor():
    return _login("vendor", "testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import dotenv_values
    env = dotenv_values("/app/backend/.env")

    async def run():
        db = AsyncIOMotorClient(env["MONGO_URL"])[env["DB_NAME"]]
        for i in CREATED["ads"]:
            await db.home_adverts.delete_one({"_id": ObjectId(i)})
        for i in CREATED["cats"]:
            await db.categories.delete_one({"_id": ObjectId(i)})
        for i in CREATED["listings"]:
            await db.mkt_listings.delete_one({"_id": ObjectId(i)})
        for i in CREATED["media"]:
            await db.mkt_media.delete_one({"_id": i})
    asyncio.run(run())


# ---- public showcase ----
class TestShowcase:
    def test_showcase_public_shape(self):
        r = requests.get(f"{V1}/market/showcase")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["products"], list) and isinstance(d["adverts"], list)
        assert len(d["products"]) <= 4
        for p in d["products"]:
            assert p.get("photos"), "showcase product without photos"
            assert "_id" not in p and "id" in p
            assert p.get("status", "live") == "live"


# ---- authz ----
class TestAuthz:
    @pytest.mark.parametrize("m,path", [("get", "/admin/home-adverts"), ("post", "/admin/home-adverts"),
                                        ("get", "/admin/category-review"), ("post", "/admin/category-review/000000000000000000000000")])
    def test_anon_rejected(self, m, path):
        r = getattr(requests, m)(f"{V1}{path}", json={"title": "TEST_x", "action": "approve"})
        assert r.status_code in (401, 403), r.status_code

    @pytest.mark.parametrize("m,path", [("get", "/admin/home-adverts"), ("post", "/admin/home-adverts"),
                                        ("get", "/admin/category-review"), ("post", "/admin/category-review/000000000000000000000000")])
    def test_vendor_rejected(self, vendor, m, path):
        r = getattr(vendor, m)(f"{V1}{path}", json={"title": "TEST_x", "action": "approve"})
        assert r.status_code in (401, 403), r.status_code


# ---- adverts CRUD ----
class TestAdverts:
    def test_image_upload_card(self, admin):
        b = io.BytesIO(); Image.new("RGB", (2000, 800), (10, 120, 60)).save(b, "PNG")
        r = admin.post(f"{V1}/admin/home-adverts/image", files={"file": ("TEST_ad.png", b.getvalue(), "image/png")})
        assert r.status_code == 200, r.text
        mid = r.json()["id"]; CREATED["media"].append(mid)
        img = requests.get(f"{V1}/market/media/{mid}")
        assert img.status_code == 200
        assert Image.open(io.BytesIO(img.content)).size == (1200, 900)
        bad = admin.post(f"{V1}/admin/home-adverts/image", files={"file": ("TEST_x.txt", b"hello", "text/plain")})
        assert bad.status_code == 400

    def test_bad_link_rejected(self, admin):
        r = admin.post(f"{V1}/admin/home-adverts", json={"title": f"TEST_bad {TAG}", "link_url": "http://insecure.com"})
        assert r.status_code == 400 and "https://" in r.json()["detail"]
        r = admin.post(f"{V1}/admin/home-adverts", json={"title": f"TEST_bad {TAG}", "link_url": "javascript:alert(1)"})
        assert r.status_code == 400

    def test_active_future_expired_inactive_visibility(self, admin):
        mk = lambda t, **k: admin.post(f"{V1}/admin/home-adverts", json={"title": f"TEST_{t} {TAG}", "link_url": "/market", **k})
        ids = {}
        for name, kw in {"live": {"starts_at": iso(-1), "ends_at": iso(24)},
                         "future": {"starts_at": iso(5)},
                         "expired": {"starts_at": iso(-48), "ends_at": iso(-1)},
                         "off": {"is_active": False}}.items():
            r = mk(name, **kw); assert r.status_code == 200, r.text
            ids[name] = r.json()["id"]; CREATED["ads"].append(ids[name])
        lst = admin.get(f"{V1}/admin/home-adverts").json()["items"]
        got = {a["id"] for a in lst}
        assert set(ids.values()) <= got
        assert all("_id" not in a for a in lst)
        pub = {a["id"]: a for a in requests.get(f"{V1}/market/showcase").json()["adverts"]}
        assert ids["live"] in pub
        assert pub[ids["live"]]["title"] == f"TEST_live {TAG}"
        for k in ("future", "expired", "off"):
            assert ids[k] not in pub, k
        TestAdverts.live_id = ids["live"]

    def test_update_and_soft_delete(self, admin):
        aid = TestAdverts.live_id
        r = admin.put(f"{V1}/admin/home-adverts/{aid}", json={"title": f"TEST_live2 {TAG}", "link_url": "https://example.com", "cta_label": "Go"})
        assert r.status_code == 200
        pub = {a["id"]: a for a in requests.get(f"{V1}/market/showcase").json()["adverts"]}
        assert pub[aid]["title"] == f"TEST_live2 {TAG}" and pub[aid]["cta_label"] == "Go"
        assert admin.put(f"{V1}/admin/home-adverts/000000000000000000000000", json={"title": "TEST_nf"}).status_code == 404
        assert admin.delete(f"{V1}/admin/home-adverts/{aid}").status_code == 200
        assert aid not in {a["id"] for a in admin.get(f"{V1}/admin/home-adverts").json()["items"]}
        assert aid not in {a["id"] for a in requests.get(f"{V1}/market/showcase").json()["adverts"]}

    def test_deleted_advert_not_resurrected_by_put(self, admin):
        """Edge: PUT on a soft-deleted advert (is_active defaults True) must not put it back on the home page."""
        aid = TestAdverts.live_id
        admin.put(f"{V1}/admin/home-adverts/{aid}", json={"title": f"TEST_zombie {TAG}"})
        pub = {a["id"] for a in requests.get(f"{V1}/market/showcase").json()["adverts"]}
        assert aid not in pub, "soft-deleted advert reappeared on home page after PUT"


# ---- category review ----
class TestCategoryReview:
    def _new_cat(self, vendor, name):
        r = vendor.post(f"{V1}/market/categories", json={"name": name})
        assert r.status_code == 200, r.text
        d = r.json(); assert d["created"] is True
        CREATED["cats"].append(d["id"])
        return d["id"]

    def _listing(self, vendor, cat):
        r = vendor.post(f"{V1}/market/listings", json={"title": f"TEST_cat listing {TAG}", "category": cat,
                                                         "sale_modes": ["fixed"], "buy_now_price": 10})
        assert r.status_code == 200, r.text
        CREATED["listings"].append(r.json()["id"])
        return r.json()["id"]

    def _queue(self, admin):
        return {c["id"]: c for c in admin.get(f"{V1}/admin/category-review").json()["items"]}

    def test_approve(self, admin, vendor):
        cid = self._new_cat(vendor, f"TEST_Approve Cat {TAG}")
        q = self._queue(admin)
        assert cid in q and q[cid]["added_by"] and q[cid]["listings"] == 0
        r = admin.post(f"{V1}/admin/category-review/{cid}", json={"action": "approve"})
        assert r.status_code == 200 and r.json()["ok"]
        assert cid not in self._queue(admin)

    def test_rename_updates_listings_and_clash(self, admin, vendor):
        cid = self._new_cat(vendor, f"TEST_Valvs {TAG}")
        lid = self._listing(vendor, f"TEST_Valvs {TAG}")
        assert self._queue(admin)[cid]["listings"] == 1
        clash = admin.post(f"{V1}/admin/category-review/{cid}", json={"action": "rename", "name": f"test_approve cat {TAG}"})
        assert clash.status_code == 409 and "Merge" in clash.json()["detail"]
        assert admin.post(f"{V1}/admin/category-review/{cid}", json={"action": "rename", "name": " "}).status_code == 400
        r = admin.post(f"{V1}/admin/category-review/{cid}", json={"action": "rename", "name": f"TEST_Valves  {TAG}"})
        assert r.status_code == 200 and r.json()["listings_moved"] == 1
        assert cid not in self._queue(admin)
        mine = vendor.get(f"{V1}/market/mine").json()
        items = mine.get("items", mine) if isinstance(mine, dict) else mine
        row = next(x for x in items if x["id"] == lid)
        assert row["category"] == f"TEST_Valves {TAG}"

    def test_merge(self, admin, vendor):
        target = next(iter([c for c in requests.get(f"{V1}/masters/categories/public").json() if c["name"].startswith("TEST_Valves")]), None)
        assert target, "renamed category should be active in public list"
        cid = self._new_cat(vendor, f"TEST_Valvez {TAG}")
        lid = self._listing(vendor, f"TEST_Valvez {TAG}")
        bad = admin.post(f"{V1}/admin/category-review/{cid}", json={"action": "merge", "target_id": cid})
        assert bad.status_code == 400
        r = admin.post(f"{V1}/admin/category-review/{cid}", json={"action": "merge", "target_id": target["id"]})
        assert r.status_code == 200 and r.json()["listings_moved"] == 1
        assert cid not in self._queue(admin)
        pub_ids = {c["id"] for c in requests.get(f"{V1}/masters/categories/public").json()}
        assert cid not in pub_ids
        mine = vendor.get(f"{V1}/market/mine").json()
        items = mine.get("items", mine) if isinstance(mine, dict) else mine
        assert next(x for x in items if x["id"] == lid)["category"] == target["name"]
        # vendor re-adding a merged (inactive) name is blocked
        again = vendor.post(f"{V1}/market/categories", json={"name": f"TEST_Valvez {TAG}"})
        assert again.status_code == 400

    def test_bad_action_and_404(self, admin):
        assert admin.post(f"{V1}/admin/category-review/000000000000000000000000", json={"action": "approve"}).status_code == 404
        assert admin.post(f"{V1}/admin/category-review/bad", json={"action": "approve"}).status_code == 404
        assert admin.post(f"{V1}/admin/category-review/000000000000000000000000", json={"action": "nuke"}).status_code == 422
