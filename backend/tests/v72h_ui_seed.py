# v72h UI fixture: seed + release a consortium tx; escrow officer pre-signs line 0. Usage: python v72h_ui_seed.py seed|clean
import sys
sys.path.insert(0, "/app/backend/tests")
from bson import ObjectId
from test_v72e_partner_consortium_notices import API, DB, _login_staff, _now

NREF = "TEST-V72H-UI"
if sys.argv[1] == "clean":
    DB.bids.delete_many({"notice_ref": NREF}); DB.escrow_transactions.delete_many({"notice_ref": NREF})
    DB.vendors.delete_many({"email": "test_v72hui_lead@example.com"}); DB.registrations.delete_many({"email": "test_v72hui_m0@example.com"})
    sys.exit(0)
vid = DB.vendors.insert_one({"email": "test_v72hui_lead@example.com", "company_name": "TEST UI Lead", "bank_name": "TEST Lead Bank",
                             "bank_branch": "Main", "bank_account_number": "UI-LEAD-001", "bank_swift": "UILDSWFT"}).inserted_id
DB.registrations.insert_one({"email": "test_v72hui_m0@example.com", "created_at": _now(), "bank_name": "TEST M0 Bank",
                             "bank_branch": "Ring", "bank_account_number": "UI-M0-002", "bank_swift": "UIM0SWFT"})
cons = {"id": "cUI", "name": "TEST UI Team", "lead_share_pct": 50.0, "escrow_mode": "shared", "deposit_mode": "lead_pays",
        "members": [{"vendor_id": "m0UI", "company_name": "TEST UI Member", "email": "test_v72hui_m0@example.com", "share_pct": 30.0},
                    {"vendor_id": "m1UI", "company_name": "TEST UI NoBank", "email": "test_v72hui_m1@example.com", "share_pct": 20.0}]}
DB.bids.insert_one({"bid_ref": "TEST-BID-V72H-UI", "notice_ref": NREF, "vendor_id": str(vid), "vendor_email": "test_v72hui_lead@example.com",
                    "company_name": "TEST UI Lead", "status": "awarded", "consortium": cons, "submitted_at": _now()})
sig = {"action": "release_to_contractor", "signed_at": _now()}
tid = str(DB.escrow_transactions.insert_one({
    "bid_ref": "TEST-BID-V72H-UI", "notice_ref": NREF, "amount": 1000.0, "currency": "USD", "status": "awaiting_signatures",
    "signatures": {"pmc": sig, "escrow_institution": sig}, "audit_trail": [], "created_at": _now(), "created_by": "TEST",
    "escrow_account_snapshot": {"name": "TEST acc", "pmc_officer": {"name": "P", "email": "adminsupport@pmcmanagers.com"},
                                "escrow_officer": {"name": "E", "email": "escrow@pmcmanagers.com"}}}).inserted_id)
a = _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")
print(a.post(f"{API}/escrow/transactions/{tid}/release", json={"action": "release_to_contractor", "memo": "TEST"}).status_code)
e = _login_staff("escrow@pmcmanagers.com", "Escrow@123", "escrow_agent")
print(e.post(f"{API}/escrow/transactions/{tid}/consortium-split/0/sign", json={}).status_code)
print("TID", tid)
