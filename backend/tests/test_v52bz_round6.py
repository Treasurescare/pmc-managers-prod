"""v52bz Round-6 tests:
- #43 Rubric persistence: POST then GET returns same weights
- #44 Scoring auto-COI retry: endpoint behaviour for score-before-COI
"""
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@12345"
TEST_REF = "TEST-RUBRIC-v52bz"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/v1/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    csrf = data.get("csrf_token") or data.get("csrf")
    assert tok
    s.headers.update({"Authorization": f"Bearer {tok}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    s.admin_id = data.get("id") or data.get("user", {}).get("id")
    s.admin_email = ADMIN_EMAIL
    return s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    yield db
    # cleanup
    db.rubrics.delete_many({"notice_ref": TEST_REF})
    client.close()


# ---------- #43 Rubric persistence ----------

def test_rubric_persistence(admin_session, mongo_db):
    # Clean any prior
    mongo_db.rubrics.delete_many({"notice_ref": TEST_REF})

    custom_criteria = [
        {"code": "experience", "label": "Relevant Experience", "weight": 0.5, "max_score": 100},
        {"code": "methodology", "label": "Methodology", "weight": 0.2, "max_score": 100},
        {"code": "team", "label": "Team", "weight": 0.15, "max_score": 100},
        {"code": "financial_health", "label": "Financial Health", "weight": 0.15, "max_score": 100},
    ]
    payload = {
        "notice_ref": TEST_REF,
        "technical_criteria": custom_criteria,
        "commercial_weight": 0.35,
        "minimum_technical": 65,
    }
    r = admin_session.post(f"{BASE_URL}/api/v1/evaluations/rubric", json=payload)
    assert r.status_code in (200, 201), r.text

    g = admin_session.get(f"{BASE_URL}/api/v1/evaluations/rubric/{TEST_REF}")
    assert g.status_code == 200, g.text
    data = g.json()
    assert data["notice_ref"] == TEST_REF
    assert data["commercial_weight"] == 0.35
    assert data["minimum_technical"] == 65
    assert len(data["technical_criteria"]) == 4
    weights = {c["code"]: c["weight"] for c in data["technical_criteria"]}
    assert weights["experience"] == 0.5
    assert weights["methodology"] == 0.2


def test_rubric_update_persists(admin_session, mongo_db):
    # Overwrite with different weight to verify update-upsert flow
    payload = {
        "notice_ref": TEST_REF,
        "technical_criteria": [
            {"code": "experience", "label": "Exp", "weight": 0.7, "max_score": 100},
            {"code": "methodology", "label": "M", "weight": 0.3, "max_score": 100},
        ],
        "commercial_weight": 0.4,
        "minimum_technical": 60,
    }
    r = admin_session.post(f"{BASE_URL}/api/v1/evaluations/rubric", json=payload)
    assert r.status_code in (200, 201)
    g = admin_session.get(f"{BASE_URL}/api/v1/evaluations/rubric/{TEST_REF}")
    assert g.status_code == 200
    data = g.json()
    weights = {c["code"]: c["weight"] for c in data["technical_criteria"]}
    assert weights["experience"] == 0.7


def test_rubric_get_404_when_missing(admin_session):
    g = admin_session.get(f"{BASE_URL}/api/v1/evaluations/rubric/NOT-EXISTS-xyz-v52bz")
    assert g.status_code == 404


# ---------- #44 Score-before-COI backend contract ----------

def test_score_requires_coi(admin_session, mongo_db):
    """The frontend auto-COI retry depends on backend rejecting score with
    a detail containing 'Conflict-of-Interest' when no COI is on file."""
    # Need a bid. Pull one.
    r = admin_session.get(f"{BASE_URL}/api/v1/bids")
    if r.status_code != 200:
        pytest.skip(f"Cannot list bids: {r.status_code}")
    bids = r.json()
    if isinstance(bids, dict):
        bids = bids.get("items") or []
    if not bids:
        pytest.skip("No bids available for COI test")
    admin_id = admin_session.admin_id
    # Find a bid whose notice has an unlocked technical envelope
    chosen = None
    for b in bids:
        nref = b.get("notice_ref")
        if not nref:
            continue
        n = mongo_db.notices.find_one({"notice_ref": nref})
        if n and not n.get("technical_locked_at"):
            chosen = b
            break
    if not chosen:
        pytest.skip("No bid on an unlocked-technical notice available")
    bid = chosen
    notice_ref = bid.get("notice_ref")

    # Remove any existing COI for this evaluator/notice
    if admin_id:
        mongo_db.coi_declarations.delete_many(
            {"notice_ref": notice_ref, "evaluator_id": admin_id})

    # Attempt scoring without COI
    r = admin_session.post(f"{BASE_URL}/api/v1/evaluations/score",
                           json={"bid_id": bid["id"], "kind": "technical",
                                 "scores": {"experience": 80}})
    # Expect rejection mentioning Conflict-of-Interest
    assert r.status_code in (400, 403, 409), f"Unexpected: {r.status_code} {r.text}"
    assert "Conflict-of-Interest" in r.text or "COI" in r.text or "conflict" in r.text.lower(), r.text

    # Now declare COI (no conflict) and retry
    r2 = admin_session.post(f"{BASE_URL}/api/v1/evaluations/coi",
                            json={"notice_ref": notice_ref, "has_conflict": False,
                                  "details": "Auto-declared via scoring form"})
    assert r2.status_code == 200, r2.text

    r3 = admin_session.post(f"{BASE_URL}/api/v1/evaluations/score",
                            json={"bid_id": bid["id"], "kind": "technical",
                                  "scores": {"experience": 80}})
    assert r3.status_code in (200, 201), r3.text

    # Verify COI persisted with Auto-declared marker
    coi = mongo_db.coi_declarations.find_one(
        {"notice_ref": notice_ref, "evaluator_id": admin_id})
    assert coi is not None
    assert coi.get("has_conflict") is False
    assert "Auto-declared" in (coi.get("details") or "")

    # Cleanup: remove the test COI + score we created
    mongo_db.coi_declarations.delete_many(
        {"notice_ref": notice_ref, "evaluator_id": admin_id,
         "details": "Auto-declared via scoring form"})
