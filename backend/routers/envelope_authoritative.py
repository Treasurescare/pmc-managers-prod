"""DocuSign envelope authoritativeness (Bucket B follow-through).

Bidders and admins want to know which envelope for a given `(bid_id, sub_kind)`
tuple is the *authoritative* one (most recent + status=completed). This
endpoint returns exactly that flag alongside the envelope log.
"""
from typing import Optional
from fastapi import APIRouter, Depends

from db import db
from security import current_admin

router = APIRouter(prefix="/api/v1/envelope-log", tags=["envelope-log"])


def _rank(status: str) -> int:
    """Higher = more authoritative."""
    return {"completed": 4, "delivered": 3, "sent": 2, "declined": 1, "voided": 0}.get(
        status or "", 0,
    )


@router.get("")
async def envelope_log(
    bid_id: Optional[str] = None,
    kind: Optional[str] = None,   # award | bid_ack
    sub_kind: Optional[str] = None,  # po | sla | contract
    admin=Depends(current_admin),
):
    """Return envelopes filtered by bid + kind and flag the authoritative one.
    Authoritative = highest-ranked status; break ties by most recent created_at.
    """
    q: dict = {}
    if bid_id:
        q["bid_id"] = bid_id
    if kind:
        q["kind"] = kind
    if sub_kind:
        q["sub_kind"] = sub_kind
    cursor = db.docusign_envelopes.find(q).sort("created_at", -1).limit(200)
    items: list[dict] = []
    async for row in cursor:
        row.pop("_id", None)
        items.append(row)
    # group by (bid_id, sub_kind or kind) and mark authoritative
    groups: dict[tuple, list] = {}
    for r in items:
        key = (r.get("bid_id"), r.get("sub_kind") or r.get("kind"))
        groups.setdefault(key, []).append(r)
    for key, group in groups.items():
        best = max(
            group,
            key=lambda x: (_rank(x.get("status")), x.get("created_at") or ""),
        )
        for r in group:
            r["is_authoritative"] = (r is best)
    return {"count": len(items), "items": items}
