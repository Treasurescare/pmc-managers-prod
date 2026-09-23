"""v46 · Vendor Ratings & Reviews portal — end-to-end backend tests."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://tender-hub-57.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api/v1/vendor-ratings"

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PW = "Admin@12345"
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PW = "Vendor@12345"
TEST_VENDOR = "PMC-SUP-000036"
OTHER_VENDOR = "PMC-SUP-000035"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_auth():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    d = r.json()
    tok = d.get("token") or d.get("access_token")
    csrf = d.get("csrf_token") or d.get("csrf")
    assert tok and csrf, f"missing token/csrf in login response: {d}"
    s.headers.update({"Authorization": f"Bearer {tok}", "X-CSRF-Token": csrf})
    return s


@pytest.fixture(scope="module")
def vendor_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/v1/vendor/auth/login",
               json={"email": VENDOR_EMAIL, "password": VENDOR_PW}, timeout=30)
    assert r.status_code == 200, f"vendor login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def vendor_ref(vendor_session):
    r = vendor_session.get(f"{BASE}/api/v1/vendor/auth/me", timeout=30)
    assert r.status_code == 200
    return r.json().get("vendor_ref")


# ---------- Public endpoints ----------
class TestPublic:
    def test_top(self):
        r = requests.get(f"{API}/public/top", timeout=30)
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert isinstance(items, list)
        if items:
            it = items[0]
            for k in ("vendor_ref", "company_name", "count", "average_score", "badge"):
                assert k in it, f"missing {k}"
            assert it["badge"] in {"platinum", "gold", "silver", "bronze", "none"}

    def test_public_aggregate(self):
        r = requests.get(f"{API}/public/{TEST_VENDOR}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("count", "average_score", "badge", "by_reviewer_kind",
                  "criteria_averages", "recent_comments"):
            assert k in d

    def test_public_aggregate_unknown_vendor_404(self):
        r = requests.get(f"{API}/public/PMC-SUP-DOES-NOT-EXIST", timeout=30)
        assert r.status_code == 404

    def test_public_submit_unknown_vendor_404(self):
        r = requests.post(f"{API}/public/submit", json={
            "vendor_ref": "PMC-SUP-DOES-NOT-EXIST",
            "reviewer_name": "Buyer A",
            "reviewer_email": "TEST_buyer_unknown@example.com",
            "scores": {"delivery": 4, "quality": 4, "comms": 4},
        }, timeout=30)
        assert r.status_code == 404

    def test_public_submit_short_name_422(self):
        r = requests.post(f"{API}/public/submit", json={
            "vendor_ref": TEST_VENDOR,
            "reviewer_name": "A",
            "reviewer_email": "TEST_buyer_short@example.com",
            "scores": {"delivery": 4},
        }, timeout=30)
        assert r.status_code == 422

    def test_public_submit_ok_then_rate_limit(self):
        email = f"TEST_rl_{int(time.time())}@example.com"
        # try 4 different vendor_refs to accumulate pending; 429 on the 4th (limit 3/email/day)
        candidates = ["PMC-SUP-000031", "PMC-SUP-000032", "PMC-SUP-000033",
                      "PMC-SUP-000034", "PMC-SUP-000035", "PMC-SUP-000036"]
        successes = 0
        rate_limited = False
        for v in candidates:
            r = requests.post(f"{API}/public/submit", json={
                "vendor_ref": v,
                "reviewer_name": "RL Buyer",
                "reviewer_email": email,
                "scores": {"delivery": 4, "quality": 4, "comms": 4},
                "comment": "TEST_rl",
            }, timeout=30)
            if r.status_code == 200:
                successes += 1
            elif r.status_code == 429:
                rate_limited = True
                break
            elif r.status_code == 404:
                continue
        assert successes >= 1, "no public submit succeeded"
        assert rate_limited, f"rate limit never triggered (successes={successes})"

    def test_public_submit_pending_not_in_aggregate(self):
        # Get aggregate before, submit a pending, ensure count unchanged
        pre = requests.get(f"{API}/public/{TEST_VENDOR}", timeout=30).json()
        r = requests.post(f"{API}/public/submit", json={
            "vendor_ref": TEST_VENDOR,
            "reviewer_name": "Non Leak",
            "reviewer_email": f"TEST_noleak_{int(time.time())}@example.com",
            "scores": {"delivery": 5, "quality": 5, "comms": 5},
            "comment": "leaked?",
        }, timeout=30)
        assert r.status_code in (200, 429)
        post = requests.get(f"{API}/public/{TEST_VENDOR}", timeout=30).json()
        assert post["count"] == pre["count"], "pending review leaked into aggregate"


# ---------- Auth enforcement ----------
class TestAuthEnforcement:
    def test_admin_pending_count_401_no_token(self):
        r = requests.get(f"{API}/admin/pending-count", timeout=30)
        assert r.status_code in (401, 403)

    def test_admin_submit_401_no_token(self):
        r = requests.post(f"{API}/admin/submit", json={"vendor_ref": TEST_VENDOR, "scores": {}}, timeout=30)
        assert r.status_code in (401, 403)

    def test_peer_submit_401_no_cookie(self):
        r = requests.post(f"{API}/peer/submit", json={"vendor_ref": TEST_VENDOR, "scores": {}}, timeout=30)
        assert r.status_code in (401, 403)


# ---------- Admin endpoints ----------
class TestAdmin:
    def test_admin_submit_approved(self, admin_auth):
        r = admin_auth.post(f"{API}/admin/submit", json={
            "vendor_ref": TEST_VENDOR,
            "scores": {"delivery": 5, "quality": 4, "comms": 4},
            "comment": "TEST_admin review v46",
        }, timeout=30)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d["status"] == "approved"
        assert "review_id" in d

    def test_admin_submit_upsert(self, admin_auth):
        # submit twice; count of admin reviews from this admin against this vendor should stay 1
        for _ in range(2):
            admin_auth.post(f"{API}/admin/submit", json={
                "vendor_ref": TEST_VENDOR,
                "scores": {"delivery": 5, "quality": 5, "comms": 5},
                "comment": "TEST_upsert",
            }, timeout=30)
        r = admin_auth.get(f"{API}/admin/reviews",
                         params={"vendor_ref": TEST_VENDOR}, timeout=30)
        assert r.status_code == 200
        rows = r.json()
        admin_rows = [x for x in rows if x.get("reviewer_kind") == "pmc_admin"
                      and x.get("reviewer_email") == ADMIN_EMAIL]
        assert len(admin_rows) == 1, f"upsert failed: {len(admin_rows)} admin rows"

    def test_admin_score_scale_clamp(self, admin_auth):
        # Default rubric 1..5. Send 99 — should clamp to 5 → 100.
        r = admin_auth.post(f"{API}/admin/submit", json={
            "vendor_ref": TEST_VENDOR,
            "scores": {"delivery": 99, "quality": 99, "comms": 99},
            "comment": "TEST_clamp",
        }, timeout=30)
        assert r.status_code == 200
        # fetch back
        rows = admin_auth.get(f"{API}/admin/reviews", params={"vendor_ref": TEST_VENDOR},
                              timeout=30).json()
        mine = [x for x in rows if x.get("reviewer_email") == ADMIN_EMAIL][0]
        assert mine["score_out_of_100"] == 100.0

    def test_admin_pending_count(self, admin_auth):
        r = admin_auth.get(f"{API}/admin/pending-count", timeout=30)
        assert r.status_code == 200
        assert "pending" in r.json()

    def test_admin_reviews_filter_pending(self, admin_auth):
        r = admin_auth.get(f"{API}/admin/reviews", params={"status": "pending"},
                           timeout=30)
        assert r.status_code == 200
        for row in r.json():
            assert row.get("status") == "pending"

    def test_admin_moderate_approve_then_hide_then_delete(self, admin_auth):
        # Create a fresh pending review via public/submit
        email = f"TEST_mod_{int(time.time())}@example.com"
        r = requests.post(f"{API}/public/submit", json={
            "vendor_ref": OTHER_VENDOR,
            "reviewer_name": "Mod Buyer",
            "reviewer_email": email,
            "scores": {"delivery": 5, "quality": 5, "comms": 5},
            "comment": "TEST_mod",
        }, timeout=30)
        assert r.status_code == 200
        rid = r.json()["review_id"]

        pre = requests.get(f"{API}/public/{OTHER_VENDOR}", timeout=30).json()

        # Approve
        r2 = admin_auth.post(f"{API}/admin/reviews/{rid}/moderate",
                             json={"action": "approve"}, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["status"] == "approved"

        post = requests.get(f"{API}/public/{OTHER_VENDOR}", timeout=30).json()
        assert post["count"] == pre["count"] + 1, "aggregate did not increment after approve"

        # Hide
        r3 = admin_auth.post(f"{API}/admin/reviews/{rid}/moderate",
                             json={"action": "hide"}, timeout=30)
        assert r3.status_code == 200
        hidden = requests.get(f"{API}/public/{OTHER_VENDOR}", timeout=30).json()
        assert hidden["count"] == pre["count"], "hidden review still in aggregate"

        # Delete
        r4 = admin_auth.delete(f"{API}/admin/reviews/{rid}", timeout=30)
        assert r4.status_code == 200


# ---------- Peer endpoint ----------
class TestPeer:
    def test_peer_self_rating_blocked(self, vendor_session, vendor_ref):
        r = vendor_session.post(f"{API}/peer/submit", json={
            "vendor_ref": vendor_ref,
            "scores": {"delivery": 5, "quality": 5, "comms": 5},
            "comment": "self",
        }, timeout=30)
        assert r.status_code == 400
        assert "own" in r.text.lower()

    def test_peer_rate_other_vendor(self, vendor_session, vendor_ref):
        target = TEST_VENDOR if vendor_ref != TEST_VENDOR else OTHER_VENDOR
        r = vendor_session.post(f"{API}/peer/submit", json={
            "vendor_ref": target,
            "scores": {"delivery": 4, "quality": 4, "comms": 4},
            "comment": "TEST_peer review",
        }, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] in ("approved", "pending")

    def test_peer_upsert(self, vendor_session, vendor_ref):
        target = TEST_VENDOR if vendor_ref != TEST_VENDOR else OTHER_VENDOR
        ids = set()
        for _ in range(2):
            r = vendor_session.post(f"{API}/peer/submit", json={
                "vendor_ref": target,
                "scores": {"delivery": 3, "quality": 3, "comms": 3},
            }, timeout=30)
            assert r.status_code == 200
            ids.add(r.json()["review_id"])
        assert len(ids) == 1, "peer upsert produced multiple ids"
