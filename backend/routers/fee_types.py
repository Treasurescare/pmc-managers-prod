"""Fee Type master — defines each kind of fee (subscription, registration, EMD …):
when it is collected, fixed vs percentage, single amount vs tender-value ranges,
all vs selected categories, and whether the vendor Tender Builder charges it."""
import re
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/fee-types", tags=["fee-types"])


class FeeTypeIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    code: Optional[str] = Field(default=None, max_length=40)
    timing: Literal["upfront", "on_completion"] = "upfront"
    calc: Literal["fixed", "percentage", "either"] = "fixed"
    amount_mode: Literal["single", "range"] = "single"
    category_scope: Literal["all", "selected"] = "all"
    billing: Literal["one_time", "yearly"] = "one_time"
    used_in_tender_builder: bool = False
    country_scope: Literal["all", "selected"] = "all"
    countries: list[str] = Field(default_factory=list)
    is_active: bool = True
    description: Optional[str] = Field(default=None, max_length=400)


def _out(d):
    return BaseDocument.out(d)


@router.get("")
async def list_fee_types(admin=Depends(require_role("admin", "reviewer"))):
    return [_out(d) async for d in db.fee_types.find({}).sort("name", 1)]


@router.post("")
async def create_fee_type(payload: FeeTypeIn, admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    body["code"] = re.sub(r"[^a-z0-9]+", "_", (body.get("code") or body["name"]).lower()).strip("_")
    if await db.fee_types.find_one({"code": body["code"]}):
        raise HTTPException(status_code=409, detail=f"A fee type with code '{body['code']}' already exists")
    body["is_system"] = False
    r = await db.fee_types.insert_one(body)
    await audit_log("fee_type.create", admin, "fee_type", str(r.inserted_id), {"code": body["code"]})
    return _out(await db.fee_types.find_one({"_id": r.inserted_id}))


@router.patch("/{fid}")
async def update_fee_type(fid: str, payload: FeeTypeIn, admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    body.pop("code", None)
    r = await db.fee_types.update_one({"_id": ObjectId(fid)}, {"$set": body})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Fee type not found")
    await audit_log("fee_type.update", admin, "fee_type", fid, body)
    return _out(await db.fee_types.find_one({"_id": ObjectId(fid)}))


@router.delete("/{fid}")
async def delete_fee_type(fid: str, admin=Depends(require_role("admin"))):
    ft = await db.fee_types.find_one({"_id": ObjectId(fid)})
    if not ft:
        raise HTTPException(status_code=404, detail="Fee type not found")
    n = await db.emd_masters.count_documents({"kind": ft["code"]})
    if n:
        raise HTTPException(status_code=409, detail=f"{n} fee rule(s) use this type — delete or move them first, or mark the type inactive.")
    await db.fee_types.delete_one({"_id": ft["_id"]})
    await audit_log("fee_type.delete", admin, "fee_type", fid, {"code": ft["code"]})
    return {"ok": True}
