"""Seed test data for Master Manual v4 capture."""
import asyncio, sys, secrets
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '/app/backend')
from db import db


async def seed_registration_draft():
    """Registration wizard section B/C/D/E — a partially-filled draft."""
    email = f"manual-reg-{secrets.token_hex(3)}@example.com"
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "primary_email": email,
        "primary_contact_name": "Manual Preview Vendor",
        "phone": "+91-9876543210",
        "country": "IN",
        "resume_token": token,
        "status": "draft",
        "created_at": now, "updated_at": now,
        # Section A already saved
        "section_a": {"company_name": "Manual Preview Vendor Pvt Ltd", "contact_person": "Alice"},
        # B — structure
        "section_b": {"business_type": "Private Ltd", "year_established": 2015, "employees": 42},
        # C — financials
        "section_c": {"annual_turnover_usd": 2500000, "years_profitable": 5},
        # D — documents (references only, no real uploads)
        "section_d": {"pan_uploaded": True, "gst_uploaded": True},
        # E — references
        "section_e": {"reference_1": "Acme Corp — David @ david@acme.com"},
    }
    r = await db.registrations.insert_one(doc)
    print("seeded registration token:", token, "id:", r.inserted_id)
    return token


async def seed_bid():
    """One vendor bid so /vendor/bid/new/:ref has data."""
    # Find a published notice
    n = await db.notices.find_one({"is_published": True})
    if not n:
        print("no published notice — skip bid seed")
        return None
    v = await db.vendors.find_one({"email": "manualvendor@pmcmanagers.com"})
    if not v:
        print("no manual vendor — skip bid seed")
        return None
    bid = {
        "notice_ref": n["notice_ref"],
        "vendor_id": str(v["_id"]),
        "vendor_email": v["email"],
        "bid_ref": f"PMC-BID-MANUAL-{secrets.token_hex(2).upper()}",
        "price": 850000,
        "currency": "USD",
        "status": "submitted",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r = await db.bids.insert_one(bid)
    print("seeded bid:", bid["bid_ref"], "for notice:", n["notice_ref"])
    return n["notice_ref"]


async def seed_reverse_auction():
    """A CLOSED reverse auction so the summary panel shows real data."""
    n = await db.notices.find_one({"is_published": True})
    aid = f"RA-MANUAL-{secrets.token_hex(2).upper()}"
    doc = {
        "aid": aid,
        "notice_ref": n["notice_ref"] if n else "PMC-NOT-MANUAL-01",
        "title": "Manual Preview · Reverse Auction (closed)",
        "currency": "USD",
        "starting_price": 1000000,
        "floor_price": 800000,
        "min_decrement": 5000,
        "duration_minutes": 30,
        "anti_snipe_seconds": 120,
        "status": "closed",
        "winner": {"alias": "Bidder-42", "winning_price": 872500},
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "closed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.reverse_auctions.insert_one(doc)
    print("seeded closed auction:", aid)
    return aid


async def seed_meeting():
    """Meeting with a join token."""
    token = secrets.token_urlsafe(24)
    doc = {
        "title": "Manual Preview · Bid Opening Meeting",
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "duration_minutes": 60,
        "join_token": token,
        "invitees": [
            {"email": "adminsupport@pmcmanagers.com", "name": "Master Admin", "accepted": None},
            {"email": "committee@pmcmanagers.com", "name": "Committee Chair", "accepted": True},
        ],
        "zoom_url": "https://zoom.us/j/manual-preview-test",
        "internal_only": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.meetings.insert_one(doc)
    print("seeded meeting token:", token)
    return token


async def seed_escrow_officer_token():
    """Escrow officer magic-link token."""
    token = secrets.token_urlsafe(24)
    doc = {
        "token": token,
        "email": "escrow@pmcmanagers.com",
        "purpose": "sign_release",
        "notice_ref": "PMC-NOT-MANUAL-01",
        "amount": 100000,
        "currency": "USD",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "used": False,
    }
    await db.escrow_magic_tokens.insert_one(doc)
    print("seeded escrow officer token:", token)
    return token


async def main():
    reg_token = await seed_registration_draft()
    notice_ref = await seed_bid()
    aid = await seed_reverse_auction()
    meet_token = await seed_meeting()
    escrow_token = await seed_escrow_officer_token()
    print("\n=== SEEDED ===")
    print(f"reg_token={reg_token}")
    print(f"notice_ref={notice_ref}")
    print(f"auction_aid={aid}")
    print(f"meet_token={meet_token}")
    print(f"escrow_token={escrow_token}")

if __name__ == "__main__":
    asyncio.run(main())
