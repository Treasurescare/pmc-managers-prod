"""v51ad — Filter presets per admin user, per scope.

A preset is a saved MoneyFilterBar state so operators don't retype the same
filter every day. Scopes map 1:1 to the panel they belong to (notices,
auctions, awards, billing, escrow, evaluation, l1, docusign, bidding_ops,
corrigenda).
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/filter-presets", tags=["filter-presets"])

VALID_SCOPES = {
    "notices", "auctions", "awards", "billing", "escrow", "evaluation",
    "l1", "docusign", "bidding_ops", "corrigenda", "vendors", "registrations",
}


class PresetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=80)
    criteria: dict = Field(default_factory=dict)


def _out(d: dict) -> dict:
    o = BaseDocument.out(d)
    return o


@router.get("")
async def list_presets(scope: Optional[str] = None,
                        admin=Depends(require_role("admin", "reviewer", "auditor"))):
    q = {"owner_id": admin["id"]}
    if scope: q["scope"] = scope
    rows = []
    async for d in db.filter_presets.find(q).sort("name", 1):
        rows.append(_out(d))
    return {"items": rows, "total": len(rows)}


@router.post("")
async def create_preset(payload: PresetIn, admin=Depends(require_role("admin", "reviewer"))):
    if payload.scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown scope '{payload.scope}'")
    doc = {
        "owner_id": admin["id"], "owner_email": admin.get("email"),
        "tenant_id": admin.get("tenant_id"),
        "scope": payload.scope, "name": payload.name.strip(),
        "criteria": payload.criteria, "created_at": now_iso(),
    }
    # Replace same-name preset for this user+scope (idempotent save).
    await db.filter_presets.update_one(
        {"owner_id": admin["id"], "scope": payload.scope, "name": doc["name"]},
        {"$set": doc}, upsert=True)
    fresh = await db.filter_presets.find_one(
        {"owner_id": admin["id"], "scope": payload.scope, "name": doc["name"]})
    return _out(fresh)


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str, admin=Depends(require_role("admin", "reviewer"))):
    try: oid = ObjectId(preset_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed preset id")
    r = await db.filter_presets.delete_one({"_id": oid, "owner_id": admin["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"ok": True}
