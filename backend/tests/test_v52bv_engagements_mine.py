"""v52bv — Backend tests for vendor-scoped GET /api/v1/engagements/mine
and regression on POST /api/v1/engagements/quote-request.
"""
import os
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PASS = "Vendor@12345"


@pytest.fixture(scope="module")
def vendor_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/v1/vendor/auth/login",
               json={"email": VENDOR_EMAIL, "password": VENDOR_PASS}, timeout=30)
    assert r.status_code == 200, f"vendor login failed: {r.status_code} {r.text}"
    return s


def test_mine_unauthenticated_returns_401():
    r = requests.get(f"{BASE_URL}/api/v1/engagements/mine", timeout=30)
    assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text}"


def test_mine_authenticated_returns_200_scoped(vendor_session):
    r = vendor_session.get(f"{BASE_URL}/api/v1/engagements/mine", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data and "count" in data
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    # scoping check — every item has the vendor's own email
    for it in data["items"]:
        assert it.get("buyer_email") == VENDOR_EMAIL, f"leak: {it.get('buyer_email')}"
        # no raw _id leaked
        assert "_id" not in it


def test_mine_route_not_shadowed_by_eid(vendor_session):
    """If /{eid} shadowed /mine, FastAPI would try to treat 'mine' as an eid
    and the admin-only /{eid} would reject the vendor cookie with 401/403."""
    r = vendor_session.get(f"{BASE_URL}/api/v1/engagements/mine", timeout=30)
    assert r.status_code == 200, f"route may be shadowed: {r.status_code} {r.text}"


def test_quote_request_regression(vendor_session):
    """v52bv regression — adding /mine must not break POST /quote-request."""
    # find any supplier-side quote-model active product
    r = requests.get(f"{BASE_URL}/api/v1/products/public?side=supplier", timeout=30)
    assert r.status_code == 200, r.text
    products = r.json().get("items", [])
    quote_product = None
    for p in products:
        if p.get("is_active") and (p.get("pricing_model") == "quote" or p.get("model") == "quote"):
            quote_product = p
            break
    if not quote_product:
        # fall back to any active supplier product
        for p in products:
            if p.get("is_active"):
                quote_product = p
                break
    assert quote_product, "no supplier product available for quote-request regression"

    r2 = vendor_session.post(f"{BASE_URL}/api/v1/engagements/quote-request",
                             json={"product_code": quote_product["code"], "quantity": 1},
                             timeout=30)
    assert r2.status_code == 200, f"quote-request failed: {r2.status_code} {r2.text}"
    body = r2.json()
    assert body.get("status") == "quote_requested"
    assert body.get("buyer_email") == VENDOR_EMAIL
    created_id = body.get("id")

    # verify it shows up in /mine
    r3 = vendor_session.get(f"{BASE_URL}/api/v1/engagements/mine", timeout=30)
    assert r3.status_code == 200
    ids = [i.get("id") for i in r3.json()["items"]]
    assert created_id in ids, f"newly created engagement {created_id} not in /mine"


def test_tile_count_increment_with_seeded_row(vendor_session):
    """Insert a quote_requested engagement via /quote-request (public API,
    no direct DB write needed), confirm /mine count increments, then
    cancel is not available to vendors so we leave it (teardown via admin
    would need admin creds — out of scope). We only check the increment."""
    before = vendor_session.get(f"{BASE_URL}/api/v1/engagements/mine", timeout=30).json()
    before_q = sum(1 for i in before["items"]
                   if i.get("status") in ("quote_requested", "quoted", "invoiced"))

    r = requests.get(f"{BASE_URL}/api/v1/products/public?side=supplier", timeout=30)
    products = r.json().get("items", [])
    p = next((x for x in products if x.get("is_active")), None)
    assert p, "no active supplier product"
    r2 = vendor_session.post(f"{BASE_URL}/api/v1/engagements/quote-request",
                             json={"product_code": p["code"], "quantity": 1}, timeout=30)
    assert r2.status_code == 200

    after = vendor_session.get(f"{BASE_URL}/api/v1/engagements/mine", timeout=30).json()
    after_q = sum(1 for i in after["items"]
                  if i.get("status") in ("quote_requested", "quoted", "invoiced"))
    assert after_q == before_q + 1, f"expected +1, got before={before_q} after={after_q}"
