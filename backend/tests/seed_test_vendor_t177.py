# Creates / cleans a TEST_ vendor for the native Face ID deletion test (iteration 177)
import asyncio, sys, uuid
sys.path.insert(0, "/app/backend")
from db import db
from security import hash_password

EMAIL = "test_gdpr_t177@example.com"

async def create():
    src = await db.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    doc = dict(src); doc.pop("_id", None)
    if "id" in doc: doc["id"] = str(uuid.uuid4())
    doc["email"] = EMAIL
    doc["vendor_ref"] = "VEN-TGDPR177"
    doc["company_name"] = "TEST_GDPR177 Co"
    doc["password_hash"] = hash_password("Vendor@12345")
    for k in ("failed_login_attempts", "locked_until", "mfa_enabled", "mfa_secret"):
        doc.pop(k, None)
    r = await db.vendors.insert_one(doc)
    print("created", r.inserted_id)

async def clean(oid):
    from bson import ObjectId
    r = await db.vendors.delete_one({"_id": ObjectId(oid)})
    print("deleted", r.deleted_count)

if sys.argv[1] == "create": asyncio.run(create())
else: asyncio.run(clean(sys.argv[2]))
