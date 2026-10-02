"""Vendor Profile Change flow (v50m).

Vendors cannot write to their own `vendors` document directly — any edit to
address, telephone, mobile or email goes through this approval queue first.

Rules per field type:
    address / tel / mobile  — Admin approval only.
    email                     — Vendor must click a verification link sent
                                 to the NEW email AND an admin must approve.
                                 Both gates must pass before the vendor's
                                 login email is updated.

Endpoints:
    GET  /api/v1/vendor/profile                       — current editable profile
    GET  /api/v1/vendor/profile/requests              — my recent change requests
    POST /api/v1/vendor/profile/request-change         — submit new change request
    GET  /api/v1/vendor/profile/email-verify/{token}  — click target from email
    GET  /api/v1/vendors/profile-change-requests        — admin list
    POST /api/v1/vendors/profile-change-requests/{id}/approve
    POST /api/v1/vendors/profile-change-requests/{id}/reject
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from bson import ObjectId
import secrets

import config
from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log
from emails import send_email, wrap

router = APIRouter(tags=["vendor-profile-changes"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


ALLOWED_FIELDS = {"address", "office_phone", "mobile", "email", "company_name"}


class ChangeRequestIn(BaseModel):
    field: str = Field(..., description="One of address|office_phone|mobile|email|company_name")
    new_value: str = Field(..., min_length=1, max_length=400)
    reason: Optional[str] = Field(default=None, max_length=400)
    # v50o — structured address parts when field == "address":
    # {"street": ..., "city": ..., "state": ..., "country": ..., "zip": ...}
    parts: Optional[dict] = Field(default=None)

    @field_validator("field")
    @classmethod
    def _check_field(cls, v):
        if v not in ALLOWED_FIELDS:
            raise ValueError(f"field must be one of {sorted(ALLOWED_FIELDS)}")
        return v


class DecisionIn(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=400)


def _current_value(v_doc: dict, field: str) -> Optional[str]:
    if field == "email":
        return v_doc.get("email")
    if field == "company_name":
        return v_doc.get("company_name")
    # The rest live inside the registration-fingerprint keys on the vendor doc.
    direct = v_doc.get(field)
    if direct:
        return direct
    # Legacy fallback — some rows store address under `contact_office_phone` etc.
    aliases = {
        "office_phone": ["contact_office_phone", "phone"],
        "mobile": ["contact_mobile"],
        "address": ["postal_address", "contact_address"],
    }
    for alt in aliases.get(field, []):
        if v_doc.get(alt):
            return v_doc.get(alt)
    return None


# ───────────────────────── Vendor side ─────────────────────────
@router.get("/api/v1/vendor/profile")
async def get_my_profile(vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {
        "vendor_ref": v.get("vendor_ref"),
        "company_name": v.get("company_name"),
        "email": v.get("email"),
        "address": _current_value(v, "address"),
        "office_phone": _current_value(v, "office_phone"),
        "mobile": _current_value(v, "mobile"),
    }


@router.get("/api/v1/vendor/profile/requests")
async def list_my_requests(vendor=Depends(current_vendor)):
    pending = [_out(r) async for r in db.vendor_profile_requests.find(
        {"vendor_ref": vendor["vendor_ref"], "status": "pending"}
    ).sort("requested_at", -1)]
    recent = [_out(r) async for r in db.vendor_profile_requests.find(
        {"vendor_ref": vendor["vendor_ref"], "status": {"$in": ["approved", "rejected"]}}
    ).sort("decided_at", -1).limit(10)]
    return {"pending": pending, "recent": recent}


@router.post("/api/v1/vendor/profile/request-change")
async def request_profile_change(payload: ChangeRequestIn, vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    new_value = payload.new_value.strip()
    # Guard against submitting a change equal to the current value.
    if (_current_value(v, payload.field) or "").strip().lower() == new_value.lower():
        raise HTTPException(status_code=400,
                             detail="The new value is the same as the current one.")

    # Email specifics — validate as email + prevent collision.
    email_token = None
    if payload.field == "email":
        try:
            # Validate shape by piggybacking on Pydantic EmailStr.
            class _E(BaseModel):
                e: EmailStr
            _E(e=new_value)
        except Exception:
            raise HTTPException(status_code=400, detail="Please provide a valid email.")
        new_email = new_value.lower()
        clash = await db.vendors.find_one({"email": new_email, "_id": {"$ne": v["_id"]}})
        if clash:
            raise HTTPException(status_code=409,
                                 detail="Another vendor is already registered with this email.")
        email_token = secrets.token_urlsafe(32)
        new_value = new_email

    # Dedupe: deny if a pending request already exists for the same field.
    dup = await db.vendor_profile_requests.find_one({
        "vendor_ref": vendor["vendor_ref"],
        "field": payload.field,
        "status": "pending",
    })
    if dup:
        raise HTTPException(status_code=409,
                             detail=f"A pending request already exists for {payload.field}.")

    doc = {
        "vendor_ref": vendor["vendor_ref"],
        "vendor_id": str(v["_id"]),
        "vendor_email": v.get("email"),
        "vendor_company": v.get("company_name"),
        "field": payload.field,
        "old_value": _current_value(v, payload.field),
        "new_value": new_value,
        "reason": payload.reason,
        "status": "pending",
        "requested_at": now_iso(),
        "email_token": email_token,
        "email_verified": None if payload.field == "email" else True,
    }
    # v50o — keep the structured address parts so the admin panel can render
    # street/city/state/zip/country cleanly instead of a single blob.
    if payload.field == "address" and payload.parts:
        doc["address_parts"] = payload.parts
    res = await db.vendor_profile_requests.insert_one(doc)
    doc["_id"] = res.inserted_id

    if payload.field == "email" and email_token:
        verify_url = f"{config.FRONTEND_URL}/vendor/verify-email-change/{email_token}"
        try:
            await send_email(
                new_value,
                "Confirm your new PMC login email",
                wrap(
                    "Confirm your new email address",
                    f"<p>Hello {v.get('company_name') or 'Supplier'},</p>"
                    f"<p>You requested to change your PMC login email to "
                    f"<b>{new_value}</b>. Please click the button below to confirm you own this inbox. "
                    f"After confirmation, a PMC administrator still needs to approve the change "
                    f"before it takes effect.</p>"
                    f"<p>If you did not request this, you can ignore this email.</p>",
                    "Confirm this email", verify_url,
                ),
            )
        except Exception:
            # Email failure must not kill the submission — admin can resend.
            pass

    await audit_log("vendor.profile_change_request", None, "vendor",
                     vendor["id"], {"field": payload.field})
    return _out(doc)


@router.get("/api/v1/vendor/profile/email-verify/{token}")
async def confirm_email_token(token: str):
    """Open from the email-verification link. Marks the request's email as
    verified. Admin approval is still required to activate the change."""
    req = await db.vendor_profile_requests.find_one({"email_token": token})
    if not req:
        raise HTTPException(status_code=404, detail="This verification link is invalid or has expired.")
    if req.get("status") != "pending":
        return {"ok": True, "already": True, "status": req.get("status")}
    if req.get("email_verified"):
        return {"ok": True, "already": True, "status": "pending"}
    await db.vendor_profile_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"email_verified": True, "email_verified_at": now_iso()}},
    )
    await audit_log("vendor.profile_change_email_verified", None, "vendor",
                     req["vendor_id"], {"field": "email", "new": req["new_value"]})
    return {"ok": True, "new_email": req["new_value"]}


# ───────────────────────── Admin side ─────────────────────────
@router.get("/api/v1/vendors/profile-change-requests")
async def admin_list_requests(status: str = "pending",
                                admin=Depends(require_role("admin", "reviewer"))):
    cursor = db.vendor_profile_requests.find({"status": status})\
        .sort("requested_at", -1).limit(500)
    return [_out(r) async for r in cursor]


@router.post("/api/v1/vendors/profile-change-requests/{request_id}/approve")
async def admin_approve_request(request_id: str, payload: DecisionIn,
                                   admin=Depends(require_role("admin"))):
    req = await db.vendor_profile_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Already {req['status']}")
    if req["field"] == "email" and not req.get("email_verified"):
        raise HTTPException(
            status_code=412,
            detail="The vendor has not yet verified the new email address. "
                   "Ask them to click the link that was emailed to the new address.",
        )

    # Apply the change.
    field = req["field"]
    new_value = req["new_value"]
    update_doc: Dict[str, object] = {}
    if field == "email":
        update_doc["email"] = new_value
    elif field == "company_name":
        update_doc["company_name"] = new_value
    else:
        update_doc[field] = new_value
        if req.get("address_parts"):
            update_doc["address_parts"] = req["address_parts"]
    await db.vendors.update_one({"_id": ObjectId(req["vendor_id"])},
                                   {"$set": update_doc})

    await db.vendor_profile_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "approved", "decided_at": now_iso(),
                   "decided_by": admin["email"], "decision_notes": payload.notes}},
    )
    await audit_log("vendor.profile_change_approve", admin, "vendor",
                     req["vendor_id"], {"field": field, "new": new_value})

    # Notify the vendor at their (possibly new) address.
    try:
        notify_to = new_value if field == "email" else req.get("vendor_email")
        if notify_to:
            await send_email(
                notify_to,
                "Your PMC profile change was approved",
                wrap(
                    "Profile change approved",
                    f"<p>Hello {req.get('vendor_company') or 'Supplier'},</p>"
                    f"<p>Your request to change <b>{field.replace('_',' ')}</b> to "
                    f"<b>{new_value}</b> has been approved by a PMC administrator "
                    f"and is now active on your account.</p>"
                    + (f"<p>Admin note: {payload.notes}</p>" if payload.notes else ""),
                    "Open vendor portal", f"{config.FRONTEND_URL}/vendor",
                ),
            )
    except Exception:
        pass
    return {"ok": True}


@router.post("/api/v1/vendors/profile-change-requests/{request_id}/reject")
async def admin_reject_request(request_id: str, payload: DecisionIn,
                                 admin=Depends(require_role("admin"))):
    req = await db.vendor_profile_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Already {req['status']}")
    if not (payload.notes or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required.")
    await db.vendor_profile_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "rejected", "decided_at": now_iso(),
                   "decided_by": admin["email"], "decision_notes": payload.notes}},
    )
    await audit_log("vendor.profile_change_reject", admin, "vendor",
                     req["vendor_id"], {"field": req["field"], "reason": payload.notes})
    try:
        if req.get("vendor_email"):
            await send_email(
                req["vendor_email"],
                "Your PMC profile change was declined",
                wrap(
                    "Profile change declined",
                    f"<p>Hello {req.get('vendor_company') or 'Supplier'},</p>"
                    f"<p>Your request to change <b>{req['field'].replace('_',' ')}</b> to "
                    f"<b>{req['new_value']}</b> was declined by a PMC administrator.</p>"
                    f"<p>Reason: {payload.notes}</p>",
                    "Open vendor portal", f"{config.FRONTEND_URL}/vendor",
                ),
            )
    except Exception:
        pass
    return {"ok": True}
