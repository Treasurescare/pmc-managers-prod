# R14 — RFQ/RFP master templates (seed, clone keeps kind, kind-styled AI draft) + vendor unread message count.
# Run serially: pytest tests/test_r14_rfq_rfp_unread.py -n 0
import os
import re
import pytest
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
VENDOR = ("testvendor@pmcmanagers.com", "Vendor@12345")
ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
_mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ST = {}


def _login(path, cred):
    s = requests.Session()
    r = s.post(f"{API}/{path}", json={"email": cred[0], "password": cred[1]})
    assert r.status_code == 200, r.text
    s.headers.update({"X-CSRF-Token": r.json().get("csrf_token") or ""})
    return s


@pytest.fixture(scope="module")
def admin():
    s = _login("admin/auth/login", ADMIN)
    yield s
    _mdb.tender_templates.delete_many({"name": {"$regex": "^TEST_R14"}})


@pytest.fixture(scope="module")
def vendor():
    s = _login("vendor/auth/login", VENDOR)
    yield s
    _mdb.messages.delete_many({"subject": {"$regex": "^TEST_"}})


def _text(html):
    return re.sub(r"<[^>]+>", " ", html or "")


# --- Masters seeded ---
class TestMasters:
    def test_rfq_master(self, admin):
        r = admin.get(f"{API}/tender-templates", params={"kind": "rfq"})
        assert r.status_code == 200, r.text
        m = [d for d in r.json() if d.get("is_master") and d["name"] == "Standard Request for Quotation (RFQ)"]
        assert len(m) == 1, [d["name"] for d in r.json()]
        codes = [s["code"] for s in m[0]["sections"]]
        assert codes == ["rfq-1", "rfq-2", "rfq-3", "rfq-4", "rfq-5", "rfq-6", "rfq-form-A", "rfq-form-B"]
        assert m[0]["kind"] == "rfq"
        ST["rfq_master"] = m[0]

    def test_rfp_master(self, admin):
        r = admin.get(f"{API}/tender-templates", params={"kind": "rfp"})
        assert r.status_code == 200
        m = [d for d in r.json() if d.get("is_master") and d["name"] == "Standard Request for Proposal (RFP)"]
        assert len(m) == 1
        assert len(m[0]["sections"]) == 10
        assert m[0]["kind"] == "rfp"
        ST["rfp_master"] = m[0]

    def test_seed_db_unique(self):
        for k in ("rfq", "rfp"):
            assert _mdb.tender_templates.count_documents({"is_master": True, "seed": True, "kind": k}) == 1

    def test_vendor_sees_masters(self, vendor):
        r = vendor.get(f"{API}/tender-templates", params={"kind": "rfq"})
        assert r.status_code == 200
        assert any(d.get("is_master") and d["kind"] == "rfq" for d in r.json())


# --- Clone + AI draft per kind ---
def _clone(admin, master, kind):
    secs = [{k: s.get(k) for k in ("code", "kind", "title", "hint", "body", "order")} for s in master["sections"]]
    payload = {"name": f"TEST_R14 {kind} draft", "kind": master["kind"], "industry": master.get("industry"),
               "header": {**(master.get("header") or {}), "work_title": "Supply of 200 LED street lights",
                          "budget_amount": 50000, "budget_currency": "USD"},
               "sections": secs}
    r = admin.post(f"{API}/tender-templates", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["kind"] == kind and d["is_master"] is False
    g = admin.get(f"{API}/tender-templates/{d['id']}")
    assert g.status_code == 200 and g.json()["kind"] == kind
    return d["id"]


def _master(admin, kind):
    r = admin.get(f"{API}/tender-templates", params={"kind": kind})
    return next(d for d in r.json() if d.get("is_master") and d["kind"] == kind)


@pytest.fixture(scope="module")
def drafts(admin):
    ST["rfq_id"] = _clone(admin, _master(admin, "rfq"), "rfq")
    ST["rfp_id"] = _clone(admin, _master(admin, "rfp"), "rfp")
    return ST


class TestCloneDraft:
    def test_clone_rfq(self, admin, drafts):
        lst = admin.get(f"{API}/tender-templates", params={"kind": "rfq"}).json()
        assert any(d["id"] == drafts["rfq_id"] for d in lst)

    def test_clone_rfp(self, admin, drafts):
        assert drafts["rfp_id"]

    def test_ai_draft_rfq(self, admin, drafts):
        r = admin.post(f"{API}/tender-templates/{ST['rfq_id']}/sections/rfq-4/ai-draft",
                       json={"tone": "formal", "length": "medium"}, timeout=180)
        assert r.status_code == 200, r.text
        body = r.json()["body"]
        ST["rfq_body"] = body
        print("RFQ words:", len(_text(body).split()), "\n", _text(body)[:800])
        assert len(body) > 50
        t = _text(body).lower()
        assert any(w in t for w in ("price", "quot", "payment", "tax"))

    def test_ai_draft_rfp(self, admin, drafts):
        r = admin.post(f"{API}/tender-templates/{ST['rfp_id']}/sections/rfp-6/ai-draft",
                       json={"tone": "formal", "length": "medium"}, timeout=180)
        assert r.status_code == 200, r.text
        body = r.json()["body"]
        print("RFP words:", len(_text(body).split()), "\n", _text(body)[:800])
        t = _text(body).lower()
        assert any(w in t for w in ("weight", "score", "methodolog", "criteria"))

    def test_ai_draft_bad_section(self, admin, drafts):
        r = admin.post(f"{API}/tender-templates/{ST['rfq_id']}/sections/nope/ai-draft", json={})
        assert r.status_code == 404


# --- Unread count ---
class TestUnread:
    def test_requires_auth(self):
        r = requests.get(f"{API}/vendor/messages/unread-count")
        assert r.status_code == 401

    def test_admin_cannot(self, admin):
        r = admin.get(f"{API}/vendor/messages/unread-count")
        assert r.status_code in (401, 403)

    def test_count_and_read(self, vendor):
        base = vendor.get(f"{API}/vendor/messages/unread-count").json()["unread"]
        ins = _mdb.messages.insert_one({"to_vendor_ref": "VEN-TEST01", "from": "PMC Managers", "kind": "payment",
                                        "subject": "TEST_ badge api", "body": "<p>x</p>", "read": False,
                                        "created_at": datetime.now(timezone.utc).isoformat()})
        r = vendor.get(f"{API}/vendor/messages/unread-count")
        assert r.status_code == 200 and r.json() == {"unread": base + 1}
        lst = vendor.get(f"{API}/vendor/messages").json()
        assert lst["unread"] == base + 1
        rr = vendor.post(f"{API}/vendor/messages/{ins.inserted_id}/read")
        assert rr.status_code == 200
        assert vendor.get(f"{API}/vendor/messages/unread-count").json()["unread"] == base
        # other vendor's message must not count
        _mdb.messages.insert_one({"to_vendor_ref": "VEN-OTHER99", "subject": "TEST_ other", "read": False,
                                  "created_at": datetime.now(timezone.utc).isoformat()})
        assert vendor.get(f"{API}/vendor/messages/unread-count").json()["unread"] == base
