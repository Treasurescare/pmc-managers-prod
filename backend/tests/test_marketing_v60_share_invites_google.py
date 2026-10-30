# v60: social share cards (PNG + OG page), buyer invites (send/list/click/joined), Google sign-in exchange guards.
# Creates a TEST_ notice via API (publishes it) and deletes it + TEST_ invites/contacts at module end.
import io
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
FRONTEND_URL = ENV["FRONTEND_URL"].strip('"').rstrip("/")
TAG = uuid.uuid4().hex[:6].lower()
INV = f"{BASE_URL}/api/v1/marketing/buyer-invites"
EMAIL = f"test_bi_{TAG}@pmcmanagers.com"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com",
               "password": "Admin@12345", "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s


@pytest.fixture(scope="module")
def notice(admin):
    deadline = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00Z")
    title = f"TEST_{TAG} Supply of <b>pumps</b> & 'valves' \"quoted\""
    r = admin.post(f"{BASE_URL}/api/v1/notices", json={
        "title": title, "description": "TEST notice for share card testing", "category": "Medical Equipment",
        "delivery_country": "GB", "submission_deadline": deadline, "budget_amount": 1000, "is_published": False})
    assert r.status_code == 200, r.text
    ref = r.json()["notice_ref"]
    yield {"ref": ref, "title": title, "admin": admin}
    DB.notices.delete_many({"notice_ref": ref})
    DB.mkt_alert_log.delete_many({"notice_ref": ref})


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    DB.mkt_buyer_invites.delete_many({"email": {"$regex": "^test_", "$options": "i"}})
    DB.mkt_contacts.delete_many({"email": {"$regex": f"^test_.*{TAG}", "$options": "i"}})
    DB.admin_users.delete_many({"email": {"$regex": f"^test_.*{TAG}", "$options": "i"}})
    DB.notices.delete_many({"title": {"$regex": f"^TEST_{TAG}"}})


# --- share cards ---
class TestShare:
    def test_unpublished_404(self, notice):
        assert requests.get(f"{BASE_URL}/api/v1/share/notice/{notice['ref']}.png").status_code == 404
        assert requests.get(f"{BASE_URL}/api/v1/share/notice/{notice['ref']}").status_code == 404

    def test_unknown_404(self):
        assert requests.get(f"{BASE_URL}/api/v1/share/notice/NOPE-{TAG}.png").status_code == 404
        assert requests.get(f"{BASE_URL}/api/v1/share/notice/NOPE-{TAG}").status_code == 404

    def test_publish_then_png(self, notice):
        r = notice["admin"].post(f"{BASE_URL}/api/v1/notices/{notice['ref']}/publish")
        assert r.status_code == 200, r.text
        r = requests.get(f"{BASE_URL}/api/v1/share/notice/{notice['ref']}.png")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        from PIL import Image
        im = Image.open(io.BytesIO(r.content))
        assert im.size == (1200, 630) and im.format == "PNG"

    def test_share_page_og(self, notice):
        r = requests.get(f"{BASE_URL}/api/v1/share/notice/{notice['ref']}")
        assert r.status_code == 200 and "text/html" in r.headers["content-type"]
        t = r.text
        assert "og:title" in t and "og:description" in t and "summary_large_image" in t
        img = re.search(r"property='og:image' content='([^']+)'", t).group(1)
        assert img.startswith("http") and img.endswith(f"/api/v1/share/notice/{notice['ref']}.png")
        assert f"0;url={FRONTEND_URL}/notices/{notice['ref']}" in t
        # escaping: raw tags/quotes must not appear
        assert "<b>pumps</b>" not in t and "&lt;b&gt;pumps&lt;/b&gt;" in t
        assert "'valves'" not in t and "&#x27;valves&#x27;" in t
        # og:image resolvable
        assert requests.get(img).status_code == 200

    def test_public_notice_detail_ok(self, notice):
        r = requests.get(f"{BASE_URL}/api/v1/notices/{notice['ref']}")
        assert r.status_code == 200 and r.json()["notice_ref"] == notice["ref"]


# --- buyer invites ---
class TestInvites:
    def test_requires_admin(self):
        assert requests.get(INV).status_code in (401, 403)
        assert requests.post(INV, json={"organisation": "TEST_x", "email": EMAIL}).status_code in (401, 403)

    def test_vendor_forbidden(self):
        v = requests.Session()
        r = v.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
        if r.status_code != 200:
            pytest.skip("vendor login failed")
        csrf = r.json().get("csrf_token")
        if csrf:
            v.headers.update({"X-CSRF-Token": csrf})
        assert v.get(INV).status_code in (401, 403)
        assert v.post(INV, json={"organisation": "TEST_x", "email": EMAIL}).status_code in (401, 403)

    def test_csrf_required(self, admin):
        s = requests.Session()
        s.cookies.update(admin.cookies)
        r = s.post(INV, json={"organisation": f"TEST_Org {TAG}", "email": EMAIL})
        assert r.status_code in (401, 403), r.status_code

    def test_validation(self, admin):
        assert admin.post(INV, json={"organisation": "X", "email": EMAIL}).status_code == 422
        assert admin.post(INV, json={"organisation": "TEST_Org", "email": "bad"}).status_code == 422
        assert admin.post(INV, json={"organisation": "TEST_Org", "email": EMAIL, "country": "GBR"}).status_code == 422

    def test_send_and_list(self, admin):
        r = admin.post(INV, json={"organisation": f"TEST_Org <i>{TAG}</i>", "contact_name": "TEST Buyer",
                                   "email": EMAIL.upper(), "country": "gb", "note": "Line1\nLine2"})
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["email_sent"], bool)
        items = admin.get(INV).json()["items"]
        row = next(i for i in items if i["email"] == EMAIL)
        assert row["country"] == "GB" and row["status"] in ("sent", "failed")
        assert "token" not in row and "_id" not in row and isinstance(row["id"], str)
        doc = DB.mkt_buyer_invites.find_one({"email": EMAIL})
        assert doc["invited_by"] == "adminsupport@pmcmanagers.com"

    def test_click_redirect_and_status(self, admin):
        tok = DB.mkt_buyer_invites.find_one({"email": EMAIL})["token"]
        r = requests.get(f"{INV}/go/{tok}", allow_redirects=False)
        assert r.status_code in (302, 307) and r.headers["location"] == f"{FRONTEND_URL}/buyers"
        row = next(i for i in admin.get(INV).json()["items"] if i["email"] == EMAIL)
        assert row["status"] == "clicked"
        first = DB.mkt_buyer_invites.find_one({"email": EMAIL})["clicked_at"]
        requests.get(f"{INV}/go/{tok}", allow_redirects=False)
        assert DB.mkt_buyer_invites.find_one({"email": EMAIL})["clicked_at"] == first

    def test_bad_token_redirects(self):
        r = requests.get(f"{INV}/go/bogus{TAG}", allow_redirects=False)
        assert r.status_code in (302, 307) and r.headers["location"].endswith("/buyers")

    def test_mark_joined(self, admin):
        iid = next(i for i in admin.get(INV).json()["items"] if i["email"] == EMAIL)["id"]
        r = admin.post(f"{INV}/{iid}/joined")
        assert r.status_code == 200 and r.json()["ok"] is True
        row = next(i for i in admin.get(INV).json()["items"] if i["id"] == iid)
        assert row["status"] == "joined" and row.get("joined_at")

    def test_auto_joined_via_admin_user(self, admin):
        e = f"test_bi2_{TAG}@pmcmanagers.com"
        assert admin.post(INV, json={"organisation": f"TEST_Org2 {TAG}", "email": e}).status_code == 200
        DB.admin_users.insert_one({"email": e, "roles": ["support"], "is_active": True, "name": "TEST"})
        row = next(i for i in admin.get(INV).json()["items"] if i["email"] == e)
        assert row["status"] == "joined"

    def test_unsubscribed_409(self, admin):
        e = f"test_unsub_{TAG}@pmcmanagers.com"
        DB.mkt_contacts.insert_one({"email": e, "unsubscribed": True, "audience": "buyer"})
        r = admin.post(INV, json={"organisation": f"TEST_Org3 {TAG}", "email": e.upper()})
        assert r.status_code == 409
        assert DB.mkt_buyer_invites.find_one({"email": e}) is None

    def test_mark_joined_bad_id(self, admin):
        r = admin.post(f"{INV}/notanid/joined")
        assert r.status_code in (400, 404, 422), r.status_code


# --- google exchange ---
class TestGoogle:
    U = f"{BASE_URL}/api/v1/auth/google/exchange"

    def test_invalid_session_401(self):
        r = requests.post(self.U, json={"session_id": f"bogus_session_{TAG}", "portal": "supplier"})
        assert r.status_code == 401, r.text
        assert "detail" in r.json()

    def test_invalid_portal_422(self):
        assert requests.post(self.U, json={"session_id": f"bogus_session_{TAG}", "portal": "escrow"}).status_code == 422

    def test_short_session_422(self):
        assert requests.post(self.U, json={"session_id": "x", "portal": "staff"}).status_code == 422
