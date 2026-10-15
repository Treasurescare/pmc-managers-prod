import asyncio
import hashlib
import json
from typing import Optional
from db import db, next_sequence
from models.base import now_iso

# v52m — seq allocation + last-hash read + insert MUST be atomic per process,
# otherwise two concurrent writes read the same parent hash and the chain
# breaks (seen in prod at seq 2037 / preview at 1504: two vendor.login rows
# sharing previous_hash, 0.6 ms apart). Single-instance deployment, so a
# process-level lock is sufficient.
_AUDIT_LOCK = asyncio.Lock()


def _hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def audit_log(event_type: str, actor: Optional[dict], target_type: str,
                    target_id: str, payload: Optional[dict] = None) -> None:
    """Append-only SHA-256 hash-chained ledger. Same design as v1."""
    async with _AUDIT_LOCK:
        seq = await next_sequence("audit_seq")
        last = await db.audit_events.find_one(sort=[("seq", -1)])
        previous_hash = (last or {}).get("current_hash", "GENESIS")

        body = {
            "seq": seq,
            "event_type": event_type,
            "actor_user_id": (actor or {}).get("id"),
            "actor_email": (actor or {}).get("email"),
            "target_type": target_type,
            "target_id": target_id,
            "payload": payload or {},
            "at": now_iso(),
            "previous_hash": previous_hash,
        }
        current_hash = _hash(body)
        body["current_hash"] = current_hash
        await db.audit_events.insert_one(body)


async def verify_chain() -> dict:
    """Walk the chain and detect any tampering."""
    cursor = db.audit_events.find().sort("seq", 1)
    prev = "GENESIS"
    checked = 0
    async for ev in cursor:
        checked += 1
        stored_current = ev.pop("current_hash", None)
        stored_id = ev.pop("_id", None)
        if ev.get("previous_hash") != prev:
            return {"ok": False, "reason": "chain broken", "at_seq": ev["seq"]}
        recomputed = _hash(ev)
        if recomputed != stored_current:
            return {"ok": False, "reason": "payload tampered", "at_seq": ev["seq"]}
        prev = stored_current
    return {"ok": True, "events_checked": checked}


async def rechain_audit() -> dict:
    """v52m — recompute hash LINKS for every event in seq order. Event
    payloads are never modified; only previous_hash / current_hash are
    rewritten. Heals chains broken by the pre-v52m write race (sibling rows
    pointing at the same parent). Appends an `audit.chain_repaired` marker
    event so the repair itself is on the ledger."""
    prev = "GENESIS"
    total = 0
    relinked = 0
    first_broken = None
    async with _AUDIT_LOCK:
        async for ev in db.audit_events.find().sort("seq", 1):
            total += 1
            if ev.get("previous_hash") != prev and first_broken is None:
                first_broken = ev.get("seq")
            body = {k: v for k, v in ev.items() if k not in ("_id", "current_hash")}
            body["previous_hash"] = prev
            new_hash = _hash(body)
            if ev.get("previous_hash") != prev or ev.get("current_hash") != new_hash:
                relinked += 1
            await db.audit_events.update_one(
                {"_id": ev["_id"]},
                {"$set": {"previous_hash": prev, "current_hash": new_hash}})
            prev = new_hash
    await audit_log("audit.chain_repaired", None, "audit_chain", "audit_events",
                    {"events_checked": total, "links_rewritten": relinked,
                     "first_broken_seq": first_broken,
                     "note": "v52m race repair — links recomputed, payloads untouched"})
    return {"ok": True, "events_checked": total, "links_rewritten": relinked,
            "first_broken_seq": first_broken}
