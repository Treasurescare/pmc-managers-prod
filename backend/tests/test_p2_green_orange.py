"""P2 Green + Orange batch tests — SBD template library, FX conversion, Vendor KPI,
Audit chain integrity, Orgs/Departments admin flows.

Reference: iteration 10 review_request.
"""
import base64
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv as _load_dotenv  # type: ignore
_load_dotenv("/app/backend/.env")

from pymongo import MongoClient
from bson import ObjectId as _ObjectId

_MONGO = MongoClient(os.environ["MONGO_URL"])
_DB = _MONGO[os.environ["DB_NAME"]]

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@pmcmanagers.com", "password": "Admin@123"}
BUYER = {"email": "buyer@pmcmanagers.com", "password": "Buyer@123"}
VENDOR = {"email": "vendor@example.com", "password": "Vendor@123"}


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(creds):
    s = _session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed {creds['email']}: {r.status_code} {r.text}"
    return s


# ------- Shared session fixtures -------
@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def buyer():
    return _login(BUYER)


@pytest.fixture(scope="module")
def vendor():
    # Ensure vendor@example.com is approved+fee_paid so vendor KPI works
    _DB.users.update_one({"email": VENDOR["email"]},
                         {"$set": {"vendor_status": "approved", "registration_fee_paid": True}})
    return _login(VENDOR)


# ==========================================================================
# SBD template library
# ==========================================================================
class TestSbdTemplates:
    # Small data-URL payload (base64 for "hello sbd")
    _b64 = base64.b64encode(b"hello sbd contents pdf placeholder").decode()
    _data_url = f"data:application/pdf;base64,{_b64}"

    def _payload(self, tag="RFP"):
        return {
            "name": f"TEST_SBD_{tag}_{uuid.uuid4().hex[:6]}",
            "document_type": "rfp",
            "category": "Consulting & Advisory",
            "description": "Standard consulting RFP template",
            "file": {
                "name": "sbd_rfp.pdf",
                "mime": "application/pdf",
                "size": 34,
                "data": self._data_url,
            },
        }

    def test_a_admin_create_template(self, admin):
        p = self._payload("A")
        r = admin.post(f"{API}/sbd/templates", json=p, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == p["name"]
        assert d["document_type"] == "rfp"
        assert d["active"] is True
        assert "id" in d
        pytest.sbd_tid = d["id"]
        pytest.sbd_name = d["name"]

    def test_b_non_admin_cannot_create(self, buyer, vendor):
        p = self._payload("Nope")
        r1 = buyer.post(f"{API}/sbd/templates", json=p, timeout=15)
        assert r1.status_code == 403, r1.text
        r2 = vendor.post(f"{API}/sbd/templates", json=p, timeout=15)
        assert r2.status_code == 403, r2.text

    def test_c_list_active_templates(self, admin):
        r = admin.get(f"{API}/sbd/templates", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert any(it["id"] == pytest.sbd_tid for it in items)
        assert all(it.get("active") for it in items)

    def test_d_filter_by_document_type(self, admin):
        # Create an RFQ-type template
        p = self._payload("RFQ")
        p["document_type"] = "rfq"
        r = admin.post(f"{API}/sbd/templates", json=p, timeout=15)
        assert r.status_code == 200
        rfq_id = r.json()["id"]
        pytest.sbd_rfq_tid = rfq_id

        r2 = admin.get(f"{API}/sbd/templates?document_type=rfp", timeout=10)
        assert r2.status_code == 200
        rfp_items = r2.json()
        assert all(it["document_type"] == "rfp" for it in rfp_items)
        assert any(it["id"] == pytest.sbd_tid for it in rfp_items)
        assert not any(it["id"] == rfq_id for it in rfp_items)

    def test_e_get_by_id(self, admin):
        r = admin.get(f"{API}/sbd/templates/{pytest.sbd_tid}", timeout=10)
        assert r.status_code == 200
        assert r.json()["id"] == pytest.sbd_tid

    def test_f_non_admin_can_list_but_not_delete(self, buyer):
        r = buyer.get(f"{API}/sbd/templates", timeout=10)
        assert r.status_code == 200  # readable by any authenticated
        r2 = buyer.delete(f"{API}/sbd/templates/{pytest.sbd_rfq_tid}", timeout=10)
        assert r2.status_code == 403, r2.text

    def test_g_archive_template(self, admin):
        r = admin.delete(f"{API}/sbd/templates/{pytest.sbd_rfq_tid}", timeout=10)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # verify not in active list
        items = admin.get(f"{API}/sbd/templates", timeout=10).json()
        assert not any(it["id"] == pytest.sbd_rfq_tid for it in items)

    def test_h_create_tender_with_sbd_template_auto_attaches(self, buyer):
        deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        payload = {
            "document_type": "rfp",
            "title": f"TEST_SBD_Tender_{uuid.uuid4().hex[:6]}",
            "description": "Tender using SBD template",
            "category": "Consulting & Advisory",
            "budget_currency": "USD",
            "budget_amount": 50000,
            "submission_deadline": deadline,
            "delivery_location": "Astana",
            "scope_of_work": "x",
            "evaluation_criteria": [
                {"name": "Technical", "weight": 60, "description": "m"},
                {"name": "Commercial", "weight": 40, "description": "p"},
            ],
            "sbd_template_id": pytest.sbd_tid,
        }
        r = buyer.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        atts = t.get("attachments") or []
        assert any(a.get("sbd_template") for a in atts), f"no sbd attachment: {atts}"
        assert t.get("sbd_template_name") == pytest.sbd_name
        pytest.sbd_tender_id = t["id"]

        # GET tender re-verifies persistence
        g = buyer.get(f"{API}/tenders/{t['id']}", timeout=10).json()
        assert any(a.get("sbd_template_id") == pytest.sbd_tid for a in (g.get("attachments") or []))

    def test_i_invalid_sbd_template_id_ignored_gracefully(self, buyer):
        deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        payload = {
            "title": f"TEST_SBD_Bad_{uuid.uuid4().hex[:6]}",
            "description": "invalid sbd id",
            "category": "Consulting & Advisory",
            "budget_currency": "USD",
            "budget_amount": 5000,
            "submission_deadline": deadline,
            "delivery_location": "Astana",
            "sbd_template_id": "not-a-valid-oid",
        }
        r = buyer.post(f"{API}/tenders", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        # Should not have sbd attachment; no crash
        assert not any(a.get("sbd_template") for a in (t.get("attachments") or []))


# ==========================================================================
# FX conversion
# ==========================================================================
class TestFxConversion:
    def test_fx_rates_default_base_usd(self, buyer):
        r = buyer.get(f"{API}/fx/rates?base=USD", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["base"] == "USD"
        rates = d.get("rates") or {}
        # If network permits, we expect KZT/EUR/RUB present. If empty, warn but don't fail.
        if not rates:
            pytest.skip("FX external API returned empty rates — treated as ok per review_request")
        for k in ("KZT", "EUR", "RUB"):
            assert k in rates, f"{k} missing in rates"
            assert rates[k] > 0

    def test_fx_convert_valid(self, buyer):
        r = buyer.get(f"{API}/fx/convert?amount=1000&source=USD&target=KZT", timeout=20)
        assert r.status_code in (200, 400)
        if r.status_code == 400:
            pytest.skip("FX external API unavailable — 400 on missing rate")
        d = r.json()
        assert d["converted"] > 0
        assert d["rate"] > 0

    def test_fx_convert_same_source_target(self, buyer):
        r = buyer.get(f"{API}/fx/convert?amount=500&source=USD&target=USD", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["rate"] == 1.0
        assert d["converted"] == 500

    def test_fx_convert_unknown_target(self, buyer):
        r = buyer.get(f"{API}/fx/convert?amount=100&source=USD&target=ZZZ", timeout=15)
        # If rates loaded, ZZZ missing -> 400. If rates empty, will also 400.
        assert r.status_code == 400, r.text

    def test_fx_requires_auth(self):
        r = requests.get(f"{API}/fx/rates?base=USD", timeout=15)
        assert r.status_code == 401


# ==========================================================================
# Vendor KPI dashboard
# ==========================================================================
class TestVendorKpi:
    def test_vendor_kpi_shape(self, vendor):
        r = vendor.get(f"{API}/vendor/kpi", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("total_bids", "awarded", "submitted", "rejected", "win_rate",
                  "avg_price_amount", "avg_delivery_days", "by_category",
                  "emd_forfeited", "emd_refunded"):
            assert k in d, f"missing {k}"
        assert isinstance(d["by_category"], list)
        assert isinstance(d["win_rate"], (int, float))

    def test_buyer_forbidden(self, buyer):
        r = buyer.get(f"{API}/vendor/kpi", timeout=10)
        assert r.status_code == 403

    def test_admin_forbidden(self, admin):
        r = admin.get(f"{API}/vendor/kpi", timeout=10)
        assert r.status_code == 403


# ==========================================================================
# Audit chain — list, filters, verify, tamper detection
# ==========================================================================
class TestAuditChain:
    def test_a_list_audit_admin(self, admin):
        r = admin.get(f"{API}/admin/audit", timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        # Must be sorted seq desc
        if len(rows) >= 2:
            assert rows[0]["seq"] > rows[-1]["seq"]
        pytest.audit_all = rows

    def test_b_audit_non_admin_forbidden(self, buyer, vendor):
        for s in (buyer, vendor):
            r = s.get(f"{API}/admin/audit", timeout=10)
            assert r.status_code == 403
            v = s.get(f"{API}/admin/audit/verify", timeout=10)
            assert v.status_code == 403

    def test_c_filter_by_action(self, admin):
        r = admin.get(f"{API}/admin/audit?action=tender.create", timeout=10)
        assert r.status_code == 200
        rows = r.json()
        assert all(x["action"] == "tender.create" for x in rows), rows

    def test_d_filter_by_target_id(self, admin):
        # find any tender.create row to reuse its target_id
        rows = admin.get(f"{API}/admin/audit?action=tender.create&limit=10", timeout=10).json()
        if not rows:
            pytest.skip("no tender.create rows to filter by")
        tid = rows[0]["target_id"]
        r = admin.get(f"{API}/admin/audit?target_id={tid}", timeout=10)
        assert r.status_code == 200
        got = r.json()
        assert all(x["target_id"] == tid for x in got)
        assert len(got) >= 1

    def test_e_verify_chain_ok(self, admin):
        r = admin.get(f"{API}/admin/audit/verify", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True, f"chain broken pre-tamper: {d}"
        assert d["checked"] >= 1
        assert d["tampered"] == []
        pytest.audit_head_hash = d["head_hash"]
        pytest.audit_checked = d["checked"]

    def test_f_seq_monotonic_and_hashes_link(self, admin):
        rows = admin.get(f"{API}/admin/audit?limit=500", timeout=15).json()
        # rows are seq desc — reverse to ascending
        asc = list(reversed(rows))
        for i in range(1, len(asc)):
            assert asc[i]["seq"] == asc[i - 1]["seq"] + 1, \
                f"seq gap between {asc[i-1]['seq']} and {asc[i]['seq']}"
        # previous_hash linkage
        for i in range(1, len(asc)):
            assert asc[i]["previous_hash"] == asc[i - 1]["event_hash"], \
                f"chain break at seq {asc[i]['seq']}: prev_hash mismatch"

    def test_g_e2e_new_events_appear_and_verify(self, buyer, vendor, admin):
        # Fresh tender.create
        deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        title = f"TEST_AUDIT_E2E_{uuid.uuid4().hex[:6]}"
        rc = buyer.post(f"{API}/tenders", json={
            "title": title,
            "description": "e2e audit",
            "category": "Consulting & Advisory",
            "budget_currency": "USD",
            "budget_amount": 5000,
            "submission_deadline": deadline,
            "delivery_location": "Astana",
        }, timeout=15)
        assert rc.status_code == 200
        tid = rc.json()["id"]

        # Verify audit contains tender.create for this tender
        rows = admin.get(f"{API}/admin/audit?target_id={tid}", timeout=10).json()
        assert any(x["action"] == "tender.create" for x in rows)

        # Chain still verifies
        v = admin.get(f"{API}/admin/audit/verify", timeout=30).json()
        assert v["ok"] is True, v

    def test_h_tamper_detection(self, admin):
        # Grab a mid-chain audit event and mutate its 'details' directly in Mongo
        rows = admin.get(f"{API}/admin/audit?limit=500", timeout=15).json()
        assert len(rows) >= 2
        # Pick a non-head event to avoid impacting the head_hash returned
        victim = rows[-1]  # oldest in this list
        vid = victim["id"]
        original = _DB.audit_events.find_one({"_id": _ObjectId(vid)})
        assert original is not None
        try:
            _DB.audit_events.update_one({"_id": _ObjectId(vid)},
                                        {"$set": {"details": {"TAMPERED": True}}})
            v = admin.get(f"{API}/admin/audit/verify", timeout=30).json()
            assert v["ok"] is False, f"tamper not detected: {v}"
            assert any(t["seq"] == victim["seq"] for t in v["tampered"]), v
        finally:
            # Restore original details
            _DB.audit_events.update_one({"_id": _ObjectId(vid)},
                                        {"$set": {"details": original.get("details") or {}}})
            # Confirm restored
            v2 = admin.get(f"{API}/admin/audit/verify", timeout=30).json()
            assert v2["ok"] is True, f"chain not restored after cleanup: {v2}"


# ==========================================================================
# Orgs / Departments admin CRUD (backing /admin/orgs page)
# ==========================================================================
class TestOrgsDepartments:
    def test_a_list_orgs_seeded(self, admin):
        r = admin.get(f"{API}/orgs", timeout=10)
        assert r.status_code == 200
        orgs = r.json()
        assert isinstance(orgs, list)
        # seeded PMC-GLOBAL should exist
        assert any(o.get("code") == "PMC-GLOBAL" for o in orgs), orgs

    def test_b_create_org_admin_only(self, admin, buyer):
        payload = {"name": f"TEST_ORG_{uuid.uuid4().hex[:5]}", "code": f"TST-{uuid.uuid4().hex[:4].upper()}", "country": "KZ"}
        # buyer forbidden
        r0 = buyer.post(f"{API}/orgs", json=payload, timeout=10)
        assert r0.status_code == 403
        r = admin.post(f"{API}/orgs", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["name"] == payload["name"]
        assert "id" in o
        pytest.test_org_id = o["id"]

    def test_c_create_department_with_thresholds(self, admin):
        payload = {
            "org_id": pytest.test_org_id,
            "name": f"TEST_DEPT_{uuid.uuid4().hex[:5]}",
            "code": f"TD-{uuid.uuid4().hex[:4].upper()}",
            "approval_thresholds": [{"threshold": 25000, "level": "finance"}],
        }
        r = admin.post(f"{API}/departments", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == payload["name"]
        assert any(t.get("level") == "finance" and (t.get("threshold") == 25000 or t.get("amount") == 25000)
                   for t in (d.get("approval_thresholds") or d.get("thresholds") or []))
