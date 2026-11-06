# v83: Supplier AI tender summary + bid readiness (real LLM calls; slow). Deletes only the ai_reports it created.
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
S = {"ids": []}
TXT = ("TEST_ TENDER DOCUMENT. Buyer: Municipal Water Board of Testville. Scope: supply and installation of 40 solar water pumps. "
       "Eligibility: bidder must have average annual turnover of USD 2 million over last 3 years and at least 2 similar projects "
       "in the last 5 years. EMD: USD 15,000 bank guarantee. Tender fee: USD 200 non-refundable. Bid submission deadline 15 March 2026. "
       "Bid opening 16 March 2026. Documents required: ISO 9001 certificate, audited accounts, tax clearance certificate.")


@pytest.fixture(scope="module", autouse=True)
def setup():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": "testvendor@pmcmanagers.com", "password": "Vendor@12345"})
    assert r.status_code == 200
    j = r.json()
    if j.get("access_token"):
        s.headers["Authorization"] = f"Bearer {j['access_token']}"
    if j.get("csrf_token"):
        s.headers["X-CSRF-Token"] = j["csrf_token"]
    S["v"] = s
    yield
    for i in S["ids"]:
        DB.ai_reports.delete_one({"_id": ObjectId(i)})


def test_summary_from_file_and_cache():
    t = time.time()
    r = S["v"].post(f"{API}/supplier-ai/summary", files={"file": ("TEST_tender.txt", TXT.encode(), "text/plain")},
                    data={"lang": "English"}, timeout=180)
    print("summary secs", round(time.time() - t, 1))
    assert r.status_code == 200, r.text
    j = r.json()
    S["ids"].append(j["id"])
    S["rep"] = j["id"]
    res = j["result"]
    assert res.get("summary") and isinstance(res.get("eligibility"), list)
    assert res.get("emd") and "15" in res["emd"]
    assert "source_text" not in j
    r2 = S["v"].post(f"{API}/supplier-ai/summary", files={"file": ("TEST_tender.txt", TXT.encode(), "text/plain")},
                     data={"lang": "English"}, timeout=60)
    assert r2.status_code == 200 and r2.json()["id"] == j["id"]


def test_summary_short_file_rejected():
    r = S["v"].post(f"{API}/supplier-ai/summary", files={"file": ("TEST_s.txt", b"too short", "text/plain")}, timeout=60)
    assert r.status_code == 422


def test_readiness_from_report_and_notice():
    r = S["v"].post(f"{API}/supplier-ai/readiness", json={"report_id": S["rep"]}, timeout=180)
    assert r.status_code == 200, r.text
    S["ids"].append(r.json()["id"])
    res = r.json()["result"]
    assert isinstance(res.get("score"), (int, float)) and res.get("verdict") in ("ready", "gaps", "high_risk")
    r2 = S["v"].post(f"{API}/supplier-ai/readiness", json={"notice_ref": "DEMO-TND-001"}, timeout=180)
    assert r2.status_code == 200, r2.text
    S["ids"].append(r2.json()["id"])


def test_summary_from_notice_and_history():
    r = S["v"].post(f"{API}/supplier-ai/summary", data={"notice_ref": "DEMO-TND-002", "lang": "English"}, timeout=180)
    assert r.status_code == 200, r.text
    S["ids"].append(r.json()["id"])
    h = S["v"].get(f"{API}/supplier-ai/reports").json()["items"]
    ids = {x["id"] for x in h}
    assert set(S["ids"]) <= ids
    assert all("source_text" not in x for x in h)
