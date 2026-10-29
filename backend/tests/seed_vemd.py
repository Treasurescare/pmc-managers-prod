# Seed/cleanup TEST_ bids for vendor EMD page testing. Usage: python seed_vemd.py seed|clean|show
import sys, asyncio, os, uuid
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient

db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


async def main(cmd):
    v = await db.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    if not v:
        v = await db.vendor_users.find_one({"email": "testvendor@pmcmanagers.com"})
    print("vendor:", v and {k: v.get(k) for k in ("_id", "id", "company_name", "vendor_ref", "status")})
    vid = str(v.get("id") or v["_id"])
    if cmd == "show":
        async for b in db.bids.find({"vendor_id": vid}):
            print({k: b.get(k) for k in ("bid_ref", "status", "emd_currency", "emd_due_amount", "emd_paid_amount", "emd_refund_state")})
        return
    if cmd == "clean":
        r = await db.bids.delete_many({"vendor_id": vid, "bid_ref": {"$regex": "^PMC-BID-2026-99"}})
        r2 = await db.notices.delete_many({"notice_ref": {"$regex": "^TEST_"}})
        print("deleted bids", r.deleted_count, "notices", r2.deleted_count)
        return
    await db.notices.insert_one({"id": str(uuid.uuid4()), "notice_ref": "TEST_NOTICE_EMD", "title": "TEST_ EMD Notice",
                                 "submission_deadline": "2026-03-01T00:00:00Z", "status": "published"})
    base = {"vendor_id": vid, "notice_ref": "TEST_NOTICE_EMD", "created_at": "2026-01-10T00:00:00Z"}
    rows = [
        dict(bid_ref="PMC-BID-2026-9901", status="emd_pending", emd_currency="USD", emd_due_amount=1000, emd_paid_amount=0),
        dict(bid_ref="PMC-BID-2026-9902", status="emd_pending", emd_currency="INR", emd_due_amount=50000, emd_paid_amount=0),
        dict(bid_ref="PMC-BID-2026-9903", status="escrow_accepted", emd_currency="USD", emd_due_amount=2000, emd_paid_amount=2000),
        dict(bid_ref="PMC-BID-2026-9904", status="not_awarded", emd_currency="USD", emd_due_amount=3000, emd_paid_amount=3000, emd_refund_state="initiated", emd_refund_due_at="2026-02-15T00:00:00Z"),
        dict(bid_ref="PMC-BID-2026-9905", status="not_awarded", emd_currency="INR", emd_due_amount=7000, emd_paid_amount=7000, emd_refund_state="released"),
    ]
    for r in rows:
        await db.bids.insert_one({**base, **r, "id": str(uuid.uuid4())})
    print("seeded", len(rows))

asyncio.run(main(sys.argv[1]))
