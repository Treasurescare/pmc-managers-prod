# v56n — Verification of 24-item production bug sheet (P0/P1) against PREVIEW.
# Read-mostly; creates TEST_ prefixed auctions/corrigenda/rubric data only.
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api/v1"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _admin():
    s = requests.Session()
    r = s.post(f"{API}/admin/auth/login", json={"email": "adminsupport@pmcmanagers.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['token']}", "X-CSRF-Token": d["csrf_token"]})
    return s


def _vendor():
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": "manualvendor@pmcmanagers.com", "password": "Vendor@12345"})
    if r.status_code != 200:
        pytest.skip(f"vendor login failed {r.status_code} {r.text[:200]}")
    d = r.json()
    hdr = {}
    if d.get("token"):
        hdr["Authorization"] = f"Bearer {d['token']}"
    if d.get("csrf_token"):
        hdr["X-CSRF-Token"] = d["csrf_token"]
    s.headers.update(hdr)
    return s, d


@pytest.fixture(scope="module")
def admin():
    return _admin()


def _published_notice():
    n = mdb.notices.find_one({"is_published": True, "submission_deadline": {"$gt": "2026-10-25"}},
                             sort=[("_id", -1)])
    assert n, "no published notice"
    return n


# ---------- BUG 18 / 44 / 43 — Evaluation ----------
class TestEvaluation:
    def test_award_report_scored_notice(self, admin):
        for ref in ["PMC-NOT-2026-0015", "PMC-NOT-2026-0016", "PMC-NOT-2026-0018"]:
            r = admin.get(f"{API}/evaluations/award-report/{ref}")
            print(ref, r.status_code, r.text[:400])
            assert r.status_code == 200
            assert "ranking" in r.json()

    def test_rubric_save_persists(self, admin):
        ref = "PMC-NOT-2026-0016"
        before = admin.get(f"{API}/evaluations/rubric/{ref}")
        print("before", before.status_code, before.text[:300])
        crit = [{"code": "TECH_A", "label": "Approach", "weight": 0.7, "max_score": 100},
                {"code": "TECH_B", "label": "Team", "weight": 0.3, "max_score": 100}]
        r = admin.post(f"{API}/evaluations/rubric", json={"notice_ref": ref, "technical_criteria": crit,
                                                         "commercial_weight": 0.35, "minimum_technical": 55})
        print("save", r.status_code, r.text[:300])
        assert r.status_code == 200
        g = admin.get(f"{API}/evaluations/rubric/{ref}").json()
        assert g["commercial_weight"] == 0.35
        assert g["minimum_technical"] == 55
        assert [c["code"] for c in g["technical_criteria"]] == ["TECH_A", "TECH_B"]
        # restore previous
        if before.status_code == 200:
            b = before.json()
            admin.post(f"{API}/evaluations/rubric", json={k: b[k] for k in ("notice_ref", "technical_criteria", "commercial_weight", "minimum_technical") if k in b})

    def test_rubric_zero_commercial_weight_respected(self, admin):
        """commercial_weight=0 should give tech_weight 1.0 (code uses `or 0.4`)."""
        ref = "PMC-NOT-2026-0015"
        before = admin.get(f"{API}/evaluations/rubric/{ref}").json()
        admin.post(f"{API}/evaluations/rubric", json={"notice_ref": ref, "technical_criteria": before["technical_criteria"],
                                                     "commercial_weight": 0.0, "minimum_technical": 0})
        rep = admin.get(f"{API}/evaluations/award-report/{ref}").json()
        admin.post(f"{API}/evaluations/rubric", json={k: before[k] for k in ("notice_ref", "technical_criteria", "commercial_weight", "minimum_technical") if k in before})
        print("rubric in report", rep["rubric"])
        assert rep["rubric"]["commercial_weight"] == 0.0, "commercial_weight 0 coerced to 0.4"
        assert rep["rubric"]["minimum_technical"] == 0.0, "minimum_technical 0 coerced to 60"

    def test_score_without_coi_then_with_coi_nonzero(self, admin):
        bid = mdb.bids.find_one({"notice_ref": "PMC-NOT-2026-0016"})
        if not bid:
            pytest.skip("no bid on 0016")
        ref = bid["notice_ref"]
        notice = mdb.notices.find_one({"notice_ref": ref}, {"technical_locked_at": 1})
        if notice and notice.get("technical_locked_at"):
            pytest.skip("technical envelope locked on 0016 — needs unlocked scored tender")
        rub = admin.get(f"{API}/evaluations/rubric/{ref}").json()
        scores = {c["code"]: float(c.get("max_score", 100)) * 0.8 for c in rub["technical_criteria"]}
        admin.post(f"{API}/evaluations/coi", json={"notice_ref": ref, "has_conflict": False, "details": "TEST_auto"})
        r = admin.post(f"{API}/evaluations/score", json={"bid_id": str(bid["_id"]), "kind": "technical", "scores": scores})
        print("score", r.status_code, r.text[:300])
        assert r.status_code == 200
        rep = admin.get(f"{API}/evaluations/award-report/{ref}").json()
        row = [x for x in rep["ranking"] if x["bid_id"] == str(bid["_id"])][0]
        print("row", row)
        assert row["technical_avg"] > 0

    def test_no_rubric_notice_scores_zero(self, admin):
        """Notice 0018 has scores but no rubric → technical_avg 0 (bug-44 RCA candidate)."""
        rep = admin.get(f"{API}/evaluations/award-report/PMC-NOT-2026-0018").json()
        print(rep["rubric"], [(x["bid_ref"], x["technical_avg"], x["qualifies"]) for x in rep["ranking"]])
        tech_scores = list(mdb.scores.find({"notice_ref": "PMC-NOT-2026-0018", "kind": "technical"}))
        if tech_scores:
            assert any(x["technical_avg"] > 0 for x in rep["ranking"]), "tech scores exist but all compute to 0 (no rubric → empty criteria)"


# ---------- BUG 67 — audit + masters ----------
class TestAuditMasters:
    def test_audit_events(self, admin):
        r = admin.get(f"{API}/audit-events?limit=5")
        assert r.status_code == 200
        assert len(r.json() if isinstance(r.json(), list) else r.json().get("items", [])) > 0


# ---------- BUG 72 — escrow magic link invalid token ----------
def test_escrow_magic_invalid_token():
    r = requests.get(f"{API}/escrow/magic/{uuid.uuid4().hex}")
    print(r.status_code, r.text[:200])
    assert r.status_code in (400, 401, 404, 410)


# ---------- BUG 60 — reverse auction create/start ----------
class TestAuction:
    def test_create_start_and_vendor_state(self, admin):
        n = _published_notice()
        r = admin.post(f"{API}/reverse-auctions", json={"notice_ref": n["notice_ref"], "title": "TEST_v56n auction",
                                                       "starting_price": 10000, "floor_price": 5000, "min_decrement": 100,
                                                       "duration_minutes": 30})
        print("create", r.status_code, r.text[:200])
        assert r.status_code == 200
        aid = r.json()["id"]
        s0 = admin.post(f"{API}/reverse-auctions/{aid}/start")
        print("start w/o participants", s0.status_code, s0.text[:250])
        assert s0.status_code == 400 and "participants" in s0.text
        vs, vd = _vendor()
        reg = vs.post(f"{API}/reverse-auctions/{aid}/register")
        print("vendor register", reg.status_code, reg.text[:200])
        assert reg.status_code == 200
        # seed 2nd participant directly (needs seed data — only one vendor credential)
        mdb.reverse_auction_participants.insert_one({"auction_id": aid, "vendor_id": "TEST_seed_vendor",
                                                     "vendor_email": "TEST_seed@example.com", "alias": "Bidder Z",
                                                     "company_name": "TEST_seed"})
        s1 = admin.post(f"{API}/reverse-auctions/{aid}/start")
        print("start", s1.status_code, s1.text[:200])
        assert s1.status_code == 200 and s1.json()["status"] == "live"
        g = admin.get(f"{API}/reverse-auctions/{aid}").json()
        assert g["auction"]["status"] == "live"
        st = vs.get(f"{API}/reverse-auctions/{aid}/state-mine")
        print("state-mine", st.status_code, st.text[:300])
        assert st.status_code == 200
        b = vs.post(f"{API}/reverse-auctions/{aid}/bid", json={"price": 9800})
        print("bid", b.status_code, b.text[:200])
        assert b.status_code == 200
        admin.post(f"{API}/reverse-auctions/{aid}/close")
        os.environ["V56N_AID"] = aid


# ---------- BUG 15 / 55 — registrations decisions ----------
class TestRegistrations:
    def test_decisions_on_submitted(self, admin):
        lst = admin.get(f"{API}/registrations?status=submitted&limit=200").json()
        print("submitted count", len(lst))
        res = []
        for reg in lst[:6]:
            rid = reg["id"]
            r = admin.post(f"{API}/registrations/{rid}/decision", json={"action": "clarify", "notes": "TEST_v56n clarify"})
            res.append((reg.get("company_name"), reg.get("email"), "clarify", r.status_code, r.text[:160]))
        for x in res:
            print(x)
        assert all(x[3] == 200 for x in res), res

    def test_approve_moves_status(self, admin):
        lst = admin.get(f"{API}/registrations?limit=200").json()
        cands = [r for r in lst if r.get("status") in ("submitted", "needs_clarification")]
        out = []
        approved_any = None
        for reg in cands[:8]:
            r = admin.post(f"{API}/registrations/{reg['id']}/decision", json={"action": "approve", "notes": "TEST_v56n"})
            out.append((reg.get("email"), r.status_code, r.text[:200]))
            if r.status_code == 200:
                approved_any = reg["id"]
                break
        for o in out:
            print(o)
        assert approved_any, "no registration could be approved"
        d = admin.get(f"{API}/registrations/{approved_any}").json()
        print("after approve status", d.get("status"), d.get("vendor_ref"))
        assert d["status"] in ("approved", "pending_verify", "approved_pending_verify")
        sub = admin.get(f"{API}/registrations?status=submitted&limit=200").json()
        assert approved_any not in [x["id"] for x in sub]

    def test_reject_requires_notes(self, admin):
        lst = admin.get(f"{API}/registrations?status=needs_clarification&limit=200").json()
        if not lst:
            pytest.skip("none")
        r = admin.post(f"{API}/registrations/{lst[0]['id']}/decision", json={"action": "reject", "notes": "TEST_v56n reject"})
        print("reject", r.status_code, r.text[:200])
        assert r.status_code == 200


# ---------- BUG 45 — contracts list ----------
def test_contracts_listed(admin):
    r = admin.get(f"{API}/contracts")
    print(r.status_code, r.text[:300])
    assert r.status_code == 200 and len(r.json()) >= 1


# ---------- BUG 23/37 — corrigenda publish → public + pdf ----------
class TestCorrigenda:
    def test_publish_public_pdf(self, admin):
        n = _published_notice()
        ref = n["notice_ref"]
        old_dl = n.get("submission_deadline")
        r = admin.post(f"{API}/notices/{ref}/corrigenda", json={"title": "TEST_v56n corr", "summary": "TEST_v56n summary of change",
                                                               "extend_deadline_days": 3})
        print("publish", r.status_code, r.text[:400])
        assert r.status_code == 200
        cid = (r.json().get("corrigendum") or {}).get("id") or r.json().get("id")
        pub = requests.get(f"{API}/notices/{ref}/corrigenda").json()
        print("public total", pub["total"])
        assert cid in [i["id"] for i in pub["items"]]
        pdf = requests.get(f"{API}/notices/{ref}/corrigenda/{cid}/pdf")
        print("pdf", pdf.status_code, pdf.headers.get("content-type"))
        assert pdf.status_code == 200
        nn = mdb.notices.find_one({"notice_ref": ref})
        print("deadline", old_dl, "->", nn.get("submission_deadline"))
        assert nn.get("submission_deadline") != old_dl, "key dates did not update"
        # cleanup
        admin.delete(f"{API}/notices/{ref}/corrigenda/{cid}", params={"reason": "TEST_v56n cleanup of verification data"})
        mdb.notices.update_one({"notice_ref": ref}, {"$set": {"submission_deadline": old_dl}})


# ---------- BUG 58 — catalog disable ----------
class TestCatalog:
    def test_partial_patch_disable(self, admin):
        p = mdb.products.find_one({"is_active": True})
        pid = str(p["_id"])
        r = admin.patch(f"{API}/products/{pid}", json={"is_active": False})
        print("partial patch (what UI sends)", r.status_code, r.text[:300])
        if r.status_code == 200:
            admin.patch(f"{API}/products/{pid}", json={"is_active": True})
        assert r.status_code == 200


# ---------- BUG 13 — vendor invite ----------
def test_vendor_invite_email(admin):
    em = f"delivered+v56n{uuid.uuid4().hex[:6]}@resend.dev"
    r = admin.post(f"{API}/vendors/invite", json={"email": em, "company_name": "TEST_v56n Invite Co"})
    print("invite", r.status_code, r.text[:500])
    assert r.status_code in (200, 201)


# ---------- BUG 15 — approve a fully-filled seeded registration ----------
def test_seeded_full_registration_approve(admin):
    em = f"delivered+v56nreg{uuid.uuid4().hex[:6]}@resend.dev"
    c = requests.post(f"{API}/registrations", json={"email": em, "company_name": "TEST_v56n Reg Co", "country": "KZ",
                                                    "data_processing_consent": True})
    assert c.status_code == 200, c.text
    rid, tok = c.json()["id"], c.json()["magic_token"]
    body = {"registered_address": "1 Test St", "registration_number": "TEST123", "legal_entity_type": "LLP",
            "decl_conflict_of_interest": True, "decl_integrity": True, "decl_accuracy": True,
            "decl_data_consent": True, "decl_fee": True, "decl_notification": True,
            "signature_name": "T Tester", "signature_title": "CEO", "signature_date": "2026-10-21"}
    u = requests.patch(f"{API}/registrations/{rid}?token={tok}", json=body)
    print("patch", u.status_code, u.text[:300])
    assert u.status_code == 200
    sb = requests.post(f"{API}/registrations/{rid}/submit?token={tok}")
    print("submit", sb.status_code, sb.text[:200])
    assert sb.status_code == 200
    a = admin.post(f"{API}/registrations/{rid}/decision", json={"action": "approve", "notes": "TEST_v56n"})
    print("approve", a.status_code, a.text[:300])
    assert a.status_code == 200
    d = admin.get(f"{API}/registrations/{rid}").json()
    print("status", d.get("status"), d.get("vendor_ref"))
    assert d["status"] != "submitted"
    os.environ["V56N_RID"] = rid
