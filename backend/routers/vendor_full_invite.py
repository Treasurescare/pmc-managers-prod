"""Wave 14 — Admin creates a vendor with the FULL Sections A–E form.

Unlike `/vendors/invite` (which just sends a magic-link email), this endpoint
lets the admin submit the entire registration on the vendor's behalf. Two modes:

  mode=activate   Admin sets a password → vendor account is immediately active.
                  Vendor can log in with the given password.
  mode=verify     A magic-link email is sent so the vendor sets their own
                  password (behaviour identical to /vendors/invite).

The registration document (Sections A–E fields + document_slots) is persisted
as an APPROVED registration linked to the new vendor, so the Vendors panel and
Vendor Intel dashboards see it as a fully-vetted supplier.
"""
import asyncio
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

import config
from db import db, next_sequence
from models.base import now_iso
from security import require_role, hash_password, new_magic_token
from emails import send_email, wrap
from audit import audit_log

router = APIRouter(prefix="/api/v1/vendors", tags=["vendor-full-invite"])


class AdminVendorFullIn(BaseModel):
    email: EmailStr
    mode: Literal["activate", "verify"] = "verify"
    password: Optional[str] = Field(default=None, min_length=8)
    registration: dict  # full Sections A–E dict (matches RegistrationDraftIn shape)


def _fingerprint_registration(reg: dict) -> dict:
    """Take only the safe fields from the registration payload for the vendor
    doc. Drops any admin-only or transient keys."""
    keep = ["company_name", "trade_name", "country", "registration_number",
            "legal_entity_type", "primary_sector", "website", "employees_count",
            "contact_name", "contact_email", "contact_office_phone", "contact_mobile"]
    return {k: reg.get(k) for k in keep if reg.get(k) is not None}


@router.post("/admin-create")
async def admin_create_vendor(payload: AdminVendorFullIn,
                                admin=Depends(require_role("admin"))):
    if payload.mode == "activate" and not payload.password:
        raise HTTPException(status_code=400,
                             detail="password is required when mode=activate")
    email = payload.email.lower()
    existing = await db.vendors.find_one({"email": email})
    if existing and existing.get("is_active"):
        raise HTTPException(status_code=409, detail="Vendor already active")

    # Allocate vendor_ref
    seq = await next_sequence("vendor_seq")
    vendor_ref = f"PMC-SUP-{seq:06d}"

    # Vendor stub
    vendor_doc = {
        "vendor_ref": vendor_ref, "email": email,
        **_fingerprint_registration(payload.registration),
        "tenant_id": admin["tenant_id"],
        "invited_by": admin["id"], "invited_at": now_iso(),
        "created_at": now_iso(),
        "onboarding_mode": payload.mode,
    }
    if payload.mode == "activate":
        vendor_doc.update({
            "password_hash": hash_password(payload.password),
            "email_verified": True, "email_verified_at": now_iso(),
            "is_active": True, "must_change_password": True,
        })
    else:
        token = new_magic_token()
        vendor_doc.update({
            "email_verified": False, "magic_token": token,
            "is_active": False,
        })

    if existing:
        await db.vendors.update_one({"_id": existing["_id"]}, {"$set": vendor_doc})
    else:
        await db.vendors.insert_one(vendor_doc)

    # Persist the FULL registration form as an approved record (admin-vouched)
    reg = dict(payload.registration or {})
    reg.update({
        "email": email,
        "vendor_ref": vendor_ref,
        "status": "approved" if payload.mode == "activate" else "submitted",
        "submitted_at": now_iso(),
        "approved_at": now_iso() if payload.mode == "activate" else None,
        "approved_by": admin["id"] if payload.mode == "activate" else None,
        "created_via": "admin_full_form",
        "tenant_id": admin["tenant_id"],
    })
    result = await db.registrations.insert_one(reg)

    # Email
    if payload.mode == "verify":
        verify_url = f"{config.FRONTEND_URL}/vendor/verify/{vendor_doc['magic_token']}"
        asyncio.create_task(send_email(
            email, "PMC Managers — Vendor registration completed by our team",
            wrap(f"Welcome to PMC · {vendor_ref}",
                 f"<p>The PMC Managers procurement team has completed your "
                 f"registration on your behalf. Please verify your email and set "
                 f"a password to activate your account.</p>",
                 "Verify email & set password", verify_url)))
    else:
        # Optional courtesy notification (no action required)
        asyncio.create_task(send_email(
            email, f"PMC Managers — Vendor account activated · {vendor_ref}",
            wrap(f"Welcome to PMC · {vendor_ref}",
                 f"<p>Your PMC vendor account has been activated. Please sign in and "
                 f"change your password on first login.</p>"
                 f"<p><strong>Login email:</strong> {email}</p>",
                 "Sign in", f"{config.FRONTEND_URL}/vendor/login")))

    await audit_log("vendor.admin_full_create", admin, "vendor", vendor_ref,
                    {"mode": payload.mode, "email": email,
                     "registration_id": str(result.inserted_id)})

    return {"vendor_ref": vendor_ref, "email": email, "mode": payload.mode,
            "registration_id": str(result.inserted_id),
            "activate_url": f"{config.FRONTEND_URL}/vendor/verify/{vendor_doc.get('magic_token', '')}" if payload.mode == "verify" else None}
