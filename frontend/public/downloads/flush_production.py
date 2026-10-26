"""
PRODUCTION fresh-start flush — mirrors the final PREVIEW state.

Deletes all transactional + vendor/registration/KYC + escrow-operational data
(including work packages, catalog products, escrow institutions & signatories,
and the audit ledger) while KEEPING: admin & user logins, all master/reference
data, access-control settings, and reusable templates — so the app still boots.

SAFETY
------
- Reads MONGO_URL and DB_NAME from the environment (same as the backend).
  It NEVER contains any connection string itself.
- Refuses to run unless you explicitly confirm by setting CONFIRM_FLUSH=YES.
- Backs up every collection it deletes to JSON before deleting.
- ALSO take a full `mongodump` first (see RUNBOOK) — this per-collection JSON
  is a convenience net, not a substitute for a real backup.

RUN
---
  CONFIRM_FLUSH=YES MONGO_URL="<prod-uri>" DB_NAME="<prod-db>" \
      python3 flush_production.py
"""
import asyncio, os, sys, datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util

# Collections to PRESERVE (everything else is deleted).
KEEP = {
    # logins / accounts
    "admin_users", "users",
    # access control / settings
    "app_settings", "approval_matrices", "permission_matrix", "role_master",
    # master / reference data
    "categories", "contract_types", "currencies", "sectors", "departments",
    "orgs", "tenants", "companies", "legal_entity_types", "emd_masters",
    "taxonomy_nodes",
    "masters_banks", "masters_banks_merge_log", "masters_cities",
    "masters_countries", "masters_country_formats", "masters_country_licenses",
    "masters_states", "masters_unspsc",
}

async def main():
    if os.environ.get("CONFIRM_FLUSH") != "YES":
        sys.exit("Refusing to run: set CONFIRM_FLUSH=YES to proceed.")
    mongo = os.environ.get("MONGO_URL")
    dbname = os.environ.get("DB_NAME")
    if not mongo or not dbname:
        sys.exit("MONGO_URL and DB_NAME must be set.")
    db = AsyncIOMotorClient(mongo)[dbname]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = f"./prod_flush_backup_{ts}"
    os.makedirs(bdir, exist_ok=True)

    names = sorted(await db.list_collection_names())
    to_delete = [n for n in names if n not in KEEP]
    kept = [n for n in names if n in KEEP]
    print(f"TARGET DB : {dbname}")
    print(f"KEEPING   : {len(kept)} collections")
    print(f"DELETING  : {len(to_delete)} collections")
    print(f"BACKUP DIR: {bdir}\n")

    total = 0
    for n in to_delete:
        docs = await db[n].find({}).to_list(length=None)
        with open(f"{bdir}/{n}.json", "w") as f:
            f.write(json_util.dumps(docs))
        res = await db[n].delete_many({})
        total += res.deleted_count
        print(f"  cleared {res.deleted_count:>7}  {n}  (backed up {len(docs)})")

    # Purge EXTERNAL logins (vendors + buyers) from `users`; keep internal PMC
    # admin/staff. admin_users (the PMC team) is never touched.
    ext = await db.users.find({"role": {"$in": ["vendor", "buyer"]}}).to_list(length=None)
    with open(f"{bdir}/users_external.json", "w") as f:
        f.write(json_util.dumps(ext))
    ures = await db.users.delete_many({"role": {"$in": ["vendor", "buyer"]}})
    total += ures.deleted_count
    kept_users = await db.users.estimated_document_count()
    print(f"  purged {ures.deleted_count:>7}  users (vendor/buyer)  -> kept {kept_users} internal login(s)")

    print(f"\nTOTAL DOCS DELETED: {total}")
    print(f"JSON BACKUP AT    : {bdir}")

if __name__ == "__main__":
    asyncio.run(main())
