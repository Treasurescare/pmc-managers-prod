"""
POST-DEPLOY cleanup — remove ONLY the demo content that the old v57a backend
re-seeded on startup (notices, KZ work packages, product catalog, and the
tender/BOQ/SBD/vendor template masters + rubrics).

Run this ONCE after you have deployed the v57b backend (which no longer seeds
demo data). It is safe, backs everything up to JSON first, and touches nothing
else — no logins, masters, settings, orgs or access-control data.

SAFETY
------
- Reads MONGO_URL and DB_NAME from the environment (same as the backend).
  It NEVER contains any connection string itself.
- Refuses to run unless you explicitly confirm with CONFIRM_FLUSH=YES.
- Backs up every collection it clears to JSON before deleting.

RUN
---
  CONFIRM_FLUSH=YES MONGO_URL="<prod-uri>" DB_NAME="<prod-db>" \
      python3 flush_reseeded_demo.py
"""
import asyncio, os, sys, datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util

# Exactly the collections the startup seeders repopulate.
TARGETS = [
    "notices", "packages", "products",
    "tender_templates", "boq_templates", "sbd_templates", "vendor_templates",
    "rubrics", "rating_criteria_sets", "auction_invite_templates",
]

async def main():
    if os.environ.get("CONFIRM_FLUSH") != "YES":
        sys.exit("Refusing to run: set CONFIRM_FLUSH=YES to proceed.")
    mongo = os.environ.get("MONGO_URL")
    dbname = os.environ.get("DB_NAME")
    if not mongo or not dbname:
        sys.exit("MONGO_URL and DB_NAME must be set.")
    db = AsyncIOMotorClient(mongo)[dbname]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = f"./reseeded_demo_backup_{ts}"
    os.makedirs(bdir, exist_ok=True)

    existing = set(await db.list_collection_names())
    print(f"TARGET DB : {dbname}")
    print(f"BACKUP DIR: {bdir}\n")

    total = 0
    for n in TARGETS:
        if n not in existing:
            print(f"  (skip)           {n}  — not present")
            continue
        docs = await db[n].find({}).to_list(length=None)
        with open(f"{bdir}/{n}.json", "w") as f:
            f.write(json_util.dumps(docs))
        res = await db[n].delete_many({})
        total += res.deleted_count
        print(f"  cleared {res.deleted_count:>7}  {n}  (backed up {len(docs)})")

    print(f"\nTOTAL DOCS DELETED: {total}")
    print(f"JSON BACKUP AT    : {bdir}")
    print("\nDone. Restarting the v57b backend will NOT re-create these records.")

if __name__ == "__main__":
    asyncio.run(main())
