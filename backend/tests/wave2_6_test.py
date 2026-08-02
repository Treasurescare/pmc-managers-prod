"""PMC v2 — Wave 2-6 backend regression tests.

Covers:
- Wave 2: Evaluation rubric, COI, scoring (tech+comm), envelope lock, award report
- Wave 3: BOQ template + Excel import, vendor submission, comparison; Contracts + milestones + variations
- Wave 4: Vendor Intelligence (rating/blacklist/watchlist/ESG/summary), Masters UI (CRUD)
- Wave 5: Analytics dashboard, AI bid anomaly (LLM key optional)
- Wave 6: Reverse auction (create + bid), Helpdesk tickets (open/reply/close)
- Notifications: state-transition fires notification row for target role
"""
import io
import os
import uuid
import bcrypt
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL",
                          "https://tender-hub-57.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api/v1"

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@123"


# ---------- Helpers ----------

def _admin_session() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"master admin login failed: {r.status_code} {r.text}"
    body = r.json()
    csrf = body.get("csrf_token") or s.cookies.get("csrf_token")
    s.headers.update({"Authorization": f"Bearer {body['token']}", "X-CSRF-Token": csrf})
    s._me = body
    return s


def _staff_login(email: str, password: str, active_role: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login",
               json={"email": email, "password": password, "active_role": active_role},
               timeout=15)
    assert r.status_code == 200, f"staff login {email}/{active_role}: {r.status_code} {r.text}"
    body = r.json()
    csrf = body.get("csrf_token") or s.cookies.get("csrf_token")
    s.headers.update({"X-CSRF-Token": csrf})
    s._me = body
    return s


@pytest.fixture(scope="session")
def admin_session():
    return _admin_session()


@pytest.fixture(scope="session")
def mongo_db():
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "pmc_tender_db")
    return MongoClient(mongo_url)[db_name]


# Shared state across ordered tests
STATE: dict = {}


# ============================================================
#  0. Master admin login (adminsupport)
# ============================================================
class TestMasterAdmin:
    def test_master_admin_login(self):
        r = requests.post(f"{API}/admin/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == ADMIN_EMAIL
        assert body["role"] == "admin"
        assert body.get("token")


# ============================================================
#  1. Seed a fresh notice + 2 vendors + 2 bids (needed by Wave 2-6)
# ============================================================
class TestSeed:
    def test_create_notice_and_bids(self, admin_session, mongo_db):
        # Fresh notice
        payload = {
            "title": f"TEST_Wave2_{uuid.uuid4().hex[:6]}",
            "description": "Wave 2-6 test notice",
            "document_type": "tender",
            "category": "Modular operation theatres (OTs)",
            "delivery_country": "KZ",
            "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            "budget_currency": "USD",
            "budget_amount": 1000000,
            "emd_config": {"fixed_amount": 500.0, "percentage": 1.0, "currency": "USD"},
            "is_published": True,
        }
        r = admin_session.post(f"{API}/notices", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        STATE["notice_ref"] = r.json()["notice_ref"]

        # Seed 2 vendors with known password
        vendors = []
        for i in range(2):
            email = f"test_wv26_v{i}_{uuid.uuid4().hex[:6]}@example.com"
            pw = "VendorPw@123"
            hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            vref = f"PMC-VND-TEST-{uuid.uuid4().hex[:6]}"
            res = mongo_db.vendors.insert_one({
                "email": email, "password_hash": hashed,
                "company_name": f"TEST_WV26_Vendor_{i}",
                "vendor_ref": vref,
                "must_change_password": False,
                "is_active": True,
                "tenant_id": "PMC-KZ-01",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            vendors.append({"id": str(res.inserted_id), "email": email, "pw": pw, "ref": vref})
        STATE["vendors"] = vendors

        # Login each vendor and create a bid
        bids = []
        for i, v in enumerate(vendors):
            vs = requests.Session()
            rl = vs.post(f"{API}/vendor/auth/login",
                         json={"email": v["email"], "password": v["pw"]}, timeout=15)
            assert rl.status_code == 200, rl.text
            csrf = rl.json().get("csrf_token")
            vs.headers.update({"X-CSRF-Token": csrf})
            rb = vs.post(f"{API}/bids", json={
                "notice_ref": STATE["notice_ref"],
                "price_amount": 900000 + i * 50000,
                "price_currency": "USD",
                "documents": [],
            }, timeout=15)
            assert rb.status_code == 200, rb.text
            bids.append({"id": rb.json()["id"], "bid_ref": rb.json()["bid_ref"],
                         "session": vs, "vendor": v})
        STATE["bids"] = bids


# ============================================================
#  2. Wave 2 — Evaluation
# ============================================================
class TestWave2Evaluation:
    def test_create_rubric(self, admin_session):
        rubric = {
            "notice_ref": STATE["notice_ref"],
            "technical_criteria": [
                {"code": "experience", "label": "Experience", "weight": 0.3, "max_score": 100},
                {"code": "methodology", "label": "Methodology", "weight": 0.3, "max_score": 100},
                {"code": "team", "label": "Team", "weight": 0.2, "max_score": 100},
                {"code": "financial_health", "label": "Financial", "weight": 0.2, "max_score": 100},
            ],
            "commercial_weight": 0.4,
            "minimum_technical": 60.0,
        }
        r = admin_session.post(f"{API}/evaluations/rubric", json=rubric, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["commercial_weight"] == 0.4

    def test_scoring_requires_coi_first(self, admin_session):
        # admin has NOT declared COI yet — scoring must 400
        bid_id = STATE["bids"][0]["id"]
        # Ensure no COI exists for this admin/notice
        r = admin_session.post(f"{API}/evaluations/score", json={
            "bid_id": bid_id, "kind": "technical",
            "scores": {"experience": 80, "methodology": 75, "team": 70, "financial_health": 85},
        }, timeout=15)
        # Must be 400 (COI required)
        assert r.status_code == 400, f"expected 400 without COI, got {r.status_code} {r.text}"

    def test_declare_coi_then_score(self, admin_session, mongo_db):
        # Declare COI (no conflict)
        r = admin_session.post(f"{API}/evaluations/coi", json={
            "notice_ref": STATE["notice_ref"], "has_conflict": False,
        }, timeout=15)
        assert r.status_code == 200, r.text

        # Score technical for both bids
        tech_scores = [
            {"experience": 80, "methodology": 75, "team": 70, "financial_health": 85},   # bid0 tech avg = 77.5
            {"experience": 90, "methodology": 85, "team": 80, "financial_health": 90},   # bid1 tech avg = 86.5
        ]
        for i, b in enumerate(STATE["bids"]):
            rs = admin_session.post(f"{API}/evaluations/score", json={
                "bid_id": b["id"], "kind": "technical", "scores": tech_scores[i],
            }, timeout=15)
            assert rs.status_code == 200, rs.text

        # Score commercial
        comm_scores = [95.0, 80.0]
        for i, b in enumerate(STATE["bids"]):
            rc = admin_session.post(f"{API}/evaluations/score", json={
                "bid_id": b["id"], "kind": "commercial", "scores": {"commercial": comm_scores[i]},
            }, timeout=15)
            assert rc.status_code == 200, rc.text

    def test_award_report(self, admin_session):
        r = admin_session.get(f"{API}/evaluations/award-report/{STATE['notice_ref']}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "ranking" in d and len(d["ranking"]) == 2
        # Verify combined = tech*0.6 + comm*0.4
        for row in d["ranking"]:
            expected = round(row["technical_avg"] * 0.6 + row["commercial_avg"] * 0.4, 2)
            assert abs(row["combined"] - expected) < 0.5, f"combined mismatch: {row}"
            assert "qualifies" in row
        # First row should be higher combined
        assert d["ranking"][0]["combined"] >= d["ranking"][1]["combined"]
        # Recommendation qualifies flag
        if d["recommendation"]:
            assert d["recommendation"]["qualifies"] is True

    def test_envelope_lock(self, admin_session, mongo_db):
        r = admin_session.post(f"{API}/evaluations/lock-envelope", json={
            "notice_ref": STATE["notice_ref"], "kind": "technical",
        }, timeout=15)
        assert r.status_code == 200, r.text
        n = mongo_db.notices.find_one({"notice_ref": STATE["notice_ref"]})
        assert n.get("technical_locked_at") is not None


# ============================================================
#  3. Wave 3 — BOQ & Contracts
# ============================================================
class TestWave3BOQ:
    def test_create_boq_template(self, admin_session):
        r = admin_session.post(f"{API}/boq/templates", json={
            "name": f"TEST_BOQ_{uuid.uuid4().hex[:6]}",
            "notice_ref": STATE["notice_ref"], "currency": "USD",
            "items": [],
        }, timeout=15)
        assert r.status_code == 200, r.text
        STATE["boq_template_id"] = r.json()["id"]

    def test_import_boq_excel(self, admin_session):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Sl.No", "Description", "Unit", "Quantity", "Unit Rate", "Remarks"])
        ws.append([1, "Item A", "nos", 10, 100, "n/a"])
        ws.append([2, "Item B", "kg", 5, 50, ""])
        ws.append([3, "Item C", "m", 20, 25, ""])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        # multipart upload
        headers = {k: v for k, v in admin_session.headers.items() if k.lower() != "content-type"}
        r = requests.post(
            f"{API}/boq/templates/{STATE['boq_template_id']}/import-excel",
            files={"file": ("boq.xlsx", buf.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            cookies=admin_session.cookies, headers=headers, timeout=20,
        )
        assert r.status_code == 200, r.text
        assert r.json()["items"] == 3

        # Verify items via GET
        rg = admin_session.get(f"{API}/boq/templates/{STATE['boq_template_id']}", timeout=15)
        assert rg.status_code == 200
        items = rg.json()["items"]
        assert len(items) == 3
        assert items[0]["description"] == "Item A"

    def test_vendor_boq_submission(self):
        # Vendor 0 submits priced BOQ
        b = STATE["bids"][0]
        r = b["session"].post(f"{API}/boq/submissions", json={
            "template_id": STATE["boq_template_id"], "bid_id": b["id"],
            "prices": [{"sl_no": 1, "unit_rate": 110},
                       {"sl_no": 2, "unit_rate": 55},
                       {"sl_no": 3, "unit_rate": 30}],
        }, timeout=15)
        assert r.status_code == 200, r.text
        # total = 110*10 + 55*5 + 30*20 = 1100 + 275 + 600 = 1975
        assert r.json()["total_amount"] == pytest.approx(1975.0)

        # Second vendor
        b2 = STATE["bids"][1]
        r2 = b2["session"].post(f"{API}/boq/submissions", json={
            "template_id": STATE["boq_template_id"], "bid_id": b2["id"],
            "prices": [{"sl_no": 1, "unit_rate": 120},
                       {"sl_no": 2, "unit_rate": 45},
                       {"sl_no": 3, "unit_rate": 28}],
        }, timeout=15)
        assert r2.status_code == 200

    def test_boq_compare(self, admin_session):
        r = admin_session.get(f"{API}/boq/compare/{STATE['boq_template_id']}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["rows"]) == 3
        assert len(d["totals"]) == 2


class TestWave3Contracts:
    def test_create_contract_for_awarded_bid(self, admin_session, mongo_db):
        from bson import ObjectId
        # Mark bid 0 as awarded directly
        bid = STATE["bids"][0]
        mongo_db.bids.update_one({"_id": ObjectId(bid["id"])},
                                 {"$set": {"status": "awarded"}})
        v0 = STATE["vendors"][0]
        r = admin_session.post(f"{API}/contracts", json={
            "notice_ref": STATE["notice_ref"], "bid_id": bid["id"],
            "vendor_id": v0["id"],
            "title": "TEST_Contract_Wave3", "value": 900000, "currency": "USD",
            "start_date": datetime.now(timezone.utc).date().isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat(),
            "milestones": [
                {"order": 1, "title": "Kickoff", "amount": 100000,
                 "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()},
                {"order": 2, "title": "Delivery", "amount": 800000,
                 "due_date": (datetime.now(timezone.utc) + timedelta(days=300)).date().isoformat()},
            ],
            "obligations": ["Quality gate"],
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["contract_ref"].startswith("PMC-CON-")
        STATE["contract_id"] = d["id"]

    def test_complete_milestone(self, admin_session):
        r = admin_session.post(
            f"{API}/contracts/{STATE['contract_id']}/milestones/1/complete", timeout=15)
        assert r.status_code == 200, r.text

    def test_add_variation(self, admin_session):
        r = admin_session.post(f"{API}/contracts/variations", json={
            "contract_id": STATE["contract_id"],
            "reason": "Scope change", "amount_delta": 5000,
        }, timeout=15)
        assert r.status_code == 200, r.text

    def test_contract_reject_non_awarded(self, admin_session):
        # bid[1] is NOT awarded
        b1 = STATE["bids"][1]
        v1 = STATE["vendors"][1]
        r = admin_session.post(f"{API}/contracts", json={
            "notice_ref": STATE["notice_ref"], "bid_id": b1["id"], "vendor_id": v1["id"],
            "title": "TEST_Reject", "value": 900000,
            "start_date": datetime.now(timezone.utc).date().isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat(),
            "milestones": [], "obligations": [],
        }, timeout=15)
        assert r.status_code == 400


# ============================================================
#  4. Wave 4 — Vendor Intelligence + Masters
# ============================================================
class TestWave4VendorIntel:
    def test_upsert_rating(self, admin_session):
        vref = STATE["vendors"][0]["ref"]
        r = admin_session.post(f"{API}/vendor-intel/ratings", json={
            "vendor_ref": vref, "score": 82.5, "band": "good",
            "delivery_score": 85, "quality_score": 80,
            "financial_score": 82, "esg_score": 78,
        }, timeout=15)
        assert r.status_code == 200, r.text

    def test_blacklist_and_unblacklist(self, admin_session):
        vref = STATE["vendors"][1]["ref"]
        r = admin_session.post(f"{API}/vendor-intel/blacklist", json={
            "vendor_ref": vref, "reason": "Test blacklist reason",
        }, timeout=15)
        assert r.status_code == 200, r.text

        rl = admin_session.get(f"{API}/vendor-intel/blacklist", timeout=15)
        assert rl.status_code == 200
        assert any(b["vendor_ref"] == vref for b in rl.json())

        rd = admin_session.delete(f"{API}/vendor-intel/blacklist/{vref}", timeout=15)
        assert rd.status_code == 200

    def test_watchlist_and_esg(self, admin_session):
        vref = STATE["vendors"][0]["ref"]
        r1 = admin_session.post(f"{API}/vendor-intel/watchlist", json={
            "vendor_ref": vref, "reason": "Watching for delivery"}, timeout=15)
        assert r1.status_code == 200

        r2 = admin_session.post(f"{API}/vendor-intel/esg", json={
            "vendor_ref": vref, "environmental_policy": True,
            "social_policy": True, "governance_policy": True,
            "certifications": ["ISO14001"], "notes": "test"}, timeout=15)
        assert r2.status_code == 200

    def test_summary(self, admin_session):
        r = admin_session.get(f"{API}/vendor-intel/summary", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d, list)
        # Find our vendor 0
        v0 = next((x for x in d if x.get("vendor_ref") == STATE["vendors"][0]["ref"]), None)
        assert v0 is not None
        assert v0.get("rating") == 82.5
        assert v0.get("band") == "good"
        assert v0.get("watchlisted") is True


class TestWave4Masters:
    def test_masters_crud(self, admin_session):
        code = f"TEST{uuid.uuid4().hex[:4].upper()}"
        rc = admin_session.post(f"{API}/masters/companies", json={
            "name": f"TEST_Wv4_Co_{code}", "code": code, "country": "KZ"}, timeout=15)
        assert rc.status_code == 200, rc.text
        rlst = admin_session.get(f"{API}/masters/companies", timeout=15)
        assert rlst.status_code == 200
        assert any(c.get("code") == code for c in rlst.json())

        rcode = f"TESTROLE_{uuid.uuid4().hex[:4]}"
        rr = admin_session.post(f"{API}/masters/roles", json={
            "code": rcode, "label": "Wave4 Test Role",
            "permissions": ["bid.read"]}, timeout=15)
        assert rr.status_code == 200, rr.text
        rl = admin_session.get(f"{API}/masters/roles", timeout=15)
        assert any(r.get("code") == rcode for r in rl.json())

        rm = admin_session.post(f"{API}/masters/approval-matrices", json={
            "name": f"TEST_Wv4_Matrix_{uuid.uuid4().hex[:4]}",
            "applies_to": "bid",
            "steps": [
                {"order": 1, "role_code": "escrow_agent",
                 "action_label": "Escrow", "sla_hours": 24, "required": True},
            ],
        }, timeout=15)
        assert rm.status_code == 200, rm.text
        rml = admin_session.get(f"{API}/masters/approval-matrices", timeout=15)
        assert rml.status_code == 200


# ============================================================
#  5. Wave 5 — Analytics + AI anomaly
# ============================================================
class TestWave5Analytics:
    def test_dashboard(self, admin_session):
        r = admin_session.get(f"{API}/analytics/dashboard", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "totals" in d and "funnel" in d and "top_bids" in d
        for k in ["notices", "bids", "vendors", "awarded", "emd_collected"]:
            assert k in d["totals"], f"missing totals.{k}"

    def test_ai_bid_anomaly(self, admin_session):
        # Use bid[1] which has peer (bid[0])
        bid_id = STATE["bids"][1]["id"]
        r = admin_session.post(f"{API}/analytics/ai/bid-anomaly/{bid_id}", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "score" in d
        assert "flags" in d and isinstance(d["flags"], list)
        assert "deviation_pct" in d
        assert "peer_avg" in d
        assert "narrative" in d  # may be real or fallback


# ============================================================
#  6. Wave 6 — Auctions + Helpdesk
# ============================================================
class TestWave6Auction:
    def test_create_reverse_auction(self, admin_session):
        now = datetime.now(timezone.utc)
        r = admin_session.post(f"{API}/auctions", json={
            "notice_ref": STATE["notice_ref"],
            "auction_type": "reverse",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(hours=1)).isoformat(),
            "starting_price": 100000, "currency": "USD",
            "minimum_decrement": 500, "is_anonymous": True,
        }, timeout=15)
        assert r.status_code == 200, r.text
        STATE["auction_id"] = r.json()["id"]

    def test_bid_lower_accepted(self):
        b = STATE["bids"][0]
        # 100000 - 500 = 99500 (must be <= 99500)
        r = b["session"].post(f"{API}/auctions/bid", json={
            "auction_id": STATE["auction_id"], "price": 99000,
        }, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["current_price"] == 99000

    def test_bid_higher_rejected(self):
        b = STATE["bids"][1]
        # current = 99000; higher price 99500 should be rejected in reverse
        r = b["session"].post(f"{API}/auctions/bid", json={
            "auction_id": STATE["auction_id"], "price": 99500,
        }, timeout=15)
        assert r.status_code == 400


class TestWave6Helpdesk:
    def test_open_reply_close_ticket(self, admin_session):
        ro = admin_session.post(f"{API}/support/tickets", json={
            "subject": f"TEST_Ticket_{uuid.uuid4().hex[:5]}",
            "body": "Test ticket body", "priority": "medium",
        }, timeout=15)
        assert ro.status_code == 200, ro.text
        tid = ro.json()["id"]

        rr = admin_session.post(f"{API}/support/tickets/reply", json={
            "ticket_id": tid, "body": "Reply from admin", "attachments": []
        }, timeout=15)
        assert rr.status_code == 200, rr.text

        rc = admin_session.post(f"{API}/support/tickets/{tid}/close", timeout=15)
        assert rc.status_code == 200, rc.text


# ============================================================
#  7. Notifications — fire bid transition, verify row appears
# ============================================================
class TestNotifications:
    def test_state_transition_creates_notification(self, admin_session, mongo_db):
        """Move bid[1] (still emd_pending) to emd_paid then escrow_accepted,
        then verify a notification row was inserted for the admin role."""
        from bson import ObjectId
        bid = STATE["bids"][1]
        # Force to emd_paid
        mongo_db.bids.update_one({"_id": ObjectId(bid["id"])},
                                 {"$set": {"status": "emd_paid",
                                           "emd_paid_amount": 10500.0}})
        # Escrow accepts → next role is admin
        es = _staff_login("escrow@pmcmanagers.com", "Escrow@123", "escrow_agent")
        r = es.post(f"{API}/bids/{bid['id']}/decision",
                    json={"action": "accept", "role": "escrow_agent"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "escrow_accepted"

        # Small wait for the notify insert
        import time
        time.sleep(1.5)

        # Query notifications collection directly to be robust
        recent = list(mongo_db.notifications.find(
            {"related_id": bid["id"]}).sort("created_at", -1))
        assert len(recent) > 0, "no notification row created after transition"
        assert any(n.get("role") == "admin" for n in recent), \
            f"no admin notification: {[n.get('role') for n in recent]}"

    def test_list_my_notifications_endpoint(self, admin_session):
        r = admin_session.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d, list)
        STATE["_notif_list"] = d

    def test_mark_read_and_read_all(self, admin_session):
        d = STATE.get("_notif_list") or []
        if d:
            nid = d[0]["id"]
            r = admin_session.post(f"{API}/notifications/{nid}/read", timeout=15)
            assert r.status_code == 200
        ra = admin_session.post(f"{API}/notifications/read-all", timeout=15)
        assert ra.status_code == 200
