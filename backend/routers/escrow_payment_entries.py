"""Escrow payment entries + per-transaction DocuSign envelopes — v54a.

A single escrow transaction (ledger row) can accrue multiple **payment
entries** over its lifetime:

    direction  kind              description
    ---------  ----------------  --------------------------------------
    in         emd_in            EMD received from bidder (confirmation)
    out        release_out       released to vendor / contractor
    out        refund_out        refunded to bidder (lost / cancelled)
    out        fee_out           bank / escrow fees deducted

Every entry carries a proof upload (receipt / wire slip / bank screenshot)
and requires BOTH signatures (PMC officer + Institution officer) before
it is considered posted. Signing is always done through DocuSign per the
2026-02 scope decision — admin issues the envelope, institution officer
clicks a hosted DocuSign link and signs.

The admin console also has a shortcut to send a DocuSign envelope on the
TRANSACTION itself (not just a payment entry) which is what the user sees
on their escrow institution dashboard as "a document to sign".
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/escrow", tags=["escrow-payment-entries"])


# ---------------- Models ----------------

PE_DIRECTION = Literal["in", "out"]
PE_KIND = Literal["emd_in", "release_out", "refund_out", "fee_out"]
PE_STATUS = Literal["pending_signatures", "fully_signed", "rejected", "void"]


class PaymentEntryIn(BaseModel):
    transaction_id: str
    direction: PE_DIRECTION
    kind: PE_KIND
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=5)
    dated_on: Optional[str] = Field(None, description="ISO date, defaults to now")
    bank_reference: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    notes: Optional[str] = None
    # Base64 data URL (data:application/pdf;base64,...) for a proof slip.
    # Small files only — frontend enforces 2 MB max. Larger uploads should
    # go through /api/v1/uploads/direct and the key stored in proof_key.
    proof_data_url: Optional[str] = None
    proof_filename: Optional[str] = None
    proof_key: Optional[str] = None  # if uploaded via uploads router first


class SignPaymentEntryIn(BaseModel):
    action: Literal["approve", "reject"] = "approve"
    comment: Optional[str] = None


# ---------------- Helpers ----------------

def _out_pe(d: dict) -> dict:
    out = {k: v for k, v in d.items() if k != "_id"}
    out["id"] = str(d["_id"])
    return out


async def _load_tx(tid: str) -> dict:
    if not ObjectId.is_valid(tid):
        raise HTTPException(400, "Invalid transaction id")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return tx


def _resolve_signer_side(email: str, acc_snap: dict) -> Optional[str]:
    pmc_email = ((acc_snap.get("pmc_officer") or {}).get("email") or "").lower()
    esc_email = ((acc_snap.get("escrow_officer") or {}).get("email") or "").lower()
    e = (email or "").lower()
    if e and e == pmc_email: return "pmc"
    if e and e == esc_email: return "escrow_institution"
    return None


async def _maybe_finalise(pe_id: ObjectId) -> dict:
    """Mark fully_signed when both officers signed `approve`. Return the
    updated row."""
    pe = await db.escrow_payment_entries.find_one({"_id": pe_id})
    if not pe:
        raise HTTPException(404, "Payment entry not found")
    sigs = pe.get("signatures") or {}
    pmc = sigs.get("pmc") or {}
    esc = sigs.get("escrow_institution") or {}
    new_status = pe.get("status") or "pending_signatures"
    if pmc.get("action") == "approve" and esc.get("action") == "approve" \
            and pmc.get("signed_at") and esc.get("signed_at"):
        new_status = "fully_signed"
    if pmc.get("action") == "reject" or esc.get("action") == "reject":
        new_status = "rejected"
    if new_status != pe.get("status"):
        await db.escrow_payment_entries.update_one(
            {"_id": pe_id},
            {"$set": {"status": new_status, "updated_at": now_iso()}})
        pe["status"] = new_status
    return pe


# ---------------- Admin: payment entries ----------------

@router.get("/transactions/{tid}/payment-entries")
async def list_payment_entries(
    tid: str,
    admin=Depends(require_role("admin", "accounting", "reviewer", "escrow_agent")),
):
    tx = await _load_tx(tid)
    out: List[Dict[str, Any]] = []
    async for d in db.escrow_payment_entries.find(
        {"transaction_id": tid}
    ).sort("created_at", -1):
        out.append(_out_pe(d))
    return {
        "items": out,
        "transaction": {
            "id": str(tx["_id"]),
            "bid_ref": tx.get("bid_ref"),
            "amount": tx.get("amount"),
            "currency": tx.get("currency"),
            "status": tx.get("status"),
            "escrow_account_snapshot": tx.get("escrow_account_snapshot"),
        },
    }


@router.post("/payment-entries")
async def create_payment_entry(
    payload: PaymentEntryIn,
    admin=Depends(require_role("admin", "accounting")),
):
    tx = await _load_tx(payload.transaction_id)
    doc = {
        "transaction_id": payload.transaction_id,
        "escrow_account_id": tx.get("escrow_account_id"),
        "escrow_account_snapshot": tx.get("escrow_account_snapshot"),
        "bid_ref": tx.get("bid_ref"),
        "notice_ref": tx.get("notice_ref"),
        "direction": payload.direction,
        "kind": payload.kind,
        "amount": payload.amount,
        "currency": payload.currency.upper(),
        "dated_on": payload.dated_on or now_iso(),
        "bank_reference": payload.bank_reference,
        "counterparty_name": payload.counterparty_name,
        "counterparty_account": payload.counterparty_account,
        "notes": payload.notes,
        "proof": {
            "data_url": payload.proof_data_url,
            "filename": payload.proof_filename,
            "key": payload.proof_key,
        } if (payload.proof_data_url or payload.proof_key) else None,
        "signatures": {},
        "status": "pending_signatures",
        "audit_trail": [{
            "at": now_iso(),
            "by": admin.get("email"),
            "event": "created",
            "source": "admin",
        }],
        "docusign_envelope_id": None,
        "created_at": now_iso(),
        "created_by": admin.get("email"),
        "created_by_role": "admin",
    }
    r = await db.escrow_payment_entries.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log(
        "escrow.payment_entry_create", admin, "escrow_payment_entry",
        str(r.inserted_id),
        {"tx_id": payload.transaction_id, "kind": payload.kind,
         "amount": payload.amount, "currency": payload.currency},
    )
    return _out_pe(doc)


@router.post("/payment-entries/{peid}/sign")
async def admin_sign_payment_entry(
    peid: str, payload: SignPaymentEntryIn,
    admin=Depends(require_role("admin", "accounting", "escrow_agent")),
):
    if not ObjectId.is_valid(peid):
        raise HTTPException(400, "Invalid payment entry id")
    pe = await db.escrow_payment_entries.find_one({"_id": ObjectId(peid)})
    if not pe:
        raise HTTPException(404, "Payment entry not found")
    if pe.get("status") in ("fully_signed", "rejected", "void"):
        raise HTTPException(409, f"Payment entry already {pe.get('status')}")
    side = _resolve_signer_side(admin.get("email"), pe.get("escrow_account_snapshot") or {})
    if not side:
        raise HTTPException(
            403,
            "You are not registered as an officer on this escrow account. "
            "Only the PMC or Institution officer on the joint account can "
            "sign this payment entry.",
        )
    signatures = pe.get("signatures") or {}
    signatures[side] = {
        "email": admin.get("email"),
        "action": payload.action,
        "comment": payload.comment,
        "signed_at": now_iso(),
        "via": "admin_portal",
    }
    trail = pe.get("audit_trail") or []
    trail.append({
        "at": now_iso(), "by": admin.get("email"),
        "event": f"signed_{side}", "action": payload.action,
        "comment": payload.comment, "via": "admin_portal",
    })
    await db.escrow_payment_entries.update_one(
        {"_id": ObjectId(peid)},
        {"$set": {"signatures": signatures, "audit_trail": trail,
                   "updated_at": now_iso()}},
    )
    pe = await _maybe_finalise(ObjectId(peid))
    await audit_log("escrow.payment_entry_sign", admin, "escrow_payment_entry",
                    peid, {"side": side, "action": payload.action})
    return _out_pe(pe)


@router.post("/payment-entries/{peid}/void")
async def void_payment_entry(
    peid: str, admin=Depends(require_role("admin")),
):
    if not ObjectId.is_valid(peid):
        raise HTTPException(400, "Invalid payment entry id")
    pe = await db.escrow_payment_entries.find_one({"_id": ObjectId(peid)})
    if not pe:
        raise HTTPException(404, "Payment entry not found")
    if pe.get("status") == "fully_signed":
        raise HTTPException(409, "Cannot void a fully signed entry")
    trail = pe.get("audit_trail") or []
    trail.append({"at": now_iso(), "by": admin.get("email"),
                   "event": "voided", "via": "admin_portal"})
    await db.escrow_payment_entries.update_one(
        {"_id": ObjectId(peid)},
        {"$set": {"status": "void", "audit_trail": trail,
                   "updated_at": now_iso()}})
    await audit_log("escrow.payment_entry_void", admin,
                    "escrow_payment_entry", peid, {})
    return _out_pe(await db.escrow_payment_entries.find_one({"_id": ObjectId(peid)}))


# ---------------- DocuSign envelope on an escrow transaction ----------------

def _build_tx_pdf(tx: dict) -> bytes:
    """Build a one-page PDF summarising the escrow transaction with signature
    anchors for 2 signers. Uses ReportLab (already in requirements)."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    snap = tx.get("escrow_account_snapshot") or {}
    pmc = snap.get("pmc_officer") or {}
    esc = snap.get("escrow_officer") or {}

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Escrow EMD Receipt — PMC Managers")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>PMC Managers · Escrow EMD Receipt &amp; Release Mandate</b>", styles["Title"]),
        Spacer(1, 10),
        Paragraph(
            f"This document records receipt of Earnest Money Deposit (EMD) "
            f"against bid <b>{tx.get('bid_ref')}</b> on tender "
            f"<b>{tx.get('notice_ref') or '—'}</b>, held in the joint escrow "
            f"account <b>{snap.get('name') or '—'}</b> at "
            f"<b>{snap.get('institution') or '—'}</b> (account "
            f"<b>{snap.get('account_no') or '—'}</b>). Both named officers must "
            f"sign below to authorise the release workflow.", styles["BodyText"]),
        Spacer(1, 10),
        Table([
            ["Bid ref", tx.get("bid_ref") or "—"],
            ["Notice", tx.get("notice_ref") or "—"],
            ["Vendor", tx.get("vendor_ref") or "—"],
            ["Amount", f"{tx.get('amount')} {tx.get('currency')}"],
            ["Received at", (tx.get("received_at") or "")[:19].replace("T", " ") or "—"],
            ["Bank reference / UTR", tx.get("reference") or "—"],
            ["Current status", tx.get("status") or "—"],
        ], colWidths=[140, 320], style=TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ])),
        Spacer(1, 20),
        Paragraph(
            "<b>Officer declarations.</b> By signing below each officer confirms "
            "receipt/release of the stated amount from/to the counterparty on "
            "record, under the joint-control governance of this escrow account.",
            styles["BodyText"]),
        Spacer(1, 30),
        Table([
            ["PMC officer", "Institution officer"],
            [f"{pmc.get('name') or '—'}\n{pmc.get('email') or '—'}",
             f"{esc.get('name') or '—'}\n{esc.get('email') or '—'}"],
            ["/pmc_sig/\n\n", "/esc_sig/\n\n"],
            ["Date: /pmc_date/", "Date: /esc_date/"],
        ], colWidths=[240, 240], style=TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 2), (-1, 2), [colors.whitesmoke]),
            ("ROWBACKGROUNDS", (0, 0), (-1, 0), [colors.lightgrey]),
            ("MINROWHEIGHT", (0, 2), (-1, 2), 60),
        ])),
    ]
    doc.build(story)
    return buf.getvalue()


@router.post("/transactions/{tid}/docusign")
async def create_tx_docusign_envelope(
    tid: str,
    admin=Depends(require_role("admin")),
):
    """Admin issues a 2-signer DocuSign envelope on an escrow transaction.
    Signers: PMC officer + Institution officer recorded on the account
    snapshot. Delivery is email-mode (DocuSign hosts the signing session),
    so the institution officer sees it in both their email inbox AND in the
    "Pending signatures" section of their PMC escrow dashboard, where a
    Open in DocuSign button pulls a one-time recipient view URL."""
    tx = await _load_tx(tid)
    if tx.get("status") in ("released_to_contractor", "released_to_vendor",
                             "forfeited", "cancelled"):
        raise HTTPException(409, f"Transaction already {tx['status']}")
    snap = tx.get("escrow_account_snapshot") or {}
    pmc = snap.get("pmc_officer") or {}
    esc = snap.get("escrow_officer") or {}
    if not (pmc.get("email") and esc.get("email")):
        raise HTTPException(
            400,
            "Both PMC officer and Escrow institution officer must be set on "
            "the joint account before issuing a DocuSign envelope.",
        )
    if pmc["email"].lower() == esc["email"].lower():
        raise HTTPException(
            400,
            "PMC officer and Escrow officer share the same email — DocuSign "
            "needs two independent signers. Fix the joint account first.",
        )
    # Import lazily to avoid DocuSign SDK init cost at module load.
    try:
        import docusign_esign as ds
        from routers.docusign import _client, DS_ACCOUNT_ID
    except Exception as e:
        raise HTTPException(503, f"DocuSign SDK not available: {e}")
    pdf = _build_tx_pdf(tx)
    try:
        client = _client()
    except HTTPException as e:
        # Normalise consent/auth failures to a 503 so clients can treat
        # "no DocuSign in this environment" identically regardless of
        # whether the SDK is missing, consent is pending or JWT auth fails.
        if 400 <= (e.status_code or 0) < 500:
            raise HTTPException(503, "DocuSign is not configured in this "
                                      "environment — contact platform admin.")
        raise
    import base64 as _b64
    document = ds.Document(
        document_base64=_b64.b64encode(pdf).decode("ascii"),
        name=f"PMC-ESCROW-{tx.get('bid_ref') or tid}.pdf",
        file_extension="pdf",
        document_id="1",
    )
    pmc_signer = ds.Signer(
        email=pmc["email"], name=pmc.get("name") or pmc["email"],
        recipient_id="1", routing_order="1",
        tabs=ds.Tabs(
            sign_here_tabs=[ds.SignHere(
                anchor_string="/pmc_sig/", anchor_units="pixels",
                anchor_y_offset="-6", recipient_id="1", document_id="1")],
            date_signed_tabs=[ds.DateSigned(
                anchor_string="/pmc_date/", anchor_units="pixels",
                anchor_y_offset="-6", recipient_id="1", document_id="1")],
        ),
    )
    esc_signer = ds.Signer(
        email=esc["email"], name=esc.get("name") or esc["email"],
        recipient_id="2", routing_order="1",
        tabs=ds.Tabs(
            sign_here_tabs=[ds.SignHere(
                anchor_string="/esc_sig/", anchor_units="pixels",
                anchor_y_offset="-6", recipient_id="2", document_id="1")],
            date_signed_tabs=[ds.DateSigned(
                anchor_string="/esc_date/", anchor_units="pixels",
                anchor_y_offset="-6", recipient_id="2", document_id="1")],
        ),
    )
    envelope = ds.EnvelopeDefinition(
        email_subject=f"PMC Escrow — signature required for {tx.get('bid_ref')}",
        email_blurb="Please review and sign the EMD escrow receipt & release mandate.",
        documents=[document],
        recipients=ds.Recipients(signers=[pmc_signer, esc_signer]),
        status="sent",
    )
    envelopes = ds.EnvelopesApi(client)
    try:
        result = envelopes.create_envelope(DS_ACCOUNT_ID, envelope_definition=envelope)
        envelope_id = result.envelope_id
    except Exception as e:
        raise HTTPException(502, f"DocuSign envelope create failed: {e}")
    # Persist the envelope row for status mirroring + lookups.
    env_doc = {
        "envelope_id": envelope_id,
        "kind": "escrow_tx",
        "sub_kind": "escrow_receipt",
        "escrow_transaction_id": tid,
        "bid_id": None,
        "bid_ref": tx.get("bid_ref"),
        "status": "sent",
        "signers": [
            {"side": "pmc", "name": pmc_signer.name, "email": pmc_signer.email,
             "recipient_id": "1"},
            {"side": "escrow_institution", "name": esc_signer.name,
             "email": esc_signer.email, "recipient_id": "2"},
        ],
        "created_at": now_iso(),
        "created_by": admin.get("email"),
    }
    await db.docusign_envelopes.insert_one(env_doc)
    await db.escrow_transactions.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {"docusign_envelope_id": envelope_id,
                   "docusign_status": "sent",
                   "updated_at": now_iso()},
         "$push": {"audit_trail": {
             "at": now_iso(), "by": admin.get("email"),
             "event": "docusign_envelope_sent",
             "envelope_id": envelope_id,
             "signers": [pmc_signer.email, esc_signer.email],
         }}},
    )
    await audit_log("escrow.docusign_envelope_sent", admin,
                    "escrow_tx", tid,
                    {"envelope_id": envelope_id,
                     "pmc": pmc_signer.email, "institution": esc_signer.email})
    return {"envelope_id": envelope_id, "status": "sent",
            "signers": env_doc["signers"]}


@router.get("/transactions/{tid}/docusign-url")
async def get_tx_docusign_url(
    tid: str,
    side: Literal["pmc", "escrow_institution"] = "pmc",
    admin=Depends(require_role("admin", "accounting", "reviewer", "escrow_agent")),
):
    """Return a one-time DocuSign recipient view URL for the requested side.
    Admin-only; the institution has its own portal-scoped sibling endpoint
    in escrow_accounts."""
    tx = await _load_tx(tid)
    env_id = tx.get("docusign_envelope_id")
    if not env_id:
        raise HTTPException(404, "No DocuSign envelope on this transaction")
    row = await db.docusign_envelopes.find_one({"envelope_id": env_id})
    if not row:
        raise HTTPException(404, "Envelope row missing")
    signer = None
    for s in (row.get("signers") or []):
        if s.get("side") == side:
            signer = s; break
    if not signer:
        raise HTTPException(400, f"No signer on side {side}")
    try:
        import docusign_esign as ds
        from routers.docusign import _client, DS_ACCOUNT_ID
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        # Email-flow envelopes do NOT carry a client_user_id, so recipient
        # view URLs cannot be minted; instead redirect to the DocuSign
        # hosted signing session URL via the envelope's console view, or
        # tell the operator to use the emailed link. We attempt console
        # view and fall back to a message.
        view = envelopes.create_console_view(DS_ACCOUNT_ID,
            console_view_request=ds.ConsoleViewRequest(
                envelope_id=env_id, return_url=f"{config.FRONTEND_URL}/admin"))
        return {"url": view.url, "mode": "console"}
    except Exception as e:
        # v54a — degrade gracefully: email-mode envelopes always ship the
        # hosted-signing link directly to both officers' inboxes, so the
        # console-view is only a convenience, never a hard failure.
        import logging; logging.getLogger("escrow").info(
            "admin docusign-url fallback for %s: %s", env_id, e)
        return {"url": None, "envelope_id": env_id, "mode": "email_only",
                "message": "DocuSign emailed the hosted-signing link to both "
                           "officers when the envelope was issued. Ask the "
                           "officer to open that email to sign."}
