"""Extra demo data for the video retakes (run after demo_showcase.py seed). PREVIEW ONLY. Prints tokens as JSON."""
import asyncio
import json
import secrets
import sys

import requests
from bson import ObjectId

sys.path.insert(0, "/app/scripts")
sys.argv = [sys.argv[0], "noop"]
import demo_showcase as ds  # noqa: E402

D, API, TAG, PW, DOM, iso, hp = ds.D, ds.API, ds.TAG, ds.PW, ds.DOM, ds.iso, ds.hp


def staff_session(email):
    s = requests.Session()
    r = s.post(f"{API}/staff/auth/login", json={"email": email, "password": PW, "active_role": "committee_member"})
    assert r.status_code == 200, r.text
    s.headers["X-CSRF-Token"] = r.json().get("csrf_token", "")
    return s


def main():
    out = {}
    # partner sign-up demo: one invited (join page), one submitted (admin review with fee-waiver tick-box)
    out["partner_join_token"] = tok = secrets.token_urlsafe(32)
    D.agents.insert_one({**TAG, "email": f"newpartner@{DOM}", "name": "Grace Mensah (Demo)", "status": "invited", "invite_token": tok,
                         "invite_expires_at": iso(7), "token_generation": 0, "created_at": iso()})
    D.agents.insert_one({**TAG, "email": f"applicant@{DOM}", "name": "Anita Rao (Demo)", "legal_name": "Rao Tender Consulting (Demo)",
                         "status": "submitted", "country": "GB", "token_generation": 0, "password_hash": hp(PW), "phone": "+447700900789",
                         "entity_type": "company", "city": "Leeds", "bank": {"bank_name": "Demo Bank plc", "account_name": "Rao Tender Consulting",
                         "account_number": "DEMO1234", "sort_code": "00-00-00"}, "submitted_at": iso(0, -2), "created_at": iso(-1)})
    # partner filling a supplier form (consent given)
    out["partner_edit_token"] = pet = secrets.token_urlsafe(32)
    out["supplier_review_token"] = mt = secrets.token_urlsafe(24)
    pid = str(D.agents.find_one({"email": f"partner@{DOM}"})["_id"])
    D.registrations.insert_one({**TAG, "email": f"maple@{DOM}", "company_name": "Maple Foods Ltd (Demo)", "contact_email": f"maple@{DOM}",
        "contact_name": "Ruth Adams", "contact_mobile": "+447700900321", "country": "GB", "status": "draft", "trading_name": "Maple Foods",
        "registration_number": "DEMO-87654321", "partner_id": pid, "partner_code": "PT-DEMO", "partner_name": "Hart Procurement Advisory (Demo)",
        "invited_by_partner_id": pid, "partner_access": "granted", "partner_stage": "ready_for_review", "partner_edit_token": pet, "magic_token": mt,
        "partner_consent": {"version": "2026-11-v1", "signer_name": "Ruth Adams", "at": iso(-1)}, "partner_invited_at": iso(-2),
        "partner_claim_expires_at": iso(28), "data_processing_consent": True, "email_verified_at": iso(-1),
        "partner_fields": ["company_name", "trading_name", "registration_number", "contact_mobile", "document:certificate_of_incorporation"],
        "partner_edits": [{"at": iso(-1), "fields": ["trading_name", "registration_number"], "partner_code": "PT-DEMO"}], "created_at": iso(-2)})
    # tender taken all the way to award
    ref = out["award_tender"] = "DEMO-TND-AWD"
    title = "Road resurfacing — city council framework (Demo)"
    D.notices.insert_one({**TAG, "tenant_id": "PMC-KZ-01", "notice_ref": ref, "title": title, "description": f"{title}. Demonstration tender.",
        "category": "", "delivery_country": "GB", "is_published": True, "status": "published", "kyc_bypass": True, "budget_amount": 640000.0,
        "currency": "GBP", "emd_config": {"fixed_amount": 5000.0, "percentage": 0, "currency": "GBP"},
        "submission_deadline": iso(3), "bid_opening_date": iso(3), "created_at": iso(-12)})
    bids = [ds.bid(ds.vendor_session(f"northfield@{DOM}"), ref, 598000.0, "Full resurfacing of 14 km, 10-year guarantee", "Rate £42.70/m²"),
            ds.bid(ds.vendor_session(f"kestrel@{DOM}"), ref, 612500.0, "Resurfacing with recycled asphalt, 8-year guarantee", "Rate £43.75/m²")]
    D.bids.update_many({"notice_ref": ref}, {"$set": {**TAG, "status": "escrow_accepted", "emd_paid_amount": 5000.0, "emd_currency": "GBP",
                                                      "title": title, "notice_title": title}})
    mids = [str(D.admin_users.find_one({"email": f"committee{i}@{DOM}"})["_id"]) for i in (1, 2)]
    D.committees.insert_one({**TAG, "notice_ref": ref, "chairperson_id": mids[0], "member_ids": [mids[1]], "status": "open", "quorum": 2, "votes": [], "created_at": iso(-11)})
    D.notices.update_one({"notice_ref": ref}, {"$set": {"submission_deadline": iso(-4), "bid_opening_date": iso(-3)}})
    for stage in ("technical", "commercial"):
        if stage == "commercial":
            D.bids.update_many({"notice_ref": ref}, {"$set": {"technical_cleared_at": iso(-2), "technical_score": 86}})
        for i, nm in ((1, "Priya Shah"), (2, "Tom Ellis")):
            r = staff_session(f"committee{i}@{DOM}").post(f"{API}/bid-opening/{ref}/approve", json={"stage": stage, "signer_name": nm, "consent": True})
            assert r.status_code == 200, (stage, i, r.text)
    win, lose = bids
    D.bids.update_one({"_id": ObjectId(win)}, {"$set": {"status": "awarded", "awarded_at": iso(-1)}})
    D.bids.update_one({"_id": ObjectId(lose)}, {"$set": {"status": "rejected"}})
    D.notices.update_one({"notice_ref": ref}, {"$set": {"status": "awarded", "awarded_bid_id": win}})
    sys.path.insert(0, "/app/backend")
    import os
    os.chdir("/app/backend")
    from routers.awards import generate_award_documents
    asyncio.run(generate_award_documents(win, "committee1@" + DOM))
    D.awards.update_many({"bid_id": win}, {"$set": TAG})
    out["award_bid_id"] = win
    print(json.dumps(out))


main()
