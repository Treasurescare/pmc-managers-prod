# v56o — Re-verification of 6 bug fixes (58, 44, 17, 23) — backend part.
import os
import uuid
import pytest
import requests
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}", "X-CSRF-Token": d["csrf_token"]})
    return s


@pytest.fixture(scope="module")
def vendor():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": "manualvendor@pmcmanagers.com", "password": "Vendor@12345"})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code}")
    d = r.json()
    if d.get("token"):
        s.headers["Authorization"] = f"Bearer {d['token']}"
    if d.get("csrf_token"):
        s.headers["X-CSRF-Token"] = d["csrf_token"]
    return s


# BUG 58 — product enable/disable toggle
def test_bug58_product_toggle(admin):
    p = mdb.products.find_one({"is_active": True})
    pid = str(p["_id"])
    r = admin.patch(f"{API}/products/{pid}/active", params={"is_active": "false"})
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False
    assert mdb.products.find_one({"_id": p["_id"]})["is_active"] is False
    r = admin.patch(f"{API}/products/{pid}/active", params={"is_active": "true"})
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is True
    assert mdb.products.find_one({"_id": p["_id"]})["is_active"] is True


def test_bug58_toggle_invalid_and_missing(admin):
    assert admin.patch(f"{API}/products/badid/active", params={"is_active": "false"}).status_code == 400
    assert admin.patch(f"{API}/products/{ObjectId()}/active", params={"is_active": "false"}).status_code == 404


# BUG 44 — default tech criteria fallback
def test_bug44_award_report_nonzero_tech(admin):
    r = admin.get(f"{API}/evaluations/award-report/PMC-NOT-2026-0018")
    assert r.status_code == 200, r.text
    d = r.json()
    print("rubric", d["rubric"])
    print("ranking", d["ranking"])
    assert len(d["rubric"]["criteria"]) == 4
    scored = [row for row in d["ranking"] if (row.get("technical_avg") or 0) > 0]
    assert scored, "no bid has non-zero technical_avg"


# BUG 17 — vendor docusign /mine
def test_bug17_vendor_mine(vendor):
    r = vendor.get(f"{API}/docusign/mine")
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    print("vendor envelopes:", len(items))


# BUG 23 — corrigendum past deadline leaves no orphan
NOTICE = "PMC-NOT-2026-0102"


def test_bug23_past_deadline_rejected_no_orphan(admin):
    before_n = mdb.notices.find_one({"notice_ref": NOTICE})
    before_cnt = mdb.corrigenda.count_documents({"notice_ref": NOTICE})
    past = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    r = admin.post(f"{API}/notices/{NOTICE}/corrigenda", json={
        "title": "TEST_past_corr", "summary": "TEST past deadline value",
        "new_submission_deadline": past})
    print(r.status_code, r.text[:200])
    assert r.status_code == 400
    assert mdb.corrigenda.count_documents({"notice_ref": NOTICE}) == before_cnt
    assert mdb.notices.find_one({"notice_ref": NOTICE})["submission_deadline"] == before_n["submission_deadline"]


def test_bug23_extend_negative_days_rejected(admin):
    before_n = mdb.notices.find_one({"notice_ref": NOTICE})
    before_cnt = mdb.corrigenda.count_documents({"notice_ref": NOTICE})
    r = admin.post(f"{API}/notices/{NOTICE}/corrigenda", json={
        "title": "TEST_neg_corr", "summary": "TEST negative extend", "extend_deadline_days": -1000})
    print(r.status_code, r.text[:200])
    assert r.status_code in (400, 422)
    assert mdb.corrigenda.count_documents({"notice_ref": NOTICE}) == before_cnt
    assert mdb.notices.find_one({"notice_ref": NOTICE})["submission_deadline"] == before_n["submission_deadline"]


def _cleanup(ref, orig):
    mdb.corrigenda.delete_many({"notice_ref": ref, "title": {"$regex": "^TEST_"}})
    mdb.notices.update_one({"notice_ref": ref}, {"$set": {"submission_deadline": orig}})


def test_bug23_valid_future_publishes(admin):
    ref = "PMC-NOT-2026-0098"
    orig = mdb.notices.find_one({"notice_ref": ref})["submission_deadline"]
    new_dl = (datetime.fromisoformat(orig.replace("Z", "+00:00")) - timedelta(days=1)).isoformat()
    try:
        r = admin.post(f"{API}/notices/{ref}/corrigenda", json={
            "title": "TEST_future_corr", "summary": "TEST future deadline", "new_submission_deadline": new_dl})
        assert r.status_code in (200, 201), r.text
        assert mdb.notices.find_one({"notice_ref": ref})["submission_deadline"] == new_dl
    finally:
        _cleanup(ref, orig)


def test_bug23_chain_violation_leaves_no_orphan(admin):
    """Future deadline that breaks the tender date chain -> 400; must not persist anything."""
    ref = NOTICE  # bid_award_date 2026-10-17 < submission deadline -> chain error
    orig = mdb.notices.find_one({"notice_ref": ref})["submission_deadline"]
    cnt = mdb.corrigenda.count_documents({"notice_ref": ref})
    new_dl = (datetime.fromisoformat(orig.replace("Z", "+00:00")) + timedelta(days=2)).isoformat()
    try:
        r = admin.post(f"{API}/notices/{ref}/corrigenda", json={
            "title": "TEST_chain_corr", "summary": "TEST chain violation", "new_submission_deadline": new_dl})
        assert r.status_code == 400, r.text
        after_cnt = mdb.corrigenda.count_documents({"notice_ref": ref})
        after_dl = mdb.notices.find_one({"notice_ref": ref})["submission_deadline"]
        assert after_cnt == cnt, f"orphan corrigendum persisted ({cnt}->{after_cnt})"
        assert after_dl == orig, f"notice deadline moved {orig}->{after_dl} despite 400"
    finally:
        _cleanup(ref, orig)
