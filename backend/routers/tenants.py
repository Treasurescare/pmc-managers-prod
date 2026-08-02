"""Wave 7 — Tenant Master. Enables multi-tenant portals: each Corporate
Client / Government Department can hold its own notices, vendors, and
staff. Full portal isolation UI ships in a follow-up; this router provides
the master record + assignment endpoints."""
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


TenantKind = Literal["pmc", "corporate", "government"]


class TenantIn(BaseModel):
    code: str = Field(min_length=3, max_length=32)
    name: str
    kind: TenantKind = "corporate"
    country: str = "KZ"
    primary_contact_email: Optional[str] = None
    primary_contact_name: Optional[str] = None
    branding_color: Optional[str] = None  # hex e.g. "#0b1e3f"
    is_active: bool = True


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.post("")
async def create_tenant(payload: TenantIn, admin=Depends(require_role("admin"))):
    if await db.tenants.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail="Tenant code already exists")
    doc = payload.model_dump()
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await db.tenants.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("tenant.create", admin, "tenant", payload.code, {"name": payload.name})
    return _out(doc)


@router.get("")
async def list_tenants(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    return [_out(t) async for t in db.tenants.find({}).sort("name", 1)]


@router.get("/public/{code}")
async def public_tenant(code: str):
    """Public tenant lookup used to skin the vendor portal via ?tenant=CODE.
    Returns only the safe, non-sensitive fields."""
    t = await db.tenants.find_one({"code": code, "is_active": True})
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"code": t.get("code"), "name": t.get("name"),
            "kind": t.get("kind"), "country": t.get("country"),
            "branding_color": t.get("branding_color")}


@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: str, payload: TenantIn,
                        admin=Depends(require_role("admin"))):
    r = await db.tenants.update_one({"_id": ObjectId(tenant_id)},
                                     {"$set": payload.model_dump()})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(await db.tenants.find_one({"_id": ObjectId(tenant_id)}))
