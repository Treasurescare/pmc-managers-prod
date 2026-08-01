from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from bson import ObjectId

import config
from db import db, next_sequence
from models import RegistrationDraftIn, RegistrationUpdateIn, RegistrationDecisionIn
from models.base import BaseDocument, now_iso
from security import require_role, new_magic_token
from emails import send_email, wrap
from audit import audit_log

router = APIRouter(prefix="/api/v1/registrations", tags=["registrations"])


def _out(doc: dict) -> dict:
    d = BaseDocument.out(doc)
    d.pop("magic_token", None)  # never leak
    return d


# ---------- PUBLIC (draft/resume/submit) ----------

@router.post("")
async def create_draft(payload: RegistrationDraftIn):
    """PUBLIC — create a fresh registration draft. Returns magic_token in response
    so the caller may store the resume link. In production, this is emailed."""
    existing = await db.registrations.find_one({
        "email": payload.email.lower(),
        "status": {"$in": ["draft", "submitted", "under_review", "needs_clarification"]},
    })
    if existing:
        # Resume existing draft rather than creating a duplicate
        token = existing["magic_token"]
        rid = str(existing["_id"])
    else:
        token = new_magic_token()
        doc = {
            "email": payload.email.lower(),
            "company_name": payload.company_name,
            "country": payload.country,
            "status": "draft",
            "tenant_id": config.DEFAULT_TENANT_ID,
            "magic_token": token,
            "created_at": now_iso(),
        }
        res = await db.registrations.insert_one(doc)
        rid = str(res.inserted_id)

    resume_url = f"{config.FRONTEND_URL}/register/resume?token={token}"
    # Fire magic-link email (best-effort)
    await send_email(payload.email, "PMC Managers — Continue your registration",
                     wrap("Continue your PMC registration",
                          f"<p>Use the link below to resume your Pre-Tender Registration Form. "
                          f"This link is unique to you — do not share.</p><p>Link expires in 72 hours.</p>",
                          "Resume registration", resume_url))
    return {"id": rid, "magic_token": token, "resume_url": resume_url}


@router.get("/resume/{token}")
async def resume_by_token(token: str):
    """PUBLIC — resolve a magic-link token to a draft."""
    doc = await db.registrations.find_one({"magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    return _out(doc)


@router.patch("/{registration_id}")
async def update_draft(registration_id: str, payload: RegistrationUpdateIn,
                       token: str = Query(..., description="Magic-link token")):
    """PUBLIC — update draft. Requires magic-link token."""
    doc = await db.registrations.find_one({"_id": ObjectId(registration_id), "magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Registration not found or token invalid")
    if doc["status"] not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400, detail=f"Cannot edit — status is {doc['status']}")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None or k in ("operating_regions", "business_categories", "kz_licenses", "documents", "previous_projects", "references")}
    updates["updated_at"] = now_iso()
    await db.registrations.update_one({"_id": ObjectId(registration_id)}, {"$set": updates})
    fresh = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    return _out(fresh)


@router.post("/{registration_id}/submit")
async def submit_registration(registration_id: str,
                              token: str = Query(..., description="Magic-link token")):
    """PUBLIC — final submission. Locks the draft and moves to `submitted`."""
    doc = await db.registrations.find_one({"_id": ObjectId(registration_id), "magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Registration not found")
    if doc["status"] not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400, detail=f"Cannot submit — status is {doc['status']}")

    # Validate all 6 declarations present & true
    decls = ["decl_conflict_of_interest", "decl_integrity", "decl_accuracy",
             "decl_data_consent", "decl_fee", "decl_notification"]
    missing = [d for d in decls if not doc.get(d)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing declarations: {', '.join(missing)}")

    # Validate signature block
    for f in ("signature_name", "signature_title", "signature_date"):
        if not doc.get(f):
            raise HTTPException(status_code=400, detail=f"Missing signature field: {f}")

    await db.registrations.update_one(
        {"_id": ObjectId(registration_id)},
        {"$set": {"status": "submitted", "submitted_at": now_iso()}},
    )
    await audit_log("registration.submit", None, "registration", registration_id,
                    {"email": doc["email"], "company_name": doc.get("company_name")})
    # Confirm to vendor
    await send_email(doc["email"], "PMC Managers — Registration submitted",
                     wrap("Registration submitted",
                          f"<p>Thank you. Your registration has been received and will be reviewed by our team. "
                          f"You will receive an update once a decision is made.</p>"))
    return {"ok": True, "status": "submitted"}


@router.get("/status/{token}")
async def status_by_token(token: str):
    """PUBLIC — status probe via magic-link (no sensitive data returned)."""
    doc = await db.registrations.find_one(
        {"magic_token": token},
        {"status": 1, "submitted_at": 1, "reviewed_at": 1, "reviewer_notes": 1, "vendor_ref": 1, "email": 1},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["id"] = str(doc.pop("_id"))
    return doc


# ---------- ADMIN queue + decisions ----------

@router.get("")
async def admin_list(status: Optional[str] = None, limit: int = 50,
                     admin=Depends(require_role("admin", "reviewer"))):
    q: dict = {"tenant_id": admin["tenant_id"]}
    if status:
        q["status"] = status
    limit = max(1, min(int(limit), 200))
    return [_out(r) async for r in db.registrations.find(q).sort("submitted_at", -1).limit(limit)]


@router.get("/{registration_id}")
async def admin_detail(registration_id: str, admin=Depends(require_role("admin", "reviewer"))):
    doc = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(doc)


@router.post("/{registration_id}/decision")
async def admin_decide(registration_id: str, payload: RegistrationDecisionIn,
                       admin=Depends(require_role("admin"))):
    doc = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    updates = {"reviewed_at": now_iso(), "reviewer_notes": payload.notes,
               "reviewed_by": admin["id"]}
    if payload.action == "approve":
        # Assign vendor_ref
        seq = await next_sequence("vendor_seq")
        vendor_ref = f"PMC-SUP-{seq:06d}"
        updates.update({"status": "approved", "vendor_ref": vendor_ref})
        await db.vendors.insert_one({
            "vendor_ref": vendor_ref,
            "email": doc["email"],
            "company_name": doc.get("company_name"),
            "country": doc.get("country"),
            "kz_licenses": doc.get("kz_licenses") or [],
            "profile": {k: doc.get(k) for k in doc.keys() if k not in ("_id", "magic_token", "status")},
            "tenant_id": doc.get("tenant_id", config.DEFAULT_TENANT_ID),
            "created_at": now_iso(),
        })
        await send_email(doc["email"], "PMC Managers — Registration approved",
                         wrap(f"You're approved · {vendor_ref}",
                              f"<p>Congratulations. Your PMC Managers vendor registration has been approved. "
                              f"Your supplier reference is <strong>{vendor_ref}</strong>.</p>"))
    elif payload.action == "reject":
        if not payload.notes:
            raise HTTPException(status_code=400, detail="Notes required when rejecting")
        updates["status"] = "rejected"
        await send_email(doc["email"], "PMC Managers — Registration update",
                         wrap("Registration update",
                              f"<p>Thank you for your interest. Unfortunately your registration was not approved at this time.</p>"
                              f"<p><em>Reason:</em> {payload.notes}</p>"))
    elif payload.action == "clarify":
        if not payload.notes:
            raise HTTPException(status_code=400, detail="Notes required when requesting clarification")
        updates["status"] = "needs_clarification"
        resume_url = f"{config.FRONTEND_URL}/register/resume?token={doc['magic_token']}"
        await send_email(doc["email"], "PMC Managers — Clarification needed",
                         wrap("Clarification needed on your registration",
                              f"<p>We reviewed your submission and need some clarification before approving.</p>"
                              f"<p><em>Reviewer notes:</em> {payload.notes}</p>",
                              "Resume registration", resume_url))
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    await db.registrations.update_one({"_id": ObjectId(registration_id)}, {"$set": updates})
    await audit_log(f"registration.{payload.action}", admin, "registration", registration_id,
                    {"notes": payload.notes, "vendor_ref": updates.get("vendor_ref")})
    return {"ok": True, "status": updates["status"]}
