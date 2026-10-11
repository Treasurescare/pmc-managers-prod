"""v52bu tests — Vendor Signatures sync, EMD per-bid receipt PDF."""
import os
import asyncio
import pytest
import requests
from datetime import datetime, timezone
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PASSWORD = "Vendor@12345"

# ---------- shared helpers ----------

@pytest.fixture(scope="module")
def vendor_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
               json={"email": VENDOR_EMAIL, "password": VENDOR_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"vendor login failed: {r.status_code} {r.text}"
    data = r.json()
    s.headers.update({"X-CSRF-Token": data.get("csrf_token", "")})
    s.vendor_id = data["id"]
    s.vendor_email = data["email"]
    return s


@pytest.fixture(scope="module")
def mongo_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "pmc_tender_db")]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------- Feature 1: EMD per-bid receipt PDF ----------

class TestEmdReceiptPdf:
    def test_unauth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/v1/payments/emd/bid/507f1f77bcf86cd799439011/receipt.pdf",
                         timeout=30, allow_redirects=False)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_bogus_bid_returns_404(self, vendor_session):
        # valid ObjectId that does not belong to this vendor
        r = vendor_session.get(
            f"{BASE_URL}/api/v1/payments/emd/bid/507f1f77bcf86cd799439011/receipt.pdf",
            timeout=30)
        assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text[:200]}"

    def test_paid_tx_returns_pdf(self, vendor_session, mongo_db):
        # Find or create a bid for this vendor with a paid EMD transaction.
        async def _setup():
            vid = vendor_session.vendor_id
            # pick an existing bid
            bid = await mongo_db.bids.find_one({"vendor_id": vid})
            if not bid:
                pytest.skip("vendor has no bids to attach a receipt to")
            bid_id = str(bid["_id"])
            # look for existing paid tx
            tx = await mongo_db.payment_transactions.find_one(
                {"bid_id": bid_id, "vendor_id": vid, "purpose": "emd",
                 "payment_status": "paid"})
            inserted_id = None
            if not tx:
                iso = datetime.now(timezone.utc).isoformat()
                doc = {
                    "bid_id": bid_id, "vendor_id": vid, "purpose": "emd",
                    "payment_status": "paid", "status": "paid",
                    "amount": 1000.0, "currency": "USD",
                    "paid_at": iso, "provider_ref": "ch_test_fake_v52bu",
                    "session_id": "cs_test_fake_v52bu",
                    "created_at": iso, "updated_at": iso,
                }
                res = await mongo_db.payment_transactions.insert_one(doc)
                inserted_id = res.inserted_id
            return bid_id, inserted_id, bid.get("bid_ref")

        bid_id, inserted_id, bid_ref = run(_setup())
        try:
            r = vendor_session.get(
                f"{BASE_URL}/api/v1/payments/emd/bid/{bid_id}/receipt.pdf",
                timeout=60)
            assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text[:300]}"
            ctype = r.headers.get("content-type", "")
            assert "application/pdf" in ctype, f"wrong content-type {ctype}"
            cd = r.headers.get("content-disposition", "")
            assert "PMC-EMD-Receipt-" in cd, f"wrong Content-Disposition: {cd}"
            assert r.content[:4] == b"%PDF", "body is not a PDF"
            assert len(r.content) > 1000, "pdf too small"
        finally:
            if inserted_id is not None:
                run(mongo_db.payment_transactions.delete_one({"_id": inserted_id}))

    def test_bid_without_paid_tx_returns_404(self, vendor_session, mongo_db):
        async def _find():
            vid = vendor_session.vendor_id
            async for b in mongo_db.bids.find({"vendor_id": vid}):
                bid_id = str(b["_id"])
                tx = await mongo_db.payment_transactions.find_one(
                    {"bid_id": bid_id, "vendor_id": vid, "purpose": "emd",
                     "payment_status": "paid"})
                if not tx:
                    return bid_id
            return None
        bid_id = run(_find())
        if not bid_id:
            pytest.skip("every bid already has a paid EMD; skip 404 case")
        r = vendor_session.get(
            f"{BASE_URL}/api/v1/payments/emd/bid/{bid_id}/receipt.pdf",
            timeout=30)
        assert r.status_code == 404


# ---------- Feature 2: Vendor Signatures 'signed' status surfaces ----------

class TestVendorSignaturesSignedStatus:
    def test_signed_envelope_returned_in_mine(self, vendor_session, mongo_db):
        """Insert a docusign_envelopes doc with status=signed and signer_email
        matching the vendor; GET /api/v1/docusign/mine must include it."""
        async def _setup():
            iso = datetime.now(timezone.utc).isoformat()
            envelope_id = f"TEST-v52bu-{int(datetime.now().timestamp())}"
            doc = {
                "envelope_id": envelope_id,
                "signer_email": vendor_session.vendor_email,
                "status": "signed",
                "sub_kind": "contract",
                "subject": "TEST v52bu signed envelope",
                "created_at": iso,
                "last_updated_at": iso,
                "archived": False,
            }
            res = await mongo_db.docusign_envelopes.insert_one(doc)
            return res.inserted_id, envelope_id

        inserted_id, envelope_id = run(_setup())
        try:
            r = vendor_session.get(f"{BASE_URL}/api/v1/docusign/mine", timeout=60)
            assert r.status_code == 200, f"mine failed: {r.status_code} {r.text[:200]}"
            items = r.json().get("items", [])
            hit = [e for e in items if e.get("envelope_id") == envelope_id]
            assert hit, f"inserted signed envelope not surfaced in /mine; items={len(items)}"
            assert hit[0].get("status") == "signed", f"status not preserved: {hit[0].get('status')}"
        finally:
            run(mongo_db.docusign_envelopes.delete_one({"_id": inserted_id}))
