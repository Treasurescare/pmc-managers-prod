"""v52bw — DocuSign refresh endpoint + _apply_live_status fallback tests."""
import os
import asyncio
import pytest
import requests
import uuid
from bson import ObjectId

def _load_base_url():
    v = os.environ.get('REACT_APP_BACKEND_URL')
    if not v:
        try:
            with open("/app/frontend/.env", "r") as f:
                for ln in f:
                    if ln.startswith("REACT_APP_BACKEND_URL="):
                        v = ln.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL not set"
    return v.rstrip('/')

BASE_URL = _load_base_url()
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:300]}"
    d = r.json()
    token = d.get("token") or d.get("access_token")
    csrf = d.get("csrf_token") or d.get("csrfToken")
    assert token, f"no token in {d}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


def test_refresh_unauth_401():
    r = requests.post(f"{BASE_URL}/api/v1/docusign/envelopes/anything-xyz/refresh")
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} {r.text[:200]}"


def test_refresh_nonexistent_envelope_is_stable(admin_session):
    fake_id = f"nonexistent-{uuid.uuid4().hex[:12]}"
    r = admin_session.post(f"{BASE_URL}/api/v1/docusign/envelopes/{fake_id}/refresh")
    # Spec: endpoint is best-effort, returns 200 with {ok:false, error:...}; must NOT be 500.
    assert r.status_code != 500, f"got 500 traceback: {r.text[:400]}"
    assert r.status_code in (200, 404, 410, 424), f"unexpected status {r.status_code}: {r.text[:400]}"
    if r.status_code == 200:
        body = r.json()
        assert "ok" in body
        # ok may be True or False; if False an error string must be present
        if body.get("ok") is False:
            assert body.get("error"), f"missing error field: {body}"


def test_refresh_endpoint_registered_not_404(admin_session):
    # Authed request to a random id — if the path were unregistered we'd get 404 w/ `Not Found` body
    fake_id = f"endpoint-check-{uuid.uuid4().hex[:8]}"
    r = admin_session.post(f"{BASE_URL}/api/v1/docusign/envelopes/{fake_id}/refresh")
    # The specific 404 "detail: Not Found" from FastAPI routing would indicate unregistered.
    if r.status_code == 404:
        try:
            detail = r.json().get("detail", "")
        except Exception:
            detail = r.text
        assert detail != "Not Found", "endpoint is NOT registered"


def test_resend_except_block_catches_unknown_recipient():
    """Code review: ensure routers/docusign.py resend except catches new strings."""
    with open("/app/backend/routers/docusign.py", "r") as f:
        src = f.read()
    assert "UNKNOWN_ENVELOPE_RECIPIENT" in src
    assert "not a valid recipient of the specified envelope" in src
    # Confirm those are inside a 410 branch
    idx_u = src.find("UNKNOWN_ENVELOPE_RECIPIENT")
    nearby = src[max(0, idx_u-300): idx_u+800]
    assert "410" in nearby, "UNKNOWN_ENVELOPE_RECIPIENT branch should raise 410"
    assert "orphaned" in nearby, "should mark envelope orphaned"


# --- _apply_live_status fallback (direct code call) ---
def test_apply_live_status_fallback_via_award_ref():
    async def _run():
        import sys
        sys.path.insert(0, "/app/backend")
        from routers import docusign as ds_mod
        from server import db

        award_ref = f"PMC-AWD-TEST-v52bw-{uuid.uuid4().hex[:6]}"
        env_id = f"test-env-{uuid.uuid4().hex[:10]}"

        bid_doc = {
            "status": "awarded",
            "vendor_email": "manualvendor@pmcmanagers.com",
            "test_marker": "TEST_v52bw",
        }
        bid_res = await db.bids.insert_one(bid_doc)
        bid_id = str(bid_res.inserted_id)

        await db.awards.insert_one({
            "award_ref": award_ref,
            "bid_id": bid_id,
            "test_marker": "TEST_v52bw",
        })

        await db.docusign_envelopes.insert_one({
            "envelope_id": env_id,
            "award_ref": award_ref,
            "signer_email": "manualvendor@pmcmanagers.com",
            "signer_name": "Manual Vendor",
            "status": "created",
            "sub_kind": "contract",
            "test_marker": "TEST_v52bw",
        })

        try:
            await ds_mod._apply_live_status(env_id, "sent")
            env_after = await db.docusign_envelopes.find_one({"envelope_id": env_id})
            assert env_after is not None
            assert env_after.get("status") == "sent", f"status not mirrored: {env_after.get('status')}"
            assert env_after.get("bid_id") == bid_id, f"bid_id fallback failed: got {env_after.get('bid_id')}"

            bid_after = await db.bids.find_one({"_id": ObjectId(bid_id)})
            assert bid_after.get("docusign_status") == "sent", f"bid.docusign_status not mirrored: {bid_after.get('docusign_status')}"
        finally:
            await db.docusign_envelopes.delete_many({"test_marker": "TEST_v52bw"})
            await db.awards.delete_many({"test_marker": "TEST_v52bw"})
            await db.bids.delete_many({"test_marker": "TEST_v52bw"})

    asyncio.run(_run())
