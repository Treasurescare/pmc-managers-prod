"""Wave 7 — Tenant Master. Enables multi-tenant portals: each Corporate
Client / Government Department can hold its own notices, vendors, and
staff. Portal skinning + host-based resolution ship here so Managed can
migrate from `?tenant=CODE` query strings to real CNAME subdomains.
"""
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Depends, Query
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
    # Wave 17 — host/subdomain aliases for CNAME-based multi-tenant routing.
    # `subdomain`  → the leftmost label of the CNAME hostname the client will
    #                point at PMC, e.g. "acme" for acme.pmcmanagers.com.
    # `host_alias` → optional fully-qualified custom domain (e.g. "tenders.acme.com")
    #                so the client can plug in a top-level custom domain.
    subdomain: Optional[str] = None
    host_alias: Optional[str] = None
    is_active: bool = True


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


def _extract_subdomain(host: str) -> Optional[str]:
    """Return the leftmost label of a hostname if it looks like a subdomain of
    a PMC apex (e.g. `acme.pmcmanagers.com` → `acme`). Filters out common
    reserved/utility labels so preview envs and www don't accidentally match.
    """
    if not host:
        return None
    host = host.split(":", 1)[0].strip().lower()
    parts = host.split(".")
    if len(parts) < 3:
        return None
    head = parts[0]
    if head in {"www", "app", "api", "admin", "preview", "staging",
                "localhost", "tender-hub-57"}:
        return None
    return head


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
            "branding_color": t.get("branding_color"),
            "subdomain": t.get("subdomain"),
            "host_alias": t.get("host_alias")}


@router.get("/by-host")
async def tenant_by_host(host: str = Query(..., description="Full hostname including port, e.g. acme.pmcmanagers.com")):
    """CNAME-aware tenant resolution. Two-step lookup:
      1) exact match on `host_alias` (e.g. tenders.acme.com)
      2) subdomain match — leftmost label of the hostname vs. tenants.subdomain

    Returns 404 when no tenant is bound to that hostname so the caller can
    fall back to `?tenant=CODE` or the default PMC brand.
    """
    host_l = (host or "").split(":", 1)[0].strip().lower()
    if not host_l:
        raise HTTPException(status_code=400, detail="host param required")

    # 1) full host alias match
    t = await db.tenants.find_one({"host_alias": host_l, "is_active": True})
    if not t:
        sub = _extract_subdomain(host_l)
        if not sub:
            raise HTTPException(status_code=404, detail="No tenant bound to this hostname")
        # 2) subdomain match (case-insensitive)
        t = await db.tenants.find_one({"subdomain": sub, "is_active": True})
    if not t:
        raise HTTPException(status_code=404, detail="No tenant bound to this hostname")
    return {"code": t.get("code"), "name": t.get("name"),
            "kind": t.get("kind"), "country": t.get("country"),
            "branding_color": t.get("branding_color"),
            "subdomain": t.get("subdomain"),
            "host_alias": t.get("host_alias")}


@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: str, payload: TenantIn,
                        admin=Depends(require_role("admin"))):
    r = await db.tenants.update_one({"_id": ObjectId(tenant_id)},
                                     {"$set": payload.model_dump()})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(await db.tenants.find_one({"_id": ObjectId(tenant_id)}))
