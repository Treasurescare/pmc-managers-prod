# v190 UI setup: `create` -> verified buyer A (admin-added) with notifs/order (+XSS probe in delivery note), pending buyer P; `clean`
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone

import jwt
import requests
from bson import ObjectId
from dotenv import dotenv_values
from pymongo import MongoClient

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
API = FE["REACT_APP_BACKEND_URL"].rstrip("/") + "/api/v1"
mdb = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
PWD = "Buyer@12345"
F = "/tmp/v190.json"
now = lambda: datetime.now(timezone.utc)


def login(email, pwd, role):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pwd, "active_role": role})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def set_pwd(email):
    u = mdb.admin_users.find_one({"email": email})
    tok = jwt.encode({"sub": str(u["_id"]), "email": email, "portal": "buyer", "jti": u["pwd_reset_jti"], "type": "pwd_reset",
                      "iat": now(), "exp": now() + timedelta(days=1)}, BE["JWT_SECRET"], algorithm="HS256")
    assert requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": PWD}).status_code == 200


def create():
    t = secrets.token_hex(3)
    adm = login("adminsupport@pmcmanagers.com", "Admin@12345", "admin")
    a = f"test_uia_{t}@example.com"
    r = adm.post(f"{API}/buyer/admin/buyers", json={"email": a, "name": "TEST UI Buyer", "phone": "9876543210", "country_code": "IN", "city": "Abhaneri", "org_name": f"TEST_UIOrg {t}"})
    assert r.status_code == 200, r.text
    set_pwd(a)
    # pending (self-registered, email confirmed, not approved)
    p = f"test_uip_{t}@example.com"
    r = requests.post(f"{API}/buyer/register", json={"email": p, "password": PWD, "name": "TEST Pending", "phone": "9876543210", "country_code": "IN", "city": "Abhaneri"})
    assert r.status_code == 200, r.text
    pu = mdb.admin_users.find_one({"email": p})
    tok = jwt.encode({"sub": str(pu["_id"]), "email": p, "type": "buyer_verify", "exp": now() + timedelta(days=1)}, BE["JWT_SECRET"], algorithm="HS256")
    seller = mdb.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    base = {"description": "TEST", "category": "TEST_cat", "quantity": 1, "unit": "lot", "currency": "USD", "status": "live", "seller_id": str(seller["_id"]),
            "seller_name": "Test Supplier Co", "eligibility": "verified_buyers", "min_increment": 1, "created_at": now().isoformat(), "updated_at": now().isoformat()}
    la = mdb.mkt_listings.insert_one({**base, "title": f"TEST_UI auction {t}", "sale_modes": ["auction"], "start_price": 100, "closes_at": (now() + timedelta(days=2)).isoformat()}).inserted_id
    lf = mdb.mkt_listings.insert_one({**base, "title": f"TEST_UI fixed {t}", "sale_modes": ["fixed"], "buy_now_price": 50}).inserted_id
    lf2 = mdb.mkt_listings.insert_one({**base, "title": f"TEST_UI fixed2 {t}", "sale_modes": ["fixed"], "buy_now_price": 75}).inserted_id
    sa = login(a, PWD, "buyer")
    assert sa.post(f"{API}/market/listings/{la}/bid", json={"amount": 120}).status_code == 200
    o1 = sa.post(f"{API}/market/listings/{lf}/buy").json()["id"]
    o2 = sa.post(f"{API}/market/listings/{lf2}/buy").json()["id"]
    mdb.mkt_orders.update_one({"_id": ObjectId(o1)}, {"$set": {"status": "paid", "paid_at": now().isoformat(), "delivery_status": "awaiting_dispatch"}})
    v = requests.Session()
    vr = v.post(f"{API}/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
    v.headers["X-CSRF-Token"] = vr.json().get("csrf_token", "")
    r = v.post(f"{API}/market/orders/{o1}/delivery", json={"status": "dispatched", "note": "AWB <img src=x onerror=\"window.__xss=1\">"})
    assert r.status_code == 200, r.text
    json.dump({"tag": t, "a": a, "p": p, "verify_token": tok, "listings": [str(x) for x in (la, lf, lf2)], "o1": o1, "o2": o2}, open(F, "w"))
    print(json.load(open(F)))


def clean():
    d = json.load(open(F))
    for e in [d["a"], d["p"]] + [x["email"] for x in mdb.buyer_team_requests.find({"invited_by": d["a"]})]:
        for u in mdb.admin_users.find({"email": e, "roles": "buyer"}):
            mdb.notifications.delete_many({"user_id": str(u["_id"])})
            mdb.admin_users.delete_one({"_id": u["_id"]})
        for a in mdb.buyer_applications.find({"email": e}):
            if a.get("tenant_code"):
                mdb.tenants.delete_one({"code": a["tenant_code"], "source": "buyer_application"})
            mdb.buyer_applications.delete_one({"_id": a["_id"]})
        mdb.buyer_team_requests.delete_many({"email": e})
        mdb.notifications.delete_many({"user_email": e})
    for lid in d["listings"]:
        lid = ObjectId(lid)
        mdb.mkt_bids.delete_many({"listing_id": lid})
        mdb.mkt_orders.delete_many({"listing_id": lid})
        mdb.mkt_listings.delete_one({"_id": lid})
    print("cleaned")


if __name__ == "__main__":
    {"create": create, "clean": clean}[sys.argv[1]]()
