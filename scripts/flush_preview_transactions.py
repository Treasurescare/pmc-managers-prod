"""Preview DB flush: back up then clear transactional + vendor collections.
Keeps: logins (admin_users, users), all master/reference data, reusable
templates/config, and escrow partner institutions + signatory logins."""
import asyncio, os, datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

KEEP = {
    # logins / accounts
    "admin_users", "users",
    # escrow partner registry + their signatory logins
    "escrow_institutions", "escrow_signatories",
    # settings / access control
    "app_settings", "approval_matrices", "permission_matrix", "role_master",
    # master / reference data
    "categories", "contract_types", "currencies", "sectors", "departments",
    "orgs", "tenants", "companies", "legal_entity_types", "emd_masters",
    "packages", "products", "taxonomy_nodes",
    "masters_banks", "masters_banks_merge_log", "masters_cities",
    "masters_countries", "masters_country_formats", "masters_country_licenses",
    "masters_states", "masters_unspsc",
    # reusable templates / scoring config
    "auction_invite_templates", "boq_templates", "tender_templates",
    "sbd_templates", "vendor_templates", "rubrics", "rating_criteria_sets",
}

async def main():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = f"/app/backups/preview_flush_{ts}"
    os.makedirs(bdir, exist_ok=True)
    names = sorted(await db.list_collection_names())
    to_delete = [n for n in names if n not in KEEP]
    print("BACKUP DIR:", bdir)
    print("KEEPING:", len([n for n in names if n in KEEP]), "collections")
    print("DELETING:", len(to_delete), "collections\n")
    total_deleted = 0
    for n in to_delete:
        docs = await db[n].find({}).to_list(length=None)
        with open(f"{bdir}/{n}.json", "w") as f:
            f.write(json_util.dumps(docs))
        res = await db[n].delete_many({})
        total_deleted += res.deleted_count
        print(f"  cleared {res.deleted_count:>6}  {n}  (backed up {len(docs)})")
    print(f"\nTOTAL DOCS DELETED: {total_deleted}")
    print("BACKUP WRITTEN TO:", bdir)

asyncio.run(main())
