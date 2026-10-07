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
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import db
from security import require_role
from audit import audit_log
from models.base import now_iso

router = APIRouter(prefix="/api/v1/escrow-institutions", tags=["escrow-institutions"])

Status = Literal["draft", "submitted", "under_review", "needs_clarification",
                 "approved", "rejected"]


class Signatory(BaseModel):
    name: str
    designation: str
    email: EmailStr
    phone: Optional[str] = None
    passport_or_id_key: Optional[str] = None     # upload key for photo ID
    specimen_signature_key: Optional[str] = None


class BankingCoord(BaseModel):
    account_name: str
    account_number: str
    iban: Optional[str] = None
    swift: Optional[str] = None
    currency: str = "USD"
    institution_name: str
    branch: Optional[str] = None
    correspondent_bank: Optional[str] = None
    settlement_cutoff: Optional[str] = None       # free-text TZ-aware, e.g. "16:00 UK"


class EscrowInstitutionIn(BaseModel):
    legal_name: str
    trading_name: Optional[str] = None
    country: str
    registered_address: str
    reg_number: str                                # company / trust registration no.
    tax_id: Optional[str] = None
    gst_or_vat: Optional[str] = None
    regulator: Optional[str] = None               # issuing authority
    licence_number: Optional[str] = None
    licence_expiry: Optional[str] = None          # ISO date
    website: Optional[str] = None
    primary_contact_email: EmailStr
    primary_contact_phone: Optional[str] = None
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

@router.post("/register")
async def register_institution(payload: EscrowInstitutionIn) -> dict:
    """Public self-registration — creates a draft that the institution
    continues to fill via the returned magic link, then submits for review."""
    doc = payload.model_dump()
    doc["status"] = "draft"
    doc["magic_token"] = _new_token()
    doc["created_at"] = now_iso()
    r = await db.escrow_institutions.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log("escrow_inst.register", None, "escrow_institution",
                    str(r.inserted_id), {"email": payload.primary_contact_email})
    return {"id": str(r.inserted_id),
            "magic_token": doc["magic_token"],
            "status": "draft"}


@router.get("/resume/{token}")
async def resume(token: str) -> dict:
    doc = await db.escrow_institutions.find_one({"magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    return _out(doc)


@router.patch("/{iid}")
async def update_institution(iid: str, payload: EscrowInstitutionIn,
                              token: str) -> dict:
    doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid),
                                                   "magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc["status"] not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=400,
            detail=f"Cannot edit — status is {doc['status']}")
    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = now_iso()
    await db.escrow_institutions.update_one({"_id": ObjectId(iid)}, {"$set": updates})
    return _out(await db.escrow_institutions.find_one({"_id": ObjectId(iid)}))


@router.post("/{iid}/submit")
async def submit(iid: str, token: str) -> dict:
    doc = await db.escrow_institutions.find_one({"_id": ObjectId(iid),
                                                   "magic_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
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
        {"$set": {"status": "submitted", "updated_at": now_iso()}})
    await audit_log("escrow_inst.submit", None, "escrow_institution", iid, {})
    return {"ok": True, "status": "submitted"}


# -------- Admin endpoints ---------------------------------------------------

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
