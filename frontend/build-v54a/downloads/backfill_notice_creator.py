"""One-off backfill: populate created_by_email on existing notices.

Matches notices.created_by (admin user id) against admin_users._id and
stamps created_by_email. Idempotent — safe to run again after deploys.
Run: python3 /app/scripts/backfill_notice_creator.py
"""
import asyncio, os, sys
sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    # Self-load backend/.env (shell extraction mangles URIs with special chars)
    env = {}
    for line in open("/app/backend/.env"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    client = AsyncIOMotorClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    users = {}
    async for u in db.admin_users.find({}, {"email": 1}):
        users[str(u["_id"])] = u.get("email")
    fixed = skipped = 0
    async for n in db.notices.find({"created_by_email": {"$exists": False}}, {"created_by": 1}):
        email = users.get(str(n.get("created_by") or ""))
        if email:
            await db.notices.update_one({"_id": n["_id"]},
                                        {"$set": {"created_by_email": email}})
            fixed += 1
        else:
            skipped += 1
    print(f"backfilled={fixed} skipped={skipped} (unknown creator id)")

if __name__ == "__main__":
    asyncio.run(main())
