import asyncio
import base64
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
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


# ---------- Wave 10 — Per-section document slots ----------

# Slot definitions — each slot is a canonical "kind" of document a vendor must
# attach. The exact list is derived from the Registration Form Draft.docx.
DOC_SLOTS = {
    # Page 1 — Identity & Basic Info
    "incorporation_certificate": {"label": "Incorporation Certificate", "section": "a", "required": True},
    "address_proof": {"label": "Address Proof (utility bill / lease deed)", "section": "a", "required": True},
    "tin_proof": {"label": "TIN / VAT Proof", "section": "a", "required": True},
    "audited_financials": {"label": "Audited Financial Statements (last 3 years)", "section": "a", "required": False},
    # Page 2 — Business Profile
    "previous_works": {"label": "Previous Works Completed", "section": "b", "required": True},
    "iso_certificates": {"label": "ISO / Quality Certifications", "section": "b", "required": False},
    "licenses_permits": {"label": "Licenses / Permits / Regulatory Authorizations", "section": "b", "required": True},
    # Page 3 — Documents to be Attached
    "articles_of_incorporation": {"label": "Articles of Incorporation / Charter / Bylaws", "section": "c", "required": True},
    "bank_reference": {"label": "Bank Reference / Statement", "section": "c", "required": True},
    "power_of_attorney": {"label": "Power of Attorney for Signatory", "section": "c", "required": False},
    "other_supporting": {"label": "Other Supporting Documents", "section": "c", "required": False},
    # Page 4 — Signed declaration
    "signed_declaration": {"label": "Signed Declarations & Consent (PDF)", "section": "d", "required": False},
}


@router.get("/document-slots/schema")
async def get_slot_schema():
    """PUBLIC — returns the canonical slot list so the frontend renders the correct uploaders."""
    return {"slots": DOC_SLOTS}


# v51ac — admin fetches the vendor's magic resume URL so admins can edit a
# non-approved registration on behalf of the vendor using the same 5-section
# UI the vendor fills. Reused by RegistrationsPanel's new per-row Edit button.
@router.get("/admin/{rid}/resume-link")
async def admin_resume_link(rid: str, admin=Depends(require_role("admin", "reviewer"))):
    try:
        reg_obj_id = ObjectId(rid)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id")
    reg = await db.registrations.find_one({"_id": reg_obj_id})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.get("status") == "approved":
        raise HTTPException(status_code=400,
                            detail="Approved registrations use the vendor profile editor "
                                   "(/admin/vendors/{vendor_ref}/edit).")
    token = reg.get("magic_token") or ""
    if not token:
        # Legacy registrations pre-date magic links — mint one so the admin
        # resume editor always opens instead of bouncing back to /register.
        token = new_magic_token()
        await db.registrations.update_one(
            {"_id": reg_obj_id},
            {"$set": {"magic_token": token, "updated_at": now_iso()}})
    await audit_log("registration.admin_resume_link", admin, "registration", rid,
                    {"status": reg.get("status")})
    frontend = (getattr(config, "FRONTEND_URL", "") or "").rstrip("/")
    path = f"/register/resume?rid={rid}&token={token}&from=admin"
    return {"url": (frontend + path) if frontend else path,
            "path": path,
            "status": reg.get("status")}


@router.post("/{registration_id}/documents/{slot}")
async def upload_registration_doc(registration_id: str, slot: str,
                                    file: UploadFile = File(...),
                                    token: str = Form(...)):
    """PUBLIC (token-authed) — upload a document into a specific slot on this registration."""
    if slot not in DOC_SLOTS:
        raise HTTPException(status_code=400, detail=f"Unknown slot '{slot}'")
    try:
        reg_obj_id = ObjectId(registration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id — save the draft first")
    reg = await db.registrations.find_one({"_id": reg_obj_id, "magic_token": token})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found or token invalid")
    if reg["status"] not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400, detail=f"Cannot edit — status is {reg['status']}")

    body = await file.read()
    if len(body) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds pilot upload limit")
    key = f"registration-docs/{registration_id}/{slot}/{uuid.uuid4().hex}_{file.filename}"
    await db.uploads.insert_one({
        "key": key, "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(body),
        "data_b64": base64.b64encode(body).decode("ascii"),
        "created_at": now_iso(),
    })
    meta = {"slot": slot, "file_name": file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": len(body),
            "url": f"/api/v1/uploads/files/{key}",
            "uploaded_at": now_iso(), "key": key}
    await db.registrations.update_one(
        {"_id": reg_obj_id},
        {"$set": {f"document_slots.{slot}": meta, "updated_at": now_iso()}},
    )
    await audit_log("registration.document_upload", None, "registration", registration_id,
                    {"slot": slot, "file_name": file.filename})
    return meta


# v51af — admin edits a non-approved registration's section data directly
# (RegistrationResume opened with ?from=admin&rid=...). The public token PATCH
# only permits draft/needs_clarification; admins may also edit submitted /
# under_review records on behalf of the vendor.
@router.patch("/admin/{rid}")
async def admin_update_registration(rid: str, payload: RegistrationUpdateIn,
                                    admin=Depends(require_role("admin", "reviewer"))):
    try:
        reg_obj_id = ObjectId(rid)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id")
    reg = await db.registrations.find_one({"_id": reg_obj_id})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.get("status") in ("approved", "rejected"):
        raise HTTPException(status_code=400,
                            detail="Approved/rejected registrations use the vendor profile editor.")
    updates = payload.model_dump(exclude_unset=True)
    for protected in ("id", "_id", "status", "vendor_ref", "magic_token", "tenant_id",
                      "created_at", "submitted_at", "reviewed_at", "reviewer_notes"):
        updates.pop(protected, None)
    updates["updated_at"] = now_iso()
    await db.registrations.update_one({"_id": reg_obj_id}, {"$set": updates})
    await audit_log("registration.admin_update", admin, "registration", rid,
                    {"fields": sorted(updates.keys())})
    fresh = await db.registrations.find_one({"_id": reg_obj_id})
    return _out(fresh)


@router.get("/{registration_id}/documents/{slot}/file")
async def download_registration_doc(registration_id: str, slot: str,
                                     token: str = Query(..., min_length=1),
                                     download: bool = False):
    """View or download a registration document using the magic token.

    PUBLIC — used by the vendor while filling the form (not yet signed in).
    Admin reviewers use `/admin-file` which validates the admin cookie.
    """
    from fastapi.responses import Response
    import base64
    try:
        reg_obj_id = ObjectId(registration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id")
    reg = await db.registrations.find_one({"_id": reg_obj_id, "magic_token": token})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found or token invalid")
    slots = reg.get("document_slots") or {}
    meta = slots.get(slot)
    if not meta or not meta.get("key"):
        raise HTTPException(status_code=404, detail="Document not uploaded")
    doc = await db.uploads.find_one({"key": meta["key"]})
    if not doc:
        raise HTTPException(status_code=404, detail="File missing")
    body = base64.b64decode(doc["data_b64"])
    disp = "attachment" if download else "inline"
    display_name = meta.get("file_name") or slot
    return Response(
        content=body,
        media_type=doc.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f'{disp}; filename="{display_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{registration_id}/documents/{slot}/admin-file")
async def admin_download_registration_doc(registration_id: str, slot: str,
                                           download: bool = False,
                                           admin=Depends(require_role("admin", "reviewer", "support"))):
    """Admin-authenticated variant used by the reviewer UI."""
    from fastapi.responses import Response
    import base64
    try:
        reg_obj_id = ObjectId(registration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id")
    reg = await db.registrations.find_one({"_id": reg_obj_id})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    slots = reg.get("document_slots") or {}
    meta = slots.get(slot)
    if not meta or not meta.get("key"):
        raise HTTPException(status_code=404, detail="Document not uploaded")
    doc = await db.uploads.find_one({"key": meta["key"]})
    if not doc:
        raise HTTPException(status_code=404, detail="File missing")
    body = base64.b64decode(doc["data_b64"])
    disp = "attachment" if download else "inline"
    display_name = meta.get("file_name") or slot
    return Response(
        content=body,
        media_type=doc.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f'{disp}; filename="{display_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{registration_id}/documents/{slot}")
async def delete_registration_doc(registration_id: str, slot: str,
                                    token: str = Query(...)):
    """PUBLIC (token-authed) — delete a slot's document."""
    try:
        reg_obj_id = ObjectId(registration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id")
    reg = await db.registrations.find_one({"_id": reg_obj_id, "magic_token": token})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found or token invalid")
    if reg["status"] not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400, detail=f"Cannot edit — status is {reg['status']}")
    await db.registrations.update_one(
        {"_id": reg_obj_id},
        {"$unset": {f"document_slots.{slot}": ""}, "$set": {"updated_at": now_iso()}},
    )
    await audit_log("registration.document_delete", None, "registration", registration_id,
                    {"slot": slot})
    return {"ok": True}


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
            "data_processing_consent": payload.data_processing_consent,
            "marketing_consent": payload.marketing_consent,
            "consent_at": now_iso() if payload.data_processing_consent else None,
            "created_at": now_iso(),
        }
        res = await db.registrations.insert_one(doc)
        rid = str(res.inserted_id)

    resume_url = f"{config.FRONTEND_URL}/register/resume?token={token}"
    # Fire magic-link email in the background — never block the API response on SMTP.
    asyncio.create_task(send_email(
        payload.email, "PMC Managers — Continue your registration",
        wrap("Continue your PMC registration",
             f"<p>Use the link below to resume your Pre-Tender Registration Form. "
             f"This link is unique to you — do not share.</p><p>Link expires in 72 hours.</p>",
             "Resume registration", resume_url)))
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

    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = now_iso()
    await db.registrations.update_one({"_id": ObjectId(registration_id)}, {"$set": updates})
    fresh = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    return _out(fresh)


@router.post("/{registration_id}/submit")
async def submit_registration(registration_id: str,
                              token: str = Query(..., description="Magic-link token")):
    """PUBLIC — final submission. Locks the draft and moves to `submitted`."""
    # Bug #new — harden id parsing: an invalid id would previously bubble up
    # as a BSON InvalidId → 500.
    try:
        oid = ObjectId(registration_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed registration id")
    doc = await db.registrations.find_one({"_id": oid, "magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Registration not found")
    if doc.get("status") not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400,
                            detail=f"Cannot submit — status is {doc.get('status') or 'unknown'}")

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

    # Guard against a data row missing an email — must have been captured on
    # RegistrationStart. Return a clean 400 instead of KeyError → 500.
    email = doc.get("email")
    if not email:
        raise HTTPException(status_code=400,
            detail="This registration is missing an email address. Please restart from the beginning.")

    await db.registrations.update_one(
        {"_id": oid},
        {"$set": {"status": "submitted", "submitted_at": now_iso()}},
    )
    await audit_log("registration.submit", None, "registration", registration_id,
                    {"email": email, "company_name": doc.get("company_name")})
    # Confirm to vendor — fire-and-forget, swallow any transport error so a
    # broken SMTP/Resend key can never take down a successful submission.
    async def _notify():
        try:
            await send_email(
                email, "PMC Managers — Registration submitted",
                wrap("Registration submitted",
                     f"<p>Thank you. Your registration has been received and will be reviewed by our team. "
                     f"You will receive an update once a decision is made.</p>"))
        except Exception:
            pass
    asyncio.create_task(_notify())
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

@router.post("/admin/send-reminders")
async def admin_send_reminders(admin: dict = Depends(require_role("admin"))) -> dict:
    """Send reminder emails to vendors with drafts older than 7 days.

    A vendor only receives one reminder every 7 days (via `reminder_sent_at`).
    Returns { checked, reminded }.
    """
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    q = {
        "status": {"$in": ["draft", "needs_clarification"]},
        "created_at": {"$lt": cutoff},
        "$or": [
            {"reminder_sent_at": {"$exists": False}},
            {"reminder_sent_at": {"$lt": cutoff}},
        ],
    }
    checked = 0
    reminded = 0
    async for reg in db.registrations.find(q):
        checked += 1
        resume_url = f"{config.FRONTEND_URL}/register/resume?token={reg['magic_token']}"
        asyncio.create_task(send_email(
            reg["email"],
            "PMC Managers — Your registration is still open",
            wrap("Continue your registration",
                 f"<p>You started a PMC Managers vendor registration but haven't finished it yet. "
                 f"Your progress is saved — pick up right where you left off:</p>",
                 "Resume registration", resume_url)))
        await db.registrations.update_one(
            {"_id": reg["_id"]},
            {"$set": {"reminder_sent_at": now_iso()}},
        )
        # Bug #51 — also drop an in-app notification for the admin panel so
        # ops know the nudge actually reached someone.
        try:
            await db.notifications.insert_one({
                "tenant_id": reg.get("tenant_id") or config.DEFAULT_TENANT_ID,
                "recipient_role": "admin",
                "kind": "registration.reminder_sent",
                "title": "Reminder email sent",
                "body": f"Nudged {reg.get('email')} — draft is 7+ days old.",
                "resource_type": "registration",
                "resource_id": str(reg["_id"]),
                "created_at": now_iso(),
                "read": False,
            })
        except Exception:
            pass  # notifications table optional; never break the reminder run
        reminded += 1

    await audit_log("registration.reminders_sent", admin, "registration_batch", "reminders",
                    {"checked": checked, "reminded": reminded})
    return {"ok": True, "checked": checked, "reminded": reminded}


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
    from routers.registrations_helpers import (
        approve_and_create_vendor,
        dispatch_rejection_email,
        dispatch_clarification_email,
    )

    doc = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    # Bug #23 / #77 fix — reject any decision on a registration that has
    # already been approved. Prevents the "double-approve → 500" crash and
    # gives the reviewer a clear message instead of a stack trace.
    current_status = (doc.get("status") or "").lower()
    if current_status == "approved":
        raise HTTPException(
            status_code=409,
            detail=f"Registration already approved (vendor {doc.get('vendor_ref') or '—'}). "
                   "No further decisions can be recorded.",
        )
    if current_status == "rejected" and payload.action == "reject":
        raise HTTPException(status_code=409, detail="Registration already rejected.")

    updates = {
        "reviewed_at": now_iso(),
        "reviewer_notes": payload.notes,
        "reviewed_by": admin["id"],
    }

    if payload.action == "approve":
        # Bug #83 fix — strict validation before approval. Prevents admins
        # from approving a supplier that hasn't filled the Identity fields.
        REQUIRED = ["company_name", "registered_address", "country",
                    "registration_number", "legal_entity_type", "email"]
        missing = [f for f in REQUIRED if not (doc.get(f) or "").strip()] if isinstance(doc.get("company_name"), str) else [f for f in REQUIRED if not doc.get(f)]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot approve — the supplier has not filled these required "
                    f"Section A fields: {', '.join(missing)}. Ask them to complete "
                    "the registration or use Request Clarification instead."
                ),
            )
        updates.update(await approve_and_create_vendor(doc))
    elif payload.action == "reject":
        if not payload.notes:
            raise HTTPException(status_code=400, detail="Notes required when rejecting")
        updates["status"] = "rejected"
        dispatch_rejection_email(doc, payload.notes)
    elif payload.action == "clarify":
        if not payload.notes:
            raise HTTPException(status_code=400, detail="Notes required when requesting clarification")
        updates["status"] = "needs_clarification"
        dispatch_clarification_email(doc, payload.notes)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    await db.registrations.update_one({"_id": ObjectId(registration_id)}, {"$set": updates})
    await audit_log(f"registration.{payload.action}", admin, "registration", registration_id,
                    {"notes": payload.notes, "vendor_ref": updates.get("vendor_ref")})
    return {"ok": True, "status": updates["status"]}


# ---------- Wave 7 — GDPR right-to-be-forgotten ----------

@router.post("/{registration_id}/gdpr-forget")
async def gdpr_forget(registration_id: str, admin=Depends(require_role("admin"))):
    """Anonymise a registration + linked vendor. Retains the audit trail
    (hash chain preserved) but strips personal data per GDPR Art. 17."""
    reg = await db.registrations.find_one({"_id": ObjectId(registration_id)})
    if not reg:
        raise HTTPException(status_code=404, detail="Not found")
    email = reg.get("email")
    anon = {
        "email": f"anonymised+{registration_id}@example.invalid",
        "company_name": "[REDACTED]",
        "contact_name": None, "contact_email": None, "contact_mobile": None,
        "contact_office_phone": None, "signatory_name": None,
        "signatory_contact": None, "signature_name": None,
        "registered_address": None, "mailing_address": None,
        "bank_account_number": None, "bank_swift": None,
        "documents": [], "previous_projects": [], "references": [],
        "gdpr_forgotten_at": now_iso(), "gdpr_forgotten_by": admin["email"],
    }
    await db.registrations.update_one({"_id": ObjectId(registration_id)}, {"$set": anon})
    if email:
        await db.vendors.update_many({"email": email},
                                     {"$set": {**anon, "is_active": False}})
    await audit_log("gdpr.forget", admin, "registration", registration_id,
                    {"original_email": email})
    return {"ok": True}
