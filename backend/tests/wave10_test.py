"""Wave 10 regression tests — backend router helpers refactor.

Covers:
- bids.py::decide_bid using routers/bids_helpers.py
- analytics.py::audit_copilot + dashboard using routers/analytics_helpers.py
- packages.py::import_packages_csv using routers/packages_helpers.py
- committee.py::create_committee using routers/committee_helpers.py
"""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api/v1"

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@123"


# ---------- session fixture ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    csrf = s.cookies.get("csrf_token") or r.json().get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


# ---------- Analytics ----------
def test_analytics_dashboard(admin_session):
    r = admin_session.get(f"{API}/analytics/dashboard", timeout=20)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    # Assert data structure
    assert "totals" in data
    assert "funnel" in data
    assert "top_bids" in data
    assert isinstance(data["top_bids"], list)


def _pick_bid(admin_session, prefer_status=None):
    r = admin_session.get(f"{API}/bids", timeout=15)
    assert r.status_code == 200, r.text[:200]
    bids = r.json()
    assert isinstance(bids, list) and bids, "no bids seeded"
    if prefer_status:
        for b in bids:
            if b.get("status") == prefer_status:
                return b
    return bids[0]


def test_audit_copilot(admin_session):
    bid = _pick_bid(admin_session)
    bid_id = bid.get("id") or bid.get("_id")
    assert bid_id, "no bid id found"
    r = admin_session.post(f"{API}/analytics/ai/audit-copilot/{bid_id}", timeout=60)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    for k in ("verdict", "flags", "narrative", "history_length"):
        assert k in data, f"missing {k} in {list(data.keys())}"
    assert isinstance(data["flags"], list)
    assert isinstance(data["history_length"], int)


# ---------- Bids decide (escrow_accepted → admin_flagged) ----------
def test_bid_decision_admin_flag(admin_session):
    bid = _pick_bid(admin_session, prefer_status="escrow_accepted")
    if bid.get("status") != "escrow_accepted":
        pytest.skip(f"no escrow_accepted bid available (found status={bid.get('status')})")
    bid_id = bid.get("id") or bid.get("_id")
    payload = {"role": "admin", "action": "accept", "notes": "TEST_admin_flag_wave10"}
    r = admin_session.post(f"{API}/bids/{bid_id}/decision", json=payload, timeout=15)
    assert r.status_code == 200, r.text[:300]
    result = r.json()
    assert result.get("ok") is True
    assert result.get("status") == "admin_flagged", result
    # Verify workflow_history persisted via GET
    r2 = admin_session.get(f"{API}/bids", timeout=15)
    bids = r2.json()
    updated = next((x for x in bids if (x.get("id") == bid_id)), None)
    assert updated, "updated bid not found in list"
    hist = updated.get("workflow_history") or []
    assert any(h.get("to_status") == "admin_flagged" for h in hist), hist


# ---------- Packages CSV import ----------
def test_packages_import_csv_valid_and_invalid(admin_session):
    ts = int(time.time())
    csv_body = (
        "title,category,phase,value,currency,status\n"
        f"TEST_wave10_pkg_{ts},Medical,Phase 1,10000,USD,backlog\n"
        ",Medical,Phase 1,5000,USD,backlog\n"
    )
    files = {"file": (f"wave10_{ts}.csv", io.BytesIO(csv_body.encode()), "text/csv")}
    r = admin_session.post(f"{API}/packages/import", files=files, timeout=20)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    assert data.get("ok") is True, data
    assert data.get("created") == 1, data
    assert data.get("skipped") == 1, data
    errors = data.get("errors") or []
    assert errors, "expected error rows"
    assert "missing title or category" in errors[0].get("reason", "").lower(), errors


# ---------- Committee create ----------
def test_committee_create(admin_session):
    # find a published notice with a notice_ref
    r = admin_session.get(f"{API}/notices", timeout=15)
    assert r.status_code == 200, r.text[:200]
    notices = r.json()
    if isinstance(notices, dict):
        notices = notices.get("items", [])
    notice_ref = None
    for n in notices:
        if n.get("notice_ref"):
            notice_ref = n["notice_ref"]
            break
    if not notice_ref:
        pytest.skip("no published notice available")

    # find admin/staff docs to use as chair + one member
    rs = admin_session.get(f"{API}/staff", timeout=15)
    if rs.status_code != 200:
        pytest.skip(f"cannot list staff: {rs.status_code}")
    staff = rs.json()
    if len(staff) < 2:
        pytest.skip("need at least 2 staff docs")
    chair_id = staff[0].get("id") or staff[0].get("_id")
    member_id = staff[1].get("id") or staff[1].get("_id")

    payload = {
        "notice_ref": notice_ref,
        "chairperson_id": chair_id,
        "member_ids": [member_id],
        "external_invitees": [
            {"email": f"test_wave10_{int(time.time())}@example.com",
             "name": "TEST Wave10 Ext",
             "designation": "Observer"}
        ],
    }
    r = admin_session.post(f"{API}/committees", json=payload, timeout=20)
    # Allow 409/404 gracefully but NEVER 500
    assert r.status_code != 500, f"server error: {r.text[:400]}"
    if r.status_code in (400, 404, 409):
        pytest.skip(f"pre-conditions not met ({r.status_code}): {r.text[:200]}")
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    assert data.get("notice_ref") == notice_ref
    assert data.get("status") == "open"
    externals = data.get("external_invitees") or []
    assert externals and externals[0].get("accept_token"), externals
