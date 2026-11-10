# v189 — Buyer sign-in invites: approve -> auto sign-in, resend/add-user/409s, set-password, buyer login + RBAC
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
mdb = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]

CREATED = {"apps": [], "tenants": [], "users": []}


def _login(email, pwd, role):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": pwd, "active_role": role})
    if r.status_code == 200:
        s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s, r


def _insert_app(status="pending", **extra):
    tag = secrets.token_hex(3).upper()
    doc = {"org_name": f"TEST_Buyer Org {tag}", "org_type": "private", "country": "IN", "contact_name": "TEST Contact",
           "email": f"test_buyer_{tag.lower()}@example.com", "status": status, "ip": "test",
           "created_at": datetime.now(timezone.utc).isoformat(), **extra}
    _id = mdb.buyer_applications.insert_one(doc).inserted_id
    CREATED["apps"].append(_id)
    return str(_id), doc


def _mint(user):
    return jwt.encode({"sub": str(user["_id"]), "email": user["email"], "portal": "buyer", "jti": user["pwd_reset_jti"],
                       "type": "pwd_reset", "iat": datetime.now(timezone.utc),
                       "exp": datetime.now(timezone.utc) + timedelta(days=7)}, BE["JWT_SECRET"], algorithm="HS256")


@pytest.fixture(scope="module")
def admin():
    s, r = _login(*ADMIN, "admin")
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    for a in CREATED["apps"]:
        d = mdb.buyer_applications.find_one({"_id": a})
        if d and d.get("tenant_code"):
            CREATED["tenants"].append(d["tenant_code"])
        mdb.buyer_applications.delete_one({"_id": a})
    for code in set(CREATED["tenants"]):
        mdb.tenants.delete_one({"code": code, "source": "buyer_application"})
        for u in mdb.admin_users.find({"tenant_id": code, "source": "buyer_application"}, {"_id": 1}):
            CREATED["users"].append(u["_id"])
    for u in set(CREATED["users"]):
        mdb.admin_users.delete_one({"_id": u, "source": "buyer_application"})


class TestBuyerSignin:
    state = {}

    def test_approve_creates_signin(self, admin):
        aid, doc = _insert_app()
        r = admin.post(f"{API}/buyer-applications/{aid}/decision", json={"action": "approve", "tier": "Standard"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "approved" and d["signin_status"] == "sent" and d["signin_email"] == doc["email"]
        code = d["tenant_code"]
        CREATED["tenants"].append(code)
        u = mdb.admin_users.find_one({"email": doc["email"]})
        assert u and u["roles"] == ["buyer"] and u["tenant_id"] == code and u["must_change_password"] is True and u["pwd_reset_jti"]
        CREATED["users"].append(u["_id"])
        t = mdb.tenants.find_one({"code": code})
        assert t and t["source"] == "buyer_application"
        app = mdb.buyer_applications.find_one({"_id": ObjectId(aid)})
        assert app["signin_status"] == "sent" and app.get("signin_sent_at")
        self.state.update(aid=aid, email=doc["email"], code=code)

    def test_cannot_decide_twice(self, admin):
        r = admin.post(f"{API}/buyer-applications/{self.state['aid']}/decision", json={"action": "approve"})
        assert r.status_code == 409

    def test_set_password_and_buyer_login(self, admin):
        u = mdb.admin_users.find_one({"email": self.state["email"]})
        tok = _mint(u)
        v = requests.post(f"{API}/auth/password-reset/verify", json={"token": tok})
        assert v.status_code == 200 and v.json()["portal"] == "buyer"
        c = requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": "Buyer@12345"})
        assert c.status_code == 200, c.text
        u2 = mdb.admin_users.find_one({"_id": u["_id"]})
        assert u2["must_change_password"] is False and "pwd_reset_jti" not in u2
        # token one-time
        assert requests.post(f"{API}/auth/password-reset/confirm", json={"token": tok, "new_password": "Buyer@99999"}).status_code == 400
        s, r = _login(self.state["email"], "Buyer@12345", "buyer")
        assert r.status_code == 200 and r.json()["active_role"] == "buyer"
        w = s.get(f"{API}/market/whoami")
        assert w.json()["kind"] == "buyer"
        self.state["buyer"] = s

    def test_buyer_forbidden_on_admin(self):
        s = self.state["buyer"]
        assert s.get(f"{API}/buyer-applications").status_code == 403
        assert s.get(f"{API}/market/admin/settings").status_code == 403
        assert s.post(f"{API}/buyer-applications/{self.state['aid']}/signin", json={}).status_code == 403
        _, r = _login(self.state["email"], "Buyer@12345", "admin")
        assert r.status_code == 403

    def test_buyer_legacy_admin_login_is_not_admin(self):
        s = requests.Session()
        r = s.post(f"{API}/admin/auth/login", json={"email": self.state["email"], "password": "Buyer@12345"})
        print("legacy admin login:", r.status_code, r.text[:200])
        if r.status_code == 200:
            assert r.json()["role"] == "buyer"
            s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
            assert s.get(f"{API}/buyer-applications").status_code == 403

    def test_resend_rotates_jti(self, admin):
        old = mdb.admin_users.find_one({"email": self.state["email"]})
        r = admin.post(f"{API}/buyer-applications/{self.state['aid']}/signin", json={})
        assert r.status_code == 200 and r.json()["signin_status"] == "sent" and r.json()["signin_email"] == self.state["email"]
        new = mdb.admin_users.find_one({"email": self.state["email"]})
        assert new["pwd_reset_jti"] and new["pwd_reset_jti"] != old.get("pwd_reset_jti")
        assert new["roles"] == ["buyer"] and new["tenant_id"] == self.state["code"]
        assert mdb.admin_users.count_documents({"email": self.state["email"]}) == 1
        # existing password still works
        assert _login(self.state["email"], "Buyer@12345", "buyer")[1].status_code == 200

    def test_invite_other_user(self, admin):
        other = f"test_other_{secrets.token_hex(3)}@example.com"
        r = admin.post(f"{API}/buyer-applications/{self.state['aid']}/signin", json={"email": other.upper(), "name": "TEST Other"})
        assert r.status_code == 200 and r.json()["signin_email"] == other
        u = mdb.admin_users.find_one({"email": other})
        assert u and u["tenant_id"] == self.state["code"] and u["roles"] == ["buyer"] and u["name"] == "TEST Other"
        CREATED["users"].append(u["_id"])
        app = mdb.buyer_applications.find_one({"_id": ObjectId(self.state["aid"])})
        assert app["signin_email"] == self.state["email"]  # primary unchanged

    def test_email_in_use_409(self, admin):
        before = mdb.admin_users.find_one({"email": ADMIN[0]})
        r = admin.post(f"{API}/buyer-applications/{self.state['aid']}/signin", json={"email": ADMIN[0]})
        assert r.status_code == 409
        after = mdb.admin_users.find_one({"email": ADMIN[0]})
        assert before.get("roles") == after.get("roles") and before.get("tenant_id") == after.get("tenant_id")
        assert before.get("pwd_reset_jti") == after.get("pwd_reset_jti")

    def test_legacy_approval_without_user(self, admin):
        code = "TESTOLD" + secrets.token_hex(2).upper()
        mdb.tenants.insert_one({"code": code, "name": "TEST_Old", "source": "buyer_application", "is_active": True})
        CREATED["tenants"].append(code)
        aid, doc = _insert_app(status="approved", tenant_code=code)
        assert mdb.admin_users.find_one({"email": doc["email"]}) is None
        r = admin.post(f"{API}/buyer-applications/{aid}/signin", json={})
        assert r.status_code == 200 and r.json()["signin_status"] == "sent"
        u = mdb.admin_users.find_one({"email": doc["email"]})
        assert u and u["tenant_id"] == code and u["must_change_password"] is True
        CREATED["users"].append(u["_id"])

    def test_pending_rejected_invalid_409(self, admin):
        aid, _ = _insert_app()
        assert admin.post(f"{API}/buyer-applications/{aid}/signin", json={}).status_code == 409
        r = admin.post(f"{API}/buyer-applications/{aid}/decision", json={"action": "reject", "notes": "TEST no"})
        assert r.status_code == 200 and r.json()["status"] == "rejected" and "signin_status" not in r.json()
        assert admin.post(f"{API}/buyer-applications/{aid}/signin", json={}).status_code == 409
        assert admin.post(f"{API}/buyer-applications/notanid/signin", json={}).status_code == 409
        assert admin.post(f"{API}/buyer-applications/{aid}/signin", json={"email": "bad"}).status_code == 422

    def test_unauth(self):
        assert requests.post(f"{API}/buyer-applications/{self.state['aid']}/signin", json={}).status_code in (401, 403)
        assert requests.get(f"{API}/buyer-applications").status_code in (401, 403)

    def test_approve_with_email_in_use(self, admin):
        aid, _ = _insert_app()
        mdb.buyer_applications.update_one({"_id": ObjectId(aid)}, {"$set": {"email": ADMIN[0]}})
        before = mdb.admin_users.find_one({"email": ADMIN[0]})
        r = admin.post(f"{API}/buyer-applications/{aid}/decision", json={"action": "approve"})
        assert r.status_code == 200 and r.json()["signin_status"] == "email_in_use"
        CREATED["tenants"].append(r.json()["tenant_code"])
        after = mdb.admin_users.find_one({"email": ADMIN[0]})
        assert before.get("roles") == after.get("roles") and before.get("pwd_reset_jti") == after.get("pwd_reset_jti")
        # then invite a different email
        other = f"test_alt_{secrets.token_hex(3)}@example.com"
        r2 = admin.post(f"{API}/buyer-applications/{aid}/signin", json={"email": other})
        assert r2.status_code == 200
        CREATED["users"].append(mdb.admin_users.find_one({"email": other})["_id"])
        app = mdb.buyer_applications.find_one({"_id": ObjectId(aid)})
        print("app signin_status after alt invite:", app.get("signin_status"), app.get("signin_email"))
