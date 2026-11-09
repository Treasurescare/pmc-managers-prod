# v61f — Home advert view/click counts (+admin stats CSV/JSON) and marketplace category alerts for verified buyers
# Requires: python tests/mkt_t180_seed.py create (TEST_ buyer test_mkt_buyer_t180@example.com / Buyer@12345)
# Cleanup: deletes only the TEST_ adverts, stats/seen rows, follows, category, listings, alert logs created here.
import asyncio
import os
import secrets
import time

import pytest
import requests
from bson import ObjectId
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
V1 = f"{BASE_URL}/api/v1"
TAG = secrets.token_hex(3)
CAT = f"TEST_alertcat_{TAG}"
C = {"ads": [], "listings": [], "cat": None, "buyer_id": None}
ENV = dotenv_values("/app/backend/.env")


def mdb():
    return AsyncIOMotorClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]


def run(coro_fn):
    async def w():
        return await coro_fn(mdb())
    return asyncio.run(w())


def _login(path, email, pw):
    s = requests.Session()
    r = s.post(f"{V1}/{path}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin", "adminsupport@pmcmanagers.com", "Admin@12345")


@pytest.fixture(scope="module")
def vendor():
    return _login("vendor", "testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def buyer():
    s = _login("admin", "test_mkt_buyer_t180@example.com", "Buyer@12345")
    return s


@pytest.fixture(scope="module", autouse=True)
def setup_cleanup():
    async def mk(db):
        r = await db.categories.insert_one({"name": CAT, "code": f"test-{TAG}", "is_active": True, "source": "admin"})
        return str(r.inserted_id)
    C["cat"] = run(mk)
    yield

    async def clean(db):
        for a in C["ads"]:
            await db.home_adverts.delete_one({"_id": ObjectId(a)})
            await db.home_ad_stats.delete_many({"ad_id": a})
            await db.home_ad_seen.delete_many({"_id": {"$regex": f"^{a}:"}})
        for l in C["listings"]:
            await db.mkt_listings.delete_one({"_id": ObjectId(l)})
            await db.mkt_alert_log.delete_many({"_id": {"$regex": f"^{l}:"}})
        if C["buyer_id"]:
            await db.mkt_follows.delete_one({"_id": C["buyer_id"]})
        await db.categories.delete_one({"_id": ObjectId(C["cat"])})
    run(clean)


def mk_ad(admin, title, active=True):
    r = admin.post(f"{V1}/admin/home-adverts", json={"title": title, "link_url": "/market", "is_active": active})
    assert r.status_code == 200, r.text
    C["ads"].append(r.json()["id"])
    return r.json()["id"]


UA1 = {"User-Agent": f"TEST-UA-1-{TAG}"}
UA2 = {"User-Agent": f"TEST-UA-2-{TAG}"}


# ---- advert events ----
class TestAdEvents:
    def test_view_unique_per_day(self, admin):
        aid = mk_ad(admin, f"TEST_ad_{TAG}")
        r1 = requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "view"}, headers=UA1)
        assert r1.status_code == 200 and r1.json() == {"ok": True, "counted": True}, r1.text
        r2 = requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "view"}, headers=UA1)
        assert r2.json() == {"ok": True, "counted": False}
        r3 = requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "view"}, headers=UA2)
        assert r3.json()["counted"] is True
        c1 = requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "click"}, headers=UA1)
        assert c1.json()["counted"] is True
        c2 = requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "click"}, headers=UA1)
        assert c2.json()["counted"] is False
        row = next(a for a in admin.get(f"{V1}/admin/home-adverts").json()["items"] if a["id"] == aid)
        assert row["views"] == 2 and row["clicks"] == 1, row

    def test_unknown_deleted_invalid(self, admin):
        r = requests.post(f"{V1}/market/showcase/ad-event", json={"id": str(ObjectId()), "kind": "view"})
        assert r.status_code == 200 and r.json() == {"ok": False}
        aid = mk_ad(admin, f"TEST_addel_{TAG}")
        assert admin.delete(f"{V1}/admin/home-adverts/{aid}").status_code == 200
        r = requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "view"}, headers=UA1)
        assert r.json() == {"ok": False}
        assert run(lambda db: db.home_ad_stats.count_documents({"ad_id": aid})) == 0
        assert requests.post(f"{V1}/market/showcase/ad-event", json={"id": aid, "kind": "hover"}).status_code == 422
        assert requests.post(f"{V1}/market/showcase/ad-event", json={"id": "abc", "kind": "view"}).status_code == 422

    def test_new_ad_zero_totals(self, admin):
        aid = mk_ad(admin, f"TEST_adzero_{TAG}", active=False)
        row = next(a for a in admin.get(f"{V1}/admin/home-adverts").json()["items"] if a["id"] == aid)
        assert row["views"] == 0 and row["clicks"] == 0


class TestAdStats:
    def test_json_and_csv(self, admin):
        aid = C["ads"][0]
        j = admin.get(f"{V1}/admin/home-adverts/{aid}/stats")
        assert j.status_code == 200, j.text
        d = j.json()
        assert d["title"] == f"TEST_ad_{TAG}" and len(d["rows"]) == 1
        assert d["rows"][0]["views"] == 2 and d["rows"][0]["clicks"] == 1
        c = admin.get(f"{V1}/admin/home-adverts/{aid}/stats", params={"format": "csv"})
        assert c.status_code == 200 and c.headers["content-type"].startswith("text/csv")
        assert "attachment" in c.headers.get("content-disposition", "")
        lines = c.text.strip().splitlines()
        assert lines[0].startswith("Advert,")
        assert lines[-1].startswith("Total,2,1,50.0"), lines

    def test_authz(self, vendor, buyer):
        aid = C["ads"][0]
        assert requests.get(f"{V1}/admin/home-adverts/{aid}/stats").status_code == 401
        assert vendor.get(f"{V1}/admin/home-adverts/{aid}/stats").status_code in (401, 403)
        rb = buyer.get(f"{V1}/admin/home-adverts/{aid}/stats")
        print("buyer-org admin user on stats:", rb.status_code)

    def test_404(self, admin):
        assert admin.get(f"{V1}/admin/home-adverts/{ObjectId()}/stats").status_code == 404
        assert admin.get(f"{V1}/admin/home-adverts/xyz/stats").status_code == 404


# ---- category alerts ----
class TestAlerts:
    def test_authz(self, vendor):
        assert requests.get(f"{V1}/market/alerts").status_code == 401
        assert requests.put(f"{V1}/market/alerts", json={"categories": []}).status_code in (401, 403)
        assert vendor.get(f"{V1}/market/alerts").status_code == 403
        assert vendor.put(f"{V1}/market/alerts", json={"categories": [CAT]}).status_code == 403

    def test_get_put_persist(self, buyer):
        g = buyer.get(f"{V1}/market/alerts")
        assert g.status_code == 200, g.text
        assert g.json()["email"] == "test_mkt_buyer_t180@example.com"
        bad = buyer.put(f"{V1}/market/alerts", json={"categories": [CAT, "TEST_no_such_cat_zzz"]})
        assert bad.status_code == 400
        r = buyer.put(f"{V1}/market/alerts", json={"categories": [CAT, f" {CAT} "]})
        assert r.status_code == 200 and r.json()["categories"] == [CAT]
        assert buyer.get(f"{V1}/market/alerts").json()["categories"] == [CAT]
        f = run(lambda db: db.mkt_follows.find_one({"categories": CAT}))
        assert f and f["token"] and f["email"] == "test_mkt_buyer_t180@example.com"
        C["buyer_id"] = f["_id"]

    def test_approve_sends_once_and_unsubscribe(self, vendor, admin, buyer):
        r = vendor.post(f"{V1}/market/listings", json={"title": f"TEST_alert_{TAG}", "description": "TEST", "category": CAT,
                                                       "sale_modes": ["fixed"], "buy_now_price": 10, "currency": "USD"})
        assert r.status_code == 200, r.text
        lid = r.json()["id"]
        C["listings"].append(lid)
        assert vendor.post(f"{V1}/market/listings/{lid}/submit").status_code == 200
        d = admin.post(f"{V1}/market/admin/listings/{lid}/decision", json={"action": "approve"})
        assert d.status_code == 200 and d.json()["status"] == "live", d.text
        lst = None
        for _ in range(20):
            time.sleep(1)
            lst = run(lambda db: db.mkt_listings.find_one({"_id": ObjectId(lid)}))
            if "alerts_sent" in lst:
                break
        assert lst.get("alerts_sent") == 1, lst.get("alerts_sent")
        assert run(lambda db: db.mkt_alert_log.count_documents({"_id": {"$regex": f"^{lid}:"}})) == 1
        # unsubscribe
        tok = run(lambda db: db.mkt_follows.find_one({"_id": C["buyer_id"]}))["token"]
        u = requests.get(f"{V1}/market/alerts/unsubscribe", params={"t": tok})
        assert u.status_code == 200 and "no longer receive" in u.text
        assert buyer.get(f"{V1}/market/alerts").json()["categories"] == []
        bad = requests.get(f"{V1}/market/alerts/unsubscribe", params={"t": "x" * 30})
        assert bad.status_code == 200 and "not valid" in bad.text
