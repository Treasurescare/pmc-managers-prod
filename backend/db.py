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
    await db.vendors.create_index("email", unique=True, name="email_unique")
    await db.audit_events.create_index("seq", unique=True)
    await db.audit_events.create_index([("target_type", 1), ("target_id", 1)])
    await db.counters.create_index("name", unique=True)
    # Wave 1 additions
    await db.bids.create_index("bid_ref", unique=True)
    await db.bids.create_index([("notice_ref", 1), ("status", 1)])
    await db.bids.create_index([("vendor_id", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.payment_transactions.create_index("bid_id")
    await db.committees.create_index([("notice_ref", 1), ("status", 1)])
    await db.tasks.create_index([("assignee_id", 1), ("status", 1)])
    await db.tasks.create_index([("related_type", 1), ("related_id", 1)])
    await db.chat_messages.create_index([("context_type", 1), ("context_id", 1), ("created_at", 1)])
    await db.inspections.create_index([("certifier_id", 1), ("scheduled_at", -1)])
    await db.inspections.create_index("notice_ref")
    await db.companies.create_index("code", unique=True)
    await db.role_master.create_index("code", unique=True)
    await db.approval_matrices.create_index("name", unique=True)


async def next_sequence(name: str) -> int:
    """Atomic monotonic counter (used for vendor_ref, notice_ref, audit seq)."""
    doc = await db.counters.find_one_and_update(
        {"name": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True,
    )
    return int(doc["value"])
