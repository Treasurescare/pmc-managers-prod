# Marketing module regression tests: contacts, segments, AI copy, campaigns, tracking, unsubscribe,
# new-tender alerts, referrals. All data TEST_-prefixed and cleaned up at the end.
import os
import time
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
M = f"{BASE_URL}/api/v1/marketing"
TAG = uuid.uuid4().hex[:6].lower()
CC = "ZZ"
CAT = f"TEST_CAT_{TAG}"


def _mongo():
    env = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
    return MongoClient(env["MONGO_URL"].strip('"'))[env["DB_NAME"].strip('"')]


DB = _mongo()


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
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com",
               "password": "Vendor@12345"})
    if r.status_code != 200:
        pytest.skip("vendor login failed")
    s.headers.update({"X-CSRF-Token": r.json()["csrf_token"]})
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    DB.mkt_contacts.delete_many({"email": {"$regex": "^test_", "$options": "i"}})
    DB.mkt_segments.delete_many({"name": {"$regex": "^TEST_"}})
    camps = [str(c["_id"]) for c in DB.mkt_campaigns.find({"name": {"$regex": "^TEST_"}})]
    DB.mkt_sends.delete_many({"campaign_id": {"$in": camps}})
    DB.mkt_campaigns.delete_many({"name": {"$regex": "^TEST_"}})
    DB.mkt_referrals.delete_many({"email": {"$regex": "^test_", "$options": "i"}})
    DB.registrations.delete_many({"email": {"$regex": "^test_mkt", "$options": "i"}})
    refs = [n["notice_ref"] for n in DB.notices.find({"title": {"$regex": "^TEST_MKT"}})]
    DB.mkt_alert_log.delete_many({"notice_ref": {"$in": refs}})
    DB.notices.delete_many({"title": {"$regex": "^TEST_MKT"}})
    DB.vendors.update_one({"email": "testvendor@pmcmanagers.com"}, {"$pull": {"business_categories": CAT}})
    DB.mkt_settings.update_one({"_id": "tender_alerts"}, {"$set": {"enabled": False}}, upsert=True)


# ---- auth gating ----
class TestAuth:
    def test_anon_blocked(self):
        assert requests.get(f"{M}/contacts").status_code in (401, 403)

    def test_vendor_blocked(self, vendor):
        assert vendor.get(f"{M}/contacts").status_code in (401, 403)
        assert vendor.post(f"{M}/contacts", json={"email": "test_x@pmcmanagers.com"}).status_code in (401, 403)

    def test_csrf_required(self, admin):
        r = requests.post(f"{M}/contacts", json={"email": "test_nocsrf@pmcmanagers.com"}, cookies=admin.cookies)
        assert r.status_code in (401, 403)


# ---- contacts + import + sync ----
class TestContacts:
    def test_add_manual_and_list(self, admin):
        r = admin.post(f"{M}/contacts", json={"email": f"TEST_man_{TAG}@pmcmanagers.com", "country": "zz",
                                              "consent": True, "categories": [CAT]})
        assert r.status_code == 200 and r.json()["created"] is True
        r2 = admin.post(f"{M}/contacts", json={"email": f"test_man_{TAG}@pmcmanagers.com"})
        assert r2.json()["created"] is False
        lst = admin.get(f"{M}/contacts", params={"country": "zz", "q": f"man_{TAG}"}).json()
        assert lst["total"] == 1 and lst["items"][0]["source"] == "manual"
        assert "unsub_token" not in lst["items"][0] and "_id" not in lst["items"][0]

    def test_import_requires_lawful_basis(self, admin):
        r = admin.post(f"{M}/contacts/import", json={"csv_text": "email\na@b.com", "lawful_basis_confirmed": False})
        assert r.status_code == 422

    def test_import_requires_email_col(self, admin):
        r = admin.post(f"{M}/contacts/import", json={"csv_text": "name,company\nx,y", "lawful_basis_confirmed": True})
        assert r.status_code == 422 and "email" in r.text.lower()

    def test_import_dedupe_and_consent(self, admin):
        csv = ("Email,Name,Company,Country,Categories,Consent,Audience\n"
               f"TEST_imp1_{TAG}@pmcmanagers.com,A,TEST_Co,zz,{CAT};Other,yes,vendor\n"
               f"test_imp1_{TAG}@pmcmanagers.com,A,TEST_Co,ZZ,{CAT},yes,vendor\n"
               f"TEST_imp2_{TAG}@pmcmanagers.com,B,TEST_Co,ZZ,{CAT},no,vendor\n"
               f"TEST_imp3_{TAG}@pmcmanagers.com,C,TEST_Co,ZZ,,yes,buyer\n"
               "not-an-email,D,X,ZZ,,yes,vendor\n")
        r = admin.post(f"{M}/contacts/import", json={"csv_text": csv, "lawful_basis_confirmed": True})
        assert r.status_code == 200, r.text
        assert r.json() == {"created": 3, "updated": 1, "skipped": 1}
        c2 = DB.mkt_contacts.find_one({"email": f"test_imp2_{TAG}@pmcmanagers.com"})
        assert c2["consent"] is False and c2["country"] == "ZZ"
        c1 = DB.mkt_contacts.find_one({"email": f"test_imp1_{TAG}@pmcmanagers.com"})
        assert c1["consent"] is True and CAT in c1["categories"]
        assert DB.mkt_contacts.find_one({"email": f"test_imp3_{TAG}@pmcmanagers.com"})["audience"] == "buyer"

    def test_sync(self, admin):
        r = admin.post(f"{M}/contacts/sync")
        assert r.status_code == 200 and isinstance(r.json()["created"], int)
        assert DB.mkt_contacts.find_one({"email": "testvendor@pmcmanagers.com", "source": "platform"})

    def test_delete_contact(self, admin):
        admin.post(f"{M}/contacts", json={"email": f"test_del_{TAG}@pmcmanagers.com"})
        cid = str(DB.mkt_contacts.find_one({"email": f"test_del_{TAG}@pmcmanagers.com"})["_id"])
        assert admin.delete(f"{M}/contacts/{cid}").status_code == 200
        assert not DB.mkt_contacts.find_one({"email": f"test_del_{TAG}@pmcmanagers.com"})
        assert admin.delete(f"{M}/contacts/bad-id").status_code == 404


# ---- segments ----
class TestSegments:
    def test_preview_counts(self, admin):
        r = admin.post(f"{M}/segments/preview", json={"name": "TEST_p", "audience": "vendor", "countries": [CC],
                                                       "categories": [CAT]})
        # man + imp1 consent true; imp2 consent false excluded
        assert r.json()["size"] == 2
        r = admin.post(f"{M}/segments/preview", json={"name": "TEST_p", "audience": "buyer", "countries": [CC]})
        assert r.json()["size"] >= 1
        r = admin.post(f"{M}/segments/preview", json={"name": "TEST_p", "audience": "vendor", "countries": [CC],
                                                       "categories": [CAT], "sources": ["upload"]})
        assert r.json()["size"] == 1

    def test_create_list_delete(self, admin):
        r = admin.post(f"{M}/segments", json={"name": f"TEST_seg_tmp_{TAG}", "audience": "all", "countries": [CC]})
        sid = r.json()["id"]
        items = admin.get(f"{M}/segments").json()["items"]
        seg = next(s for s in items if s["id"] == sid)
        assert seg["size"] >= 3
        assert admin.delete(f"{M}/segments/{sid}").status_code == 200
        assert not any(s["id"] == sid for s in admin.get(f"{M}/segments").json()["items"])


# ---- AI copy ----
class TestAI:
    def test_ai_copy(self, admin):
        r = admin.post(f"{M}/ai-copy", json={"brief": "Invite HVAC contractors in Kazakhstan to register and bid",
                                              "audience": "vendor", "tone": "friendly"}, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["subject"]) > 3 and "<p>" in d["body_html"]

    def test_ai_copy_validation(self, admin):
        assert admin.post(f"{M}/ai-copy", json={"brief": "short"}).status_code == 422


# ---- campaigns + tracking + unsubscribe ----
class TestCampaigns:
    def test_full_flow(self, admin):
        assert admin.post(f"{M}/campaigns", json={"name": "TEST_c", "subject": "Hi", "body_html": "<p>x</p>",
                                                   "segment_id": "6ae3fd2b4808a09b8fdebc00"}).status_code == 422
        sid = admin.post(f"{M}/segments", json={"name": f"TEST_seg_{TAG}", "audience": "vendor", "countries": [CC],
                                                 "categories": [CAT]}).json()["id"]
        body = {"name": f"TEST_camp_{TAG}", "subject": "TEST subject", "segment_id": sid,
                "body_html": '<p>Hello <a href="https://example.com/page1">one</a> <a href="https://example.com/p2">two</a></p>',
                "cta_label": "Join", "cta_url": "https://example.com/cta"}
        r = admin.post(f"{M}/campaigns", json=body)
        cid = r.json()["id"]
        body["subject"] = "TEST subject v2"
        assert admin.put(f"{M}/campaigns/{cid}", json=body).status_code == 200
        assert DB.mkt_campaigns.find_one({"name": f"TEST_camp_{TAG}"})["subject"] == "TEST subject v2"
        t = admin.post(f"{M}/campaigns/{cid}/test", json={"email": "testvendor@pmcmanagers.com"}, timeout=30)
        assert t.status_code == 200 and "email_sent" in t.json()
        print("test send email_sent =", t.json()["email_sent"])
        s = admin.post(f"{M}/campaigns/{cid}/send")
        assert s.status_code == 200 and s.json()["queued"] == 2
        assert admin.post(f"{M}/campaigns/{cid}/send").status_code == 409
        assert admin.put(f"{M}/campaigns/{cid}", json=body).status_code == 409
        for _ in range(30):
            c = DB.mkt_campaigns.find_one({"name": f"TEST_camp_{TAG}"})
            if c["status"] == "sent":
                break
            time.sleep(1)
        assert c["status"] == "sent", c["status"]
        sends = list(DB.mkt_sends.find({"campaign_id": cid}))
        assert len(sends) == 2
        print("send statuses", [x["status"] for x in sends])
        rid = sends[0]["rid"]
        g = requests.get(f"{M}/t/o/{rid}.gif")
        assert g.status_code == 200 and g.headers["content-type"] == "image/gif"
        assert DB.mkt_sends.find_one({"rid": rid}).get("opened_at")
        cl = requests.get(f"{M}/t/c/{rid}/1", allow_redirects=False)
        assert cl.status_code in (302, 307) and cl.headers["location"] == "https://example.com/p2"
        assert DB.mkt_sends.find_one({"rid": rid}).get("clicked_at")
        cta = requests.get(f"{M}/t/c/{rid}/cta", allow_redirects=False)
        assert cta.headers["location"] == "https://example.com/cta"
        unk = requests.get(f"{M}/t/c/nope_{TAG}/0", allow_redirects=False)
        assert unk.status_code in (302, 307) and unk.headers["location"].rstrip("/") == BASE_URL
        stats = next(x for x in admin.get(f"{M}/campaigns").json()["items"] if x["id"] == cid)["stats"]
        assert stats["opened"] == 1 and stats["clicked"] == 1
        # unsubscribe
        con = DB.mkt_contacts.find_one({"email": f"test_imp1_{TAG}@pmcmanagers.com"})
        u = requests.get(f"{M}/unsubscribe/{con['unsub_token']}")
        assert u.status_code == 200 and "unsubscribed" in u.text.lower() and "text/html" in u.headers["content-type"]
        assert DB.mkt_contacts.find_one({"_id": con["_id"]})["unsubscribed"] is True
        size = next(x for x in admin.get(f"{M}/segments").json()["items"] if x["id"] == sid)["size"]
        assert size == 1
        assert "no longer valid" in requests.get(f"{M}/unsubscribe/bogus{TAG}").text


# ---- new-tender alerts ----
def _create_notice(admin, title):
    dl = (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d")
    r = admin.post(f"{BASE_URL}/api/v1/notices", json={"title": title, "description": "TEST notice for alerts",
                   "category": CAT, "delivery_country": "ZZ", "submission_deadline": dl, "budget_amount": 1000,
                   "is_published": False})
    assert r.status_code == 200, r.text
    return r.json()["notice_ref"]


class TestAlerts:
    def test_disabled_no_alert(self, admin):
        assert admin.put(f"{M}/alerts", json={"enabled": False, "include_uploaded": True}).status_code == 200
        assert admin.get(f"{M}/alerts").json()["enabled"] is False
        ref = _create_notice(admin, f"TEST_MKT off {TAG}")
        assert admin.post(f"{BASE_URL}/api/v1/notices/{ref}/publish").status_code == 200
        time.sleep(4)
        assert not DB.mkt_alert_log.find_one({"notice_ref": ref})

    def test_enabled_alert_once(self, admin):
        DB.vendors.update_one({"email": "testvendor@pmcmanagers.com"}, {"$addToSet": {"business_categories": CAT}})
        admin.put(f"{M}/alerts", json={"enabled": True, "include_uploaded": True})
        ref = _create_notice(admin, f"TEST_MKT on {TAG}")
        assert admin.post(f"{BASE_URL}/api/v1/notices/{ref}/publish").status_code == 200
        log = None
        for _ in range(20):
            log = DB.mkt_alert_log.find_one({"notice_ref": ref})
            if log:
                break
            time.sleep(1)
        assert log and log["category"] == CAT
        print("alert recipients (successful sends) =", log["recipients"])
        # expected targets: testvendor (vendor) + test_man (consent, not unsub). imp1 unsubscribed, imp2 no consent
        assert DB.mkt_alert_log.count_documents({"notice_ref": ref}) == 1
        # republish blocked -> no duplicate; direct second invocation returns 0
        assert admin.post(f"{BASE_URL}/api/v1/notices/{ref}/publish").status_code == 404
        import asyncio, sys
        sys.path.insert(0, "/app/backend")
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        from routers.marketing import send_tender_alert
        assert asyncio.run(send_tender_alert(ref)) == 0
        assert DB.mkt_alert_log.count_documents({"notice_ref": ref}) == 1
        admin.put(f"{M}/alerts", json={"enabled": False, "include_uploaded": True})


# ---- referrals ----
class TestReferrals:
    def test_referral_flow(self, admin, vendor):
        a = vendor.get(f"{M}/referral/me")
        assert a.status_code == 200, a.text
        d = a.json()
        assert d["link"].endswith(f"/register?ref={d['code']}")
        assert vendor.get(f"{M}/referral/me").json()["code"] == d["code"]
        before = d["joined"]
        r = requests.post(f"{BASE_URL}/api/v1/registrations", json={"email": f"test_mkt_ref_{TAG}@pmcmanagers.com",
                          "company_name": "TEST_RefCo", "country": "ZZ", "data_processing_consent": True,
                          "ref": d["code"].lower()})
        assert r.status_code == 200, r.text
        assert DB.mkt_referrals.find_one({"email": f"test_mkt_ref_{TAG}@pmcmanagers.com", "code": d["code"]})
        r2 = requests.post(f"{BASE_URL}/api/v1/registrations", json={"email": f"test_mkt_ref2_{TAG}@pmcmanagers.com",
                           "country": "ZZ", "data_processing_consent": True, "ref": "NOPE0000"})
        assert r2.status_code == 200
        assert not DB.mkt_referrals.find_one({"email": f"test_mkt_ref2_{TAG}@pmcmanagers.com"})
        assert vendor.get(f"{M}/referral/me").json()["joined"] == before + 1
        lead = admin.get(f"{M}/referrals").json()
        assert any(x["code"] == d["code"] and x["referrer"] == "Test Supplier Co" for x in lead["leaders"])
        assert any(x["email"] == f"test_mkt_ref_{TAG}@pmcmanagers.com" for x in lead["recent"])
        assert "_id" not in lead["recent"][0]
