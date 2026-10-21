# v56s — Go-Live switch, Go-Live enforcement on notices + registrations,
# public notice taxonomy filters, vendor category-request taxonomy persistence.
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login_admin(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        return None
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}", "X-CSRF-Token": d.get("csrf_token", "")})
    return s


@pytest.fixture(scope="module")
def admin():
    s = _login_admin("adminsupport@pmcmanagers.com", "Admin@12345") or _login_admin("adminsupport@pmcmanagers.com", "Admin@123")
    assert s, "admin login failed"
    yield s
    # ALWAYS reset go-live to false
    s.put(f"{API}/settings/go-live", json={"enabled": False})
    assert requests.get(f"{API}/settings/go-live/public").json()["go_live"] is False


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


def _notice_payload(**extra):
    dl = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")
    p = {"title": f"TEST_v56s notice {uuid.uuid4().hex[:6]}", "description": "TEST v56s go-live enforcement notice",
         "document_type": "tender", "category": "medical-gas-pipeline-systems", "delivery_country": "IN",
         "submission_deadline": dl, "budget_currency": "USD", "budget_amount": 1000, "is_published": False}
    p.update(extra)
    return p


def _reg_ready():
    em = f"delivered+v56s{uuid.uuid4().hex[:6]}@resend.dev"
    c = requests.post(f"{API}/registrations", json={"email": em, "company_name": f"TEST_v56s Reg {uuid.uuid4().hex[:4]}",
                                                    "country": "KZ", "data_processing_consent": True}).json()
    body = {"registered_address": "1 Test St", "registration_number": "TEST123", "legal_entity_type": "LLP",
            "decl_conflict_of_interest": True, "decl_integrity": True, "decl_accuracy": True, "decl_data_consent": True,
            "decl_fee": True, "decl_notification": True, "signature_name": "T", "signature_title": "CEO",
            "signature_date": "2026-10-21"}
    r = requests.patch(f"{API}/registrations/{c['id']}?token={c['magic_token']}", json=body)
    assert r.status_code == 200, r.text
    return c


# ---- Go-Live switch ----
def test_golive_public_default_false():
    r = requests.get(f"{API}/settings/go-live/public")
    assert r.status_code == 200
    assert r.json() == {"go_live": False}


def test_golive_admin_get_and_requires_auth(admin):
    assert requests.get(f"{API}/settings/go-live").status_code in (401, 403)
    assert requests.put(f"{API}/settings/go-live", json={"enabled": True}).status_code in (401, 403)
    r = admin.get(f"{API}/settings/go-live")
    assert r.status_code == 200
    d = r.json()
    assert d["go_live"] is False and "updated_at" in d and "updated_by" in d


def test_golive_put_validation(admin):
    r = admin.put(f"{API}/settings/go-live", json={})
    assert r.status_code == 422


def test_golive_non_admin_cannot_put(vendor):
    r = vendor.put(f"{API}/settings/go-live", json={"enabled": True})
    assert r.status_code in (401, 403)
    assert requests.get(f"{API}/settings/go-live/public").json()["go_live"] is False


# ---- Enforcement OFF ----
def test_off_notice_without_taxonomy_ok(admin):
    r = admin.post(f"{API}/notices", json=_notice_payload())
    assert r.status_code == 200, r.text
    assert r.json()["notice_ref"].startswith("PMC-NOT-")


def test_off_registration_submit_without_taxonomy_ok():
    c = _reg_ready()
    r = requests.post(f"{API}/registrations/{c['id']}/submit?token={c['magic_token']}")
    assert r.status_code == 200, r.text


# ---- Enforcement ON ----
def test_on_enforcement(admin):
    r = admin.put(f"{API}/settings/go-live", json={"enabled": True})
    assert r.status_code == 200 and r.json()["go_live"] is True
    g = admin.get(f"{API}/settings/go-live").json()
    assert g["go_live"] is True and g["updated_by"] == "adminsupport@pmcmanagers.com" and g["updated_at"]
    assert requests.get(f"{API}/settings/go-live/public").json()["go_live"] is True
    try:
        # notice missing taxonomy -> 422
        r = admin.post(f"{API}/notices", json=_notice_payload())
        assert r.status_code in (400, 422), r.text
        r = admin.post(f"{API}/notices", json=_notice_payload(sector_code="power"))
        assert r.status_code in (400, 422), r.text
        # notice with taxonomy -> ok
        r = admin.post(f"{API}/notices", json=_notice_payload(sector_code="power", contract_type_code="epc"))
        assert r.status_code == 200, r.text
        ref = r.json()["notice_ref"]
        doc = mdb.notices.find_one({"notice_ref": ref})
        assert doc["sector_code"] == "power" and doc["contract_type_code"] == "epc"
        # registration missing taxonomy -> 400
        c = _reg_ready()
        r = requests.post(f"{API}/registrations/{c['id']}/submit?token={c['magic_token']}")
        assert r.status_code in (400, 422), r.text
        assert "Sector" in r.text
        # add taxonomy -> ok
        p = requests.patch(f"{API}/registrations/{c['id']}?token={c['magic_token']}",
                           json={"sector_code": "power", "sector_name": "Power & Energy",
                                 "contract_type_code": "epc", "contract_type_name": "EPC Contracts"})
        assert p.status_code == 200, p.text
        assert p.json()["sector_code"] == "power"
        r = requests.post(f"{API}/registrations/{c['id']}/submit?token={c['magic_token']}")
        assert r.status_code == 200, r.text
    finally:
        admin.put(f"{API}/settings/go-live", json={"enabled": False})
    assert requests.get(f"{API}/settings/go-live/public").json()["go_live"] is False


# ---- Public notice filters ----
@pytest.fixture(scope="module")
def tagged_notice():
    """Tag one existing published notice (temporarily) with taxonomy; restore after."""
    n = mdb.notices.find_one({"is_published": True})
    if not n:
        pytest.skip("no published notice")
    orig = {k: n.get(k) for k in ("sector_code", "contract_type_code")}
    mdb.notices.update_one({"_id": n["_id"]}, {"$set": {"sector_code": "TEST_sec_v56s", "contract_type_code": "TEST_ct_v56s"}})
    yield n
    mdb.notices.update_one({"_id": n["_id"]}, {"$set": orig} if any(orig.values()) else {"$unset": {"sector_code": "", "contract_type_code": ""}})


def test_public_filter_sector(tagged_notice):
    r = requests.get(f"{API}/notices", params={"sector_code": "TEST_sec_v56s"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["notice_ref"] == tagged_notice["notice_ref"]


def test_public_filter_contract(tagged_notice):
    items = requests.get(f"{API}/notices", params={"contract_type_code": "TEST_ct_v56s"}).json()["items"]
    assert [i["notice_ref"] for i in items] == [tagged_notice["notice_ref"]]
    assert requests.get(f"{API}/notices", params={"contract_type_code": "nope_xyz"}).json()["total"] == 0


def test_public_filter_category(tagged_notice):
    cat = tagged_notice.get("category")
    items = requests.get(f"{API}/notices", params={"category": cat, "limit": 100}).json()["items"]
    assert items and all(i.get("category") == cat for i in items)


def test_public_filter_power_returns_only_power():
    items = requests.get(f"{API}/notices", params={"sector_code": "power", "limit": 100}).json()["items"]
    assert all(i.get("sector_code") == "power" and i.get("is_published", True) for i in items)


# ---- Vendor category request taxonomy ----
def test_vendor_category_request_persists_taxonomy(vendor):
    mine = vendor.get(f"{API}/vendor/categories/mine")
    assert mine.status_code == 200, mine.text
    approved = set(mine.json()["approved"])
    pending_codes = {p["category_code"] for p in mine.json()["pending"]}
    cat = next((c for c in mdb.categories.find({"is_active": True})
                if c.get("name") not in approved and c["code"] not in pending_codes), None)
    if not cat:
        pytest.skip("no free category")
    r = vendor.post(f"{API}/vendor/categories/request", json={
        "category_code": cat["code"], "category_name": cat.get("name") or cat["code"], "rationale": "TEST_v56s",
        "sector_code": "power", "sector_name": "Power & Energy",
        "contract_type_code": "epc", "contract_type_name": "EPC Contracts"})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    try:
        pend = vendor.get(f"{API}/vendor/categories/mine").json()["pending"]
        p = next(x for x in pend if x["id"] == rid)
        assert p["sector_code"] == "power" and p["sector_name"] == "Power & Energy"
        assert p["contract_type_code"] == "epc" and p["contract_type_name"] == "EPC Contracts"
    finally:
        from bson import ObjectId
        mdb.vendor_category_requests.delete_one({"_id": ObjectId(rid)})
