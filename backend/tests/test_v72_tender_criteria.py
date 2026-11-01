# v72: Tender Criteria Builder (stage 1) — save/validate/lock, publish gate, public view, sealed bid answers; Google OAuth config.
import os
import json
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
ENV = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
DB = MongoClient(ENV["MONGO_URL"].strip('"'))[ENV["DB_NAME"].strip('"')]
API = f"{BASE_URL}/api/v1"
RID = uuid.uuid4().hex[:6].upper()
DRAFT = f"TEST-CRITB-{RID}"
BYPASS = f"TEST-CRITBP-{RID}"
VEMAIL = "northfield@demo.pmcmanagers.com"
S = {}

MUST = {"id": "mpturn01", "title": "Average annual turnover", "answer_type": "number", "operator": "gte",
        "threshold": 1000000, "unit": "USD", "proof": "Audited accounts", "proof_required": True,
        "kind": "must_pass", "consortium_rule": "lead"}
ISO = {"id": "mpiso001", "title": "ISO 9001 certification", "answer_type": "yes_no", "kind": "must_pass",
       "proof_required": False}
SCORED = {"id": "scmeth01", "title": "Methodology", "answer_type": "text", "kind": "scored", "max_points": 20,
          "scoring": "evaluator"}


def _future(days=5):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _cleanup():
    for ref in (DRAFT, BYPASS):
        DB.bids.delete_many({"notice_ref": ref})
        DB.notices.delete_many({"notice_ref": ref})
    DB.uploads.delete_many({"key": {"$regex": f"TESTCR{RID}"}})


@pytest.fixture(scope="module", autouse=True)
def setup():
    _cleanup()
    DB.notices.insert_one({"notice_ref": DRAFT, "title": f"TEST criteria {RID}", "is_published": False,
                           "kyc_bypass": True, "category": "", "budget_amount": 100000.0, "budget_currency": "USD",
                           "emd_config": {"fixed_amount": 0, "percentage": 0, "currency": "USD"},
                           "description": "x", "submission_deadline": _future(), "bid_opening_date": _future(6),
                           "created_at": datetime.now(timezone.utc).isoformat()})
    yield
    _cleanup()


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345",
                                                "active_role": "admin"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


@pytest.fixture(scope="module")
def vendor():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": VEMAIL, "password": "Demo@Pmc2026"})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code} {r.text[:200]}")
    if r.json().get("csrf_token"):
        s.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return s


def _upload(sess, name):
    key = f"bid-docs/TESTCR{RID}{uuid.uuid4().hex[:8]}_{name}"
    r = sess.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (name, b"%PDF-1.4 cr " + name.encode(), "application/pdf")})
    assert r.status_code == 200, r.text
    return key


# Templates + validation
class TestA_SaveValidate:
    def test_templates(self, admin):
        r = admin.get(f"{API}/tender-criteria/templates")
        assert r.status_code == 200
        assert len(r.json()["templates"]) >= 6 and "annual_turnover" in r.json()["prefill_fields"]

    @pytest.mark.parametrize("bad,msg", [
        ({**MUST, "unit": ""}, "unit"),
        ({**SCORED, "max_points": None}, "maximum points"),
        ({**SCORED, "kind": "must_pass"}, "pass/fail"),
        ({"title": "Staff", "answer_type": "number", "operator": "gte", "threshold": 5, "unit": "staff",
          "kind": "scored", "max_points": 10, "scoring": "auto"}, "full points"),
    ])
    def test_validation_422(self, admin, bad, msg):
        r = admin.put(f"{API}/tender-criteria/{DRAFT}", json={"criteria": [bad]})
        assert r.status_code == 422, r.text
        assert msg in r.text

    def test_duplicate_ids_422(self, admin):
        r = admin.put(f"{API}/tender-criteria/{DRAFT}", json={"criteria": [MUST, MUST]})
        assert r.status_code == 422

    def test_public_404_for_draft(self):
        assert requests.get(f"{API}/tender-criteria/{DRAFT}").status_code == 404

    def test_vendor_cannot_save(self, vendor):
        assert vendor.put(f"{API}/tender-criteria/{DRAFT}", json={"criteria": [MUST]}).status_code in (401, 403)


# Publish gate
class TestB_PublishGate:
    def test_publish_without_criteria_409(self, admin):
        r = admin.post(f"{API}/notices/{DRAFT}/publish")
        assert r.status_code == 409 and "criteria" in r.text.lower()

    def test_publish_with_only_scored_409(self, admin):
        assert admin.put(f"{API}/tender-criteria/{DRAFT}", json={"criteria": [SCORED]}).status_code == 200
        assert admin.post(f"{API}/notices/{DRAFT}/publish").status_code == 409

    def test_save_then_publish_ok(self, admin):
        r = admin.put(f"{API}/tender-criteria/{DRAFT}", json={"criteria": [MUST, ISO, SCORED], "fx_rule": "CB rate"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["criteria"]) == 3 and d["locked"] is False and d["fx_rule"] == "CB rate"
        g = admin.get(f"{API}/tender-criteria/{DRAFT}/admin").json()
        assert [c["id"] for c in g["criteria"]] == ["mpturn01", "mpiso001", "scmeth01"]
        assert g["criteria"][2]["scoring"] == "evaluator"
        assert admin.post(f"{API}/notices/{DRAFT}/publish").status_code == 200

    def test_locked_after_publish(self, admin):
        r = admin.put(f"{API}/tender-criteria/{DRAFT}", json={"criteria": [MUST]})
        assert r.status_code == 409
        assert admin.get(f"{API}/tender-criteria/{DRAFT}/admin").json()["locked"] is True

    def test_public_view_after_publish(self):
        r = requests.get(f"{API}/tender-criteria/{DRAFT}")
        assert r.status_code == 200 and len(r.json()["criteria"]) == 3 and r.json()["locked"] is True


# Publish bypass paths (PATCH is_published / create with is_published) — must also enforce must-pass gate
class TestC_PublishBypass:
    def test_patch_publish_without_criteria_blocked(self, admin):
        DB.notices.insert_one({"notice_ref": BYPASS, "title": f"TEST bypass {RID}", "is_published": False,
                               "budget_amount": 1000.0, "submission_deadline": _future(),
                               "created_at": datetime.now(timezone.utc).isoformat()})
        r = admin.patch(f"{API}/notices/{BYPASS}", json={"is_published": True})
        pub = DB.notices.find_one({"notice_ref": BYPASS})["is_published"]
        assert r.status_code == 409 and not pub, f"PATCH published a notice without criteria: {r.status_code} pub={pub}"


# Bid answers
class TestD_BidAnswers:
    def _docs(self, vendor, extra=()):
        now = datetime.now(timezone.utc).isoformat()
        d = [{"kind": "technical", "key": _upload(vendor, "t.pdf"), "filename": "t.pdf", "size_bytes": 10, "uploaded_at": now},
             {"kind": "commercial", "key": _upload(vendor, "c.pdf"), "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]
        return d + list(extra)

    def _post(self, vendor, docs, answers):
        return vendor.post(f"{API}/bids", json={"notice_ref": DRAFT, "price_amount": 5000, "price_currency": "USD",
                                                "technical_notes": "TN", "commercial_notes": "CN",
                                                "documents": docs, "criteria_answers": answers})

    def test_missing_answers_422(self, vendor):
        r = self._post(vendor, self._docs(vendor), [])
        assert r.status_code == 422, r.text
        assert "Please answer every tender criterion" in r.text and "Average annual turnover (proof)" in r.text

    def test_missing_proof_422(self, vendor):
        r = self._post(vendor, self._docs(vendor), [{"criterion_id": "mpturn01", "value": "2000000"},
                                                    {"criterion_id": "mpiso001", "value": True}])
        assert r.status_code == 422 and "(proof)" in r.text and "(answer)" not in r.text

    def test_proof_doc_does_not_count_as_envelope(self, vendor):
        now = datetime.now(timezone.utc).isoformat()
        docs = [{"kind": "technical", "key": _upload(vendor, "p.pdf"), "filename": "p.pdf", "size_bytes": 10,
                 "uploaded_at": now, "criterion_id": "mpturn01"},
                {"kind": "commercial", "key": _upload(vendor, "c.pdf"), "filename": "c.pdf", "size_bytes": 10, "uploaded_at": now}]
        r = self._post(vendor, docs, [{"criterion_id": "mpturn01", "value": 2e6}, {"criterion_id": "mpiso001", "value": True}])
        assert r.status_code == 422 and "technical envelope" in r.text

    def test_success_sealed(self, vendor, admin):
        now = datetime.now(timezone.utc).isoformat()
        proof = {"kind": "technical", "key": _upload(vendor, "proof.pdf"), "filename": "proof.pdf", "size_bytes": 10,
                 "uploaded_at": now, "criterion_id": "mpturn01"}
        r = self._post(vendor, self._docs(vendor, [proof]),
                       [{"criterion_id": "mpturn01", "value": "2,500,000"}, {"criterion_id": "mpiso001", "value": "yes"},
                        {"criterion_id": "scmeth01", "value": "Plan A"}])
        assert r.status_code in (200, 201), r.text
        b = DB.bids.find_one({"notice_ref": DRAFT, "status": {"$nin": ["withdrawn"]}})
        assert b is not None
        S["bid_id"] = str(b["_id"])
        assert b.get("criteria_answers_json") is None, "plaintext answers stored in DB"
        assert "criteria_answers_json" in json.dumps(list((b.get("sealed") or {}).keys())) or \
            "criteria_answers_json" in str(b.get("sealed"))
        assert "2500000" not in str(b.get("sealed")), "answers not encrypted"
        assert all("criterion_id" in d for d in b["documents"])  # field present (None for envelopes)
        assert any(d.get("criterion_id") == "mpturn01" for d in b["documents"])

    def test_admin_preopening_redacted(self, admin):
        if "bid_id" not in S:
            pytest.skip("no bid")
        r = admin.get(f"{API}/bids/admin/{S['bid_id']}")
        assert r.status_code == 200, r.text
        txt = r.text
        assert "2500000" not in txt and "Plan A" not in txt
        assert r.json().get("criteria_answers_json") is None
        lst = admin.get(f"{API}/bids", params={"notice_ref": DRAFT})
        assert "2500000" not in lst.text and "Plan A" not in lst.text


# Google OAuth (PMC client) not configured
class TestE_Google:
    def test_config_disabled(self):
        r = requests.get(f"{API}/auth/google/config")
        assert r.status_code == 200 and r.json() == {"enabled": False}

    def test_start_503(self):
        r = requests.post(f"{API}/auth/google/start", json={"portal": "supplier",
                                                            "redirect_uri": f"{BASE_URL}/auth/google/callback"})
        assert r.status_code == 503
