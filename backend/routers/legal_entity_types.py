"""Legal Entity Types master (v50y).

Admin-managed list that populates the "Legal entity type" dropdown in
vendor registration Section A. Pre-seeded with sensible defaults
(LLC / JSC / Sole Proprietorship / Partnership / Branch / Other) so the
registration form keeps working even before any admin edits.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId
from pymongo import ReturnDocument

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/masters/legal-entity-types",
                   tags=["masters-legal-entity-types"])


class LegalEntityTypeIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=120)
    name_ru: Optional[str] = None
    name_kz: Optional[str] = None
    country_scope: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: bool = True


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


DEFAULT_SEED = [
    {"code": "llc", "name": "LLC (Limited Liability Company)"},
    {"code": "jsc", "name": "JSC (Joint Stock Company)"},
    {"code": "sole_proprietorship", "name": "Sole Proprietorship"},
    {"code": "partnership", "name": "Partnership"},
    {"code": "branch", "name": "Branch"},
    {"code": "other", "name": "Other"},
]


async def seed_defaults() -> None:
    """Idempotent — only inserts missing rows."""
    existing = {d["code"] async for d in db.legal_entity_types.find({}, {"code": 1})}
    now = now_iso()
    to_insert = [{**row, "is_active": True, "country_scope": None,
                  "created_at": now, "updated_at": now,
                  "source": "seed"}
                 for row in DEFAULT_SEED if row["code"] not in existing]
    if to_insert:
        await db.legal_entity_types.insert_many(to_insert)


@router.get("")
async def list_types(
    include_inactive: bool = False,
    country: Optional[str] = None,
    admin=Depends(require_role("admin", "reviewer", "support", "committee_member")),
) -> List[dict]:
    q: dict = {}
    if not include_inactive:
        q["is_active"] = True
    if country:
        cu = country.upper()
        q["$or"] = [
            {"country_scope": {"$in": [cu]}},
            {"country_scope": {"$exists": False}},
            {"country_scope": None},
            {"country_scope": []},
        ]
    rows = [_out(r) async for r in db.legal_entity_types.find(q).sort("name", 1)]
    return rows


@router.get("/public")
async def list_types_public(country: Optional[str] = None) -> List[dict]:
    """PUBLIC — used by the vendor registration Section A dropdown."""
    q: dict = {"is_active": True}
    if country:
        cu = country.upper()
        q["$or"] = [
            {"country_scope": {"$in": [cu]}},
            {"country_scope": {"$exists": False}},
            {"country_scope": None},
            {"country_scope": []},
        ]
    rows = [_out(r) async for r in db.legal_entity_types.find(q).sort("name", 1)]
    return rows


@router.post("")
async def create_type(payload: LegalEntityTypeIn,
                      admin=Depends(require_role("admin"))) -> dict:
    existing = await db.legal_entity_types.find_one({"code": payload.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Code '{payload.code}' already exists")
    now = now_iso()
    doc = payload.model_dump()
    doc.update({"created_at": now, "updated_at": now, "source": "manual"})
    r = await db.legal_entity_types.insert_one(doc)
    await audit_log("masters.legal_entity_type.create", admin,
                    "legal_entity_type", str(r.inserted_id), {"code": payload.code})
    return _out({**doc, "_id": r.inserted_id})


@router.patch("/{type_id}")
async def update_type(type_id: str, payload: LegalEntityTypeIn,
                      admin=Depends(require_role("admin"))) -> dict:
    try:
        _oid = ObjectId(type_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad id")
    patch = payload.model_dump()
    patch["updated_at"] = now_iso()
    r = await db.legal_entity_types.find_one_and_update(
        {"_id": _oid}, {"$set": patch},
        return_document=ReturnDocument.AFTER,
    )
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("masters.legal_entity_type.update", admin,
                    "legal_entity_type", type_id, {"code": payload.code})
    return _out(r)


@router.delete("/{type_id}")
async def deactivate_type(type_id: str,
                          admin=Depends(require_role("admin"))) -> dict:
    try:
        _oid = ObjectId(type_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Bad id")
    r = await db.legal_entity_types.update_one(
        {"_id": _oid}, {"$set": {"is_active": False, "updated_at": now_iso()}},
    )
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("masters.legal_entity_type.deactivate", admin,
                    "legal_entity_type", type_id, {})
    return {"ok": True}
