import asyncio, sys, json
sys.path.insert(0, "/app/backend")
from db import db


async def main():
    n = await db.notices.find_one({"notice_ref": "DEMO-TND-AWD"}, {"standstill_days": 1, "award_suspended": 1, "re_evaluation_required": 1, "is_published": 1, "created_by": 1, "created_by_email": 1})
    print("notice", n)
    async for b in db.bids.find({"notice_ref": "DEMO-TND-AWD"}, {"status": 1, "awarded_at": 1, "vendor_email": 1, "vendor_id": 1}):
        print("bid", b)
    c = await db.committees.find_one({"notice_ref": "DEMO-TND-AWD", "status": "open"})
    print("committee", c and {k: c.get(k) for k in ("chairperson_id", "member_ids", "status")})
    if c:
        from bson import ObjectId
        ids = [c.get("chairperson_id"), *(c.get("member_ids") or [])]
        async for u in db.admin_users.find({"_id": {"$in": [ObjectId(i) for i in ids if i]}}, {"email": 1, "role": 1, "roles": 1}):
            print("member", u)
    print("challenges", await db.bid_challenges.count_documents({}))
    print("corrigenda", await db.corrigenda.count_documents({"notice_ref": "DEMO-TND-AWD"}))
    async for ft in db.fee_types.find({}, {"code": 1, "is_active": 1, "show_on_pricing": 1}):
        cnt = await db.emd_masters.count_documents({"kind": ft["code"]})
        act = await db.emd_masters.count_documents({"kind": ft["code"], "is_active": True})
        print("ft", ft, cnt, act)
    a = await db.admin_users.find_one({"email": "adminsupport@pmcmanagers.com"}, {"_id": 1, "role": 1})
    print("admin", a)

asyncio.run(main())
