# v63: WhatsApp (not-connected) wiring + Instagram/WhatsApp website links + vendor opt-in.
import asyncio
import os
import sys
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
DEFAULTS = {"linkedin": "https://www.linkedin.com/feed/update/urn:li:activity:7521796802216611840/",
            "facebook": "https://www.facebook.com/profile.php?id=61596254811635", "instagram": "", "whatsapp": ""}
SOC, PUB = f"{BASE_URL}/api/v1/marketing/site-social", f"{BASE_URL}/api/v1/site/social"
WA = f"{BASE_URL}/api/v1/admin/whatsapp"
TEST_WA = ["999000111222", "999000111333", "999000111444"]


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
        pytest.skip(f"vendor login failed {r.status_code}")
    c = r.json().get("csrf_token")
    if c:
        s.headers.update({"X-CSRF-Token": c})
    return s


def _cleanup():
    DB.site_settings.update_one({"_id": "social"}, {"$set": DEFAULTS}, upsert=True)
    DB.mkt_settings.delete_one({"_id": "whatsapp"})
    DB.wa_threads.delete_many({"wa_id": {"$in": TEST_WA}})
    DB.wa_messages.delete_many({"wa_id": {"$in": TEST_WA}})
    DB.assistant_sessions.delete_many({"session_id": {"$in": [f"wa:{w}" for w in TEST_WA]}})
    DB.vendors.update_one({"email": "testvendor@pmcmanagers.com"},
                          {"$set": {"wa_opt_in": False, "wa_number": None},
                           "$unset": {"wa_opt_in_at": "", "wa_opt_in_source": "", "wa_opt_out_at": ""}})


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    _cleanup()
    yield
    _cleanup()


# ---- website links ----
class TestSocial:
    def test_public_has_new_keys(self):
        d = requests.get(PUB).json()
        assert set(d) >= {"linkedin", "facebook", "instagram", "whatsapp"}
        assert d["instagram"] == "" and d["whatsapp"] == ""

    def test_save_instagram_whatsapp_normalised(self, admin):
        r = admin.put(SOC, json={**DEFAULTS, "instagram": "https://www.instagram.com/TEST_pmc", "whatsapp": "+44 7700 900123"})
        assert r.status_code == 200, r.text
        assert r.json()["whatsapp"] == "447700900123"
        d = requests.get(PUB).json()
        assert d["instagram"] == "https://www.instagram.com/TEST_pmc" and d["whatsapp"] == "447700900123"
        assert d["linkedin"] == DEFAULTS["linkedin"]

    @pytest.mark.parametrize("bad", ["1234567", "1234567890123456", "44abc77009", "wa.me/447700"])
    def test_bad_whatsapp_422(self, admin, bad):
        assert admin.put(SOC, json={**DEFAULTS, "whatsapp": bad}).status_code == 422

    def test_bad_instagram_422(self, admin):
        assert admin.put(SOC, json={**DEFAULTS, "instagram": "http://instagram.com/x"}).status_code == 422

    def test_anon_rejected(self):
        assert requests.put(SOC, json=DEFAULTS).status_code in (401, 403)


# ---- admin whatsapp ----
class TestAdminWa:
    def test_status_not_connected(self, admin):
        d = admin.get(f"{WA}/status").json()
        assert d["configured"] is False
        assert d["webhook_url"].endswith("/api/v1/whatsapp/webhook")
        assert d["settings"] == {"tender_alerts": True, "payment_msgs": True, "ai_autoreply": True, "template_lang": "en"}

    def test_settings_persist(self, admin):
        r = admin.put(f"{WA}/settings", json={"tender_alerts": False, "payment_msgs": True, "ai_autoreply": False, "template_lang": "en_GB"})
        assert r.status_code == 200 and r.json()["tender_alerts"] is False
        d = admin.get(f"{WA}/status").json()["settings"]
        assert d["tender_alerts"] is False and d["ai_autoreply"] is False and d["template_lang"] == "en_GB"
        assert admin.put(f"{WA}/settings", json={"template_lang": "english"}).status_code == 422

    def test_settings_requires_csrf(self, admin):
        s = requests.Session(); s.cookies = admin.cookies
        assert s.put(f"{WA}/settings", json={}).status_code in (401, 403)

    def test_test_send(self, admin):
        assert admin.post(f"{WA}/test", json={"number": "12"}).status_code == 422
        r = admin.post(f"{WA}/test", json={"number": "+44 7700 900123"})
        assert r.status_code == 424 and "not connected" in r.json()["detail"].lower()

    def test_threads_404_and_list(self, admin):
        assert admin.get(f"{WA}/threads").status_code == 200
        assert admin.get(f"{WA}/threads/{TEST_WA[2]}").status_code == 404

    def test_vendor_cannot_access_admin(self, vendor):
        assert vendor.get(f"{WA}/status").status_code in (401, 403)


# ---- webhook ----
class TestWebhook:
    def test_verify_403(self):
        u = f"{BASE_URL}/api/v1/whatsapp/webhook"
        assert requests.get(u).status_code == 403
        assert requests.get(u, params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"}).status_code == 403
        assert requests.get(u, params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "1"}).status_code == 403

    def test_post_401(self):
        u = f"{BASE_URL}/api/v1/whatsapp/webhook"
        assert requests.post(u, json={"entry": []}).status_code == 401
        assert requests.post(u, json={"entry": []}, headers={"X-Hub-Signature-256": "sha256=abc"}).status_code == 401

    def test_doc_404(self):
        assert requests.get(f"{BASE_URL}/api/v1/whatsapp/doc/nope.pdf").status_code == 404


# ---- inbound processing (direct) ----
def _payload(wa_id, wamid, text, name="TEST User"):
    return {"entry": [{"changes": [{"value": {"contacts": [{"wa_id": wa_id, "profile": {"name": name}}],
            "messages": [{"from": wa_id, "id": wamid, "type": "text", "text": {"body": text}}]}}]}]}


def _run(coro):
    sys.path.insert(0, "/app/backend")
    os.chdir("/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa
    import db as dbmod
    from routers import whatsapp as w

    async def go():
        # fresh motor client bound to this loop
        cl = AsyncIOMotorClient(ENV["MONGO_URL"].strip('"'))
        orig = w.db
        w.db = cl[ENV["DB_NAME"].strip('"')]
        try:
            return await coro(w)
        finally:
            w.db = orig
    return asyncio.run(go())


class TestInbound:
    def test_inbound_creates_and_dedupes(self, admin):
        DB.mkt_settings.update_one({"_id": "whatsapp"}, {"$set": {"ai_autoreply": False}}, upsert=True)
        p = _payload(TEST_WA[0], "wamid.TEST_1", "Hello PMC")
        _run(lambda w: w._process(p))
        _run(lambda w: w._process(p))
        assert DB.wa_messages.count_documents({"wamid": "wamid.TEST_1"}) == 1
        t = DB.wa_threads.find_one({"wa_id": TEST_WA[0]})
        assert t and t["unread"] == 1 and t["name"] == "TEST User" and t["last_text"] == "Hello PMC"
        # admin threads API
        items = admin.get(f"{WA}/threads").json()["items"]
        assert any(i["wa_id"] == TEST_WA[0] for i in items)
        d = admin.get(f"{WA}/threads/{TEST_WA[0]}").json()
        assert d["window_open"] is True and len(d["messages"]) == 1 and d["messages"][0]["direction"] == "in"
        assert "_id" not in d["thread"]
        assert DB.wa_threads.find_one({"wa_id": TEST_WA[0]})["unread"] == 0
        # window open but not configured -> 424
        assert admin.post(f"{WA}/threads/{TEST_WA[0]}/reply", json={"text": "hi"}).status_code == 424
        assert admin.post(f"{WA}/threads/{TEST_WA[0]}/reply", json={"text": ""}).status_code == 422

    def test_reply_409_window_closed(self, admin):
        old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        DB.wa_threads.update_one({"wa_id": TEST_WA[1]}, {"$set": {"last_inbound_at": old, "last_at": old, "unread": 0}}, upsert=True)
        assert admin.post(f"{WA}/threads/{TEST_WA[1]}/reply", json={"text": "hi"}).status_code == 409
        assert admin.get(f"{WA}/threads/{TEST_WA[1]}").json()["window_open"] is False
        assert admin.post(f"{WA}/threads/{TEST_WA[2]}/reply", json={"text": "hi"}).status_code == 409

    def test_stop_opts_out_vendor(self):
        DB.vendors.update_one({"email": "testvendor@pmcmanagers.com"}, {"$set": {"wa_opt_in": True, "wa_number": TEST_WA[1]}})
        _run(lambda w: w._process(_payload(TEST_WA[1], "wamid.TEST_STOP", "STOP")))
        v = DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
        assert v["wa_opt_in"] is False and v.get("wa_opt_out_at")
        t = DB.wa_threads.find_one({"wa_id": TEST_WA[1]})
        assert t["vendor_ref"] == v.get("vendor_ref")
        # no outbound record since not configured
        assert DB.wa_messages.count_documents({"wa_id": TEST_WA[1], "direction": "out"}) == 0

    def test_status_update_and_media(self):
        _run(lambda w: w._process({"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.none", "status": "read"}],
            "messages": [{"from": TEST_WA[2], "id": "wamid.TEST_IMG", "type": "image"}]}}]}]}))
        m = DB.wa_messages.find_one({"wamid": "wamid.TEST_IMG"})
        assert m and m["text"] == "[image]"

    def test_outbound_hooks_noop(self):
        assert _run(lambda w: w.notify_tender("TEST-NOTICE")) == 0
        assert _run(lambda w: w.notify_payment_reminder("VEN-TEST01", "x", "GBP 1", "https://x")) is False
        assert _run(lambda w: w.notify_receipt("000000000000000000000000", {"receipt_no": "TEST"})) is False
        assert _run(lambda w: w._send(TEST_WA[2], {}, "text", "x")) is False


# ---- vendor opt-in ----
class TestVendorOptIn:
    def test_get(self, vendor):
        d = vendor.get(f"{BASE_URL}/api/v1/vendor/whatsapp").json()
        assert d["opt_in"] is False and d["available"] is False

    def test_opt_in_invalid(self, vendor):
        u = f"{BASE_URL}/api/v1/vendor/whatsapp"
        assert vendor.put(u, json={"number": "", "opt_in": True}).status_code == 422
        assert vendor.put(u, json={"number": "123", "opt_in": True}).status_code == 422

    def test_opt_in_out(self, vendor):
        u = f"{BASE_URL}/api/v1/vendor/whatsapp"
        r = vendor.put(u, json={"number": "+44 7700 900999", "opt_in": True})
        assert r.status_code == 200 and r.json() == {"number": "447700900999", "opt_in": True}
        d = vendor.get(u).json()
        assert d["opt_in"] is True and d["number"] == "447700900999"
        v = DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
        assert v["wa_opt_in_source"] == "vendor_portal"
        r = vendor.put(u, json={"number": "447700900999", "opt_in": False})
        assert r.json()["opt_in"] is False
        assert vendor.get(u).json()["opt_in"] is False

    def test_anon(self):
        assert requests.get(f"{BASE_URL}/api/v1/vendor/whatsapp").status_code == 401
