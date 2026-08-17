"""Profile & self-service ops:
  - Personal avatar upload (admin + vendor)
  - Tenant logo upload (admin only)
  - Vendor change-password already lives in vendor_auth; we add nothing here
  - Public username-lookup (find your email by phone or company name)
  - Public help-request submission (goes to admin queue)
  - Admin view / resolve help requests

Avatars & logos are stored as base64 data URLs directly in the parent document
so we don't need a separate blob store. Payload is enforced ≤ 350 KB to keep
Mongo docs lean; frontend resizes to 256×256 before upload.
"""
from typing import Optional, List, Literal
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, EmailStr, Field

from db import db
from security import current_admin, require_csrf
from audit import audit_log
from routers.vendor_auth import current_vendor

router = APIRouter(prefix="/api/v1", tags=["profile-ops"])

MAX_IMAGE_BYTES = 350 * 1024   # 350 KB after base64
DATA_URL_PREFIXES = ("data:image/png;base64,",
                     "data:image/jpeg;base64,",
                     "data:image/webp;base64,")


def _validate_data_url(data_url: str) -> str:
    if not data_url or not isinstance(data_url, str):
        raise HTTPException(status_code=400, detail="Image data required")
    if not data_url.startswith(DATA_URL_PREFIXES):
        raise HTTPException(status_code=400,
                            detail="Only PNG, JPEG or WEBP images are accepted")
    if len(data_url) > MAX_IMAGE_BYTES + 100:
        raise HTTPException(status_code=413,
                            detail=f"Image too large — max {MAX_IMAGE_BYTES // 1024} KB after encoding")
    return data_url


# =============================================================
#              1. PERSONAL AVATAR — ADMIN
# =============================================================
class AvatarIn(BaseModel):
    data_url: str


@router.post("/admin/auth/avatar", dependencies=[Depends(require_csrf)])
async def admin_upload_avatar(payload: AvatarIn, admin=Depends(current_admin)):
    data_url = _validate_data_url(payload.data_url)
    await db.admin_users.update_one(
        {"_id": ObjectId(admin["id"])},
        {"$set": {"avatar_data_url": data_url,
                  "avatar_updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    await audit_log("admin.avatar_update", admin, "admin_user", admin["id"], {})
    return {"ok": True}


@router.delete("/admin/auth/avatar", dependencies=[Depends(require_csrf)])
async def admin_remove_avatar(admin=Depends(current_admin)):
    await db.admin_users.update_one(
        {"_id": ObjectId(admin["id"])},
        {"$unset": {"avatar_data_url": "", "avatar_updated_at": ""}},
    )
    await audit_log("admin.avatar_remove", admin, "admin_user", admin["id"], {})
    return {"ok": True}


# =============================================================
#              2. PERSONAL AVATAR — VENDOR
# =============================================================
@router.post("/vendor/auth/avatar", dependencies=[Depends(require_csrf)])
async def vendor_upload_avatar(payload: AvatarIn, vendor=Depends(current_vendor)):
    data_url = _validate_data_url(payload.data_url)
    await db.vendors.update_one(
        {"_id": ObjectId(vendor["id"])},
        {"$set": {"avatar_data_url": data_url,
                  "avatar_updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    await audit_log("vendor.avatar_update", None, "vendor", vendor["id"], {})
    return {"ok": True}


@router.delete("/vendor/auth/avatar", dependencies=[Depends(require_csrf)])
async def vendor_remove_avatar(vendor=Depends(current_vendor)):
    await db.vendors.update_one(
        {"_id": ObjectId(vendor["id"])},
        {"$unset": {"avatar_data_url": "", "avatar_updated_at": ""}},
    )
    await audit_log("vendor.avatar_remove", None, "vendor", vendor["id"], {})
    return {"ok": True}


# =============================================================
#              3. TENANT LOGO (admin-only)
# =============================================================
class TenantLogoIn(BaseModel):
    data_url: str


@router.post("/tenants/{tenant_id}/logo", dependencies=[Depends(require_csrf)])
async def tenant_upload_logo(tenant_id: str, payload: TenantLogoIn,
                             admin=Depends(current_admin)):
    data_url = _validate_data_url(payload.data_url)
    r = await db.tenants.update_one(
        {"_id": ObjectId(tenant_id)},
        {"$set": {"logo_data_url": data_url,
                  "logo_updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await audit_log("tenant.logo_update", admin, "tenant", tenant_id, {})
    return {"ok": True}


@router.delete("/tenants/{tenant_id}/logo", dependencies=[Depends(require_csrf)])
async def tenant_remove_logo(tenant_id: str, admin=Depends(current_admin)):
    await db.tenants.update_one(
        {"_id": ObjectId(tenant_id)},
        {"$unset": {"logo_data_url": "", "logo_updated_at": ""}},
    )
    await audit_log("tenant.logo_remove", admin, "tenant", tenant_id, {})
    return {"ok": True}


# =============================================================
#              4. USERNAME LOOKUP  (public)
# =============================================================
class UsernameLookupIn(BaseModel):
    phone: Optional[str] = None
    company_name: Optional[str] = None


def _mask_email(email: str) -> str:
    """Return a masked version of the email so we don't leak accounts to
    random requests. e.g. 'kannan@emeraldcorporates.com' → 'k****n@e****s.com'.
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    def mask(part: str) -> str:
        if len(part) <= 2:
            return part[0] + "*"
        return f"{part[0]}{'*' * max(1, len(part) - 2)}{part[-1]}"
    if "." in domain:
        d_name, d_tld = domain.rsplit(".", 1)
        return f"{mask(local)}@{mask(d_name)}.{d_tld}"
    return f"{mask(local)}@{mask(domain)}"


@router.post("/auth/username-lookup")
async def username_lookup(payload: UsernameLookupIn):
    """Find your registered email from phone or company name.
    Returns a MASKED email hint so we don't leak accounts to random searches.
    Searches admin users, staff users, and vendors.
    """
    if not payload.phone and not payload.company_name:
        raise HTTPException(status_code=400,
                            detail="Provide phone or company name")

    matches: List[dict] = []

    if payload.company_name:
        name_q = {"company_name": {"$regex": f"^{payload.company_name.strip()}$",
                                    "$options": "i"}}
        async for v in db.vendors.find(name_q, {"email": 1, "company_name": 1}).limit(3):
            matches.append({"role": "Vendor",
                            "hint": _mask_email(v.get("email", "")),
                            "label": v.get("company_name")})
        # Also try registrations (in case vendor is not yet activated)
        async for r in db.registrations.find(name_q,
                                              {"email": 1, "company_name": 1}).limit(3):
            hint = _mask_email(r.get("email", ""))
            if not any(m["hint"] == hint for m in matches):
                matches.append({"role": "Vendor (pending)",
                                "hint": hint,
                                "label": r.get("company_name")})

    if payload.phone:
        phone = payload.phone.strip()
        # Try several fields commonly used for phone across the schema
        phone_q = {"$or": [
            {"contact_office_phone": phone},
            {"contact_mobile": phone},
            {"phone": phone},
        ]}
        async for r in db.registrations.find(phone_q,
                                              {"email": 1, "company_name": 1}).limit(3):
            hint = _mask_email(r.get("email", ""))
            if not any(m["hint"] == hint for m in matches):
                matches.append({"role": "Vendor",
                                "hint": hint,
                                "label": r.get("company_name")})

    return {"count": len(matches), "matches": matches}


# =============================================================
#              5. HELP REQUEST  (public → admin queue)
# =============================================================
class HelpRequestIn(BaseModel):
    kind: Literal["forgot-username", "forgot-password", "other"] = "forgot-username"
    full_name: str = Field(min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    message: str = Field(min_length=5, max_length=1000)


@router.post("/auth/help-request")
async def submit_help_request(payload: HelpRequestIn):
    doc = payload.model_dump()
    doc.update({
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "resolved_by": None,
        "resolution_notes": None,
    })
    r = await db.help_requests.insert_one(doc)
    await audit_log("help.request", None, "help_request", str(r.inserted_id),
                    {"kind": payload.kind, "name": payload.full_name})
    return {"ok": True, "id": str(r.inserted_id)}


@router.get("/admin/help-requests")
async def list_help_requests(admin=Depends(current_admin),
                              status: Optional[str] = None):
    q = {} if status is None else {"status": status}
    out = []
    async for h in db.help_requests.find(q).sort("created_at", -1).limit(200):
        h["id"] = str(h.pop("_id"))
        out.append(h)
    return {"count": len(out), "items": out}


class HelpResolveIn(BaseModel):
    resolution_notes: str = Field(min_length=1, max_length=1000)


@router.post("/admin/help-requests/{req_id}/resolve",
             dependencies=[Depends(require_csrf)])
async def resolve_help_request(req_id: str, payload: HelpResolveIn,
                                admin=Depends(current_admin)):
    r = await db.help_requests.update_one(
        {"_id": ObjectId(req_id)},
        {"$set": {"status": "resolved",
                  "resolved_at": datetime.now(timezone.utc).isoformat(),
                  "resolved_by": admin["email"],
                  "resolution_notes": payload.resolution_notes}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("help.resolve", admin, "help_request", req_id, {})
    return {"ok": True}
