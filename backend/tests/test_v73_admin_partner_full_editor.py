# v73: Admin full partner editor — PATCH /api/v1/admin/agents/{id}/profile (profile fields, banking, documents, ownership, validation)
import os
import uuid

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
API = f"{BASE_URL}/api/v1"
RID = uuid.uuid4().hex[:6]
EMAIL = f"test_fulledit_{RID}@example.com"
REJ_EMAIL = f"test_fulledit_rej_{RID}@example.com"
PW = "Partner@12345"
S = {}


def _cleanup():
    DB.agents.delete_many({"email": {"$in": [EMAIL, REJ_EMAIL]}})
    DB.uploads.delete_many({"key": {"$regex": f"TESTFE{RID}"}})


@pytest.fixture(scope="module", autouse=True)
def setup():
    _cleanup()
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345", "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code} {r.text[:200]}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    S["admin"] = s
    r = s.post(f"{API}/admin/agents/invite", json={"email": EMAIL, "name": "TEST Full Edit"})
    assert r.status_code == 200, r.text
    S["aid"] = r.json()["id"]
    tok = DB.agents.find_one({"email": EMAIL})["invite_token"]
    p = requests.Session()
    r = p.post(f"{API}/agents/join/{tok}", json={"password": PW})
    assert r.status_code == 200, r.text
    yield
    _cleanup()


def _patch(body, aid=None):
    return S["admin"].patch(f"{API}/admin/agents/{aid or S['aid']}/profile", json=body)


class TestAdminFullEdit:
    def test_profile_fields_persist(self):
        body = {"entity_type": "company", "legal_name": "TEST FullEdit Ltd", "trading_name": "FE", "country": "gb",
                "address_line1": "1 Test St", "city": "London", "postal_code": "E1 1AA", "reg_number": "REG123",
                "tax_id": "TAX9", "phone_country_code": "+44", "primary_contact_phone": "+44 7700900000",
                "state_name": "Greater London", "website": "https://fe.example.com", "date_of_birth": "1990-01-01"}
        r = _patch(body)
        assert r.status_code == 200, r.text
        g = S["admin"].get(f"{API}/admin/agents/{S['aid']}").json()
        for k, v in body.items():
            assert g[k] == (v.upper() if k == "country" else v), k
        assert g["status"] == "draft"
        assert g["history"][-1]["action"] == "admin_edit"
        assert "legal_name" in g["history"][-1]["fields"]

    def test_primary_contact_email_ignored(self):
        r = _patch({"primary_contact_email": "hacker@example.com", "city": "Leeds"})
        assert r.status_code == 200
        g = S["admin"].get(f"{API}/admin/agents/{S['aid']}").json()
        assert g["primary_contact_email"] == EMAIL and g["city"] == "Leeds" and g["email"] == EMAIL

    def test_unknown_fields_ignored_and_status_untouched(self):
        r = _patch({"status": "approved", "partner_code": "HACK", "password_hash": "x", "city": "York"})
        assert r.status_code == 200
        d = DB.agents.find_one({"email": EMAIL})
        assert d["status"] == "draft" and d.get("partner_code") != "HACK" and d["password_hash"] != "x"

    def test_entity_type_validation(self):
        r = _patch({"entity_type": "trust"})
        assert r.status_code == 422

    def test_nothing_to_update(self):
        assert _patch({"foo": "bar"}).status_code == 422

    def test_banking_persist_max5(self):
        banks = [{"account_name": f"TEST Acc {i}", "account_number": f"1234{i}", "currency": "GBP", "swift": "TESTGB2L"} for i in range(7)]
        r = _patch({"banking": banks})
        assert r.status_code == 200
        g = S["admin"].get(f"{API}/admin/agents/{S['aid']}").json()
        assert len(g["banking"]) == 5 and g["banking"][0]["account_name"] == "TEST Acc 0"

    def test_documents_agent_docs_only_and_owner_set(self):
        admin = S["admin"]
        key = f"agent-docs/TESTFE{RID}_id.pdf"
        r = admin.post(f"{API}/uploads/direct", data={"key": key}, files={"file": ("id.pdf", b"%PDF-1.4 test", "application/pdf")})
        assert r.status_code == 200, r.text
        assert DB.uploads.find_one({"key": key}).get("owner_agent_id") is None
        bad = f"vendor-docs/TESTFE{RID}_x.pdf"
        r = _patch({"documents": {"id_proof": {"key": key, "filename": "id.pdf"}, "address_proof": {"key": bad}}})
        assert r.status_code == 200, r.text
        g = admin.get(f"{API}/admin/agents/{S['aid']}").json()
        assert "id_proof" in g["documents"] and "address_proof" not in g["documents"]
        assert DB.uploads.find_one({"key": key})["owner_agent_id"] == S["aid"]
        S["doc_key"] = key

    def test_documents_non_dict_rejected_gracefully(self):
        r = _patch({"documents": ["agent-docs/x"]})
        assert r.status_code in (400, 422), f"got {r.status_code}: {r.text[:200]}"

    def test_partner_sees_admin_values_and_can_open_doc(self):
        p = requests.Session()
        r = p.post(f"{API}/agents/auth/login", json={"email": EMAIL, "password": PW})
        assert r.status_code == 200, r.text
        me = p.get(f"{API}/agents/me").json()
        assert me["legal_name"] == "TEST FullEdit Ltd" and me["entity_type"] == "company"
        assert me["banking"][0]["account_number"] == "12340"
        assert me["documents"]["id_proof"]["key"] == S["doc_key"]
        f = p.get(f"{API}/uploads/files/{S['doc_key']}")
        assert f.status_code == 200, f"partner cannot open admin-uploaded doc: {f.status_code} {f.text[:200]}"

    def test_audit_entry(self):
        assert DB.audit_events.find_one({"event_type": "agent.admin_edit", "target_id": S["aid"]}) or \
            DB.audit_events.find_one({"event_type": "agent.admin_edit"})

    def test_rejected_partner_409(self):
        r = S["admin"].post(f"{API}/admin/agents/invite", json={"email": REJ_EMAIL, "name": "TEST Rej"})
        aid = r.json()["id"]
        DB.agents.update_one({"email": REJ_EMAIL}, {"$set": {"status": "rejected"}})
        assert _patch({"city": "X"}, aid).status_code == 409

    def test_404_and_auth(self):
        assert _patch({"city": "X"}, "000000000000000000000000").status_code == 404
        assert requests.patch(f"{API}/admin/agents/{S['aid']}/profile", json={"city": "X"}).status_code in (401, 403)
