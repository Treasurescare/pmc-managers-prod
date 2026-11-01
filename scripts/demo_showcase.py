"""Demo showcase data for recording promo videos (PREVIEW ONLY). Usage: python demo_showcase.py seed|clean
Every record is tagged demo_showcase=True and uses @demo.pmcmanagers.com emails, so `clean` removes exactly this data."""
import json
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import requests
from pymongo import MongoClient

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
API = f"{BASE}/api/v1"
E = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l and not l.startswith("#"))
D = MongoClient(E["MONGO_URL"].strip('"'))[E["DB_NAME"].strip('"')]
TAG = {"demo_showcase": True}
PW = "Demo@Pmc2026"
DOM = "demo.pmcmanagers.com"
NOW = datetime.now(timezone.utc)
iso = lambda d=0, h=0: (NOW + timedelta(days=d, hours=h)).isoformat()  # noqa: E731
hp = lambda p: bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()  # noqa: E731
COLS = ["agents", "vendors", "registrations", "notices", "bids", "committees", "admin_users", "escrow_institutions",
        "escrow_accounts", "escrow_transactions", "partner_commissions", "uploads", "payment_transactions", "awards"]


def clean():
    for c in COLS:
        n = D[c].delete_many(TAG).deleted_count
        if n:
            print(f"removed {n} from {c}")
    D.uploads.delete_many({"key": {"$regex": "^bid-docs/DEMO"}})
    D.bids.delete_many({"notice_ref": {"$regex": "^DEMO-"}})


def vendor_session(email):
    s = requests.Session()
    r = s.post(f"{API}/vendor/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def bid(s, ref, price, tech, comm):
    keys = []
    for k in ("technical", "commercial"):
        key = f"bid-docs/DEMO{uuid.uuid4().hex[:8]}_{k}.pdf"
        r = s.post(f"{API}/uploads/direct", data={"key": key}, files={"file": (f"{k}-proposal.pdf", b"%PDF-1.4 demo proposal", "application/pdf")})
        assert r.status_code == 200, r.text
        keys.append(key)
    r = s.post(f"{API}/bids", json={"notice_ref": ref, "price_amount": price, "price_currency": "GBP", "technical_notes": tech, "commercial_notes": comm,
        "documents": [{"kind": "technical", "key": keys[0], "filename": "technical-proposal.pdf", "size_bytes": 22, "uploaded_at": iso()},
                      {"kind": "commercial", "key": keys[1], "filename": "commercial-offer.pdf", "size_bytes": 22, "uploaded_at": iso()}]})
    assert r.status_code == 200, r.text
    D.uploads.update_many({"key": {"$in": keys}}, {"$set": TAG})
    return r.json()["id"]


def seed():
    clean()
    # partner
    pid = D.agents.insert_one({**TAG, "email": f"partner@{DOM}", "name": "Daniel Hart", "legal_name": "Hart Procurement Advisory (Demo)",
        "status": "approved", "partner_code": "PT-DEMO", "password_hash": hp(PW), "token_generation": 0, "country": "GB",
        "fee_waived": True, "created_at": iso(-20), "approved_at": iso(-18),
        "commission": {"currency": "GBP", "onboarding_amount": 150.0, "deal_type": "percent", "deal_value": 2.0},
        "public_profile": {"show": True, "bio": "Demo partner — helps UK engineering suppliers win public tenders."}}).inserted_id
    pid = str(pid)
    # suppliers (vendors with login)
    sups = [("Northfield Engineering Ltd (Demo)", "northfield", "VEN-DEMO1", True), ("Brightwater Medical Supplies (Demo)", "brightwater", "VEN-DEMO2", True),
            ("Kestrel Facilities Services (Demo)", "kestrel", "VEN-DEMO3", False)]
    for name, slug, ref, via_partner in sups:
        pf = {"partner_id": pid, "partner_code": "PT-DEMO", "partner_name": "Hart Procurement Advisory (Demo)"} if via_partner else {}
        D.vendors.insert_one({**TAG, **pf, "tenant_id": "PMC-KZ-01", "email": f"{slug}@{DOM}", "company_name": name, "status": "active", "is_active": True,
                              "kyc_status": "verified", "vendor_ref": ref, "country": "GB", "password_hash": hp(PW), "created_at": iso(-10)})
        if via_partner:
            D.registrations.insert_one({**TAG, **pf, "email": f"{slug}@{DOM}", "company_name": name, "status": "approved", "vendor_ref": ref,
                "partner_access": "granted", "partner_stage": "submitted", "approved_partner_id": pid, "invited_by_partner_id": pid,
                "partner_invited_at": iso(-9), "reviewed_at": iso(-2), "magic_token": secrets.token_urlsafe(24), "created_at": iso(-9)})
    # supplier invite in progress (consent pending) + one being filled
    consent_tok = secrets.token_urlsafe(32)
    D.registrations.insert_one({**TAG, "email": f"oakline@{DOM}", "company_name": "Oakline Construction (Demo)", "contact_mobile": "+447700900123",
        "status": "draft", "partner_id": pid, "partner_code": "PT-DEMO", "partner_name": "Hart Procurement Advisory (Demo)", "invited_by_partner_id": pid,
        "partner_access": "awaiting_consent", "partner_stage": "invited", "partner_invited_at": iso(), "partner_consent_token": consent_tok,
        "partner_consent_expires_at": iso(7), "partner_claim_expires_at": iso(30), "magic_token": secrets.token_urlsafe(24),
        "partner_edits": [], "partner_fields": [], "created_at": iso()})
    D.partner_commissions.insert_many([
        {**TAG, "partner_id": pid, "partner_code": "PT-DEMO", "kind": "onboarding", "company_name": sups[0][0], "vendor_ref": "VEN-DEMO1",
         "amount": 150.0, "currency": "GBP", "basis": "Supplier approved", "status": "paid", "reference": "BACS DEMO-001", "paid_on": iso(-1)[:10],
         "settled_at": iso(-1), "created_at": iso(-2)},
        {**TAG, "partner_id": pid, "partner_code": "PT-DEMO", "kind": "onboarding", "company_name": sups[1][0], "vendor_ref": "VEN-DEMO2",
         "amount": 150.0, "currency": "GBP", "basis": "Supplier approved", "status": "due", "created_at": iso(-2)}])
    # committee members (staff)
    mids = []
    for i, nm in enumerate(["Priya Shah (Demo)", "Tom Ellis (Demo)"], 1):
        mids.append(str(D.admin_users.insert_one({**TAG, "email": f"committee{i}@{DOM}", "name": nm, "role": "committee_member",
            "roles": ["committee_member"], "is_escrow_signatory": i == 1, "password_hash": hp(PW), "is_active": True, "tenant_id": "PMC-KZ-01",
            "hierarchy_level": 5, "created_at": iso(-30)}).inserted_id))
    # tenders
    tenders = [("DEMO-TND-001", "Supply of hospital beds — NHS trust (Demo)", "Medical Equipment", 250000, 20),
               ("DEMO-TND-002", "Bridge maintenance works — county council (Demo)", "Civil Works", 1200000, 35),
               ("DEMO-TND-003", "Facilities management for council offices (Demo)", "Facilities Management", 480000, 15)]
    for ref, title, cat, budget, days in tenders:
        D.notices.insert_one({**TAG, "tenant_id": "PMC-KZ-01", "notice_ref": ref, "title": title, "description": f"{title}. Demonstration tender for PMC Managers videos.",
            "category": cat, "delivery_country": "GB", "is_published": True, "status": "published", "kyc_bypass": True, "budget_amount": float(budget),
            "currency": "GBP", "emd_config": {"fixed_amount": 2500.0, "percentage": 0, "currency": "GBP"},
            "submission_deadline": iso(days), "bid_opening_date": iso(days, 2), "created_at": iso(-3)})
    # sealed bids on the opening-demo tender
    ref = "DEMO-TND-OPEN"
    D.notices.insert_one({**TAG, "tenant_id": "PMC-KZ-01", "notice_ref": ref, "title": "Supply of school laptops — academy trust (Demo, ready to open)", "category": "",
        "delivery_country": "GB", "is_published": True, "status": "published", "kyc_bypass": True, "budget_amount": 90000.0, "currency": "GBP",
        "emd_config": {"fixed_amount": 1000.0, "percentage": 0, "currency": "GBP"}, "submission_deadline": iso(2), "bid_opening_date": iso(2), "created_at": iso(-7)})
    bids = [bid(vendor_session(f"northfield@{DOM}"), ref, 84500.0, "300 laptops, 3-year warranty, delivery in 4 weeks", "Unit price £281.67 incl. delivery"),
            bid(vendor_session(f"brightwater@{DOM}"), ref, 79900.0, "300 laptops, on-site setup, 5-year warranty", "Unit price £266.33; 2% early-payment discount")]
    D.bids.update_many({"notice_ref": ref}, {"$set": {**TAG, "status": "escrow_accepted", "emd_paid_amount": 1000.0, "emd_currency": "GBP",
                                                  "title": "Supply of school laptops — academy trust (Demo)", "notice_title": "Supply of school laptops — academy trust (Demo)"}})
    D.committees.insert_one({**TAG, "notice_ref": ref, "chairperson_id": mids[0], "member_ids": [mids[1]], "status": "open", "quorum": 2,
                             "votes": [], "created_at": iso(-6)})
    D.notices.update_one({"notice_ref": ref}, {"$set": {"submission_deadline": iso(0, -3), "bid_opening_date": iso(0, -1)}})
    # escrow
    inst = str(D.escrow_institutions.insert_one({**TAG, "legal_name": "Thames Trust Bank plc (Demo)", "status": "approved", "country": "GB",
        "primary_contact_email": f"escrow@{DOM}", "primary_contact_name": "James Okafor (Demo)",
        "signatories": [{"name": "James Okafor (Demo)", "email": f"escrow@{DOM}", "designation": "Escrow officer"}], "bank_accounts": [], "created_at": iso(-40)}).inserted_id)
    pmc_off = {"name": "Priya Shah (Demo)", "email": f"committee1@{DOM}", "designation": "Tender officer", "role": "pmc"}
    esc_off = {"name": "James Okafor (Demo)", "email": f"escrow@{DOM}", "designation": "Escrow officer", "role": "escrow_institution"}
    acc = D.escrow_accounts.insert_one({**TAG, "name": "PMC Tender EMD Escrow #1 (Demo)", "institution": "Thames Trust Bank plc (Demo)", "institution_id": inst,
        "account_no": "DEMO-00001234", "currency": "GBP", "pmc_officer": pmc_off, "escrow_officer": esc_off, "active": True, "created_at": iso(-40)}).inserted_id
    for b_id in bids:
        b = D.bids.find_one({"_id": __import__("bson").ObjectId(b_id)})
        D.escrow_transactions.insert_one({**TAG, "bid_ref": b.get("bid_ref"), "notice_ref": ref, "vendor_ref": b.get("vendor_ref"), "escrow_account_id": str(acc),
            "escrow_account_snapshot": {"name": "PMC Tender EMD Escrow #1 (Demo)", "institution": "Thames Trust Bank plc (Demo)", "account_no": "DEMO-00001234",
                                        "pmc_officer": pmc_off, "escrow_officer": esc_off},
            "amount": 1000.0, "currency": "GBP", "reference": f"DEMO-EMD-{b.get('bid_ref')}", "received_at": iso(-5), "status": "received",
            "notes": "Demo EMD deposit", "signatures": {}, "audit_trail": [{"at": iso(-5), "by": "system.demo", "event": "received", "amount": 1000.0, "currency": "GBP"}],
            "released_to": None, "released_at": None, "created_at": iso(-5), "created_by": "system.demo"})
    print(json.dumps({"password_for_all_demo_accounts": PW, "partner": f"partner@{DOM}",
                      "suppliers": [f"{s[1]}@{DOM}" for s in sups], "committee": [f"committee1@{DOM}", f"committee2@{DOM}"],
                      "supplier_consent_page": f"/supplier-invite/{consent_tok}", "sealed_tender": ref}, indent=1))


if __name__ == "__main__" and sys.argv[1] in ("seed", "clean"):
    {"seed": seed, "clean": clean}[sys.argv[1]]()
