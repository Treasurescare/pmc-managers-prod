# v59 marketing: public website sign-up (double opt-in), confirm, alert mode, weekly digest + cron.
# All data TEST_-prefixed; cleaned up at module end. Settings restored to enabled=false, mode=instant.
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")
M = f"{BASE_URL}/api/v1/marketing"
TAG = uuid.uuid4().hex[:6].lower()
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
SECRET = ENV["WEBHOOK_CRON_SECRET"].strip('"')


def ip():
    return f"10.250.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


def sub(email, consent=True, ipaddr=None, **kw):
    body = {"email": email, "audience": "vendor", "country": "gb", "categories": [f"TEST_CAT_{TAG}"],
            "consent": consent, **kw}
    return requests.post(f"{M}/subscribe", json=body, headers={"X-Forwarded-For": ipaddr or ip()})


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com",
               "password": "Admin@12345", "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    DB.mkt_contacts.delete_many({"email": {"$regex": "^test_", "$options": "i"}})
    DB.cron_runs.delete_many({"run_id": {"$regex": "^TEST_"}})
    yield
    DB.mkt_contacts.delete_many({"email": {"$regex": "^test_", "$options": "i"}})
    DB.mkt_subscribe_hits.delete_many({"ip": {"$regex": "^10\\.250\\."}})
    DB.cron_runs.delete_many({"run_id": {"$regex": "^TEST_"}})
    DB.notices.delete_many({"notice_ref": {"$regex": "^TEST_"}})
    DB.mkt_alert_log.delete_many({"notice_ref": {"$regex": "^TEST_"}})
    DB.mkt_digest_log.delete_many({})
    DB.mkt_settings.update_one({"_id": "tender_alerts"},
                               {"$set": {"enabled": False, "mode": "instant", "include_uploaded": True}}, upsert=True)


# --- public subscribe ---
class TestSubscribe:
    def test_no_consent_422(self):
        r = sub(f"test_nc_{TAG}@example.com", consent=False)
        assert r.status_code == 422
        assert DB.mkt_contacts.find_one({"email": f"test_nc_{TAG}@example.com"}) is None

    def test_honeypot_stores_nothing(self):
        r = sub(f"test_bot_{TAG}@example.com", website="http://spam")
        assert r.status_code == 200 and r.json()["ok"] is True
        assert DB.mkt_contacts.find_one({"email": f"test_bot_{TAG}@example.com"}) is None

    def test_invalid_email_422(self):
        assert sub("not-an-email").status_code == 422

    def test_creates_pending_contact(self):
        e = f"TEST_new_{TAG}@example.com"
        r = sub(e)
        assert r.status_code == 200 and r.json()["ok"] is True
        c = DB.mkt_contacts.find_one({"email": e.lower()})
        assert c and c["source"] == "website" and c["consent"] is False
        assert isinstance(c.get("confirm_token"), str) and len(c["confirm_token"]) > 10
        assert c["pending_country"] == "GB" and c["pending_categories"] == [f"TEST_CAT_{TAG}"]

    def test_confirm_sets_consent(self, admin):
        e = f"test_new_{TAG}@example.com"
        before = admin.get(f"{M}/alerts").json()["website_subscribers"]
        tok = DB.mkt_contacts.find_one({"email": e})["confirm_token"]
        r = requests.get(f"{M}/confirm/{tok}")
        assert r.status_code == 200 and "subscribed" in r.text and "text/html" in r.headers["content-type"]
        c = DB.mkt_contacts.find_one({"email": e})
        assert c["consent"] is True and "confirm_token" not in c and "pending_categories" not in c
        assert c["country"] == "GB" and f"TEST_CAT_{TAG}" in c["categories"]
        assert admin.get(f"{M}/alerts").json()["website_subscribers"] == before + 1
        # re-use of token is invalid
        assert "no longer valid" in requests.get(f"{M}/confirm/{tok}").text

    def test_invalid_token(self):
        r = requests.get(f"{M}/confirm/bogus_{TAG}")
        assert r.status_code == 200 and "no longer valid" in r.text

    def test_existing_consented_unchanged(self):
        e = f"test_new_{TAG}@example.com"
        before = DB.mkt_contacts.find_one({"email": e})
        r = sub(e, categories=["Other"])
        assert r.status_code == 200
        after = DB.mkt_contacts.find_one({"email": e})
        assert "confirm_token" not in after and after["categories"] == before["categories"] and after["consent"] is True

    def test_unsubscribed_can_resubscribe(self):
        e = f"test_new_{TAG}@example.com"
        DB.mkt_contacts.update_one({"email": e}, {"$set": {"unsubscribed": True}})
        assert sub(e).status_code == 200
        tok = DB.mkt_contacts.find_one({"email": e})["confirm_token"]
        requests.get(f"{M}/confirm/{tok}")
        assert DB.mkt_contacts.find_one({"email": e})["unsubscribed"] is False

    def test_rate_limit_429(self):
        addr = ip()
        codes = [sub(f"test_rl{i}_{TAG}@example.com", ipaddr=addr).status_code for i in range(6)]
        assert codes[:5] == [200] * 5, codes
        assert codes[5] == 429


# --- admin alerts settings ---
class TestAlertsAdmin:
    def test_mode_persist(self, admin):
        r = admin.put(f"{M}/alerts", json={"enabled": False, "include_uploaded": True, "mode": "weekly"})
        assert r.status_code == 200
        assert admin.get(f"{M}/alerts").json()["mode"] == "weekly"
        assert admin.put(f"{M}/alerts", json={"enabled": False, "mode": "bad"}).status_code == 422
        admin.put(f"{M}/alerts", json={"enabled": False, "include_uploaded": True, "mode": "instant"})
        assert admin.get(f"{M}/alerts").json()["mode"] == "instant"

    def test_alerts_requires_admin(self):
        assert requests.get(f"{M}/alerts").status_code in (401, 403)
        assert requests.post(f"{M}/alerts/digest-now").status_code in (401, 403)

    def test_digest_now_logs(self, admin):
        import time
        r = admin.post(f"{M}/alerts/digest-now")
        assert r.status_code == 200 and r.json()["queued"] is True
        time.sleep(4)
        d = admin.get(f"{M}/alerts").json()["digests"]
        assert any("manual" in g["week"] for g in d), d


# --- cron endpoint ---
class TestCron:
    U = f"{BASE_URL}/api/v1/cron/marketing-weekly-digest"

    def test_unauth(self):
        assert requests.post(self.U).status_code == 401
        assert requests.post(self.U, headers={"Authorization": "Bearer wrong"}).status_code == 401

    def test_ok_and_duplicate(self):
        h = {"Authorization": f"Bearer {SECRET}", "X-Webhook-Id": f"TEST_run_{TAG}"}
        r = requests.post(self.U, headers=h)
        assert r.status_code == 200 and r.json()["ok"] is True and not r.json().get("duplicate")
        r2 = requests.post(self.U, headers=h)
        assert r2.status_code == 200 and r2.json().get("duplicate") is True


# --- in-process digest/instant logic (send_email patched; no real mails) ---
def test_digest_logic_inprocess():
    sys.path.insert(0, "/app/backend")
    os.chdir("/app/backend")
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    import routers.marketing as mk
    import routers.marketing_public as mp
    sent = []

    async def fake_send(to, subject, html, *a, **k):
        sent.append((to, subject, html))
        return True

    async def nosleep(*a, **k):
        return None

    mp.send_email = fake_send
    mk.send_email = fake_send
    real_sleep = asyncio.sleep
    mp.asyncio.sleep = nosleep  # same module object as asyncio; restored in finally

    X, Y = f"TEST_X_{TAG}", f"TEST_Y_{TAG}"
    now = datetime.now(timezone.utc).isoformat()
    DB.notices.insert_many([{"notice_ref": f"TEST_N{i}_{TAG}", "title": f"TEST tender {i}", "category": X if i < 17 else Y,
                             "delivery_country": "GB", "is_published": True, "published_at": now} for i in range(18)])
    DB.notices.insert_one({"notice_ref": f"TEST_OLD_{TAG}", "title": "old", "category": X, "is_published": True,
                           "published_at": "2020-01-01T00:00:00+00:00"})
    base = {"audience": "vendor", "source": "website", "consent": True, "unsubscribed": False, "unsub_token": "tok" + TAG}
    DB.mkt_contacts.insert_many([
        {**base, "email": f"test_dx_{TAG}@example.com", "categories": [X]},
        {**base, "email": f"test_dy_{TAG}@example.com", "categories": [Y], "unsub_token": "toky" + TAG},
        {**base, "email": f"test_dall_{TAG}@example.com", "categories": [], "unsub_token": "toka" + TAG},
        {**base, "email": f"test_dun_{TAG}@example.com", "categories": [X], "unsubscribed": True, "unsub_token": "tokb" + TAG},
        {**base, "email": f"test_dnc_{TAG}@example.com", "categories": [X], "consent": False, "unsub_token": "tokc" + TAG},
    ])

    async def run():
        out = {}
        await DB_async_settings(mk, enabled=False, mode="weekly")
        out["disabled_sched"] = await mp.run_weekly_digest()
        await DB_async_settings(mk, enabled=True, mode="weekly")
        out["instant_when_weekly"] = await mk.send_tender_alert(f"TEST_N0_{TAG}")
        sent.clear()
        out["sched1"] = await mp.run_weekly_digest()
        out["sent1"] = list(sent)
        out["sched2"] = await mp.run_weekly_digest()  # same ISO week -> dedupe
        await DB_async_settings(mk, enabled=True, mode="instant")
        out["sched_instant"] = await mp.run_weekly_digest()
        return out

    try:
        out = asyncio.run(run())
    finally:
        mp.asyncio.sleep = real_sleep
    assert out["disabled_sched"] == 0
    assert out["instant_when_weekly"] == 0
    assert DB.mkt_alert_log.find_one({"notice_ref": f"TEST_N0_{TAG}"}) is None
    by = {t: (s, h) for t, s, h in out["sent1"]}
    assert f"test_dx_{TAG}@example.com" in by
    s, h = by[f"test_dx_{TAG}@example.com"]
    assert "15 new tenders" in s and h.count("<li>") == 15 and f"TEST_N17_{TAG}" not in h and "old" not in h
    assert "unsubscribe/tok" + TAG in h
    s, h = by[f"test_dy_{TAG}@example.com"]
    assert "1 new tender this week" in s and f"TEST_N17_{TAG}" in h
    assert by[f"test_dall_{TAG}@example.com"][1].count("<li>") == 15
    assert f"test_dun_{TAG}@example.com" not in by
    assert f"test_dnc_{TAG}@example.com" not in by
    assert out["sched1"] == len(out["sent1"])
    assert out["sched2"] == 0 and out["sched_instant"] == 0
    wk = datetime.now(timezone.utc).isocalendar()
    log = DB.mkt_digest_log.find_one({"week": f"{wk[0]}-W{wk[1]:02d}"})
    assert log and log["recipients"] == out["sched1"] and log["tenders"] == 18


async def DB_async_settings(mk, **kw):
    await mk.db.mkt_settings.update_one({"_id": "tender_alerts"}, {"$set": {**kw, "include_uploaded": True}}, upsert=True)
