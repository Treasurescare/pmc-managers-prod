"""Escrow Institution registration & dashboard — scaffold, v51al.

Trusted external escrow providers (banks / trustees) register through a
vendor-like flow: KYC docs, banking coordinates, named signatories. Once
approved, admins pick them when creating joint escrow accounts and the
institution's officers get their own portal to track pending signatures.

STATUS: *NOT wired into server.py yet* — module exists so UI can be built
and reviewed. Flip the switch by adding
    from routers import escrow_institutions
    app.include_router(escrow_institutions.router)
to backend/server.py when ready to go live.
"""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator

from db import db
from security import require_role
from audit import audit_log
from models.base import now_iso

router = APIRouter(prefix="/api/v1/escrow-institutions", tags=["escrow-institutions"])


# v52d — session OR magic-token gate. Lets the new account-first wizard
# PATCH / submit / view an institution using the escrow_account_token cookie
# while existing admin-invited magic links keep working during the transition.
async def _institution_for_write(iid: str, request: Request, token: Optional[str] = None):
    """Returns (doc, caller_tag). Order matters: cookie > magic token."""
    # 1 — new account cookie (preferred)
    try:
        from routers.escrow_accounts import current_account
        acc = await current_account(request)
        doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
        if doc and doc.get("account_id") == acc["id"]:
            return doc, f"account:{acc['id']}"
    except HTTPException:
        pass
    # 2 — legacy magic token (admin-invited rows + anything in transition)
    if token:
        doc = await db.escrow_institutions.find_one(
            {"_id": ObjectId(iid), "magic_token": token})
        if doc:
            return doc, "magic_token"
    raise HTTPException(status_code=404, detail="Not found")

Status = Literal["draft", "submitted", "under_review", "needs_clarification",
                 "approved", "rejected"]


class Signatory(BaseModel):
    name: str = ""
    designation: str = ""
    # v52cz rev5 — Optional so the default empty row the form starts with
    # (name="", email="") no longer 422s on EmailStr. "" → None via the
    # pre-validator; blank rows are then dropped entirely in _clean_payload.
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    passport_or_id_key: Optional[str] = None     # upload key for photo ID
    specimen_signature_key: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


def _clean_payload(doc: dict) -> dict:
    """Drop scaffold rows that are completely empty so a fresh form (one
    blank signatory + one blank bank row) doesn't trip required-field or
    format validation. Rows with ANY meaningful content are kept."""
    doc["signatories"] = [
        s for s in (doc.get("signatories") or [])
        if (s.get("name") or "").strip() or (s.get("email") or "").strip()
    ]
    doc["banking"] = [
        b for b in (doc.get("banking") or [])
        if (b.get("account_name") or "").strip()
        or (b.get("account_number") or "").strip()
        or (b.get("institution_name") or "").strip()
    ]
    return doc


class BankingCoord(BaseModel):
    # v52cz rev6 — every field optional so a half-filled bank row can be
    # saved as draft. `submit()` still enforces account+institution.
    account_name: str = ""
    account_number: str = ""
    iban: Optional[str] = None
    swift: Optional[str] = None
    currency: str = "USD"
    institution_name: str = ""
    bank_country: Optional[str] = None              # ISO-2 code of the bank
    bank_state: Optional[str] = None
    bank_city: Optional[str] = None
    branch: Optional[str] = None
    bank_code: Optional[str] = None                 # IFSC / ABA / BSB — local routing
    sort_code: Optional[str] = None                 # UK sort code
    routing_number: Optional[str] = None            # US ABA routing
    correspondent_bank: Optional[str] = None
    correspondent_swift: Optional[str] = None
    settlement_cutoff: Optional[str] = None         # free-text TZ-aware, e.g. "16:00 UK"


class EscrowInstitutionIn(BaseModel):
    # v52cz rev6 — core fields all optional on PATCH so "Save as draft"
    # works at any step without the user having completed the previous
    # one. submit() still enforces the mandatory set.
    legal_name: str = ""
    trading_name: Optional[str] = None
    country: str = ""                              # ISO-2 code, e.g. "IN"
    # v52cz rev4 — structured registered address (country→state→city→zip
    # →address1→address2). `registered_address` kept for backwards compat;
    # it's auto-populated from the structured pieces when any are supplied.
    registered_address: str = ""
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    postal_code: Optional[str] = None
    reg_number: str = ""                           # company / trust registration no.
    tax_id: Optional[str] = None
    gst_or_vat: Optional[str] = None
    regulator: Optional[str] = None               # issuing authority
    licence_number: Optional[str] = None
    licence_expiry: Optional[str] = None          # ISO date
    website: Optional[str] = None
    primary_contact_email: Optional[EmailStr] = None
    primary_contact_phone: Optional[str] = None   # kept for back-compat
    mobile_phone: Optional[str] = None            # v52cz rev6
    office_phone: Optional[str] = None            # v52cz rev6
    phone_country_code: Optional[str] = None       # e.g. "91" (dial code)
    primary_contact_name: Optional[str] = None
    institution_type: Literal["corporate", "personal"] = "corporate"

    @field_validator("primary_contact_email", mode="before")
    @classmethod
    def _empty_email_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v
    # Document upload keys collected during registration
    documents: dict = Field(default_factory=dict)  # slot -> {key, filename, uploaded_at}
    banking: List[BankingCoord] = Field(default_factory=list)
    signatories: List[Signatory] = Field(default_factory=list)


class EscrowInstitutionOut(EscrowInstitutionIn):
    id: str
    status: Status = "draft"
    magic_token: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewer_notes: Optional[str] = None


DOC_SLOTS = [
    "incorporation_certificate", "trust_deed", "regulatory_licence",
    "tax_registration", "gst_vat_certificate", "audited_financials_y1",
    "audited_financials_y2", "insurance_indemnity", "letterhead_sample",
    "signatory_authority_resolution",
]


def _out(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


def _new_token() -> str:
    import secrets
    return secrets.token_urlsafe(32)


# -------- Public (vendor-like) endpoints -----------------------------------

@router.get("/email-available")
async def email_available(email: str) -> dict:
    """v52cz rev8 — public dedup probe. The register form calls this on
    email blur so users see "already registered" BEFORE they fill the whole
    form. Returns {available: bool, status?: str} — never leaks any other
    detail about the existing institution."""
    e = (email or "").strip().lower()
    if not e:
        return {"available": False}
    doc = await db.escrow_institutions.find_one(
        {"primary_contact_email": {"$regex": f"^{e}$", "$options": "i"}},
        {"status": 1})
    if doc:
        return {"available": False, "status": doc.get("status") or "draft"}
    return {"available": True}


@router.post("/register", deprecated=True)
async def register_institution(payload: EscrowInstitutionIn) -> dict:
    """DEPRECATED (v52d) — use POST /api/v1/escrow-accounts/register instead.
    The account-first flow replaces this magic-link draft entry point. We
    reject new submissions here so no new orphan drafts are created."""
    raise HTTPException(status_code=410,
        detail={
            "error": "endpoint_deprecated",
            "message": "The escrow registration flow has moved. Please "
                       "create an account at /escrow/register — verify your "
                       "email, then sign in to complete all five sections.",
            "redirect_to": "/escrow/register",
        })


@router.get("/resume/{token}")
async def resume(token: str) -> dict:
    doc = await db.escrow_institutions.find_one({"magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    return _out(doc)


@router.get("/{iid}/admin-view-public")
async def view_own_institution(iid: str, request: Request) -> dict:
    """v52d — session-only read of the account's OWN institution.
    Used by the wizard to preload existing draft fields on sign-in.
    No magic-token fallback (reads are 1:1 with the signed-in account)."""
    try:
        from routers.escrow_accounts import current_account
        acc = await current_account(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")
    doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not doc or doc.get("account_id") != acc["id"]:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(doc)


# v52cz rev6 — magic-token-gated file serve. Vendors in the escrow registration
# flow previously used /api/v1/uploads/files/{key}, which requires a signed-in
# admin OR vendor cookie — and returned {"detail":"Sign in to download tender
# documents"} to anonymous (magic-link) users. This endpoint validates the
# token against the registration + confirms the file key is attached to it
# before serving.
@router.get("/{iid}/documents/{slot}/file")
async def get_registration_document(iid: str, slot: str, token: str,
                                      download: bool = False):
    doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid),
                                                   "magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    slot_meta = (doc.get("documents") or {}).get(slot) or {}
    key = slot_meta.get("key")
    if not key:
        raise HTTPException(status_code=404, detail="File not uploaded")
    from routers.uploads import _legacy_get_file_body
    return await _legacy_get_file_body(key, download)


@router.patch("/{iid}")
async def update_institution(iid: str, payload: EscrowInstitutionIn,
                              request: Request,
                              token: Optional[str] = None) -> dict:
    doc, _ = await _institution_for_write(iid, request, token)
    if doc["status"] not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400,
            detail=f"Cannot edit — status is {doc['status']}")
    updates = _clean_payload(payload.model_dump(exclude_unset=True))
    # v52cz rev8 — if the user tries to change their primary email to one
    # that already belongs to a DIFFERENT institution, reject with 409.
    new_email = (updates.get("primary_contact_email") or "").strip().lower()
    cur_email = (doc.get("primary_contact_email") or "").strip().lower()
    if new_email and new_email != cur_email:
        clash = await db.escrow_institutions.find_one({
            "_id": {"$ne": ObjectId(iid)},
            "primary_contact_email": {"$regex": f"^{new_email}$", "$options": "i"},
        })
        if clash:
            raise HTTPException(status_code=409,
                detail={"error": "escrow_email_already_registered",
                         "message": f"{new_email} is already registered.",
                         "status": clash.get("status")})
    updates["updated_at"] = now_iso()
    await db.escrow_institutions.update_one({"_id": ObjectId(iid)}, {"$set": updates})
    return _out(await db.escrow_institutions.find_one({"_id": ObjectId(iid)}))


@router.post("/{iid}/submit")
async def submit(iid: str, request: Request, token: Optional[str] = None) -> dict:
    doc, _ = await _institution_for_write(iid, request, token)
    required = ["legal_name", "country", "registered_address", "reg_number",
                "primary_contact_email"]
    missing = [k for k in required if not doc.get(k)]
    if missing:
        raise HTTPException(status_code=422,
            detail=f"Missing required fields: {', '.join(missing)}")
    if not doc.get("signatories"):
        raise HTTPException(status_code=422,
            detail="At least one named signatory is required")
    if not doc.get("banking"):
        raise HTTPException(status_code=422,
            detail="At least one banking coordinate is required")
    await db.escrow_institutions.update_one(
        {"_id": ObjectId(iid)},
        {"$set": {"status": "submitted", "updated_at": now_iso(),
                   "submitted_at": now_iso()}})
    await audit_log("escrow_inst.submit", None, "escrow_institution", iid, {})
    # Notify owning account (if any) that submission is now in review.
    if doc.get("account_id"):
        try:
            from routers.escrow_accounts import notify_account
            await notify_account(doc["account_id"], "submitted",
                "Registration submitted for review",
                "Your escrow institution registration is now with PMC's review "
                "team. We'll come back to you within 3 business days.",
                "/escrow/me")
        except Exception:
            pass
    return {"ok": True, "status": "submitted"}


# -------- Admin endpoints ---------------------------------------------------

# v52cx — admin invite flow. Instead of filling the full institution form
# themselves, admins drop in just the primary contact email (optional legal
# name) and we send that address a magic-link email. The institution then
# fills everything on their side via the public resume flow and submits for
# review as usual. The admin NEVER enters KYC data for a third party.
class AdminInviteIn(BaseModel):
    primary_contact_email: EmailStr
    legal_name: Optional[str] = None
    contact_name: Optional[str] = None
    institution_type: Literal["corporate", "personal"] = "corporate"
    message: Optional[str] = None   # optional note included in the invite email


@router.post("/admin-invite")
async def admin_invite(payload: AdminInviteIn,
                        admin=Depends(require_role("admin"))) -> dict:
    # v52cz rev8 — reject if ANY institution already registered with this
    # email in a terminal state (approved / rejected) OR in review. We only
    # reuse draft / needs_clarification rows.
    email = payload.primary_contact_email.strip().lower()
    clash = await db.escrow_institutions.find_one({
        "primary_contact_email": {"$regex": f"^{email}$", "$options": "i"},
        "status": {"$in": ["submitted", "under_review", "approved", "rejected"]},
    })
    if clash:
        raise HTTPException(status_code=409,
            detail={"error": "escrow_email_already_registered",
                     "message": f"{email} already has an institution in status "
                                f"'{clash.get('status')}'. Resend their resume "
                                f"link or ask them to use a different email.",
                     "status": clash.get("status")})
    # Dedupe: if a draft/needs_clarification record already exists for this
    # email, reuse it (reissue a magic_token) instead of creating a duplicate.
    existing = await db.escrow_institutions.find_one({
        "primary_contact_email": {"$regex": f"^{email}$", "$options": "i"},
        "status": {"$in": ["draft", "needs_clarification"]},
    })
    token = _new_token()
    if existing:
        iid = str(existing["_id"])
        await db.escrow_institutions.update_one(
            {"_id": existing["_id"]},
            {"$set": {"magic_token": token, "updated_at": now_iso(),
                      "invited_by": admin.get("email"),
                      "invited_at": now_iso()}})
        reused = True
    else:
        doc = {
            "legal_name": payload.legal_name or "",
            "primary_contact_email": email,
            "primary_contact_name": payload.contact_name or "",
            "institution_type": payload.institution_type,
            "country": "",
            "registered_address": "",
            "reg_number": "",
            "documents": {},
            "banking": [],
            "signatories": [],
            "status": "draft",
            "magic_token": token,
            "created_at": now_iso(),
            "invited_by": admin.get("email"),
            "invited_at": now_iso(),
        }
        r = await db.escrow_institutions.insert_one(doc)
        iid = str(r.inserted_id)
        reused = False

    # Fire the invite email. Degrades gracefully if email transport is down.
    sent = False
    try:
        import config
        from emails import send_email, wrap
        resume_url = f"{config.FRONTEND_URL}/escrow/resume/{token}?iid={iid}"
        kind = "trustee" if payload.institution_type == "personal" else "escrow institution"
        subject = f"PMC Managers — register as our {kind}"
        body = wrap(subject,
            f"<p>Dear {payload.contact_name or payload.legal_name or 'Partner'},</p>"
            f"<p>{admin.get('email','PMC Managers admin')} has invited you to register "
            f"as a <strong>{kind}</strong> for PMC Managers. Please click the button "
            f"below to open your private registration page.</p>"
            + (f"<p><em>{payload.message}</em></p>" if payload.message else "")
            + "<p>The link is unique to you — treat it like a password. "
              "After submitting, our team will review and come back to you.</p>",
            "Start registration", resume_url)
        await send_email(email, f"[PMC] {subject}", body)
        sent = True
    except Exception as e:
        import logging
        logging.getLogger("escrow_institutions").warning(
            "admin-invite email failed for %s: %s", email, e)

    await audit_log("escrow_inst.admin_invite", admin, "escrow_institution",
                    iid, {"email": email, "reused": reused, "email_sent": sent})
    return {"id": iid, "magic_token": token, "email_sent": sent, "reused": reused}


@router.get("")
async def list_institutions(status: Optional[Status] = None,
                              admin=Depends(require_role("admin", "reviewer"))):
    q = {"status": status} if status else {}
    items = [_out(d) async for d in db.escrow_institutions.find(q).sort("created_at", -1)]
    return {"items": items, "total": len(items)}


@router.get("/{iid}")
async def admin_get(iid: str,
                     admin=Depends(require_role("admin", "reviewer"))) -> dict:
    doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _out(doc)


@router.post("/{iid}/decision")
async def decide(iid: str, action: Literal["approve", "reject", "needs_clarification"],
                   notes: Optional[str] = None,
                   admin=Depends(require_role("admin"))):
    doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    next_status = {"approve": "approved", "reject": "rejected",
                   "needs_clarification": "needs_clarification"}[action]
    # Ensure a magic_token exists (older rows may not have one) so the
    # approval email contains a working deep-link.
    token = doc.get("magic_token") or _new_token()
    await db.escrow_institutions.update_one(
        {"_id": ObjectId(iid)},
        {"$set": {"status": next_status, "reviewed_at": now_iso(),
                  "reviewer_notes": notes, "reviewed_by": admin.get("email"),
                  "magic_token": token, "updated_at": now_iso()}})
    await audit_log(f"escrow_inst.{action}", admin, "escrow_institution", iid,
                    {"notes": notes})
    # v52d — also push an in-app notification on the owning account so the
    # bell + status banner update without waiting for email delivery.
    if doc.get("account_id"):
        try:
            from routers.escrow_accounts import notify_account
            titles = {
                "approve": "Registration approved",
                "needs_clarification": "More information needed",
                "reject": "Registration not approved",
            }
            bodies = {
                "approve": "Welcome aboard — your escrow institution is approved. "
                            "Signatories can now set passwords and sign in.",
                "needs_clarification": notes or
                    "PMC's review team has asked for more information. "
                    "Open your dashboard to resume the registration.",
                "reject": notes or
                    "After review, PMC is unable to approve this registration. "
                    "Reviewer notes are on your dashboard.",
            }
            await notify_account(doc["account_id"], action,
                                   titles[action], bodies[action],
                                   "/escrow/me")
        except Exception:
            pass
    # v51am — fire an email to the primary contact + every named signatory
    # so banks/trustees can self-serve from the moment PMC approves them.
    try:
        import config
        from emails import send_email, wrap
        recipients = {(doc.get("primary_contact_email") or "").strip().lower()}
        for s in doc.get("signatories") or []:
            if s.get("email"):
                recipients.add(s["email"].strip().lower())
        recipients.discard("")
        if action == "approve":
            # v51an — new signatories need to set a password. Deep-link to
            # the claim screen (?claim=1&iid=&token=) so they land straight on
            # the "pick a password" flow. Keep the dashboard link too for
            # anyone who's already claimed.
            claim_url = f"{config.FRONTEND_URL}/escrow/login?claim=1&iid={iid}&token={token}"
            cta_url = claim_url
            subject = f"PMC Managers — Escrow institution approved: {doc.get('legal_name')}"
            body = wrap(subject,
                f"<p>Dear {doc.get('legal_name') or 'Signatory'} team,</p>"
                f"<p>We're pleased to confirm that <strong>{doc.get('legal_name')}</strong> "
                f"has been approved as a PMC Managers escrow institution.</p>"
                f"<p>Each named signatory should click the button below and set "
                f"a password. From then on you can sign in from the main login "
                f"page under the <em>Escrow Institution</em> role to approve "
                f"EMD releases.</p>"
                f"<p>Reviewer notes: {notes or '—'}</p>",
                "Set your signatory password", cta_url)
        elif action == "needs_clarification":
            resume_url = f"{config.FRONTEND_URL}/escrow/resume/{token}?iid={iid}"
            subject = f"PMC Managers — more information needed on {doc.get('legal_name')}"
            body = wrap(subject,
                f"<p>Our review team needs a little more information before approving "
                f"<strong>{doc.get('legal_name')}</strong>.</p>"
                f"<p>Reviewer notes: {notes or 'See the registration page for details.'}</p>",
                "Open your registration", resume_url)
        else:  # reject
            subject = f"PMC Managers — Escrow institution registration update"
            body = wrap(subject,
                f"<p>Thank you for applying as a PMC Managers escrow institution.</p>"
                f"<p>After review we are unable to proceed with "
                f"<strong>{doc.get('legal_name')}</strong> at this time.</p>"
                f"<p>Reviewer notes: {notes or '—'}</p>",
                None, None)
        for to in recipients:
            await send_email(to, f"[PMC] {subject}", body)
    except Exception as e:
        import logging
        logging.getLogger("escrow_institutions").warning(
            "approval email failed for %s: %s", iid, e)
    return {"ok": True, "status": next_status, "magic_token": token}


# -------- Dashboard for the Escrow Institution portal ----------------------

@router.get("/{iid}/dashboard")
async def dashboard(iid: str, token: str) -> dict:
    """Scaffold — surfaces this institution's joint accounts and pending
    signatures. Final wiring reads from escrow_accounts + escrow_transactions
    where signatory email matches one of our registered signatories."""
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid),
                                                    "magic_token": token})
    if not inst:
        raise HTTPException(status_code=404, detail="Not found")
    emails = [s["email"].lower() for s in inst.get("signatories", [])]
    accounts = [d async for d in db.escrow_accounts.find({})
                if (d.get("escrow_officer") or {}).get("email", "").lower() in emails]
    pending_tx = [d async for d in db.escrow_transactions.find(
        {"status": {"$in": ["received", "awaiting_signatures"]}})
        if d.get("escrow_account_id") in [str(a["_id"]) for a in accounts]]
    return {"institution": {"id": str(inst["_id"]),
                             "legal_name": inst.get("legal_name"),
                             "status": inst.get("status")},
            "joint_accounts_count": len(accounts),
            "pending_signatures_count": len(pending_tx)}
