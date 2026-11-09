# Seed/cleanup TEST_ actors for the Supplier Marketplace tests (iteration 180)
# create: TEST_ verified vendor #2, TEST_ buyer_application tenant + TEST_ buyer admin user
# clean: delete only those docs + mkt_* docs created by TEST_ actors; reset mkt_settings default
import asyncio, json, sys, uuid
sys.path.insert(0, "/app/backend")
from bson import ObjectId
from db import db
from security import hash_password
from models.base import now_iso

OUT = "/tmp/mkt_t180_seed.json"
V2 = "test_mkt_v2_t180@example.com"
BUYER = "test_mkt_buyer_t180@example.com"


async def create():
    src = await db.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    doc = dict(src); doc.pop("_id", None)
    if "id" in doc: doc["id"] = str(uuid.uuid4())
    doc.update({"email": V2, "vendor_ref": "VEN-TMKT180", "company_name": "TEST_MKT Supplier Two",
                "password_hash": hash_password("Vendor@12345"), "kyc_status": "verified", "status": "active",
                "country": "XQ", "token_generation": 0, "bank_name": "TEST_Bank", "bank_account_number": "TEST-123", "bank_swift": "TESTSWFT"})
    for k in ("failed_login_attempts", "locked_until", "mfa_enabled", "mfa_secret", "fee_plan"):
        doc.pop(k, None)
    await db.vendors.delete_many({"email": V2})
    v2 = await db.vendors.insert_one(doc)
    await db.tenants.delete_many({"code": "TESTMKT180"})
    t = await db.tenants.insert_one({"code": "TESTMKT180", "name": "TEST_MKT Buyer Org", "kind": "corporate", "is_active": True,
                                     "source": "buyer_application", "created_at": now_iso()})
    await db.admin_users.delete_many({"email": BUYER})
    a = await db.admin_users.insert_one({"email": BUYER, "name": "TEST_MKT Buyer", "role": "admin", "roles": ["admin"],
                                         "password_hash": hash_password("Buyer@12345"), "tenant_id": "TESTMKT180",
                                         "is_active": True, "created_at": now_iso()})
    rule = await db.emd_masters.insert_one({"name": "TEST_MKT listing fee", "kind": "mkt_listing_fee", "country": "XQ", "countries": ["XQ"],
                                            "currency": "USD", "slabs": [{"tender_value_min": 0, "tender_value_max": None, "fee_type": "fixed", "fixed_amount": 7}],
                                            "is_active": True, "categories": [], "category": None, "created_at": now_iso()})
    ids = {"v2": str(v2.inserted_id), "tenant": str(t.inserted_id), "buyer": str(a.inserted_id), "rule": str(rule.inserted_id)}
    json.dump(ids, open(OUT, "w"))
    print(ids)


async def clean():
    ids = json.load(open(OUT))
    tv = await db.vendors.find_one({"email": "testvendor@pmcmanagers.com"})
    lids = [d["_id"] async for d in db.mkt_listings.find({"title": {"$regex": "^TEST_"}, "seller_id": {"$in": [str(tv["_id"]), ids["v2"]]}})]
    print("bids", (await db.mkt_bids.delete_many({"listing_id": {"$in": lids}})).deleted_count)
    print("orders", (await db.mkt_orders.delete_many({"listing_id": {"$in": lids}})).deleted_count)
    print("listings", (await db.mkt_listings.delete_many({"_id": {"$in": lids}})).deleted_count)
    await db.paid_uses.delete_many({"vendor_id": ids["v2"]})
    await db.vendors.delete_one({"_id": ObjectId(ids["v2"])})
    await db.tenants.delete_one({"_id": ObjectId(ids["tenant"])})
    await db.admin_users.delete_one({"_id": ObjectId(ids["buyer"])})
    await db.emd_masters.delete_one({"_id": ObjectId(ids["rule"])})
    await db.mkt_settings.update_one({"_id": "default"}, {"$set": {"fee_type": "percent", "fee_value": 0, "charge": True}}, upsert=True)
    print("cleaned")

asyncio.run(create() if sys.argv[1] == "create" else clean())
