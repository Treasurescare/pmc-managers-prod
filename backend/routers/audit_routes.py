from typing import Optional
from fastapi import APIRouter, Depends
from db import db
from security import require_role
from audit import verify_chain

router = APIRouter(prefix="/api/v1/audit-events", tags=["audit"])


@router.get("")
async def list_events(limit: int = 100, target_type: Optional[str] = None,
                      admin=Depends(require_role("admin"))):
    q = {}
    if target_type:
        q["target_type"] = target_type
    limit = max(1, min(int(limit), 500))
    out = []
    async for e in db.audit_events.find(q).sort("seq", -1).limit(limit):
        e["id"] = str(e.pop("_id"))
        out.append(e)
    return out


@router.get("/verify")
async def verify(admin=Depends(require_role("admin"))):
    return await verify_chain()
