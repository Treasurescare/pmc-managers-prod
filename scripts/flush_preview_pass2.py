"""Second preview flush pass: clear operational collections that were kept too
conservatively in pass 1 (work packages, catalog products, escrow institutions
+ signatories) and reset the audit ledger. Backs up before deleting."""
import asyncio, os, datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

COLLS = ["packages", "products", "escrow_institutions", "escrow_signatories", "audit_events"]

async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = f"/app/backups/preview_flush2_{ts}"
    os.makedirs(bdir, exist_ok=True)
    print("BACKUP DIR:", bdir)
    total = 0
    for n in COLLS:
        docs = await db[n].find({}).to_list(length=None)
        with open(f"{bdir}/{n}.json", "w") as f:
            f.write(json_util.dumps(docs))
        res = await db[n].delete_many({})
        total += res.deleted_count
        print(f"  cleared {res.deleted_count:>6}  {n}  (backed up {len(docs)})")
    print(f"\nTOTAL DELETED: {total}\nBACKUP: {bdir}")

asyncio.run(main())
