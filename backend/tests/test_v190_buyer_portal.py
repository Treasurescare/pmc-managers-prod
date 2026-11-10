# v190 — Buyer portal: self-register + email verify, PMC approve, dashboard, notifications, team invite/remove,
# admin add buyer, RBAC/security, marketplace notifications (outbid / order / delivery)
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


def reg_body(email, **kw):
    b = {"email": email, "password": PWD, "name": "TEST Buyer A", "phone": "9876543210", "country_code": "IN",
         "city": "Abhaneri", "address": "TEST addr", "org_name": f"TEST_BuyerOrg {TAG}"}
    b.update(kw)
    return b


def set_pwd(email):
    u = mdb.admin_users.find_one({"email": email})
    tok = jwt.encode({"sub": str(u["_id"]), "email": email, "portal": "buyer", "jti": u["pwd_reset_jti"], "type": "pwd_reset",
                      "iat": now(), "exp": now() + timedelta(days=1)}, BE["JWT_SECRET"], algorithm="HS256")
    r = requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": PWD})
    assert r.status_code == 200, r.text


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
        mdb.mkt_bids.delete_many({"listing_id": lid})
        mdb.mkt_orders.delete_many({"listing_id": lid})
        mdb.mkt_listings.delete_one({"_id": lid})


class TestBuyerPortal:
    def test_01_masters(self):
        r = requests.get(f"{API}/masters/countries")
        assert r.status_code == 200, r.text
        assert mdb.masters_cities.find_one({"country_code": "IN", "name": "Abhaneri", "is_active": True})

    def test_02_register_validation(self):
        e = f"test_ba_{TAG}@example.com"
        S["a"] = e
        CREATED["emails"].add(e)
        # missing required (city) -> 422 ; invalid city / country -> 422
        b = reg_body(e); b.pop("city")
        assert requests.post(f"{API}/buyer/register", json=b).status_code == 422
        r = requests.post(f"{API}/buyer/register", json=reg_body(e, city="Nowhereville"))
        assert r.status_code == 422 and "city" in r.text, r.text
        r = requests.post(f"{API}/buyer/register", json=reg_body(e, country_code="QQ"))
        assert r.status_code == 422 and "country" in r.text, r.text

    def test_03_register_ok_and_duplicate(self):
        r = requests.post(f"{API}/buyer/register", json=reg_body(S["a"], address=None, zip=None, org_name=None))
        assert r.status_code == 200, r.text
        u = mdb.admin_users.find_one({"email": S["a"]})
        assert u["email_verified"] is False and u["tenant_id"].startswith("PENDING-") and u["is_org_admin"] is True
        assert u["buyer_profile"]["phone_code"] and u["buyer_profile"]["country"]
        S["a_uid"] = str(u["_id"])
        r = requests.post(f"{API}/buyer/register", json=reg_body(S["a"]))
        assert r.status_code == 409, r.text
        r = requests.post(f"{API}/buyer/register", json=reg_body(ADMIN[0]))
        assert r.status_code == 409

    def test_04_login_before_verify_403(self, admin):
        s, r = login(S["a"], PWD)
        assert r.status_code == 403 and "confirm your email" in r.text.lower(), r.text
        app = mdb.buyer_applications.find_one({"email": S["a"]})
        S["a_app"] = str(app["_id"])
        r = admin.post(f"{API}/buyer-applications/{S['a_app']}/decision", json={"action": "approve"})
        assert r.status_code == 409, r.text

    def test_05_verify_email(self):
        bad = requests.post(f"{API}/buyer/verify-email", json={"token": "x.y.z"})
        assert bad.status_code == 400
        tok = jwt.encode({"sub": S["a_uid"], "email": S["a"], "type": "buyer_verify", "exp": now() + timedelta(days=1)},
                         BE["JWT_SECRET"], algorithm="HS256")
        r = requests.post(f"{API}/buyer/verify-email", json={"token": tok})
        assert r.status_code == 200 and r.json()["email"] == S["a"]
        assert mdb.buyer_applications.find_one({"email": S["a"]})["email_verified"] is True
        # wrong type token rejected
        t2 = jwt.encode({"sub": S["a_uid"], "email": S["a"], "type": "access", "exp": now() + timedelta(days=1)}, BE["JWT_SECRET"], algorithm="HS256")
        assert requests.post(f"{API}/buyer/verify-email", json={"token": t2}).status_code == 400

    def test_06_pending_buyer(self):
        s, r = login(S["a"], PWD)
        assert r.status_code == 200, r.text
        S["sa"] = s
        w = s.get(f"{API}/market/whoami").json()
        assert w["kind"] == "buyer" and w["verified"] is False and w.get("pending") is True, w
        me = s.get(f"{API}/buyer/me").json()
        assert me["status"] == "pending_approval" and me["verified"] is False
        r = s.post(f"{API}/buyer/team/invite", json={"name": "TEST Col", "email": f"test_col0_{TAG}@example.com", "phone": "9876500000"})
        assert r.status_code == 403
        d = s.get(f"{API}/buyer/dashboard")
        assert d.status_code == 200 and d.json()["me"]["verified"] is False

    def test_07_admin_approve(self, admin):
        r = admin.post(f"{API}/buyer-applications/{S['a_app']}/decision", json={"action": "approve"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["signin_status"] == "self_registered" and d["tenant_code"]
        S["a_code"] = d["tenant_code"]
        u = mdb.admin_users.find_one({"email": S["a"]})
        assert u["tenant_id"] == S["a_code"]
        me = S["sa"].get(f"{API}/buyer/me").json()
        assert me["verified"] is True and me["is_org_admin"] is True and me["org"]["code"] == S["a_code"]
        n = S["sa"].get(f"{API}/buyer/notifications").json()
        assert any("verified" in x["subject"].lower() for x in n["items"]), n
        assert S["sa"].get(f"{API}/market/whoami").json()["verified"] is True

    def test_08_profile_and_password(self):
        s = S["sa"]
        r = s.put(f"{API}/buyer/me", json={"name": "TEST Buyer A2", "phone": "98765 43211", "country_code": "IN", "city": "Abhaneri", "zip": "560001"})
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "TEST Buyer A2" and r.json()["profile"]["phone"] == "9876543211"
        assert s.put(f"{API}/buyer/me", json={"name": "TEST", "phone": "9876543211", "country_code": "IN", "city": "Zzz"}).status_code == 422
        assert s.get(f"{API}/buyer/me").json()["name"] == "TEST Buyer A2"
        r = s.post(f"{API}/buyer/me/password", json={"current_password": "wrong", "new_password": "Newpass@123"})
        assert r.status_code == 400
        r = s.post(f"{API}/buyer/me/password", json={"current_password": PWD, "new_password": "Newpass@123"})
        assert r.status_code == 200
        _, r2 = login(S["a"], "Newpass@123")
        assert r2.status_code == 200
        r = s.post(f"{API}/buyer/me/password", json={"current_password": "Newpass@123", "new_password": PWD})
        assert r.status_code == 200
        # avatar
        assert s.post(f"{API}/buyer/me/avatar", json={"data_url": "data:image/png;base64,iVBORw0KGgo="}).status_code == 200
        assert s.post(f"{API}/buyer/me/avatar", json={"data_url": "javascript:alert(1)"}).status_code == 422

    def test_09_team_invite_approve(self, admin):
        s = S["sa"]
        c = f"test_col_{TAG}@example.com"
        S["c"] = c
        CREATED["emails"].add(c)
        r = s.post(f"{API}/buyer/team/invite", json={"name": "TEST Colleague", "email": c, "phone": "9876500001"})
        assert r.status_code == 200, r.text
        S["c_req"] = r.json()["id"]
        assert s.post(f"{API}/buyer/team/invite", json={"name": "TEST Colleague", "email": c, "phone": "9876500001"}).status_code == 409
        lst = admin.get(f"{API}/buyer/admin/team-requests").json()["items"]
        assert any(x["id"] == S["c_req"] for x in lst)
        r = admin.post(f"{API}/buyer/admin/team-requests/{S['c_req']}/decision", json={"action": "approve"})
        assert r.status_code == 200 and r.json()["signin_status"] == "sent", r.text
        assert admin.post(f"{API}/buyer/admin/team-requests/{S['c_req']}/decision", json={"action": "approve"}).status_code == 409
        u = mdb.admin_users.find_one({"email": c})
        assert u["tenant_id"] == S["a_code"] and u["is_org_admin"] is False
        S["c_uid"] = str(u["_id"])
        t = s.get(f"{API}/buyer/team").json()
        assert any(m["email"] == c for m in t["members"])

    def test_10_colleague_cannot_manage(self):
        set_pwd(S["c"])
        sc, r = login(S["c"], PWD)
        assert r.status_code == 200, r.text
        S["sc"] = sc
        assert sc.get(f"{API}/buyer/me").json()["is_org_admin"] is False
        assert sc.post(f"{API}/buyer/team/invite", json={"name": "TEST X", "email": f"test_x_{TAG}@example.com", "phone": "9876500002"}).status_code == 403
        assert sc.post(f"{API}/buyer/team/{S['a_uid']}/remove").status_code == 403

    def test_11_admin_add_buyer(self, admin):
        b = f"test_bb_{TAG}@example.com"
        S["b"] = b
        CREATED["emails"].add(b)
        body = {"email": b, "name": "TEST Buyer B", "phone": "9876500003", "country_code": "IN", "city": "Abhaneri", "org_name": f"TEST_OrgB {TAG}"}
        r = admin.post(f"{API}/buyer/admin/buyers", json={**body, "city": "Zzz"})
        assert r.status_code == 422
        r = admin.post(f"{API}/buyer/admin/buyers", json=body)
        assert r.status_code == 200 and r.json()["signin_status"] == "sent", r.text
        S["b_code"] = r.json()["tenant_code"]
        assert admin.post(f"{API}/buyer/admin/buyers", json=body).status_code == 409
        set_pwd(b)
        sb, r = login(b, PWD)
        assert r.status_code == 200
        S["sb"] = sb
        me = sb.get(f"{API}/buyer/me").json()
        assert me["verified"] is True and me["profile"]["city"] == "Abhaneri"

    def test_12_cross_org_remove_404_and_self_400(self):
        assert S["sb"].post(f"{API}/buyer/team/{S['c_uid']}/remove").status_code == 404
        assert S["sa"].post(f"{API}/buyer/team/{S['a_uid']}/remove").status_code == 400

    def test_13_rbac(self, admin):
        sb = S["sb"]
        assert sb.get(f"{API}/buyer/admin/team-requests").status_code == 403
        assert sb.post(f"{API}/buyer/admin/buyers", json={}).status_code in (403, 422)
        assert sb.get(f"{API}/buyer-applications").status_code == 403
        assert sb.get(f"{API}/market/admin/settings").status_code == 403
        assert admin.get(f"{API}/buyer/me").status_code == 403
        assert requests.get(f"{API}/buyer/me").status_code in (401, 403)

    def test_14_marketplace_notifications(self):
        v = vlogin()
        vid = v.get(f"{API}/vendor/auth/me").json().get("id") if False else None
        fut = (now() + timedelta(days=2)).isoformat()
        seller = mdb.vendors.find_one({"email": VENDOR[0]})
        sid = str(seller["_id"])
        base = {"description": "TEST", "category": "TEST_cat", "quantity": 1, "unit": "lot", "currency": "USD", "status": "live",
                "seller_id": sid, "seller_name": "TEST seller", "eligibility": "verified_buyers", "min_increment": 1,
                "created_at": now().isoformat(), "updated_at": now().isoformat()}
        la = mdb.mkt_listings.insert_one({**base, "title": f"TEST_auc {TAG}", "sale_modes": ["auction"], "start_price": 100, "closes_at": fut}).inserted_id
        lf = mdb.mkt_listings.insert_one({**base, "title": f"TEST_fix {TAG}", "sale_modes": ["fixed"], "buy_now_price": 50}).inserted_id
        CREATED["listings"] += [la, lf]
        sa, sb = S["sa"], S["sb"]
        assert sa.post(f"{API}/market/listings/{la}/bid", json={"amount": 100}).status_code == 200
        r = sb.post(f"{API}/market/listings/{la}/bid", json={"amount": 110})
        assert r.status_code == 200, r.text
        n = sa.get(f"{API}/buyer/notifications").json()["items"]
        assert any("outbid" in x["subject"].lower() for x in n)
        da = sa.get(f"{API}/buyer/dashboard").json()
        db_ = sb.get(f"{API}/buyer/dashboard").json()
        assert [x["my_status"] for x in da["bids"]] == ["outbid"]
        assert [x["my_status"] for x in db_["bids"]] == ["leading"]
        # buy now -> order + notification
        r = sa.post(f"{API}/market/listings/{lf}/buy")
        assert r.status_code == 200, r.text
        oid = r.json()["id"]
        S["oid"] = oid
        n = sa.get(f"{API}/buyer/notifications").json()["items"]
        assert any("order placed" in x["subject"].lower() for x in n)
        da = sa.get(f"{API}/buyer/dashboard").json()
        assert da["counts"]["to_pay"] == 1 and "pmc_fee" not in da["orders"][0] and "seller_net" not in da["orders"][0]
        # delivery not allowed before paid
        assert v.post(f"{API}/market/orders/{oid}/delivery", json={"status": "dispatched"}).status_code == 404
        assert sa.post(f"{API}/buyer/orders/{oid}/received").status_code == 404
        mdb.mkt_orders.update_one({"_id": ObjectId(oid)}, {"$set": {"status": "paid", "paid_at": now().isoformat(), "delivery_status": "awaiting_dispatch"}})
        r = v.post(f"{API}/market/orders/{oid}/delivery", json={"status": "dispatched", "note": "TEST AWB"})
        assert r.status_code == 200, r.text
        n = sa.get(f"{API}/buyer/notifications").json()["items"]
        assert any("dispatched" in x["subject"].lower() for x in n)
        da = sa.get(f"{API}/buyer/dashboard").json()
        assert da["orders"][0]["delivery_status"] == "dispatched" and len(da["payments"]) == 1 and da["counts"]["in_delivery"] == 1
        # buyer B cannot act on A's order or notifications
        assert sb.post(f"{API}/buyer/orders/{oid}/received").status_code == 404
        nid = n[0]["id"]
        sb.post(f"{API}/buyer/notifications/{nid}/read")
        assert mdb.notifications.find_one({"_id": ObjectId(nid)})["read"] is False
        assert all(x["id"] != nid for x in sb.get(f"{API}/buyer/notifications").json()["items"])
        assert sa.post(f"{API}/buyer/orders/{oid}/received").status_code == 200
        # mark read / read-all
        assert sa.post(f"{API}/buyer/notifications/{nid}/read").status_code == 200
        assert mdb.notifications.find_one({"_id": ObjectId(nid)})["read"] is True
        assert sa.post(f"{API}/buyer/notifications/read-all").status_code == 200
        assert sa.get(f"{API}/buyer/notifications").json()["unread"] == 0

    def test_15_remove_colleague(self):
        sa, sc = S["sa"], S["sc"]
        assert sc.get(f"{API}/buyer/me").status_code == 200
        assert sa.post(f"{API}/buyer/team/{S['c_uid']}/remove").status_code == 200
        assert mdb.admin_users.find_one({"email": S["c"]})["is_active"] is False
        assert sc.get(f"{API}/buyer/me").status_code == 403
        _, r = login(S["c"], PWD)
        assert r.status_code in (401, 403), f"removed colleague can still log in: {r.status_code}"

    def test_16_removed_colleague_cannot_bid(self):
        """SECURITY: existing session of removed colleague should not be able to bid on the marketplace."""
        la = CREATED["listings"][0]
        r = S["sc"].post(f"{API}/market/listings/{la}/bid", json={"amount": 500})
        w = S["sc"].get(f"{API}/market/whoami").json()
        assert r.status_code in (401, 403), f"removed colleague bid accepted: {r.status_code} {r.text}; whoami={w}"
