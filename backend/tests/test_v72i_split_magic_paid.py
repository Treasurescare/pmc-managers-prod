# v72i: consortium split fixes — paid guards (proof in db.uploads, account match, concurrent paid), same-line sign race, magic-link officer signing.
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
from bson import ObjectId

from test_v72e_partner_consortium_notices import API, DB, _login_staff, _now

RID = uuid.uuid4().hex[:6].upper()
NREF = f"TEST-V72I-{RID}"
PMC_EMAIL = "adminsupport@pmcmanagers.com"
ESC_EMAIL = "escrow@pmcmanagers.com"
LEAD_VID = ObjectId()
M0 = f"test_v72i_m0_{RID.lower()}@example.com"
M1 = f"test_v72i_m1_{RID.lower()}@example.com"
PROOF = f"vendor-docs/TEST_v72i_{RID}.pdf"
ACC_ID = ObjectId()
OTHER_ACC = ObjectId()
TOK = "TEST_" + secrets.token_urlsafe(16)
TOK_OTHER = "TEST_" + secrets.token_urlsafe(16)
TOK_REVOKED = "TEST_" + secrets.token_urlsafe(16)


def _bank(tag):
    return {"bank_name": f"TEST Bank {tag}", "bank_branch": "Br", "bank_account_number": f"ACC-{tag}-{RID}", "bank_swift": "SWF", "bank_address": "A"}


def _mk(tag, acc=ACC_ID):
    ref = f"TEST-BID-{RID}-{tag}"
    cons = {"id": "c" + RID, "name": f"TEST Team {RID}", "lead_share_pct": 50.0, "escrow_mode": "shared", "deposit_mode": "lead_pays",
            "members": [{"vendor_id": f"m0{RID}", "company_name": "TEST M0", "email": M0, "share_pct": 30.0},
                        {"vendor_id": f"m1{RID}", "company_name": "TEST M1", "email": M1, "share_pct": 20.0}]}
    DB.bids.insert_one({"bid_ref": ref, "notice_ref": NREF, "vendor_id": str(LEAD_VID), "vendor_email": f"lead_{RID.lower()}@example.com",
                        "company_name": "TEST Lead", "status": "awarded", "consortium": cons, "submitted_at": _now()})
    sig = {"action": "release_to_contractor", "signed_at": _now()}
    r = DB.escrow_transactions.insert_one({
        "bid_ref": ref, "notice_ref": NREF, "amount": 1000.0, "currency": "USD", "status": "awaiting_signatures", "escrow_account_id": str(acc),
        "signatures": {"pmc": sig, "escrow_institution": sig}, "audit_trail": [], "created_at": _now(), "created_by": "TEST",
        "escrow_account_snapshot": {"name": "TEST acc", "pmc_officer": {"name": "P", "email": PMC_EMAIL}, "escrow_officer": {"name": "E", "email": ESC_EMAIL}}})
    return str(r.inserted_id)


@pytest.fixture(scope="module", autouse=True)
def setup():
    DB.vendors.insert_one({"_id": LEAD_VID, "email": f"lead_{RID.lower()}@example.com", "company_name": "TEST Lead", "vendor_ref": f"TEST-V72I-{RID}", **_bank("LEAD")})
    DB.registrations.insert_one({"email": M0, "created_at": _now(), **_bank("M0")})
    DB.registrations.insert_one({"email": M1, "created_at": _now(), **_bank("M1")})
    DB.uploads.insert_one({"key": PROOF, "content_type": "application/pdf", "size_bytes": 1, "data_b64": "eA==", "created_at": _now()})
    DB.escrow_accounts.insert_one({"_id": ACC_ID, "name": f"TEST_ v72i acc {RID}", "institution": "TEST Bank", "currency": "USD",
                                   "pmc_officer": {"email": PMC_EMAIL}, "escrow_officer": {"email": ESC_EMAIL}})
    DB.escrow_magic_tokens.insert_many([
        {"token": TOK, "account_id": str(ACC_ID), "officer_email": ESC_EMAIL, "revoked": False, "created_at": _now()},
        {"token": TOK_OTHER, "account_id": str(OTHER_ACC), "officer_email": ESC_EMAIL, "revoked": False, "created_at": _now()},
        {"token": TOK_REVOKED, "account_id": str(ACC_ID), "officer_email": ESC_EMAIL, "revoked": True, "created_at": _now()}])
    yield
    DB.bids.delete_many({"notice_ref": NREF})
    DB.escrow_transactions.delete_many({"notice_ref": NREF})
    DB.vendors.delete_many({"_id": LEAD_VID})
    DB.registrations.delete_many({"email": {"$in": [M0, M1]}})
    DB.uploads.delete_many({"key": PROOF})
    DB.escrow_accounts.delete_many({"_id": ACC_ID})
    DB.escrow_magic_tokens.delete_many({"token": {"$in": [TOK, TOK_OTHER, TOK_REVOKED]}})
    DB.notifications.delete_many({"related_notice_ref": NREF})


@pytest.fixture(scope="module")
def pmc():
    return _login_staff(PMC_EMAIL, "Admin@12345", "admin")


@pytest.fixture(scope="module")
def esc():
    return _login_staff(ESC_EMAIL, "Escrow@123", "escrow_agent")


def _u(tid, i, what):
    return f"{API}/escrow/transactions/{tid}/consortium-split/{i}/{what}"


def _released(pmc, tag, acc=ACC_ID):
    tid = _mk(tag, acc)
    assert pmc.post(f"{API}/escrow/transactions/{tid}/release", json={"action": "release_to_contractor", "memo": "TEST"}).status_code == 200
    return tid


def _lines(tid):
    return DB.escrow_transactions.find_one({"_id": ObjectId(tid)})["consortium_split"]["lines"]


# Race: both officers sign the SAME line at once — both signatures kept, approved
class TestSameLineRace:
    @pytest.mark.parametrize("n", range(4))
    def test_same_line_both_sides(self, pmc, esc, n):
        tid = _released(pmc, f"SL{n}")
        with ThreadPoolExecutor(6) as ex:
            codes = list(ex.map(lambda a: a[0].post(_u(tid, a[1], "sign"), json={}).status_code,
                                [(pmc, 0), (esc, 0), (pmc, 1), (esc, 1), (pmc, 2), (esc, 2)]))
        assert codes == [200] * 6, codes
        for x in _lines(tid):
            assert set(x["signatures"]) == {"pmc", "escrow_institution"} and x["status"] == "approved", x

    def test_only_one_side_not_approved(self, pmc):
        tid = _released(pmc, "ONE")
        with ThreadPoolExecutor(3) as ex:
            list(ex.map(lambda i: pmc.post(_u(tid, i, "sign"), json={}), range(3)))
        assert all(x["status"] == "awaiting_signatures" and set(x["signatures"]) == {"pmc"} for x in _lines(tid))


# Paid guards
class TestPaidGuards:
    def test_proof_must_exist(self, pmc, esc):
        tid = _released(pmc, "PF")
        pmc.post(_u(tid, 0, "sign"), json={}); esc.post(_u(tid, 0, "sign"), json={})
        r = pmc.post(_u(tid, 0, "paid"), json={"reference": "WIRE-X", "proof_key": "vendor-docs/does-not-exist.pdf"})
        assert r.status_code == 422 and "slip" in r.json()["detail"], r.text
        assert _lines(tid)[0]["status"] == "approved"
        r = pmc.post(_u(tid, 0, "paid"), json={"reference": "WIRE-X", "proof_key": PROOF})
        assert r.status_code == 200 and r.json()["lines"][0]["proof_key"] == PROOF

    def test_account_mismatch_409(self, pmc, esc):
        tid = _released(pmc, "AM")
        pmc.post(_u(tid, 1, "sign"), json={}); esc.post(_u(tid, 1, "sign"), json={})
        DB.escrow_transactions.update_one({"_id": ObjectId(tid)}, {"$set": {"consortium_split.lines.1.bank.bank_account_number": "CHANGED"}})
        r = pmc.post(_u(tid, 1, "paid"), json={"reference": "WIRE-X", "proof_key": PROOF})
        assert r.status_code == 409 and "bank account changed" in r.json()["detail"], r.text
        assert _lines(tid)[1]["status"] == "approved"

    def test_concurrent_paid_one_wins(self, pmc, esc):
        tid = _released(pmc, "CP")
        pmc.post(_u(tid, 0, "sign"), json={}); esc.post(_u(tid, 0, "sign"), json={})
        with ThreadPoolExecutor(4) as ex:
            codes = list(ex.map(lambda k: pmc.post(_u(tid, 0, "paid"), json={"reference": f"WIRE-C{k}", "proof_key": PROOF}).status_code, range(4)))
        assert sorted(codes) == [200, 409, 409, 409], codes
        ln = _lines(tid)[0]
        assert ln["status"] == "paid" and ln["paid_ref"].startswith("WIRE-C")


# Magic-link escrow officer
class TestMagic:
    def test_list_and_sign(self, pmc):
        tid = _released(pmc, "MG")
        other_tid = _released(pmc, "MGO", OTHER_ACC)
        r = requests.get(f"{API}/escrow/magic/{TOK}/consortium-splits")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["officer_email"] == ESC_EMAIL
        tids = [x["tid"] for x in d["items"]]
        assert tid in tids and other_tid not in tids
        item = next(x for x in d["items"] if x["tid"] == tid)
        assert len(item["lines"]) == 3 and "_id" not in item
        r = requests.post(f"{API}/escrow/magic/{TOK}/consortium-split/{tid}/0/sign", json={"comment": "TEST magic"})
        assert r.status_code == 200, r.text
        sig = r.json()["lines"][0]["signatures"]["escrow_institution"]
        assert sig["email"] == ESC_EMAIL and sig["via"] == "magic_link" and sig["comment"] == "TEST magic"
        assert r.json()["lines"][0]["status"] == "awaiting_signatures"
        assert pmc.post(_u(tid, 0, "sign"), json={}).json()["lines"][0]["status"] == "approved"
        assert requests.post(f"{API}/escrow/magic/{TOK}/consortium-split/{tid}/0/sign", json={}).status_code == 409
        # tx on another account
        r = requests.post(f"{API}/escrow/magic/{TOK}/consortium-split/{other_tid}/0/sign", json={})
        assert r.status_code == 403, r.text
        assert not _lines(other_tid)[0]["signatures"]

    def test_bad_tokens(self, pmc):
        tid = _released(pmc, "BT")
        assert requests.get(f"{API}/escrow/magic/TEST_nope/consortium-splits").status_code == 404
        assert requests.get(f"{API}/escrow/magic/{TOK_REVOKED}/consortium-splits").status_code == 404
        assert requests.post(f"{API}/escrow/magic/TEST_nope/consortium-split/{tid}/0/sign", json={}).status_code == 404
        assert requests.post(f"{API}/escrow/magic/{TOK_REVOKED}/consortium-split/{tid}/0/sign", json={}).status_code == 404
        assert requests.post(f"{API}/escrow/magic/{TOK}/consortium-split/{tid}/9/sign", json={}).status_code == 404
        assert requests.post(f"{API}/escrow/magic/{TOK}/consortium-split/badid/0/sign", json={}).status_code == 404
