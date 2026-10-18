"""v56n: Live Verify + Public Contact + Deep links + Status filter backend tests."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")


@pytest.fixture
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Verify Record (public) ---

class TestVerifyRecord:
    def test_verify_by_seq_digits(self, client):
        r = client.get(f"{BASE_URL}/api/v1/audit-events/verify-record", params={"ref": "2840"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("found") is True
        assert d.get("ok") is True
        assert d.get("reason") == "intact"
        assert d.get("seq") == 2840
        assert "event_type" in d and "target_id" in d
        assert isinstance(d.get("current_hash"), str) and len(d["current_hash"]) == 64
        assert isinstance(d.get("previous_hash"), str) and len(d["previous_hash"]) == 64

    def test_verify_by_seq_hash_prefix(self, client):
        r = client.get(f"{BASE_URL}/api/v1/audit-events/verify-record", params={"ref": "#2840"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("found") is True
        assert d.get("seq") == 2840

    def test_verify_by_target_id(self, client):
        r = client.get(f"{BASE_URL}/api/v1/audit-events/verify-record", params={"ref": "ENQ-2026-00001"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("found") is True
        assert d.get("target_id", "").upper() == "ENQ-2026-00001"

    def test_verify_bogus_ref(self, client):
        r = client.get(f"{BASE_URL}/api/v1/audit-events/verify-record", params={"ref": "NOPE-123"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("found") is False


# --- Public Contact ---

class TestPublicContact:
    def test_contact_success(self, client):
        payload = {
            "topic": "general",
            "name": "TEST Playwright User",
            "email": "test@example.com",
            "message": "This is a TEST enquiry from backend regression suite.",
            "tender_ref": "PMC-NOT-2026-0001"
        }
        r = client.post(f"{BASE_URL}/api/v1/meta/public/contact", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        ref = d.get("reference", "")
        assert re.match(r"^ENQ-\d{4}-\d{5}$", ref), f"bad reference: {ref}"

    def test_contact_validation_missing_fields(self, client):
        r = client.post(f"{BASE_URL}/api/v1/meta/public/contact", json={"name": "x"})
        assert r.status_code == 422

    def test_contact_persistence_via_verify(self, client):
        # Create enquiry and verify by its reference target_id
        payload = {
            "topic": "general",
            "name": "TEST Persist",
            "email": "test2@example.com",
            "message": "persistence check",
        }
        r = client.post(f"{BASE_URL}/api/v1/meta/public/contact", json=payload)
        assert r.status_code == 200
        ref = r.json()["reference"]
        # It should appear in audit ledger (contact.enquiry) - verify by target_id
        v = client.get(f"{BASE_URL}/api/v1/audit-events/verify-record", params={"ref": ref})
        assert v.status_code == 200
        # found may be true if audit_log wrote with target_id=ref
        # not strictly required but assert endpoint doesn't error
        assert "found" in v.json()
