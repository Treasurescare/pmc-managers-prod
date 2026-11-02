import asyncio, sys
sys.path.insert(0, "/app/backend")
from bson import ObjectId
from db import db


async def main():
    r = await db.bids.update_one({"_id": ObjectId("6ae6a21737fa842ad33531c5")},
                                 {"$set": {"status": "awarded", "awarded_at": "2026-11-01T02:21:14.711079+00:00"},
                                  "$unset": {"award_withdrawn_at": "", "award_withdrawn_reason": ""}})
    print("bid restored", r.modified_count)
    await db.notices.update_one({"notice_ref": "DEMO-TND-AWD"}, {"$unset": {"standstill_days": "", "award_suspended": "", "award_suspended_at": "", "re_evaluation_required": ""}})
    print("challenges deleted", (await db.bid_challenges.delete_many({"notice_ref": "DEMO-TND-AWD"})).deleted_count)
    print("corrigenda deleted", (await db.corrigenda.delete_many({"notice_ref": "DEMO-TND-AWD", "field_amendments.field_key": "standstill_days"})).deleted_count)
    await db.fee_types.update_one({"code": "registration"}, {"$set": {"show_on_pricing": False}})

asyncio.run(main())
