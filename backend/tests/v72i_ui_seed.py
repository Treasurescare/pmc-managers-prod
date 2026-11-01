# v72i UI fixture: escrow account + magic token + released consortium tx. Line0 PMC-signed, line1 paid (with slip). Usage: python v72i_ui_seed.py seed|clean
import sys
sys.path.insert(0, "/app/backend/tests")
from bson import ObjectId
from test_v72e_partner_consortium_notices import API, DB, _login_staff, _now

NREF = "TEST-V72I-UI"
TOK = "TEST_v72i_ui_token"
PROOF = "vendor-docs/TEST_v72i_ui_slip.pdf"
if sys.argv[1] == "clean":
    DB.bids.delete_many({"notice_ref": NREF}); DB.escrow_transactions.delete_many({"notice_ref": NREF})
    DB.vendors.delete_many({"email": "test_v72iui_lead@example.com"}); DB.registrations.delete_many({"email": {"$regex": "^test_v72iui_"}})
    DB.escrow_accounts.delete_many({"name": "TEST_ v72i UI account"}); DB.escrow_magic_tokens.delete_many({"token": TOK})
    DB.uploads.delete_many({"key": PROOF}); DB.notifications.delete_many({"related_notice_ref": NREF})
    sys.exit(0)
acc = DB.escrow_accounts.insert_one({"name": "TEST_ v72i UI account", "institution": "TEST Bank", "currency": "USD",
                                     "pmc_officer": {"email": "adminsupport@pmcmanagers.com"}, "escrow_officer": {"email": "escrow@pmcmanagers.com"}}).inserted_id
DB.escrow_magic_tokens.insert_one({"token": TOK, "account_id": str(acc), "officer_email": "escrow@pmcmanagers.com", "revoked": False, "created_at": _now()})
DB.uploads.insert_one({"key": PROOF, "content_type": "application/pdf", "size_bytes": 8, "data_b64": "JVBERi0xLjQ=", "created_at": _now()})
vid = DB.vendors.insert_one({"email": "test_v72iui_lead@example.com", "vendor_ref": "TEST-V72I-UI", "company_name": "TEST UI Lead", "bank_name": "TEST Lead Bank",
                             "bank_branch": "Main", "bank_account_number": "UI-LEAD-001", "bank_swift": "UILDSWFT"}).inserted_id
for e, a in (("test_v72iui_m0@example.com", "UI-M0-002"), ("test_v72iui_m1@example.com", "UI-M1-003")):
    DB.registrations.insert_one({"email": e, "created_at": _now(), "bank_name": "TEST Bank", "bank_branch": "B", "bank_account_number": a, "bank_swift": "SW"})
cons = {"id": "cUI", "name": "TEST UI Team", "lead_share_pct": 50.0, "escrow_mode": "shared", "deposit_mode": "lead_pays",
        "members": [{"vendor_id": "m0UI", "company_name": "TEST UI Member", "email": "test_v72iui_m0@example.com", "share_pct": 30.0},
                    {"vendor_id": "m1UI", "company_name": "TEST UI Member2", "email": "test_v72iui_m1@example.com", "share_pct": 20.0}]}
DB.bids.insert_one({"bid_ref": "TEST-BID-V72I-UI", "notice_ref": NREF, "vendor_id": str(vid), "vendor_email": "test_v72iui_lead@example.com",
                    "company_name": "TEST UI Lead", "status": "awarded", "consortium": cons, "submitted_at": _now()})
sig = {"action": "release_to_contractor", "signed_at": _now()}
tid = str(DB.escrow_transactions.insert_one({
    "bid_ref": "TEST-BID-V72I-UI", "notice_ref": NREF, "amount": 1000.0, "currency": "USD", "status": "awaiting_signatures", "escrow_account_id": str(acc),
    "signatures": {"pmc": sig, "escrow_institution": sig}, "audit_trail": [], "created_at": _now(), "created_by": "TEST",
    "escrow_account_snapshot": {"name": "TEST acc", "pmc_officer": {"name": "P", "email": "adminsupport@pmcmanagers.com"},
                                "escrow_officer": {"name": "E", "email": "escrow@pmcmanagers.com"}}}).inserted_id)
a = _login_staff("adminsupport@pmcmanagers.com", "Admin@12345", "admin")
u = lambda i, w: f"{API}/escrow/transactions/{tid}/consortium-split/{i}/{w}"
print(a.post(f"{API}/escrow/transactions/{tid}/release", json={"action": "release_to_contractor", "memo": "TEST"}).status_code)
print(a.post(u(0, "sign"), json={}).status_code, a.post(u(1, "sign"), json={}).status_code)
e = _login_staff("escrow@pmcmanagers.com", "Escrow@123", "escrow_agent")
print(e.post(u(1, "sign"), json={}).status_code)
print(a.post(u(1, "paid"), json={"reference": "WIRE-UI-1", "proof_key": PROOF}).status_code)
print("TID", tid)
