from motor.motor_asyncio import AsyncIOMotorClient
import config

client = AsyncIOMotorClient(config.MONGO_URL)
db = client[config.DB_NAME]


async def create_indexes() -> None:
    """Create indexes on startup. Idempotent."""
    await db.admin_users.create_index("email", unique=True)
    await db.notices.create_index("notice_ref", unique=True)
    await db.notices.create_index([("is_published", 1), ("published_at", -1)])
    await db.registrations.create_index("email")
    await db.registrations.create_index("magic_token")
    await db.registrations.create_index([("status", 1), ("submitted_at", -1)])
    await db.packages.create_index("package_ref", unique=True)
    await db.packages.create_index([("status", 1), ("float_target_date", 1)])
    await db.vendors.create_index("vendor_ref", unique=True)
    await db.vendors.create_index("email")
    await db.audit_events.create_index("seq", unique=True)
    await db.audit_events.create_index([("target_type", 1), ("target_id", 1)])
    await db.counters.create_index("name", unique=True)


async def next_sequence(name: str) -> int:
    """Atomic monotonic counter (used for vendor_ref, notice_ref, audit seq)."""
    doc = await db.counters.find_one_and_update(
        {"name": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True,
    )
    return int(doc["value"])
