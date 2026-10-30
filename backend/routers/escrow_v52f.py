"""Escrow v52f — chart aggregation, signatory invites, PDF statements.

Three new endpoints, all stitched onto the account-first flow added in v52d.
Chart aggregation is reused by both the institution's own dashboard and the
admin cross-institution view, which is why it lives in its own router.
"""
from __future__ import annotations
import base64
import io
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import jwt
import secrets
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, EmailStr, Field

import config
from pdf_brand import logo_flowable
from audit import audit_log
from db import db
from emails import send_email, _wrap
from models.base import now_iso
from security import require_csrf, require_role
from routers.escrow_accounts import current_account

router = APIRouter(prefix="/api/v1/escrow-accounts", tags=["escrow-accounts-v52f"])
admin_router = APIRouter(prefix="/api/v1/escrow/admin", tags=["escrow-admin-v52f"])


# ---------- Shared chart aggregator ---------------------------------------

async def _month_series(filt: dict, months: int = 12) -> List[Dict[str, Any]]:
    """Returns 12 (default) rolling months of {month, volume_by_currency} for
    escrow_transactions matching `filt`. Volume is sum(amount)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=31 * months)).isoformat()
    filt = {**filt, "created_at": {"$gte": cutoff}}
    buckets: Dict[str, Dict[str, float]] = {}
    async for t in db.escrow_transactions.find(filt):
        created = t.get("created_at")
        if not created:
            continue
        m = str(created)[:7]  # YYYY-MM
        cur = (t.get("currency") or "USD").upper()
        amt = float(t.get("amount") or 0)
        buckets.setdefault(m, {})
        buckets[m][cur] = buckets[m].get(cur, 0) + amt
    out: List[Dict[str, Any]] = []
    today = datetime.now(timezone.utc)
    for i in range(months - 1, -1, -1):
        d = (today - timedelta(days=31 * i))
        m = d.strftime("%Y-%m")
        out.append({"month": m, "volume_by_currency": buckets.get(m, {})})
    return out


async def _resolve_joint_account_ids(institution_id: str) -> List[str]:
    """Joint escrow_accounts whose officer email matches one of this
    institution's named signatories."""
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(institution_id)})
    if not inst:
        return []
    emails = {(s.get("email") or "").lower()
              for s in (inst.get("signatories") or []) if s.get("email")}
    if not emails:
        return []
    ids: List[str] = []
    async for a in db.escrow_accounts.find({}):
        officer = ((a.get("escrow_officer") or {}).get("email") or "").lower()
        if officer and officer in emails:
            ids.append(str(a["_id"]))
    return ids


# ---------- Institution-scoped chart --------------------------------------

@router.get("/me/chart")
async def my_chart(months: int = 12, account_id: Optional[str] = None,
                     acc=Depends(current_account)) -> Dict[str, Any]:
    """Returns up-to `months` of transaction volume for this institution.
    `account_id`:
      - omitted / "all"  → every joint account the institution's signatories operate
      - specific id      → just that joint account (must belong to the institution)"""
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    iid = full.get("institution_id")
    if not iid:
        return {"series": [], "accounts": []}
    joint_ids = await _resolve_joint_account_ids(iid)
    accounts_meta: List[Dict[str, Any]] = []
    async for a in db.escrow_accounts.find(
            {"_id": {"$in": [ObjectId(i) for i in joint_ids]}}):
        accounts_meta.append({
            "id": str(a["_id"]), "name": a.get("name"),
            "currency": a.get("currency"),
        })
    if account_id and account_id != "all":
        if account_id not in joint_ids:
            raise HTTPException(status_code=403,
                detail="This joint account is not operated by your institution")
        filt_ids = [account_id]
    else:
        filt_ids = joint_ids
    series = await _month_series(
        {"escrow_account_id": {"$in": filt_ids}} if filt_ids
        else {"_impossible_": True},
        months=max(3, min(months, 24)))
    return {"series": series, "accounts": accounts_meta,
             "institution": {"id": iid}}


# ---------- Admin cross-institution chart ---------------------------------

@admin_router.get("/chart")
async def admin_chart(months: int = 12,
                       institution_ids: Optional[str] = Query(default=None,
                           description="Comma-separated institution ids. Omit for ALL."),
                       admin=Depends(require_role("admin", "reviewer"))) -> Dict[str, Any]:
    """Admin view: chart across every escrow institution or a chosen subset.
    Returns `institutions` list so the UI can offer a multi-select filter."""
    inst_filter: Dict[str, Any] = {}
    if institution_ids:
        try:
            ids = [ObjectId(i.strip()) for i in institution_ids.split(",") if i.strip()]
            inst_filter["_id"] = {"$in": ids}
        except Exception:
            raise HTTPException(status_code=422, detail="Bad institution_ids")
    insts: List[Dict[str, Any]] = []
    all_joint_ids: List[str] = []
    async for d in db.escrow_institutions.find(inst_filter):
        joint = await _resolve_joint_account_ids(str(d["_id"]))
        all_joint_ids.extend(joint)
        insts.append({
            "id": str(d["_id"]), "legal_name": d.get("legal_name"),
            "status": d.get("status"), "joint_account_count": len(joint),
        })
    series = await _month_series(
        {"escrow_account_id": {"$in": all_joint_ids}} if all_joint_ids
        else {"_impossible_": True},
        months=max(3, min(months, 24)))
    # Flat list of every institution (for the multi-select source), even when
    # a filter is active, so the UI knows the full option set.
    all_opts: List[Dict[str, Any]] = []
    async for d in db.escrow_institutions.find(
            {"status": {"$in": ["approved", "changes_requested"]}}):
        all_opts.append({"id": str(d["_id"]),
                           "legal_name": d.get("legal_name")})
    return {"series": series, "institutions": insts,
             "all_approved": all_opts}


# ---------- Signatory invite (post-approval only) -------------------------

class SignatoryInviteIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    designation: str = Field(min_length=2, max_length=120)
    email: EmailStr
    # v52k — international format enforced; the UI pairs a country dropdown
    # with digit-count validation before anything reaches this endpoint.
    phone: Optional[str] = Field(default=None,
                                  pattern=r"^\+\d{1,4}\s?\d{5,15}$")


@router.post("/me/signatories/invite", dependencies=[Depends(require_csrf)])
async def invite_signatory(payload: SignatoryInviteIn,
                             acc=Depends(current_account)) -> Dict[str, Any]:
    """Primary contact adds a signatory to their approved institution. Fires
    the password-claim email immediately. Pre-approval invites are rejected
    (per user choice: 'Enable invites only after approval')."""
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    iid = full.get("institution_id")
    if not iid:
        raise HTTPException(status_code=400,
            detail="Your institution record is missing — contact support.")
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    if inst.get("status") != "approved":
        raise HTTPException(status_code=403,
            detail={"error": "not_approved",
                     "message": "Signatory invites unlock after PMC approves "
                                "your institution. Current status: "
                                f"{inst.get('status')}."})
    email_lc = payload.email.lower().strip()
    # Reject duplicate against existing signatory list.
    for s in inst.get("signatories") or []:
        if (s.get("email") or "").lower() == email_lc:
            raise HTTPException(status_code=409,
                detail=f"{payload.email} is already a signatory.")
    new_row = {
        "name": payload.name.strip(),
        "designation": payload.designation.strip(),
        "email": payload.email,
        "phone": (payload.phone or "").strip() or None,
        "invited_at": now_iso(),
        "invited_by": full.get("email"),
    }
    await db.escrow_institutions.update_one(
        {"_id": inst["_id"]},
        {"$push": {"signatories": new_row},
          "$set": {"magic_token": inst.get("magic_token") or secrets.token_urlsafe(32),
                    "updated_at": now_iso()}})
    inst = await db.escrow_institutions.find_one({"_id": inst["_id"]})
    # Fire the claim email (same deep-link format as the approval email).
    claim_url = (f"{config.FRONTEND_URL}/escrow/login?claim=1"
                 f"&iid={iid}&token={inst['magic_token']}")
    html = _wrap(
        f"PMC Managers — set your signatory password",
        f"<p>Dear {payload.name},</p>"
        f"<p><strong>{inst.get('legal_name')}</strong> has added you as a "
        f"signatory on their PMC Managers escrow institution record. "
        f"Click the button below to set a password; from then on you can "
        f"sign in from the main login page and co-sign EMD releases on "
        f"the institution's joint accounts.</p>"
        f"<p>Invited by: {full.get('email')}</p>",
        "Set your signatory password", claim_url,
    )
    try:
        await send_email(payload.email,
                           f"PMC Escrow · set your signatory password",
                           html)
    except Exception:
        pass
    await audit_log("escrow_inst.signatory_invite", None, "escrow_institution",
                     iid, {"email": payload.email})
    return {"ok": True, "signatory": new_row}


# ---------- PDF statement -------------------------------------------------

def _render_statement_pdf(institution: dict, account: dict,
                            rows: List[dict]) -> bytes:
    """ReportLab statement — simple, auditable, one page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                      Table, TableStyle)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=18 * mm, rightMargin=18 * mm,
                             topMargin=18 * mm, bottomMargin=18 * mm,
                             title=f"Statement · {account.get('name')}")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=18,
                            textColor=colors.HexColor("#0F3B2E"))
    meta = ParagraphStyle("m", parent=styles["Normal"], fontSize=9,
                           textColor=colors.HexColor("#5A5A57"))
    story = [
        logo_flowable(),
        Paragraph("PMC Managers · Escrow statement", title),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>{institution.get('legal_name','—')}</b>", styles["Normal"]),
        Paragraph(f"Joint account: <b>{account.get('name','—')}</b> · "
                   f"{account.get('account_no','—')} · {account.get('currency','—')}",
                   meta),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                   meta),
        Spacer(1, 6 * mm),
    ]
    if not rows:
        story.append(Paragraph("No transactions recorded on this account yet.",
                                 styles["Normal"]))
    else:
        data = [["Date", "Bid", "Vendor", "Amount", "Currency", "Status", "PMC", "Us"]]
        total = 0.0
        for r in rows:
            data.append([
                str(r.get("created_at") or "")[:10],
                r.get("bid_ref") or "—",
                r.get("vendor_ref") or "—",
                f"{(r.get('amount') or 0):,.2f}",
                r.get("currency") or "—",
                r.get("status") or "—",
                "✓" if r.get("signed_by_pmc") else "·",
                "✓" if r.get("signed_by_institution") else "·",
            ])
            total += float(r.get("amount") or 0)
        data.append(["", "", "Total", f"{total:,.2f}", "", "", "", ""])
        t = Table(data, colWidths=[22 * mm, 28 * mm, 28 * mm, 24 * mm,
                                     18 * mm, 24 * mm, 10 * mm, 10 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3EFE4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F3B2E")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B08E4A")),
            ("ALIGN", (3, 1), (3, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        story.append(t)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("This statement is hash-chained to the PMC audit "
                             "ledger. Report discrepancies to support@pmcmanagers.com.",
                             meta))
    doc.build(story)
    return buf.getvalue()


async def _resolve_statement_rows(account_id: str) -> List[dict]:
    rows: List[dict] = []
    async for t in db.escrow_transactions.find({"escrow_account_id": account_id}
                                                 ).sort("created_at", -1).limit(500):
        sigs = t.get("signatures") or {}
        rows.append({
            "created_at": t.get("created_at"),
            "bid_ref": t.get("bid_ref"),
            "vendor_ref": t.get("vendor_ref"),
            "amount": t.get("amount"),
            "currency": t.get("currency"),
            "status": t.get("status"),
            "signed_by_pmc": bool((sigs.get("pmc") or {}).get("signed_at")),
            "signed_by_institution": bool(
                (sigs.get("escrow_institution") or {}).get("signed_at")),
        })
    return rows


@router.get("/me/joint-accounts/{aid}/statement.pdf")
async def joint_account_statement(aid: str, email_me: bool = False,
                                     acc=Depends(current_account)):
    """PDF statement for a joint account. If `email_me=1`, also sends the
    PDF to the primary contact as an attachment."""
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    iid = full.get("institution_id")
    if not iid:
        raise HTTPException(status_code=404, detail="No institution")
    joint = await _resolve_joint_account_ids(iid)
    if aid not in joint:
        raise HTTPException(status_code=403,
            detail="This joint account is not operated by your institution")
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    acct = await db.escrow_accounts.find_one({"_id": ObjectId(aid)})
    rows = await _resolve_statement_rows(aid)
    pdf = _render_statement_pdf(inst, acct, rows)
    filename = f"statement-{(acct.get('name') or 'account').replace(' ', '_')}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    if email_me:
        html = _wrap("Your escrow statement",
            f"<p>Dear {inst.get('legal_name')} team,</p>"
            f"<p>Attached is your statement for joint account "
            f"<strong>{acct.get('name')}</strong> ({acct.get('account_no')}, "
            f"{acct.get('currency')}) generated on "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}. "
            f"{len(rows)} transaction(s) covered.</p>",
            "Open your dashboard", f"{config.FRONTEND_URL}/escrow/me")
        try:
            await send_email(full.get("email"),
                               f"PMC Escrow · statement for {acct.get('name')}", html,
                               attachments=[{
                                   "filename": filename,
                                   "content_b64": base64.b64encode(pdf).decode(),
                                   "content_type": "application/pdf",
                               }])
        except Exception:
            pass
    await audit_log("escrow_inst.statement_pdf", None, "escrow_institution",
                     iid, {"account": aid, "emailed": bool(email_me),
                            "rows": len(rows)})
    from fastapi.responses import Response
    return Response(content=pdf, media_type="application/pdf",
                     headers={"Content-Disposition":
                              f'attachment; filename="{filename}"'})
