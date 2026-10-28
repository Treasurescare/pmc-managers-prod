# R7 governance/integrity hardening — /api/v1/governance-controls regression tests
import os
import re
import secrets
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
GC = f"{API}/governance-controls"
TAG = "TEST_R7_" + secrets.token_hex(3).upper()


def _login(email, pw_list):
    for pw in pw_list:
        r = requests.post(f"{API}/admin/auth/login", json={"email": email, "password": pw})
        if r.status_code == 200:
            d = r.json()
            s = requests.Session()
            s.headers.update({"Authorization": "Bearer " + d["token"], "X-CSRF-Token": d["csrf_token"]})
            s.email = email
            return s
    return None


@pytest.fixture(scope="module")
def admin():
    s = _login("adminsupport@pmcmanagers.com", ["Admin@12345", "Admin@123"])
    if not s:
        pytest.skip("admin login failed")
    return s


@pytest.fixture(scope="module")
def owner():
    s = _login("kannan@emeraldcorporates.com", ["Owner@123"])
    if not s:
        pytest.skip("owner login failed")
    return s


@pytest.fixture(scope="module")
def legal():
    s = _login("legal@pmcmanagers.com", ["Legal@123"])
    if not s:
        pytest.skip("legal login failed")
    return s


@pytest.fixture(scope="module")
def committee():
    s = _login("committee@pmcmanagers.com", ["Bid@1234"])
    if not s:
        pytest.skip("committee login failed")
    return s


# --- AI price leak (static source check)
def test_ai_compare_scope_has_no_price():
    src = open("/app/backend/routers/bids_ai_compare.py").read()
    m = re.search(r"async def _fetch_bid_scope.*?return \"\\n\"\.join\(parts\)", src, re.S)
    assert m
    body = m.group(0)
    parts = body[body.index("parts = ["):]
    assert "price" not in parts.lower()


# --- Auth gate
def test_exceptions_requires_auth():
    r = requests.get(f"{GC}/exceptions")
    assert r.status_code in (401, 403)


def test_exceptions_list_admin(admin):
    r = admin.get(f"{GC}/exceptions")
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d["items"], list) and d["count"] == len(d["items"])
    assert all("_id" not in i for i in d["items"])


def test_exceptions_forbidden_for_legal(legal):
    assert legal.get(f"{GC}/exceptions").status_code == 403


# --- Buyer classification + SoD
def test_buyer_classify_and_sod(admin, legal, owner):
    nref = f"{TAG}-NOT"
    r = admin.post(f"{GC}/buyer-classifications", json={
        "notice_ref": nref, "buyer_name": "TEST Ministry", "buyer_type": "public_sector",
        "basis": "Government ministry procurement"})
    assert r.status_code == 200 and r.json()["status"] == "pending_verification"
    items = admin.get(f"{GC}/buyer-classifications").json()["items"]
    row = next(i for i in items if i["notice_ref"] == nref)
    assert row["classified_by"] == "adminsupport@pmcmanagers.com"
    # SoD negative
    r = admin.post(f"{GC}/buyer-classifications/verify", json={"notice_ref": nref, "agree": True})
    assert r.status_code == 403, r.text
    assert "Separation of duties" in r.json()["detail"]
    # positive with legal counsel
    r = legal.post(f"{GC}/buyer-classifications/verify", json={"notice_ref": nref, "agree": True})
    assert r.status_code == 200 and r.json()["status"] == "verified"
    row = next(i for i in admin.get(f"{GC}/buyer-classifications").json()["items"] if i["notice_ref"] == nref)
    assert row["verified_by"] == "legal@pmcmanagers.com"


def test_buyer_verify_override_writes_exception(admin, owner):
    nref = f"{TAG}-NOT2"
    admin.post(f"{GC}/buyer-classifications", json={
        "notice_ref": nref, "buyer_name": "TEST Corp", "buyer_type": "private_sector", "basis": "Listed company"})
    r = owner.post(f"{GC}/buyer-classifications/verify", json={
        "notice_ref": nref, "agree": False, "override_type": "public_sector", "note": "State owned"})
    assert r.status_code == 200 and r.json()["buyer_type"] == "public_sector"
    ex = admin.get(f"{GC}/exceptions", params={"kind": "buyer_classification_override"}).json()["items"]
    assert any(e["target_id"] == nref for e in ex)


def test_buyer_verify_404(legal):
    r = legal.post(f"{GC}/buyer-classifications/verify", json={"notice_ref": f"{TAG}-NONE", "agree": True})
    assert r.status_code == 404


def test_buyer_classify_validation(admin):
    r = admin.post(f"{GC}/buyer-classifications", json={
        "notice_ref": "x", "buyer_name": "A", "buyer_type": "bogus", "basis": "b"})
    assert r.status_code == 422


# --- Integrity committee + override
def test_integrity_flow_and_override(admin, committee):
    r = admin.post(f"{GC}/integrity-cases", json={
        "notice_ref": f"{TAG}-NOT", "title": "TEST suspicious", "reason": "Identical bid docs"})
    assert r.status_code == 200
    ref = r.json()["case_ref"]
    assert ref.startswith("INT-")
    assert any(c["case_ref"] == ref for c in admin.get(f"{GC}/integrity-cases").json()["items"])
    r = committee.post(f"{GC}/integrity-cases/review", json={"case_ref": ref, "vote": "uphold"})
    assert r.status_code == 200 and len(r.json()["reviews"]) == 1
    r = committee.post(f"{GC}/integrity-cases/resolve", json={"case_ref": ref, "resolution": "upheld"})
    assert r.status_code == 200 and r.json()["status"] == "upheld"
    # override short reason
    r = admin.post(f"{GC}/integrity-cases/senior-override", json={"case_ref": ref, "decision": "dismissed", "reason": "short"})
    assert r.status_code == 422
    # committee member (non-admin) cannot override
    r = committee.post(f"{GC}/integrity-cases/senior-override", json={"case_ref": ref, "decision": "dismissed", "reason": "Overriding committee decision"})
    assert r.status_code == 403
    r = admin.post(f"{GC}/integrity-cases/senior-override", json={"case_ref": ref, "decision": "dismissed", "reason": "Board overrides the committee decision"})
    assert r.status_code == 200 and r.json()["status"] == "overridden"
    case = next(c for c in admin.get(f"{GC}/integrity-cases").json()["items"] if c["case_ref"] == ref)
    assert case["status"] == "overridden" and case["senior_override"]["disclosed"] is True
    ex = admin.get(f"{GC}/exceptions", params={"kind": "integrity_override"}).json()["items"]
    assert any(e["target_id"] == ref for e in ex)
    # review after override -> 409
    r = committee.post(f"{GC}/integrity-cases/review", json={"case_ref": ref, "vote": "uphold"})
    assert r.status_code == 409


# --- Collusion
def test_collusion_empty_notice(admin):
    r = admin.get(f"{GC}/collusion/{TAG}-NOBIDS")
    assert r.status_code == 200
    d = r.json()
    assert d["bidder_count"] == 0 and d["flag_count"] == 0 and d["flags"] == [] and d["disclaimer"]


def test_collusion_real_notice(admin):
    r = admin.get(f"{GC}/collusion/PMC-NOT-2026-0016")
    assert r.status_code == 200
    assert set(r.json().keys()) >= {"notice_ref", "bidder_count", "flag_count", "flags", "disclaimer"}


# --- Fee waivers maker-checker
def test_fee_waiver_sod_and_exception(admin, owner):
    r = admin.post(f"{GC}/fee-waivers", json={
        "subject_type": "vendor", "subject_ref": f"{TAG}-VEN", "fee_type": "registration",
        "amount": 100, "currency": "USD", "reason": "TEST hardship waiver"})
    assert r.status_code == 200
    ref = r.json()["waiver_ref"]
    assert any(w["waiver_ref"] == ref and w["status"] == "pending" for w in admin.get(f"{GC}/fee-waivers").json()["items"])
    r = admin.post(f"{GC}/fee-waivers/decide", json={"waiver_ref": ref, "decision": "approved"})
    assert r.status_code == 403, r.text
    r = owner.post(f"{GC}/fee-waivers/decide", json={"waiver_ref": ref, "decision": "approved", "note": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    ex = admin.get(f"{GC}/exceptions", params={"kind": "fee_waiver"}).json()["items"]
    assert any(e["details"].get("waiver_ref") == ref for e in ex)
    r = owner.post(f"{GC}/fee-waivers/decide", json={"waiver_ref": ref, "decision": "rejected"})
    assert r.status_code == 409


def test_fee_waiver_reject_no_exception(admin, owner):
    ref = admin.post(f"{GC}/fee-waivers", json={
        "subject_type": "notice", "subject_ref": f"{TAG}-N", "fee_type": "doc_fee",
        "amount": 5, "reason": "TEST reject path"}).json()["waiver_ref"]
    assert owner.post(f"{GC}/fee-waivers/decide", json={"waiver_ref": ref, "decision": "rejected"}).status_code == 200
    ex = admin.get(f"{GC}/exceptions", params={"kind": "fee_waiver"}).json()["items"]
    assert not any(e["details"].get("waiver_ref") == ref for e in ex)


# --- Legal register
def test_legal_register_upsert(admin, legal):
    c = f"{TAG}-Land"
    r = legal.post(f"{GC}/legal-register", json={"country": c, "legal_status": "pending", "counsel_note": "TEST"})
    assert r.status_code == 200
    r = admin.post(f"{GC}/legal-register", json={"country": c, "legal_status": "approved"})
    assert r.status_code == 200
    rows = [i for i in admin.get(f"{GC}/legal-register").json()["items"] if i["country"] == c]
    assert len(rows) == 1 and rows[0]["legal_status"] == "approved"


def test_legal_register_forbidden_committee(committee):
    r = committee.post(f"{GC}/legal-register", json={"country": "Nowhere", "legal_status": "approved"})
    assert r.status_code == 403


# --- Incidents + public SLA
def test_incident_flow_public(admin):
    r = admin.post(f"{GC}/incidents", json={
        "title": f"{TAG} outage", "severity": "high", "category": "live_opening",
        "impact": "Opening delayed", "public_disclosure": True, "public_statement": "TEST statement"})
    assert r.status_code == 200
    ref = r.json()["incident_ref"]
    r = admin.post(f"{GC}/incidents/update", json={"incident_ref": ref, "status": "resolved"})
    assert r.status_code == 200
    pub = requests.get(f"{GC}/public/incidents")
    assert pub.status_code == 200
    d = pub.json()
    assert "sla" in d and "bid_acceptance" in d["sla"]
    inc = next(i for i in d["incidents"] if i["incident_ref"] == ref)
    assert inc["status"] == "resolved" and inc["resolved_at"] and inc["statement"] == "TEST statement"
    assert "created_by" not in inc


def test_private_incident_not_public(admin):
    ref = admin.post(f"{GC}/incidents", json={
        "title": f"{TAG} private", "severity": "low", "category": "other",
        "impact": "Internal only"}).json()["incident_ref"]
    d = requests.get(f"{GC}/public/incidents").json()
    assert not any(i["incident_ref"] == ref for i in d["incidents"])
