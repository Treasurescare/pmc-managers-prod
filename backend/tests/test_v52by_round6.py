"""v52by Round-6 tests:
- Reverse Auction create robustness (#64) & list visibility (#59)
- BOQ Excel + PDF exports (#48/#57)
- Non-existent BOQ template export => 404 (not 500)
"""
import io
import os
import pytest
import requests
from openpyxl import load_workbook

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@12345"


# ---------- fixtures ----------

@pytest.fixture(scope="session")
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
    assert tok, f"No token in login response: {list(data.keys())}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


@pytest.fixture
def notice_ref(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/v1/notices")
    assert r.status_code == 200, r.text
    items = r.json()
    if isinstance(items, dict):
        items = items.get("items") or items.get("notices") or []
    if not items:
        pytest.skip("No notices available to attach reverse-auction to")
    return items[0].get("notice_ref") or items[0].get("ref")


# ---------- Reverse Auction robustness ----------

class TestReverseAuctionCreate:
    """#64 — create must not 422 when floor_price/min_decrement omitted."""

    def test_create_without_floor_and_min_decrement_defaults(self, admin_session, notice_ref):
        payload = {
            "notice_ref": notice_ref,
            "title": "TEST_v52by RA defaults",
            "starting_price": 1000,
            "duration_minutes": 15,
        }
        r = admin_session.post(f"{BASE_URL}/api/v1/reverse-auctions", json=payload)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        data = r.json()
        assert data.get("floor_price") == 0.0
        assert data.get("min_decrement") == 1.0
        assert data.get("status") == "draft"
        aid = data.get("id") or data.get("_id")
        assert aid

        # #59 — must appear in list
        lst = admin_session.get(f"{BASE_URL}/api/v1/reverse-auctions")
        assert lst.status_code == 200
        items = lst.json().get("items", [])
        assert any((it.get("id") == aid) for it in items), "Newly created draft not in list"

        # cleanup
        from pymongo import MongoClient
        from bson import ObjectId
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if mongo_url and db_name:
            MongoClient(mongo_url)[db_name].reverse_auctions.delete_one({"_id": ObjectId(aid)})

    def test_create_floor_ge_starting_rejected(self, admin_session, notice_ref):
        payload = {
            "notice_ref": notice_ref,
            "title": "TEST_v52by RA floor",
            "starting_price": 1000,
            "floor_price": 1000,  # equal => should 400
            "min_decrement": 5,
            "duration_minutes": 15,
        }
        r = admin_session.post(f"{BASE_URL}/api/v1/reverse-auctions", json=payload)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"


# ---------- BOQ exports ----------

@pytest.fixture
def boq_template(admin_session):
    """Ensure a BOQ template with >=2 items exists; return (id, created_flag)."""
    r = admin_session.get(f"{BASE_URL}/api/v1/boq/templates")
    assert r.status_code == 200
    tpls = r.json()
    if isinstance(tpls, dict):
        tpls = tpls.get("items") or []
    created_id = None
    tid = None
    for t in tpls:
        if len(t.get("items") or []) >= 2:
            tid = t.get("id") or t.get("_id")
            break
    if not tid:
        payload = {
            "name": "TEST_v52by BOQ Export",
            "currency": "USD",
            "items": [
                {"sl_no": 1, "description": "Cement 50kg bag", "unit": "bag",
                 "quantity": 100, "unit_rate": 10, "remarks": ""},
                {"sl_no": 2, "description": "Steel rebar", "unit": "ton",
                 "quantity": 5, "unit_rate": 500, "remarks": ""},
            ],
        }
        r = admin_session.post(f"{BASE_URL}/api/v1/boq/templates", json=payload)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        tid = data.get("id") or data.get("_id")
        created_id = tid
    yield tid
    if created_id:
        try:
            from pymongo import MongoClient
            from bson import ObjectId
            mongo_url = os.environ.get("MONGO_URL")
            db_name = os.environ.get("DB_NAME")
            if mongo_url and db_name:
                MongoClient(mongo_url)[db_name].boq_templates.delete_one({"_id": ObjectId(created_id)})
        except Exception:
            pass


class TestBOQExports:
    def test_xlsx_unauth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/v1/boq/templates/anything/export.xlsx")
        assert r.status_code in (401, 403), f"Unauth should 401/403, got {r.status_code}"

    def test_xlsx_export_admin(self, admin_session, boq_template):
        tid = boq_template
        r = admin_session.get(f"{BASE_URL}/api/v1/boq/templates/{tid}/export.xlsx")
        assert r.status_code == 200, r.text[:200]
        assert "spreadsheetml" in r.headers.get("Content-Type", "")
        cd = r.headers.get("Content-Disposition", "")
        assert "BOQ-" in cd
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb.active
        header = [c.value for c in ws[1]]
        expected = ["Sl.No", "Description", "Unit", "Quantity", "Unit Rate",
                    "Line Total", "UNSPSC", "UNSPSC Title", "Remarks"]
        assert header == expected, f"Header mismatch: {header}"

    def test_pdf_export_admin(self, admin_session, boq_template):
        tid = boq_template
        r = admin_session.get(f"{BASE_URL}/api/v1/boq/templates/{tid}/export.pdf")
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("Content-Type", "").startswith("application/pdf")
        assert "BOQ-" in r.headers.get("Content-Disposition", "")
        assert r.content[:4] == b"%PDF", "Response body is not a PDF"

    def test_pdf_export_not_found(self, admin_session):
        # 24-char hex but doesn't exist
        r = admin_session.get(
            f"{BASE_URL}/api/v1/boq/templates/000000000000000000000000/export.pdf")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text[:200]}"


# ---------- Corrigendum optimistic withdraw (API-side preconditions) ----------
# We only verify API endpoints exist here; optimistic UI flip is tested via playwright
class TestCorrigendumWithdrawAPI:
    def test_withdraw_endpoint_exists(self, admin_session):
        # Hitting with a bogus id must return 404, NOT 405/500
        r = admin_session.post(
            f"{BASE_URL}/api/v1/corrigenda/000000000000000000000000/withdraw",
            json={"reason": "x" * 15})
        assert r.status_code in (400, 404), f"Got {r.status_code}: {r.text[:200]}"
