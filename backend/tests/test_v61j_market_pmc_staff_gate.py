# v61j — pmc_staff gate: buyer-org admins get 403 on all marketplace staff endpoints; PMC admin still 200; buyer can still bid/buy.
# Requires: python tests/mkt_t180_seed.py create (TEST_ buyer org + vendor #2); clean afterwards.
import os
import pytest
import requests
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
V1 = f"{BASE_URL}/api/v1"
API = f"{V1}/market"
_mongo = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED = {"listings": [], "ads": []}
FAKE = "000000000000000000000000"


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for lid in CREATED["listings"]:
        _mongo.mkt_bids.delete_many({"listing_id": ObjectId(lid)})
        _mongo.mkt_orders.delete_many({"listing_id": ObjectId(lid)})
        _mongo.mkt_listings.delete_one({"_id": ObjectId(lid)})
    for aid in CREATED["ads"]:
        _mongo.home_adverts.delete_one({"_id": ObjectId(aid)})


def login(kind, email, pw):
    s = requests.Session()
    r = s.post(f"{V1}/{kind}/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"{kind} login failed {r.text[:200]}")
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


@pytest.fixture(scope="module")
def v1():
    return login("vendor", "testvendor@pmcmanagers.com", "Vendor@12345")


@pytest.fixture(scope="module")
def adm():
    return login("admin", "adminsupport@pmcmanagers.com", "Admin@12345")


@pytest.fixture(scope="module")
def buyer():
    return login("admin", "test_mkt_buyer_t180@example.com", "Buyer@12345")


def pending(v, title, **kw):
    body = {"title": title, "sale_modes": ["fixed"], "buy_now_price": 10, "category": "TEST_cat", **kw}
    r = v.post(f"{API}/listings", json=body)
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    CREATED["listings"].append(lid)
    assert v.post(f"{API}/listings/{lid}/submit").status_code == 200
    return lid


AD = {"title": "TEST_ad", "image_url": "https://example.com/x.jpg", "link_url": "https://example.com", "is_active": False}

# (method, url, json) — every staff endpoint
ENDPOINTS = [
    ("get", f"{API}/admin/listings", None),
    ("post", f"{API}/admin/listings/{FAKE}/decision", {"action": "approve"}),
    ("post", f"{API}/admin/listings/bulk-decision", {"ids": [FAKE], "action": "approve"}),
    ("get", f"{API}/admin/settings", None),
    ("put", f"{API}/admin/settings", {"fee_type": "percent", "fee_value": 0, "charge": True}),
    ("get", f"{API}/admin/orders", None),
    ("post", f"{API}/admin/orders/{FAKE}/payout", {"reference": "TEST_ref"}),
    ("get", f"{V1}/admin/home-adverts", None),
    ("post", f"{V1}/admin/home-adverts", AD),
    ("put", f"{V1}/admin/home-adverts/{FAKE}", AD),
    ("delete", f"{V1}/admin/home-adverts/{FAKE}", None),
    ("get", f"{V1}/admin/home-adverts/{FAKE}/stats", None),
    ("get", f"{V1}/admin/category-review", None),
    ("post", f"{V1}/admin/category-review/{FAKE}", {"action": "approve"}),
]


class TestBuyerOrgBlocked:
    @pytest.mark.parametrize("method,url,body", ENDPOINTS, ids=[f"{m} {u.split('/api/v1')[1]}" for m, u, _ in ENDPOINTS])
    def test_buyer_403(self, buyer, method, url, body):
        r = getattr(buyer, method)(url, json=body) if body is not None else getattr(buyer, method)(url)
        assert r.status_code == 403, f"{r.status_code} {r.text[:150]}"
        assert r.json().get("detail") == "PMC staff only"

    def test_buyer_ad_image_403(self, buyer):
        r = buyer.post(f"{V1}/admin/home-adverts/image", files={"file": ("x.jpg", b"xx", "image/jpeg")})
        assert r.status_code == 403 and r.json().get("detail") == "PMC staff only", r.text

    def test_buyer_bulk_leaves_pending(self, v1, buyer):
        a = pending(v1, "TEST_j_bulk_buyer")
        r = buyer.post(f"{API}/admin/listings/bulk-decision", json={"ids": [a], "action": "approve"})
        assert r.status_code == 403
        r = buyer.post(f"{API}/admin/listings/{a}/decision", json={"action": "approve"})
        assert r.status_code == 403
        assert _mongo.mkt_listings.find_one({"_id": ObjectId(a)})["status"] == "pending"


class TestPmcAdminAllowed:
    @pytest.mark.parametrize("url", [f"{API}/admin/listings", f"{API}/admin/settings", f"{API}/admin/orders",
                                     f"{V1}/admin/home-adverts", f"{V1}/admin/category-review"])
    def test_admin_get_200(self, adm, url):
        r = adm.get(url)
        assert r.status_code == 200, r.text[:150]

    def test_admin_put_settings_200(self, adm):
        cur = adm.get(f"{API}/admin/settings").json()
        body = {"fee_type": cur.get("fee_type", "percent"), "fee_value": cur.get("fee_value", 0), "charge": cur.get("charge", True)}
        r = adm.put(f"{API}/admin/settings", json=body)
        assert r.status_code == 200 and r.json()["fee_type"] == body["fee_type"], r.text

    def test_admin_payout_reaches_logic(self, adm):
        r = adm.post(f"{API}/admin/orders/{FAKE}/payout", json={"reference": "TEST_ref"})
        assert r.status_code == 409, r.text  # passed the gate, no such paid order

    def test_admin_single_decide_200(self, v1, adm):
        a = pending(v1, "TEST_j_single")
        r = adm.post(f"{API}/admin/listings/{a}/decision", json={"action": "approve"})
        assert r.status_code == 200 and r.json()["status"] == "live"

    def test_admin_bulk_dupes_skipped(self, v1, adm):
        a, b = pending(v1, "TEST_j_bulk_a"), pending(v1, "TEST_j_bulk_b")
        r = adm.post(f"{API}/admin/listings/bulk-decision",
                     json={"ids": [a, a, b, b, "bad", FAKE], "action": "approve"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["decided"] == 2 and d["skipped"] == 1, d  # dupes ignored; 'bad' invalid id ignored; FAKE skipped

    def test_admin_home_advert_crud(self, adm):
        r = adm.get(f"{V1}/admin/home-adverts/{FAKE}/stats")
        assert r.status_code == 404
        r = adm.delete(f"{V1}/admin/home-adverts/{FAKE}")
        assert r.status_code == 404


class TestBuyerStillTrades:
    def test_buyer_buy_now(self, v1, adm, buyer):
        a = pending(v1, "TEST_j_buy")
        assert adm.post(f"{API}/admin/listings/{a}/decision", json={"action": "approve"}).status_code == 200
        r = buyer.post(f"{API}/listings/{a}/buy")
        assert r.status_code == 200, r.text
        assert r.json()["amount"] == 10

    def test_buyer_bid(self, v1, adm, buyer):
        closes = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        a = pending(v1, "TEST_j_bid", sale_modes=["auction"], buy_now_price=None, start_price=5, closes_at=closes)
        assert adm.post(f"{API}/admin/listings/{a}/decision", json={"action": "approve"}).status_code == 200
        r = buyer.post(f"{API}/listings/{a}/bid", json={"amount": 6})
        assert r.status_code == 200 and r.json()["top_bid"] == 6, r.text

    def test_whoami_buyer(self, buyer):
        assert buyer.get(f"{API}/whoami").json()["kind"] == "buyer"
