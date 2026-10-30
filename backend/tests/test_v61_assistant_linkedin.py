# v61: AI assistant chat, LinkedIn social-post approval queue, LinkedIn sign-in (disabled), Google exchange regression.
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

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
TAG = uuid.uuid4().hex[:6].lower()
CHAT = f"{BASE_URL}/api/v1/assistant/chat"
SP = f"{BASE_URL}/api/v1/marketing/social-posts"


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
def vendor():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    refs = [n["notice_ref"] for n in DB.notices.find({"title": {"$regex": f"^TEST_{TAG}"}}, {"notice_ref": 1})]
    DB.mkt_social_posts.delete_many({"notice_ref": {"$in": refs}})
    DB.mkt_alert_log.delete_many({"notice_ref": {"$in": refs}})
    DB.notices.delete_many({"title": {"$regex": f"^TEST_{TAG}"}})
    DB.assistant_sessions.delete_many({"session_id": {"$regex": "^TEST_"}})


def _mk_notice(admin, suffix):
    dl = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00Z")
    r = admin.post(f"{BASE_URL}/api/v1/notices", json={
        "title": f"TEST_{TAG} {suffix}", "description": "TEST social post notice", "category": "Medical Equipment",
        "delivery_country": "GB", "submission_deadline": dl, "budget_amount": 1000, "is_published": False})
    assert r.status_code == 200, r.text
    ref = r.json()["notice_ref"]
    assert admin.post(f"{BASE_URL}/api/v1/notices/{ref}/publish").status_code == 200
    for _ in range(20):
        if DB.mkt_social_posts.find_one({"notice_ref": ref}):
            break
        time.sleep(0.5)
    return ref


# --- AI assistant ---
class TestAssistant:
    def test_validation_422(self):
        assert requests.post(CHAT, json={"session_id": f"TEST_{TAG}_v", "message": ""}).status_code == 422
        assert requests.post(CHAT, json={"session_id": f"TEST_{TAG}_v", "message": "x" * 1001}).status_code == 422
        assert requests.post(CHAT, json={"session_id": "short", "message": "hi"}).status_code == 422

    def test_chat_and_multiturn(self):
        sid = f"TEST_{TAG}_anon"
        r = requests.post(CHAT, json={"session_id": sid, "message": "Is the first business category free?"}, timeout=60)
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["reply"], str) and len(r.json()["reply"]) > 5
        r2 = requests.post(CHAT, json={"session_id": sid, "message": "and a second category?"}, timeout=60)
        assert r2.status_code == 200, r2.text
        print("REPLY1:", r.json()["reply"][:300], "\nREPLY2:", r2.json()["reply"][:300])
        s = DB.assistant_sessions.find_one({"session_id": sid})
        assert len(s["messages"]) == 4 and s["vendor_id"] is None
        assert any(w in r2.json()["reply"].lower() for w in ["fee", "paid", "charge", "cost"])

    def test_vendor_personalised_and_isolated(self, vendor):
        sid = f"TEST_{TAG}_ven"
        r = vendor.post(CHAT, json={"session_id": sid, "message": "What is my company name and vendor reference? Also remember the code word ZEBRA77."}, timeout=60)
        assert r.status_code == 200, r.text
        rep = r.json()["reply"]
        print("VENDOR REPLY:", rep[:300])
        assert "VEN-TEST01" in rep or "Test Supplier" in rep
        s = DB.assistant_sessions.find_one({"session_id": sid})
        assert s["vendor_id"]
        # anonymous re-use of vendor's session id must NOT see vendor history
        r2 = requests.post(CHAT, json={"session_id": sid, "message": "What code word did I tell you earlier, and what is my company name?"}, timeout=60)
        assert r2.status_code == 409
        s = DB.assistant_sessions.find_one({"session_id": sid})
        assert s["vendor_id"] and len(s["messages"]) >= 2


# --- LinkedIn social posts queue ---
class TestSocialPosts:
    def test_non_admin_blocked(self, vendor):
        assert requests.get(SP).status_code in (401, 403)
        assert vendor.get(SP).status_code in (401, 403)
        assert requests.get(f"{BASE_URL}/api/v1/marketing/linkedin/connect").status_code in (401, 403)

    def test_publish_queues_one_post(self, admin):
        ref = _mk_notice(admin, "Supply of pumps")
        assert DB.mkt_social_posts.count_documents({"notice_ref": ref}) == 1
        # re-queue is idempotent
        from_mod = admin.post(f"{BASE_URL}/api/v1/notices/{ref}/publish")
        assert from_mod.status_code == 404
        assert DB.mkt_social_posts.count_documents({"notice_ref": ref}) == 1
        d = admin.get(SP).json()
        assert d["linkedin"]["app_configured"] is False and d["linkedin"]["connected"] is False
        assert "org_configured" in d["linkedin"]
        it = next(i for i in d["items"] if i["notice_ref"] == ref)
        assert it["status"] == "pending" and it["share_url"].endswith(f"/api/v1/share/notice/{ref}")
        assert "_id" not in it and isinstance(it["id"], str)
        assert "Medical Equipment" in it["text"] and "TEST_" in it["text"]
        TestSocialPosts.pid = it["id"]
        TestSocialPosts.ref = ref

    def test_edit_pending(self, admin):
        r = admin.put(f"{SP}/{self.pid}", json={"text": "TEST edited text #tenders"})
        assert r.status_code == 200
        assert DB.mkt_social_posts.find_one({"notice_ref": self.ref})["text"] == "TEST edited text #tenders"
        assert admin.put(f"{SP}/{self.pid}", json={"text": "abc"}).status_code == 422

    def test_csrf_required(self, admin):
        r = requests.post(f"{SP}/{self.pid}/reject", cookies=admin.cookies)
        assert r.status_code in (401, 403)

    def test_approve_not_connected_424(self, admin):
        r = admin.post(f"{SP}/{self.pid}/approve")
        assert r.status_code == 424, r.text
        assert "Connect your LinkedIn company page first" in r.json()["detail"]

    def test_mark_posted_then_approve_409_and_edit_locked(self, admin):
        assert admin.post(f"{SP}/{self.pid}/mark-posted").status_code == 200
        p = DB.mkt_social_posts.find_one({"notice_ref": self.ref})
        assert p["status"] == "posted" and p["posted_manually"] is True
        assert admin.post(f"{SP}/{self.pid}/approve").status_code == 409
        admin.put(f"{SP}/{self.pid}", json={"text": "TEST should not apply"})
        assert DB.mkt_social_posts.find_one({"notice_ref": self.ref})["text"] == "TEST edited text #tenders"

    def test_reject(self, admin):
        ref = _mk_notice(admin, "Supply of valves")
        pid = str(DB.mkt_social_posts.find_one({"notice_ref": ref})["_id"])
        assert admin.post(f"{SP}/{pid}/reject").status_code == 200
        assert DB.mkt_social_posts.find_one({"notice_ref": ref})["status"] == "rejected"
        assert admin.post(f"{SP}/{pid}/approve").status_code == 409

    def test_unknown_id(self, admin):
        r = admin.post(f"{SP}/000000000000000000000000/approve")
        assert r.status_code in (404, 409)


# --- LinkedIn sign-in (keys absent) ---
class TestLinkedInSignIn:
    def test_status_disabled(self):
        r = requests.get(f"{BASE_URL}/api/v1/auth/linkedin/status")
        assert r.status_code == 200 and r.json() == {"signin_enabled": False}

    def test_start_redirects_with_error(self):
        r = requests.get(f"{BASE_URL}/api/v1/auth/linkedin/start?portal=supplier", allow_redirects=False)
        assert r.status_code in (302, 307)
        loc = r.headers["location"]
        assert "/login?li_error=" in loc and "not set up" in unquote(loc)

    def test_start_bad_portal(self):
        assert requests.get(f"{BASE_URL}/api/v1/auth/linkedin/start?portal=evil", allow_redirects=False).status_code == 422

    def test_callback_bad_state(self):
        r = requests.get(f"{BASE_URL}/api/v1/auth/linkedin/callback?code=x&state=bogus", allow_redirects=False)
        assert r.status_code in (302, 307) and "/login?li_error=" in r.headers["location"]
        r = requests.get(f"{BASE_URL}/api/v1/auth/linkedin/callback?error=user_cancelled", allow_redirects=False)
        assert "/login?li_error=" in r.headers["location"]

    def test_connect_admin(self, admin):
        r = admin.get(f"{BASE_URL}/api/v1/marketing/linkedin/connect")
        assert r.status_code == 424


# --- Google regression ---
class TestGoogleRegression:
    def test_invalid_session_401(self):
        r = requests.post(f"{BASE_URL}/api/v1/auth/google/exchange", json={"session_id": "invalid_session_123", "portal": "supplier"})
        assert r.status_code == 401

    def test_bad_portal_422(self):
        r = requests.post(f"{BASE_URL}/api/v1/auth/google/exchange", json={"session_id": "invalid_session_123", "portal": "evil"})
        assert r.status_code == 422
