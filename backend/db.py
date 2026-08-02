"""MongoDB connection + index bootstrap.

All UNIQUE indexes are declared `sparse=True` so documents missing the key
(or with the key set to null) are excluded from the index — this prevents a
prod-time DuplicateKeyError when partial documents linger from earlier writes
or migrations. Index creation is best-effort: an individual failure is logged
and does NOT abort application startup (a stray orphan won't kill the pod).
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import config

log = logging.getLogger("db")

client = AsyncIOMotorClient(config.MONGO_URL)
db = client[config.DB_NAME]


# Every entry: (collection, keys, kwargs). kwargs may include unique / sparse / name.
_INDEX_SPECS = [
    ("admin_users", "email", {"unique": True, "sparse": True, "name": "email_unique"}),
    ("notices", "notice_ref", {"unique": True, "sparse": True, "name": "notice_ref_unique"}),
    ("notices", [("is_published", 1), ("published_at", -1)], {}),
    ("registrations", "email", {}),
    ("registrations", "magic_token", {"sparse": True, "name": "magic_token_sparse"}),
    ("registrations", [("status", 1), ("submitted_at", -1)], {}),
    ("packages", "package_ref", {"unique": True, "sparse": True, "name": "package_ref_unique"}),
    ("packages", [("status", 1), ("float_target_date", 1)], {}),
    ("vendors", "vendor_ref", {"unique": True, "sparse": True, "name": "vendor_ref_unique"}),
    ("vendors", "email", {"unique": True, "sparse": True, "name": "vendor_email_unique"}),
    ("audit_events", "seq", {"unique": True, "sparse": True, "name": "audit_seq_unique"}),
    ("audit_events", [("target_type", 1), ("target_id", 1)], {}),
    ("counters", "name", {"unique": True, "sparse": True, "name": "counter_name_unique"}),
    # Wave 1+
    ("bids", "bid_ref", {"unique": True, "sparse": True, "name": "bid_ref_unique"}),
    ("bids", [("notice_ref", 1), ("status", 1)], {}),
    ("bids", [("vendor_id", 1), ("created_at", -1)], {}),
    ("payment_transactions", "session_id", {"unique": True, "sparse": True, "name": "session_id_unique"}),
    ("payment_transactions", "bid_id", {}),
    ("committees", [("notice_ref", 1), ("status", 1)], {}),
    ("tasks", [("assignee_id", 1), ("status", 1)], {}),
    ("tasks", [("related_type", 1), ("related_id", 1)], {}),
    ("chat_messages", [("context_type", 1), ("context_id", 1), ("created_at", 1)], {}),
    ("inspections", [("certifier_id", 1), ("scheduled_at", -1)], {}),
    ("inspections", "notice_ref", {}),
    ("companies", "code", {"unique": True, "sparse": True, "name": "company_code_unique"}),
    ("role_master", "code", {"unique": True, "sparse": True, "name": "role_code_unique"}),
    ("approval_matrices", "name", {"unique": True, "sparse": True, "name": "matrix_name_unique"}),
]


async def _cleanup_null_keys() -> None:
    """Remove orphan documents where a unique key is null — these are almost
    always leftovers from crashed/partial writes and would block sparse-index
    creation only in the rare case an old NON-sparse index still exists."""
    targets = [
        ("admin_users", "email"),
        ("notices", "notice_ref"),
        ("vendors", "vendor_ref"),
        ("vendors", "email"),
        ("packages", "package_ref"),
        ("bids", "bid_ref"),
        ("payment_transactions", "session_id"),
        ("companies", "code"),
        ("role_master", "code"),
        ("approval_matrices", "name"),
        ("counters", "name"),
    ]
    for col, key in targets:
        try:
            res = await db[col].delete_many({key: None})
            if res.deleted_count:
                log.warning(f"Purged {res.deleted_count} orphan {col} docs with {key}=null")
        except Exception as e:
            log.warning(f"Cleanup of {col}.{key}=null skipped: {e}")


async def create_indexes() -> None:
    """Best-effort index bootstrap. Never aborts startup on a single failure."""
    await _cleanup_null_keys()
    for col, keys, kwargs in _INDEX_SPECS:
        try:
            await db[col].create_index(keys, **kwargs)
        except Exception as e:
            # Fallback for pre-existing NON-sparse unique index colliding with our new one
            log.warning(f"Index create failed on {col}({keys}) kwargs={kwargs}: {e}")
            if kwargs.get("unique"):
                name = kwargs.get("name")
                try:
                    if name:
                        await db[col].drop_index(name)
                    await db[col].create_index(keys, **kwargs)
                    log.info(f"Recovered index {col}({keys}) after drop")
                except Exception as e2:
                    log.error(f"Recovery failed on {col}({keys}): {e2} — continuing")


async def next_sequence(name: str) -> int:
    """Atomic monotonic counter (used for vendor_ref, notice_ref, audit seq)."""
    doc = await db.counters.find_one_and_update(
        {"name": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True,
    )
    return int(doc["value"])
