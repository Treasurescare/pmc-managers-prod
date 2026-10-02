"""Vendor Licenses & Company-KYC (v50n).

Gives the supplier portal a real, editable Licence & certificate book per
vendor. Drives the Company & KYC page's `Licences & certificates` tab and
its "1 expiring + 1 missing" callout with actual DB state instead of the
static mockup.

Collection: `vendor_licenses` — one doc per licence:
    vendor_ref, vendor_id, licence_type, country, number, issued_at,
    expires_at (ISO date), file_key (optional uploaded proof), status
    (auto-computed on read), created_at, updated_at.

Endpoints:
    GET  /api/v1/vendor/licenses            — list + computed status
    POST /api/v1/vendor/licenses            — add new licence
    PUT  /api/v1/vendor/licenses/{id}       — renew / update
    DELETE /api/v1/vendor/licenses/{id}     — remove (admin-review path
                                              will replace hard delete later)
"""
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

import config
from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(tags=["vendor-licenses"])

EXPIRING_DAYS = 45  # "Expires soon" threshold


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


def _status(expires_iso: Optional[str]) -> str:
    """Compute live status: valid / expiring / expired / missing."""
    if not expires_iso:
        return "valid"  # open-ended
    try:
        d = datetime.fromisoformat(expires_iso.replace("Z", "+00:00")).date()
    except Exception:
        return "valid"
    today = date.today()
    if d < today:
        return "expired"
    if (d - today).days <= EXPIRING_DAYS:
        return "expiring"
    return "valid"


class LicenseIn(BaseModel):
    licence_type: str = Field(..., min_length=2, max_length=120)
    country: str = Field(..., min_length=2, max_length=3)
    number: str = Field(..., min_length=2, max_length=60)
    issued_at: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    expires_at: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    file_key: Optional[str] = Field(default=None, max_length=200)

    @field_validator("country")
    @classmethod
    def _country_upper(cls, v):
        return v.upper()

    @field_validator("issued_at", "expires_at")
    @classmethod
    def _iso_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except Exception:
            raise ValueError("date must be YYYY-MM-DD")
        return v


# ───────────────────────── Vendor side ─────────────────────────

@router.get("/api/v1/vendor/licenses")
async def list_my_licenses(vendor=Depends(current_vendor)):
    """Live list of the vendor's licences with computed status. Also returns
    the KZ licence catalogue and which ones are missing for this vendor so
    the UI can render the 'Missing' row with an Add licence button."""
    vendor_doc = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    rows = []
    async for lic in db.vendor_licenses.find({"vendor_ref": vendor["vendor_ref"]}).sort("expires_at", 1):
        lic["status"] = _status(lic.get("expires_at"))
        rows.append(_out(lic))

    # Build "missing" list against the KZ master catalogue.
    held_types = {r["licence_type"] for r in rows}
    # Honour the legacy kz_licenses array (string list) as "on file".
    legacy_held = set(vendor_doc.get("kz_licenses") or []) if vendor_doc else set()
    missing = [
        lt for lt in config.KZ_LICENSE_TYPES
        if lt not in held_types and lt not in legacy_held
    ]
    return {
        "licenses": rows,
        "catalogue": config.KZ_LICENSE_TYPES,
        "missing": missing,
        "expiring_soon": sum(1 for r in rows if r.get("status") == "expiring"),
        "expired": sum(1 for r in rows if r.get("status") == "expired"),
    }


@router.post("/api/v1/vendor/licenses")
async def add_license(payload: LicenseIn, vendor=Depends(current_vendor)):
    # Dedupe: one row per (vendor_ref, licence_type, country).
    dup = await db.vendor_licenses.find_one({
        "vendor_ref": vendor["vendor_ref"],
        "licence_type": payload.licence_type,
        "country": payload.country,
    })
    if dup:
        raise HTTPException(status_code=409,
            detail=f"You already have a {payload.licence_type} licence on file for {payload.country}.")
    doc = payload.model_dump()
    doc.update({
        "vendor_ref": vendor["vendor_ref"],
        "vendor_id": vendor["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    res = await db.vendor_licenses.insert_one(doc)
    doc["_id"] = res.inserted_id
    doc["status"] = _status(doc.get("expires_at"))
    await audit_log("vendor.license_add", None, "vendor", vendor["id"],
                    {"type": payload.licence_type, "country": payload.country})
    return _out(doc)


@router.put("/api/v1/vendor/licenses/{lic_id}")
async def update_license(lic_id: str, payload: LicenseIn, vendor=Depends(current_vendor)):
    lic = await db.vendor_licenses.find_one({"_id": ObjectId(lic_id)})
    if not lic or lic.get("vendor_ref") != vendor["vendor_ref"]:
        raise HTTPException(status_code=404, detail="Licence not found")
    await db.vendor_licenses.update_one(
        {"_id": ObjectId(lic_id)},
        {"$set": {**payload.model_dump(), "updated_at": now_iso()}},
    )
    await audit_log("vendor.license_update", None, "vendor", vendor["id"],
                    {"lic_id": lic_id, "type": payload.licence_type})
    updated = await db.vendor_licenses.find_one({"_id": ObjectId(lic_id)})
    updated["status"] = _status(updated.get("expires_at"))
    return _out(updated)


@router.delete("/api/v1/vendor/licenses/{lic_id}")
async def delete_license(lic_id: str, vendor=Depends(current_vendor)):
    lic = await db.vendor_licenses.find_one({"_id": ObjectId(lic_id)})
    if not lic or lic.get("vendor_ref") != vendor["vendor_ref"]:
        raise HTTPException(status_code=404, detail="Licence not found")
    await db.vendor_licenses.delete_one({"_id": ObjectId(lic_id)})
    await audit_log("vendor.license_delete", None, "vendor", vendor["id"],
                    {"lic_id": lic_id, "type": lic.get("licence_type")})
    return {"ok": True}


# ───────────────────────── Admin side (read-only for now) ─────────────────────────

@router.get("/api/v1/vendors/{vendor_ref}/licenses")
async def admin_list_licenses(vendor_ref: str,
                               admin=Depends(require_role("admin", "reviewer"))):
    rows = []
    async for lic in db.vendor_licenses.find({"vendor_ref": vendor_ref}).sort("expires_at", 1):
        lic["status"] = _status(lic.get("expires_at"))
        rows.append(_out(lic))
    return {"items": rows, "vendor_ref": vendor_ref}
