from typing import Optional, Dict, Any, List
import re

from fastapi import APIRouter, Depends
from db import db
from security import require_role, require_csrf
from audit import verify_chain, rechain_audit

router = APIRouter(prefix="/api/v1/audit-events", tags=["audit"])


@router.get("")
async def list_events(
    limit: int = 100,
    target_type: Optional[str] = None,
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_role("admin")),
) -> List[Dict[str, Any]]:
    """v52m — real server-side filters. The UI used to fetch the last 100
    events and filter client-side, so anything older than the window was
    invisible to the filter ('event type does not filter properly')."""
    q: Dict[str, Any] = {}
    if target_type:
        q["target_type"] = target_type
    if event_type:
        q["event_type"] = {"$regex": re.escape(event_type), "$options": "i"}
    if actor:
        q["actor_email"] = {"$regex": re.escape(actor), "$options": "i"}
    if from_date:
        q.setdefault("at", {})["$gte"] = from_date
    if to_date:
        q.setdefault("at", {})["$lte"] = to_date + "T23:59:59.999999+00:00"
    limit = max(1, min(int(limit), 500))
    out: List[Dict[str, Any]] = []
    async for e in db.audit_events.find(q).sort("seq", -1).limit(limit):
        e["id"] = str(e.pop("_id"))
        out.append(e)
    return out


@router.get("/verify")
async def verify(admin: Dict[str, Any] = Depends(require_role("admin"))) -> Dict[str, Any]:
    return await verify_chain()


@router.post("/rechain", dependencies=[Depends(require_csrf)])
async def rechain(admin: Dict[str, Any] = Depends(require_role("admin"))) -> Dict[str, Any]:
    """Admin-only repair: recomputes hash links for the whole ledger after a
    chain break. Payloads are never modified. Logged on the ledger itself."""
    return await rechain_audit()
