# v61b seed/cleanup: TEST_ second vendor for foreign-ownership tests + cleanup of TEST_ listings/media/imports created by tests
import asyncio, json, sys, uuid
sys.path.insert(0, "/app/backend")
from bson import ObjectId
from db import db
from security import hash_password

OUT = "/tmp/mkt_v61b_seed.json"
V2 = "test_mkt_v2_v61b@example.com"


async def create():
    src = await db.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    doc = dict(src); doc.pop("_id", None)
    if "id" in doc: doc["id"] = str(uuid.uuid4())
    doc.update({"email": V2, "vendor_ref": "VEN-TMKT61B", "company_name": "TEST_MKT61B Supplier Two",
                "password_hash": hash_password("Vendor@12345"), "kyc_status": "verified", "status": "active", "token_generation": 0})
    for k in ("failed_login_attempts", "locked_until", "mfa_enabled", "mfa_secret", "fee_plan"):
        doc.pop(k, None)
    await db.vendors.delete_many({"email": V2})
    v2 = await db.vendors.insert_one(doc)
    json.dump({"v2": str(v2.inserted_id), "tv": str(src["_id"])}, open(OUT, "w"))
    print("seeded", v2.inserted_id)


async def clean():
    ids = json.load(open(OUT))
    sellers = [ids["v2"], ids["tv"]]
    tracked = json.load(open("/tmp/mkt_v61b_created.json")) if __import__("os").path.exists("/tmp/mkt_v61b_created.json") else {}
    lids = [ObjectId(x) for x in tracked.get("listings", []) if ObjectId.is_valid(x)]
    lids += [d["_id"] async for d in db.mkt_listings.find({"title": {"$regex": "^TEST_"}, "seller_id": {"$in": sellers}})]
    print("listings", (await db.mkt_listings.delete_many({"_id": {"$in": lids}, "seller_id": {"$in": sellers}})).deleted_count)
    imps = tracked.get("imports", [])
    print("imports-media", (await db.mkt_media.delete_many({"import_id": {"$in": imps}})).deleted_count)
    print("media", (await db.mkt_media.delete_many({"_id": {"$in": tracked.get("media", [])}})).deleted_count)
    print("imports", (await db.mkt_imports.delete_many({"_id": {"$in": imps}})).deleted_count)
    print("v2 media", (await db.mkt_media.delete_many({"owner": ids["v2"]})).deleted_count)
    await db.vendors.delete_one({"_id": ObjectId(ids["v2"])})
    print("cleaned")

asyncio.run(create() if sys.argv[1] == "create" else clean())
