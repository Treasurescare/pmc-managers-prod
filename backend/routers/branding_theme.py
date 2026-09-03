"""Portal Branding — theming + logo history (Bucket B follow-through).

Extends tenant branding with:
  * primary_color + accent_color + favicon_data_url  (theme)
  * logo_history[]  — every upload keeps a rolling history (max 10)
  * live preview payload the frontend picks up before saving
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from security import require_role
from models.base import now_iso
from audit import audit_log

router = APIRouter(prefix="/api/v1/branding", tags=["branding-theme"])


class ThemeIn(BaseModel):
    primary_color: Optional[str] = Field(None, pattern="^#[0-9a-fA-F]{6}$")
    accent_color: Optional[str] = Field(None, pattern="^#[0-9a-fA-F]{6}$")
    favicon_data_url: Optional[str] = None


@router.get("/{tenant_id}/theme")
async def get_theme(tenant_id: str, admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(tenant_id):
        raise HTTPException(400, "Invalid tenant_id")
    t = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if not t:
        raise HTTPException(404, "Tenant not found")
    return {
        "primary_color": t.get("primary_color") or "#0B1F3A",
        "accent_color": t.get("accent_color") or "#5B7BA1",
        "favicon_data_url": t.get("favicon_data_url") or None,
        "logo_data_url": t.get("logo_data_url") or None,
        "logo_history": t.get("logo_history") or [],
    }


@router.patch("/{tenant_id}/theme")
async def set_theme(tenant_id: str, payload: ThemeIn,
                     admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(tenant_id):
        raise HTTPException(400, "Invalid tenant_id")
    body = {k: v for k, v in payload.model_dump().items() if v is not None}
    body["theme_updated_at"] = now_iso()
    body["theme_updated_by"] = admin.get("email")
    r = await db.tenants.update_one({"_id": ObjectId(tenant_id)}, {"$set": body})
    if r.matched_count == 0:
        raise HTTPException(404, "Tenant not found")
    await audit_log("branding.theme_update", admin, "tenant", tenant_id, body)
    return {"ok": True, "updated": body}


@router.get("/{tenant_id}/logo-history")
async def logo_history(tenant_id: str, admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(tenant_id):
        raise HTTPException(400, "Invalid tenant_id")
    t = await db.tenants.find_one({"_id": ObjectId(tenant_id)}, {"logo_history": 1})
    return {"history": (t or {}).get("logo_history") or []}


@router.post("/{tenant_id}/logo-history/append")
async def push_history(tenant_id: str, payload: dict,
                        admin=Depends(require_role("admin"))):
    """Called by the existing logo-upload path after a save — cheap append."""
    if not ObjectId.is_valid(tenant_id):
        raise HTTPException(400, "Invalid tenant_id")
    entry = {
        "logo_data_url": (payload or {}).get("logo_data_url"),
        "at": now_iso(),
        "by": admin.get("email"),
    }
    if not entry["logo_data_url"]:
        raise HTTPException(400, "logo_data_url required")
    # cap at 10
    await db.tenants.update_one(
        {"_id": ObjectId(tenant_id)},
        {"$push": {"logo_history": {"$each": [entry], "$slice": -10}}},
    )
    return {"ok": True, "entry": entry}
