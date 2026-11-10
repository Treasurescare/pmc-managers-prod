# v191 — Retest of v190 buyer-portal fixes: XSS escaping, deactivated user 403, delivery state guard,
# pending buyer team self, buyer pay success URL, register rate-limit IP (last XFF hop)
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import requests
from bson import ObjectId
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FE["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api/v1"
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
mdb = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
TAG = secrets.token_hex(3)
PWD = "Buyer@12345"
XSS = '<img src=x onerror=window.__xss=1>'
S = {}
CREATED = {"emails": set(), "listings": []}


def now():
    return datetime.now(timezone.utc)


def login(email, pwd, role="buyer"):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pwd, "active_role": role})
    if r.status_code == 200:
        s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s, r


def vlogin():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": VENDOR[0], "password": VENDOR[1]})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def set_pwd(email):
    u = mdb.admin_users.find_one({"email": email})
    tok = jwt.encode({"sub": str(u["_id"]), "email": email, "portal": "buyer", "jti": u["pwd_reset_jti"], "type": "pwd_reset",
                      "iat": now(), "exp": now() + timedelta(days=1)}, BE["JWT_SECRET"], algorithm="HS256")
    r = requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": PWD})
    assert r.status_code == 200, r.text


def listing(title, **kw):
    seller = mdb.vendors.find_one({"email": VENDOR[0]})
    base = {"description": "TEST", "category": "TEST_cat", "quantity": 1, "unit": "lot", "currency": "USD", "status": "live",
            "seller_id": str(seller["_id"]), "seller_name": "TEST seller", "eligibility": "verified_buyers", "min_increment": 1,
            "created_at": now().isoformat(), "updated_at": now().isoformat(), "title": title}
    base.update(kw)
    lid = mdb.mkt_listings.insert_one(base).inserted_id
    CREATED["listings"].append(lid)
    return lid


@pytest.fixture(scope="module")
def admin():
    s, r = login(*ADMIN, role="admin")
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for e in CREATED["emails"]:
        for u in mdb.admin_users.find({"email": e, "roles": "buyer"}):
            mdb.notifications.delete_many({"user_id": str(u["_id"])})
            mdb.admin_users.delete_one({"_id": u["_id"]})
        for a in mdb.buyer_applications.find({"email": e}):
            if a.get("tenant_code"):
                mdb.tenants.delete_one({"code": a["tenant_code"], "source": "buyer_application"})
            mdb.buyer_applications.delete_one({"_id": a["_id"]})
        mdb.buyer_team_requests.delete_many({"email": e})
        mdb.notifications.delete_many({"user_email": e})
    for lid in CREATED["listings"]:
        for o in mdb.mkt_orders.find({"listing_id": lid}):
            if o.get("session_id"):
                mdb.payment_transactions.delete_many({"session_id": o["session_id"]})
        mdb.mkt_bids.delete_many({"listing_id": lid})
        mdb.mkt_orders.delete_many({"listing_id": lid})
        mdb.mkt_listings.delete_one({"_id": lid})


class TestBuyerFixes:
    def test_01_setup_buyer_and_colleague(self, admin):
        a = f"test_fa_{TAG}@example.com"
        CREATED["emails"].add(a)
        r = admin.post(f"{API}/buyer/admin/buyers", json={"email": a, "name": "TEST FixBuyer", "phone": "9876500011", "country_code": "IN",
                                                          "city": "Abhaneri", "org_name": f"TEST_FixOrg {TAG}"})
        assert r.status_code == 200, r.text
        set_pwd(a)
        sa, r = login(a, PWD)
        assert r.status_code == 200, r.text
        S.update(a=a, sa=sa, a_uid=str(mdb.admin_users.find_one({"email": a})["_id"]))
        c = f"test_fc_{TAG}@example.com"
        CREATED["emails"].add(c)
        r = sa.post(f"{API}/buyer/team/invite", json={"name": "TEST FixCol", "email": c, "phone": "9876500012"})
        assert r.status_code == 200, r.text
        r = admin.post(f"{API}/buyer/admin/team-requests/{r.json()['id']}/decision", json={"action": "approve"})
        assert r.status_code == 200, r.text
        set_pwd(c)
        sc, r = login(c, PWD)
        assert r.status_code == 200
        S.update(c=c, sc=sc, c_uid=str(mdb.admin_users.find_one({"email": c})["_id"]))

    # XSS: listing title + delivery note are html-escaped in stored notification bodies
    def test_02_xss_escaped(self):
        sa, v = S["sa"], vlogin()
        lf = listing(f"TEST_xss {XSS}", sale_modes=["fixed"], buy_now_price=50)
        r = sa.post(f"{API}/market/listings/{lf}/buy")
        assert r.status_code == 200, r.text
        oid = r.json()["id"]
        S["oid_paid"] = oid
        mdb.mkt_orders.update_one({"_id": ObjectId(oid)}, {"$set": {"status": "paid", "paid_at": now().isoformat(), "delivery_status": "awaiting_dispatch"}})
        r = v.post(f"{API}/market/orders/{oid}/delivery", json={"status": "dispatched", "note": f"AWB {XSS}"})
        assert r.status_code == 200, r.text
        items = sa.get(f"{API}/buyer/notifications").json()["items"]
        bodies = [x["body"] for x in items]
        assert bodies, items
        for b in bodies:
            assert "<img" not in b, f"unescaped HTML in body: {b}"
        assert any("&lt;img" in b for b in bodies), bodies
        S["v"] = v

    # Seller cannot change delivery after buyer marked received
    def test_03_delivery_after_received_409(self):
        sa, v, oid = S["sa"], S["v"], S["oid_paid"]
        assert sa.post(f"{API}/buyer/orders/{oid}/received").status_code == 200
        for st in ("dispatched", "delivered"):
            r = v.post(f"{API}/market/orders/{oid}/delivery", json={"status": st})
            assert r.status_code == 409, r.text
        assert mdb.mkt_orders.find_one({"_id": ObjectId(oid)})["delivery_status"] == "received"

    # Buyer pay: Stripe success_url -> /buyer/orders?order=
    def test_04_pay_success_url(self):
        sa = S["sa"]
        lf = listing(f"TEST_pay {TAG}", sale_modes=["fixed"], buy_now_price=20)
        oid = sa.post(f"{API}/market/listings/{lf}/buy").json()["id"]
        r = sa.post(f"{API}/market/orders/{oid}/pay", headers={"Origin": BASE_URL})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        assert r.json()["checkout_url"].startswith("https://")
        import stripe
        stripe.api_key = BE["STRIPE_API_KEY"]
        ses = stripe.checkout.Session.retrieve(sid)
        assert f"/buyer/orders?order={oid}" in ses.success_url, ses.success_url
        assert ses.cancel_url.endswith("/buyer/orders"), ses.cancel_url
        S["oid_pay"] = oid

    # Deactivated colleague: existing session blocked on market + buyer actions
    def test_05_removed_colleague_403(self):
        sa, sc = S["sa"], S["sc"]
        la = listing(f"TEST_auc {TAG}", sale_modes=["auction", "offer"], start_price=100,
                     closes_at=(now() + timedelta(days=2)).isoformat())
        lf = listing(f"TEST_fix2 {TAG}", sale_modes=["fixed"], buy_now_price=30)
        assert sc.get(f"{API}/market/whoami").json()["verified"] is True
        assert sa.post(f"{API}/buyer/team/{S['c_uid']}/remove").status_code == 200
        codes = {
            "bid": sc.post(f"{API}/market/listings/{la}/bid", json={"amount": 500}).status_code,
            "offer": sc.post(f"{API}/market/listings/{la}/offer", json={"amount": 90}).status_code,
            "buy": sc.post(f"{API}/market/listings/{lf}/buy").status_code,
            "pay": sc.post(f"{API}/market/orders/{S['oid_pay']}/pay").status_code,
            "buyer_me": sc.get(f"{API}/buyer/me").status_code,
            "my_purchases": sc.get(f"{API}/market/my-purchases").status_code,
        }
        assert all(c in (401, 403) for c in codes.values()), codes
        w = sc.get(f"{API}/market/whoami").json()
        assert w.get("verified") is not True, w
        assert mdb.mkt_bids.count_documents({"listing_id": la}) == 0

    # Pending buyer sees themselves on /buyer/team
    def test_06_pending_team_self_and_xff(self):
        p = f"test_fp_{TAG}@example.com"
        CREATED["emails"].add(p)
        r = requests.post(f"{API}/buyer/register", headers={"X-Forwarded-For": "9.9.9.9"},
                          json={"email": p, "password": PWD, "name": "TEST FixPending", "phone": "9876500013", "country_code": "IN", "city": "Abhaneri"})
        assert r.status_code == 200, r.text
        app = mdb.buyer_applications.find_one({"email": p})
        assert app["ip"] != "9.9.9.9", f"spoofed XFF used as ip: {app['ip']}"
        u = mdb.admin_users.find_one({"email": p})
        tok = jwt.encode({"sub": str(u["_id"]), "email": p, "type": "buyer_verify", "exp": now() + timedelta(days=1)}, BE["JWT_SECRET"], algorithm="HS256")
        assert requests.post(f"{API}/buyer/verify-email", json={"token": tok}).status_code == 200
        sp, r = login(p, PWD)
        assert r.status_code == 200, r.text
        t = sp.get(f"{API}/buyer/team").json()
        assert len(t["members"]) == 1 and t["members"][0]["email"] == p and t["members"][0]["me"] is True, t
