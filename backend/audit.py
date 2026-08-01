import hashlib
import json
from typing import Optional
from db import db, next_sequence
from models.base import now_iso


def _hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def audit_log(event_type: str, actor: Optional[dict], target_type: str,
                    target_id: str, payload: Optional[dict] = None) -> None:
    """Append-only SHA-256 hash-chained ledger. Same design as v1."""
    seq = await next_sequence("audit_seq")
    last = await db.audit_events.find_one(sort=[("seq", -1)])
    previous_hash = last["current_hash"] if last else "GENESIS"

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
