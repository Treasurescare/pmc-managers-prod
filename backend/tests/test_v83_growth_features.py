# v83: Growth features — global tenders, directory, consulting, buyer applications, data API, saved alerts,
# supplier AI tools, cron auth and supplier fee defaults. Cleans up only the records it created.
import os
import time

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE + "/api/v1"
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
CRON = ENV.get("WEBHOOK_CRON_SECRET", "").strip('"')
S = {"apps": [], "svcs": [], "reqs": [], "clients": [], "alerts": [], "tenants": []}


def _sess(path, email, pw):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    j = r.json()
    tok = j.get("access_token") or j.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    if j.get("csrf_token"):
        s.headers["X-CSRF-Token"] = j["csrf_token"]
    return s


@pytest.fixture(scope="module", autouse=True)
def setup():
    S["admin"] = _sess("admin/auth/login", "adminsupport@pmcmanagers.com", "Admin@12345")
    S["vendor"] = _sess("vendor/auth/login", "testvendor@pmcmanagers.com", "Vendor@12345")
    S["vdoc"] = DB.vendors.find_one({"email": "testvendor@pmcmanagers.com"}, {"directory": 1})
    yield
    for a in S["apps"]:
        DB.buyer_applications.delete_one({"_id": ObjectId(a)})
    for t in S["tenants"]:
        DB.tenants.delete_one({"code": t, "source": "buyer_application"})
    for sid in S["svcs"]:
        DB.consulting_services.delete_one({"_id": ObjectId(sid)})
    for rid in S["reqs"]:
        DB.consulting_requests.delete_one({"_id": ObjectId(rid)})
    for c in S["clients"]:
        DB.api_clients.delete_one({"_id": ObjectId(c)})
        DB.api_usage.delete_many({"client_id": c})
    for a in S["alerts"]:
        DB.saved_alerts.delete_one({"_id": ObjectId(a)})
    d = (S["vdoc"] or {}).get("directory")
    if d is None:
        DB.vendors.update_one({"_id": S["vdoc"]["_id"]}, {"$unset": {"directory": ""}})
    else:
        DB.vendors.update_one({"_id": S["vdoc"]["_id"]}, {"$set": {"directory": d}})


# Global tenders (public)
def test_global_tenders_list_and_filters():
    r = requests.get(f"{API}/global-tenders", params={"limit": 5})
    assert r.status_code == 200
    j = r.json()
    assert j["total"] > 0 and len(j["items"]) <= 5
    it = j["items"][0]
    assert it["source"] in ("WORLDBANK", "TED") and it.get("url") and it.get("ref")
    assert "_id" not in it and "dedupe_key" not in it
    r2 = requests.get(f"{API}/global-tenders", params={"source": "TED", "limit": 10}).json()
    assert all(i["source"] == "TED" for i in r2["items"])
    p2 = requests.get(f"{API}/global-tenders", params={"limit": 5, "offset": 5}).json()
    assert {i["ref"] for i in p2["items"]}.isdisjoint({i["ref"] for i in j["items"]})


# Supplier fee defaults include new codes
def test_supplier_fee_defaults_codes():
    r = S["admin"].get(f"{API}/pricing/supplier-fees/defaults")
    assert r.status_code == 200, r.text
    txt = r.text
    for c in ("ai_tender_summary", "ai_bid_readiness", "featured_listing"):
        assert c in txt


# Cron auth
def test_cron_requires_secret():
    assert requests.post(f"{API}/cron/tender-feeds").status_code == 401
    assert requests.post(f"{API}/cron/saved-alerts?freq=daily").status_code == 401
    assert requests.post(f"{API}/cron/saved-alerts?freq=daily", headers={"Authorization": "Bearer wrong"}).status_code == 401
    r = requests.post(f"{API}/cron/saved-alerts?freq=daily", headers={"Authorization": f"Bearer {CRON}"})
    assert r.status_code == 200 and r.json()["accepted"] is True


# Buyer applications
def test_buyer_application_approve_and_reject():
    body = {"org_name": "TEST_ Growth Bank", "org_type": "bank", "country": "in", "contact_name": "Test Person",
            "email": "TEST_buyer@example.com"}
    r = requests.post(f"{API}/buyer-applications", json=body)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    S["apps"].append(aid)
    lst = S["admin"].get(f"{API}/buyer-applications").json()["items"]
    row = next(x for x in lst if x["id"] == aid)
    assert row["status"] == "pending" and row["country"] == "IN" and "ip" not in row
    d = S["admin"].post(f"{API}/buyer-applications/{aid}/decision", json={"action": "approve", "code": "TESTGRB"})
    assert d.status_code == 200, d.text
    code = d.json()["tenant_code"]
    S["tenants"].append(code)
    assert code.startswith("TESTGRB")
    assert DB.tenants.find_one({"code": code})["name"] == "TEST_ Growth Bank"
    again = S["admin"].post(f"{API}/buyer-applications/{aid}/decision", json={"action": "reject"})
    assert again.status_code == 409
    r2 = requests.post(f"{API}/buyer-applications", json={**body, "org_name": "TEST_ Reject Org"})
    aid2 = r2.json()["id"]
    S["apps"].append(aid2)
    d2 = S["admin"].post(f"{API}/buyer-applications/{aid2}/decision", json={"action": "reject", "notes": "n/a"})
    assert d2.status_code == 200 and d2.json()["status"] == "rejected"


def test_buyer_application_validation_and_auth():
    assert requests.post(f"{API}/buyer-applications", json={"org_name": "x"}).status_code == 422
    assert requests.get(f"{API}/buyer-applications").status_code in (401, 403)


# Consulting services + requests
def test_consulting_service_and_request_flow():
    r = S["admin"].post(f"{API}/consulting/admin/services", json={"name": "TEST_ Bid Writing", "summary": "We write your bid for you.",
                                                                  "price": 250, "currency": "usd"})
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    S["svcs"].append(sid)
    assert r.json()["currency"] == "USD"
    pub = requests.get(f"{API}/consulting/services").json()["items"]
    assert any(s["id"] == sid for s in pub)
    rq = requests.post(f"{API}/consulting/requests", json={"service_id": sid, "name": "Test Requester", "email": "TEST_req@example.com",
                                                           "message": "Please help with our bid"})
    assert rq.status_code == 200, rq.text
    rid = rq.json()["id"]
    S["reqs"].append(rid)
    reqs = S["admin"].get(f"{API}/consulting/admin/requests").json()["items"]
    row = next(x for x in reqs if x["id"] == rid)
    assert row["status"] == "new" and row["service_name"] == "TEST_ Bid Writing"
    u = S["admin"].patch(f"{API}/consulting/admin/requests/{rid}", json={"status": "in_progress", "notes": "ok"})
    assert u.status_code == 200
    assert DB.consulting_requests.find_one({"_id": ObjectId(rid)})["status"] == "in_progress"
    # deactivate -> hidden publicly, request rejected
    up = S["admin"].put(f"{API}/consulting/admin/services/{sid}", json={"name": "TEST_ Bid Writing", "summary": "We write your bid for you.",
                                                                       "is_active": False})
    assert up.status_code == 200
    assert not any(s["id"] == sid for s in requests.get(f"{API}/consulting/services").json()["items"])
    assert requests.post(f"{API}/consulting/requests", json={"service_id": sid, "name": "Test", "email": "TEST_req@example.com",
                                                             "message": "Please help"}).status_code == 404


def test_consulting_service_requires_admin():
    assert requests.post(f"{API}/consulting/admin/services", json={"name": "TEST_x", "summary": "abcdefghijkl"}).status_code in (401, 403)


# Data API
def test_data_api_keys_limits():
    r = S["admin"].post(f"{API}/data-api/clients", json={"name": "TEST_ Client", "email": "TEST_api@example.com", "daily_limit": 10})
    assert r.status_code == 200, r.text
    j = r.json()
    cid, key = j["id"], j["api_key"]
    S["clients"].append(cid)
    assert key.startswith("pmc_") and "key_hash" not in j
    lst = S["admin"].get(f"{API}/data-api/clients").json()["items"]
    assert all("key_hash" not in c for c in lst) and any(c["id"] == cid for c in lst)
    assert requests.get(f"{API}/data/tenders").status_code == 401
    assert requests.get(f"{API}/data/tenders", headers={"X-API-Key": "pmc_bad"}).status_code == 401
    codes = [requests.get(f"{API}/data/tenders", headers={"X-API-Key": key}, params={"limit": 2}).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10, codes
    assert codes[10] == 429, codes
    # rotate -> old key invalid
    rot = S["admin"].post(f"{API}/data-api/clients/{cid}/rotate").json()["api_key"]
    assert requests.get(f"{API}/data/tenders", headers={"X-API-Key": key}).status_code == 401
    DB.api_usage.delete_many({"client_id": cid})
    ok = requests.get(f"{API}/data/tenders", headers={"X-API-Key": rot}, params={"limit": 3})
    assert ok.status_code == 200 and 0 < len(ok.json()["items"]) <= 3
    # BUG (v83): count is computed before items are truncated to limit (pmc+global merged)
    assert ok.json()["count"] == len(ok.json()["items"]), ok.json()["count"]
    # disable
    S["admin"].put(f"{API}/data-api/clients/{cid}", json={"name": "TEST_ Client", "email": "TEST_api@example.com", "daily_limit": 10,
                                                          "is_active": False})
    assert requests.get(f"{API}/data/tenders", headers={"X-API-Key": rot}).status_code == 401


def test_data_api_admin_only():
    assert S["vendor"].get(f"{API}/data-api/clients").status_code in (401, 403)


# Directory
def test_directory_listing_flow():
    me = S["vendor"].put(f"{API}/directory/me", json={"listed": True, "headline": "TEST_ headline supplier"})
    assert me.status_code == 200, me.text
    assert me.json()["listed"] is True
    d = requests.get(f"{API}/directory", params={"q": "TEST_ headline"}).json()
    assert any(i["headline"] == "TEST_ headline supplier" for i in d["items"])
    full = requests.get(f"{API}/directory").json()["items"]
    refs = [v["vendor_ref"] for v in DB.vendors.find({"directory.listed": True, "status": {"$in": ["approved", "active"]}})]
    assert sorted(i["vendor_ref"] for i in full) == sorted(refs)
    f = S["vendor"].post(f"{API}/directory/me/feature")
    assert f.status_code == 409
    vref = S["vendor"].get(f"{API}/directory/me").json()["vendor_ref"]
    a = S["admin"].put(f"{API}/directory/admin/{vref}/feature", json={"days": 7})
    assert a.status_code == 200
    first = requests.get(f"{API}/directory").json()["items"][0]
    assert first["vendor_ref"] == vref and first["featured"] is True
    S["admin"].put(f"{API}/directory/admin/{vref}/feature", json={"days": 0})
    S["vendor"].put(f"{API}/directory/me", json={"listed": False})
    assert not any(i["vendor_ref"] == vref for i in requests.get(f"{API}/directory").json()["items"])


# Saved alerts
def test_saved_alerts_crud_preview():
    r = S["vendor"].post(f"{API}/vendor-alerts/saved", json={"name": "TEST_ alert", "keywords": ["construction"], "frequency": "weekly"})
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    S["alerts"].append(aid)
    assert any(a["id"] == aid for a in S["vendor"].get(f"{API}/vendor-alerts/saved").json()["items"])
    u = S["vendor"].put(f"{API}/vendor-alerts/saved/{aid}", json={"name": "TEST_ alert2", "keywords": ["road"], "frequency": "daily"})
    assert u.status_code == 200 and u.json()["name"] == "TEST_ alert2" and u.json()["frequency"] == "daily"
    p = S["vendor"].get(f"{API}/vendor-alerts/saved/{aid}/preview")
    assert p.status_code == 200 and isinstance(p.json()["items"], list)
    assert S["vendor"].post(f"{API}/vendor-alerts/saved", json={"name": "TEST_ bad", "frequency": "hourly"}).status_code == 422
    dl = S["vendor"].delete(f"{API}/vendor-alerts/saved/{aid}")
    assert dl.status_code == 200
    assert S["vendor"].get(f"{API}/vendor-alerts/saved/{aid}/preview").status_code == 404
    assert requests.get(f"{API}/vendor-alerts/saved").status_code == 401


# Admin sources
def test_admin_sources_list():
    r = S["admin"].get(f"{API}/tender-feeds/sources")
    assert r.status_code == 200
    codes = {s["code"]: s for s in r.json()["items"]}
    assert {"WORLDBANK", "TED", "PROVIDER"} <= set(codes)
    assert codes["WORLDBANK"]["count"] > 0
    assert requests.get(f"{API}/tender-feeds/sources").status_code in (401, 403)


# Supplier AI (validation, prices)
def test_ai_prices_and_validation():
    r = S["vendor"].get(f"{API}/supplier-ai/prices")
    assert r.status_code == 200 and set(r.json()) == {"ai_tender_summary", "ai_bid_readiness", "featured_listing"}
    assert S["vendor"].post(f"{API}/supplier-ai/summary", data={"lang": "English"}).status_code == 422
    assert S["vendor"].post(f"{API}/supplier-ai/summary", data={"notice_ref": "NOPE-XYZ"}).status_code == 404
    assert S["vendor"].post(f"{API}/supplier-ai/readiness", json={}).status_code == 422
    assert requests.post(f"{API}/supplier-ai/summary", data={"notice_ref": "DEMO-TND-001"}).status_code == 401
