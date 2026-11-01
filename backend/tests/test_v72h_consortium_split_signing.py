# v72h: consortium payment instructions — bank snapshot, dual officer signing, mark-paid with proof.
import uuid

import pytest
from bson import ObjectId

from test_v72e_partner_consortium_notices import API, DB, _login_staff, _now

RID = uuid.uuid4().hex[:6].upper()
NREF = f"TEST-V72H-{RID}"
PMC_EMAIL = "adminsupport@pmcmanagers.com"
ESC_EMAIL = "escrow@pmcmanagers.com"
SIG = lambda a: {"pmc": {"action": a, "signed_at": _now()}, "escrow_institution": {"action": a, "signed_at": _now()}}
LEAD_VID = ObjectId()
M0_EMAIL = f"test_v72h_m0_{RID.lower()}@example.com"
M1_EMAIL = f"test_v72h_m1_{RID.lower()}@example.com"
S = {}
PROOF = f"vendor-docs/TEST_v72h_{RID}.pdf"  # real db.uploads doc (paid now validates proof_key)


def _bank(tag):
    return {"bank_name": f"TEST Bank {tag}", "bank_branch": f"Br {tag}", "bank_account_number": f"ACC-{tag}-{RID}",
            "bank_swift": f"SWF{tag}", "bank_address": f"Addr {tag}"}


def _cons():
    return {"id": "c" + RID, "name": f"TEST Team {RID}", "lead_share_pct": 50.0, "escrow_mode": "shared", "deposit_mode": "lead_pays",
            "members": [{"vendor_id": f"m0{RID}", "company_name": "TEST Member Zero", "email": M0_EMAIL, "share_pct": 30.0},
                        {"vendor_id": f"m1{RID}", "company_name": "TEST NoBank Member", "email": M1_EMAIL, "share_pct": 20.0}]}


def _mk(tag, pmc=PMC_EMAIL, esc=ESC_EMAIL):
    ref = f"TEST-BID-{RID}-{tag}"
    DB.bids.insert_one({"bid_ref": ref, "notice_ref": NREF, "vendor_id": str(LEAD_VID), "vendor_email": f"test_v72h_lead_{RID.lower()}@example.com",
                        "company_name": "TEST Lead Co", "status": "awarded", "consortium": _cons(), "submitted_at": _now()})
    r = DB.escrow_transactions.insert_one({
        "bid_ref": ref, "notice_ref": NREF, "amount": 1000.0, "currency": "USD", "status": "awaiting_signatures",
        "signatures": SIG("release_to_contractor"), "audit_trail": [], "created_at": _now(), "created_by": "TEST",
        "escrow_account_snapshot": {"name": "TEST acc", "pmc_officer": {"name": "P", "email": pmc}, "escrow_officer": {"name": "E", "email": esc}}})
    return ref, str(r.inserted_id)


@pytest.fixture(scope="module", autouse=True)
def setup():
    DB.vendors.update_one({"_id": LEAD_VID}, {"$set": {"email": f"test_v72h_lead_{RID.lower()}@example.com", "vendor_ref": f"TEST-V72H-{RID}",
                                                       "company_name": "TEST Lead Co", **_bank("LEAD")}}, upsert=True)
    DB.registrations.insert_one({"email": M0_EMAIL, "created_at": "2020-01-01T00:00:00", **_bank("OLD")})
    DB.registrations.insert_one({"email": M0_EMAIL, "created_at": _now(), **_bank("M0")})
    DB.uploads.delete_many({"key": PROOF}); DB.uploads.insert_one({"key": PROOF, "content_type": "application/pdf", "size_bytes": 1, "data_b64": "eA==", "created_at": _now()})
    yield
    DB.uploads.delete_many({"key": PROOF})
    DB.bids.delete_many({"notice_ref": NREF})
    DB.escrow_transactions.delete_many({"notice_ref": NREF})
    DB.vendors.delete_many({"_id": LEAD_VID})
    DB.registrations.delete_many({"email": {"$in": [M0_EMAIL, M1_EMAIL]}})
    DB.notifications.delete_many({"related_notice_ref": NREF})


@pytest.fixture(scope="module")
def pmc():
    return _login_staff(PMC_EMAIL, "Admin@12345", "admin")


@pytest.fixture(scope="module")
def esc():
    return _login_staff(ESC_EMAIL, "Escrow@123", "escrow_agent")


@pytest.fixture(scope="module")
def other():
    return _login_staff("kannan@emeraldcorporates.com", "Owner@123", "admin")


@pytest.fixture(scope="module")
def reviewer():
    return _login_staff("reviewerqa@pmcmanagers.com", "Reviewer@12345", "reviewer")


def _u(tid, i, what):
    return f"{API}/escrow/transactions/{tid}/consortium-split/{i}/{what}"


class TestSigningFlow:
    def test_release_creates_instructions(self, pmc):
        S["bref"], S["tid"] = _mk("A")
        r = pmc.post(f"{API}/escrow/transactions/{S['tid']}/release", json={"action": "release_to_contractor", "memo": "TEST"})
        assert r.status_code == 200, r.text
        lines = DB.escrow_transactions.find_one({"_id": ObjectId(S["tid"])})["consortium_split"]["lines"]
        assert [x["instruction_ref"] for x in lines] == [f"{S['bref']}-P{i}" for i in (1, 2, 3)]
        assert all(x["status"] == "awaiting_signatures" and x["signatures"] == {} for x in lines)
        assert lines[0]["bank"] == _bank("LEAD")            # from vendors doc
        assert lines[1]["bank"] == _bank("M0")              # latest registrations doc by email
        assert lines[2]["bank"] == {}                       # nothing on file

    def test_rbac_and_non_officer(self, other, reviewer):
        r = other.post(_u(S["tid"], 0, "sign"), json={})
        assert r.status_code == 403, r.text
        assert reviewer.post(_u(S["tid"], 0, "sign"), json={}).status_code == 403
        assert other.post(_u(S["tid"], 9, "sign"), json={}).status_code == 404

    def test_no_bank_409(self, pmc):
        r = pmc.post(_u(S["tid"], 2, "sign"), json={})
        assert r.status_code == 409 and "TEST NoBank Member" in r.json()["detail"], r.text

    def test_pmc_sign_then_paid_blocked(self, pmc):
        r = pmc.post(_u(S["tid"], 0, "sign"), json={"comment": "TEST ok"})
        assert r.status_code == 200, r.text
        ln = r.json()["lines"][0]
        assert ln["status"] == "awaiting_signatures" and set(ln["signatures"]) == {"pmc"}
        assert ln["signatures"]["pmc"]["email"] == PMC_EMAIL and ln["signatures"]["pmc"]["comment"] == "TEST ok"
        assert ln["signatures"]["pmc"]["account"] == _bank("LEAD")["bank_account_number"]
        assert pmc.post(_u(S["tid"], 0, "paid"), json={"reference": "WIRE-1", "proof_key": "vendor-docs/x.pdf"}).status_code == 409

    def test_escrow_sign_approves(self, esc):
        r = esc.post(_u(S["tid"], 0, "sign"), json={})
        assert r.status_code == 200, r.text
        ln = r.json()["lines"][0]
        assert ln["status"] == "approved" and set(ln["signatures"]) == {"pmc", "escrow_institution"}
        assert esc.post(_u(S["tid"], 0, "sign"), json={}).status_code == 409
        tx = DB.escrow_transactions.find_one({"_id": ObjectId(S["tid"])})
        ev = [e["event"] for e in tx["audit_trail"]]
        assert f"split_{S['bref']}-P1_signed_by_pmc" in ev and f"split_{S['bref']}-P1_signed_by_escrow_institution" in ev

    def test_escrow_agent_cannot_mark_paid(self, esc):
        assert esc.post(_u(S["tid"], 0, "paid"), json={"reference": "WIRE-1", "proof_key": "vendor-docs/x.pdf"}).status_code == 403

    def test_mark_paid(self, pmc):
        assert pmc.post(_u(S["tid"], 0, "paid"), json={"reference": "WIRE-1"}).status_code == 422
        assert pmc.post(_u(S["tid"], 0, "paid"), json={"reference": "WI", "proof_key": "vendor-docs/x.pdf"}).status_code == 422
        r = pmc.post(_u(S["tid"], 0, "paid"), json={"reference": " WIRE-TEST-1 ", "proof_key": PROOF})
        assert r.status_code == 200, r.text
        ln = r.json()["lines"][0]
        assert ln["status"] == "paid" and ln["paid_ref"] == "WIRE-TEST-1" and ln["proof_key"] == PROOF and ln["paid_by"] == PMC_EMAIL
        assert pmc.post(_u(S["tid"], 0, "paid"), json={"reference": "WIRE-2", "proof_key": "vendor-docs/x.pdf"}).status_code == 409
        assert pmc.post(_u(S["tid"], 0, "sign"), json={}).status_code == 409
        db_ln = DB.escrow_transactions.find_one({"_id": ObjectId(S["tid"])})["consortium_split"]["lines"]
        assert db_ln[0]["status"] == "paid" and db_ln[1]["status"] == "awaiting_signatures"

    def test_bank_added_later_resnapshots(self, pmc):
        DB.registrations.insert_one({"email": M1_EMAIL, "created_at": _now(), **_bank("M1")})
        r = pmc.post(_u(S["tid"], 2, "sign"), json={})
        assert r.status_code == 200, r.text
        assert r.json()["lines"][2]["bank"]["bank_account_number"] == _bank("M1")["bank_account_number"]


class TestSameEmail:
    def test_same_email_409(self, pmc):
        _, tid = _mk("SAME", pmc=PMC_EMAIL, esc=PMC_EMAIL.upper())
        assert pmc.post(f"{API}/escrow/transactions/{tid}/release", json={"action": "release_to_contractor", "memo": "TEST"}).status_code == 200
        r = pmc.post(_u(tid, 0, "sign"), json={})
        assert r.status_code == 409 and "same email" in r.json()["detail"], r.text
