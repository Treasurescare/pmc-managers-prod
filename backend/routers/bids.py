"""Bid workflow router — Wave 1.

Vendors submit bids on published notices; each bid moves through the sequential
approval pipeline: emd_paid → escrow_accepted → admin_flagged → certifier_cleared
→ legal_cleared → accounting_cleared → committee_review → awarded/rejected.
"""
from typing import Optional, List
from datetime import datetime, timezone
import os
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

import config
from db import db, next_sequence
from models.bid import BidCreateIn, BidUpdateIn, BidDecisionIn
from models.emd_payment import EMDConfig
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/bids", tags=["bids"])


# Wave 39 — Two-Cover enforcement.
# Roles that must NEVER see commercial fields until finance envelope is opened.
_TECH_ONLY_ROLES = {"tech_evaluator", "technical_evaluator"}
# Roles that may always see the commercial cover (finance / audit / admin).
_FINANCE_ROLES = {"admin", "accounting", "auditor", "committee_member"}


def _redact_commercial(doc: dict, viewer_roles: set) -> dict:
    """Drop `price_amount`, `commercial_notes` and `kind=='commercial'` docs
    for tech-only evaluators, and also whenever the financial envelope has
    not yet been opened (unless the viewer holds a finance-cleared role)."""
    is_tech_only = bool(viewer_roles & _TECH_ONLY_ROLES) and not (viewer_roles & _FINANCE_ROLES)
    fin_open = bool(doc.get("financial_opened_at"))
    finance_role = bool(viewer_roles & _FINANCE_ROLES)
    if is_tech_only or (not fin_open and not finance_role):
        doc = dict(doc)
        doc["price_amount"] = None
        doc["price_currency"] = None
        doc["commercial_notes"] = None
        doc["documents"] = [d for d in (doc.get("documents") or []) if d.get("kind") != "commercial"]
        doc["commercial_redacted"] = True
    return doc


def _viewer_role_set(user: dict) -> set:
    r = set()
    if user:
        if user.get("role"):
            r.add(user["role"])
        r.update(user.get("roles") or [])
    return r


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


_MIME_BY_EXT = {
    ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
    ".bmp": "image/bmp", ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def _enrich_docs(doc: dict) -> dict:
    """v47h — attach a servable url + mime to every stored bid document so
    admin/vendor detail views can open, preview and download the vendor's
    actual uploads (older rows only stored the storage key, never the url)."""
    docs = doc.get("documents") or []
    if not docs:
        return doc
    keys = [d.get("key") for d in docs if d.get("key")]
    mime_by_key = {}
    if keys:
        async for u in db.uploads.find({"key": {"$in": keys}}, {"key": 1, "content_type": 1}):
            mime_by_key[u["key"]] = u.get("content_type")
    enriched = []
    for d in docs:
        d = dict(d)
        k = d.get("key")
        if k and not d.get("url"):
            d["url"] = f"/api/v1/uploads/files/{k}"
        if not d.get("mime"):
            ext = os.path.splitext((d.get("filename") or d.get("name") or "").lower())[1]
            d["mime"] = mime_by_key.get(k) or _MIME_BY_EXT.get(ext) or ""
        enriched.append(d)
    doc = dict(doc)
    doc["documents"] = enriched
    return doc


# ---------- Vendor endpoints ----------

@router.post("")
async def create_bid(payload: BidCreateIn, vendor=Depends(current_vendor)) -> dict:
    """Vendor creates a bid draft against a published notice."""
    notice = await db.notices.find_one({"notice_ref": payload.notice_ref, "is_published": True})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found or not published")
    # Deadline check
    deadline = notice.get("submission_deadline")
    if deadline and deadline < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Submission deadline has passed")

    # v51al — Harden bid submission so a 422/412 UI error never leaves an
    # orphan skeleton in the collection (regression fix for Bid 48 et al.).
    # The frontend-step/half-submitted "empty bid" rows were slipping through
    # because `price_amount: float = Field(ge=0)` accepted 0 and `documents`
    # defaulted to []. Enforce real values up-front, before any DB write.
    if payload.price_amount is None or payload.price_amount <= 0:
        raise HTTPException(status_code=422,
            detail="Quoted price must be greater than zero")
    if not payload.documents:
        raise HTTPException(status_code=422,
            detail="At least one envelope document is required to submit a bid")
    kinds = {d.kind for d in payload.documents}
    if "technical" not in kinds:
        raise HTTPException(status_code=422,
            detail="A technical envelope document is required to submit a bid")

    # v51al — Corrigenda gate. Vendor cannot submit a bid on a notice that
    # has unacknowledged active corrigenda (carried over from v51ad).
    try:
        from routers.corrigenda import ensure_corrigenda_acknowledged
        await ensure_corrigenda_acknowledged(payload.notice_ref, vendor["id"])
    except HTTPException:
        raise
    except Exception as _e:
        import logging
        logging.getLogger("bids").warning("corrigenda check skipped: %s", _e)

    # Prevent duplicate active bid per vendor+notice
    dup = await db.bids.find_one({
        "notice_ref": payload.notice_ref,
        "vendor_id": vendor["id"],
        "status": {"$nin": ["withdrawn", "rejected"]},
    })
    if dup:
        raise HTTPException(status_code=409, detail="You already have an active bid on this notice")

    # KYC pre-bid gate — vendor must have a passing KYC decision on file.
    # Skips when the vendor already has a `verified` flag OR when the notice
    # was explicitly created with `kyc_bypass=true` (admin escape hatch).
    if not notice.get("kyc_bypass"):
        vendor_doc = await db.vendors.find_one({"_id": ObjectId(vendor["id"])}) if ObjectId.is_valid(vendor["id"]) else None
        kyc_ok = False
        if vendor_doc:
            k = (vendor_doc.get("kyc") or {})
            kyc_ok = k.get("status") in ("verified", "cleared", "passed") \
                     or vendor_doc.get("kyc_status") in ("verified", "cleared", "passed")
        # Also accept a passed KYC case tied to the vendor via kyc_cases collection.
        if not kyc_ok:
            latest = await db.kyc_cases.find_one({"vendor_id": vendor["id"], "status": "passed"},
                                                   sort=[("created_at", -1)])
            kyc_ok = bool(latest)
        if not kyc_ok:
            raise HTTPException(status_code=412,
                detail="KYC verification required before submitting a bid. Please complete KYC from your vendor dashboard.")

    # Compute EMD due. v46z — if notice has no `emd_config` at all, fall back
    # to 1% of the budget (Kazakh procurement default) with a $500 floor so
    # vendors never silently skip the EMD step because of an admin oversight.
    if notice.get("emd_config") is None and (notice.get("budget_amount") or 0) > 0:
        fallback_pct = 1.0
        fallback_min = 500.0
        emd_due = max(fallback_min, round((fallback_pct / 100.0) * float(notice["budget_amount"]), 2))
        emd_currency = notice.get("budget_currency") or "USD"
        emd_source = "default_fallback"
    else:
        emd_cfg = EMDConfig(**(notice.get("emd_config") or {}))
        emd_due = emd_cfg.compute(notice.get("budget_amount") or 0.0)
        emd_currency = emd_cfg.currency
        emd_source = "notice_config" if notice.get("emd_config") else "none"

    seq = await next_sequence("bid_seq")
    year = datetime.now(timezone.utc).year
    bid_ref = f"PMC-BID-{year}-{seq:05d}"

    doc = {
        "bid_ref": bid_ref,
        "notice_ref": payload.notice_ref,
        "vendor_id": vendor["id"],
        "vendor_email": vendor["email"],
        "vendor_ref": vendor.get("vendor_ref"),
        "company_name": vendor.get("company_name"),
        "price_amount": payload.price_amount,
        "price_currency": payload.price_currency,
        "technical_notes": payload.technical_notes,
        "commercial_notes": payload.commercial_notes,
        "documents": [d.model_dump() for d in payload.documents],
        "emd_due_amount": emd_due,
        "emd_currency": emd_currency,
        "emd_paid_amount": 0.0,
        "emd_source": emd_source,
        "status": "emd_pending" if emd_due > 0 else "submitted",
        "tenant_id": config.DEFAULT_TENANT_ID,
        "workflow_history": [],
        "created_at": now_iso(),
        "submitted_at": now_iso(),
    }
    res = await db.bids.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("bid.submit", None, "bid", bid_ref,
                    {"vendor": vendor["email"], "notice": payload.notice_ref, "price": payload.price_amount})
    # v47c — confirmatory email to the bidder. EMD-due bids include the direct
    # payment deep-link so the vendor can pay without hunting the dashboard.
    try:
        from notify import vendor_confirm
        body = (f"<p>Dear {vendor.get('company_name') or 'Vendor'},</p>"
                f"<p>We have received your bid <strong>{bid_ref}</strong> for tender "
                f"<code>{payload.notice_ref}</code>.</p>"
                f"<p>Quoted price: <strong>{payload.price_currency} {payload.price_amount:,.2f}</strong><br/>"
                f"Status: <strong>{doc['status']}</strong></p>")
        if emd_due > 0:
            body += (f"<p>EMD due: <strong>{emd_currency} {emd_due:,.2f}</strong>. "
                     f"Your bid enters the evaluation pipeline once the EMD is paid.</p>")
            await vendor_confirm(vendor["email"], f"Bid received — {bid_ref}", body,
                                 "Pay EMD securely",
                                 f"{config.FRONTEND_URL}/vendor/bids/{res.inserted_id}/pay")
        else:
            body += "<p>No EMD is due on this tender — your bid is already in the evaluation pipeline.</p>"
            await vendor_confirm(vendor["email"], f"Bid received — {bid_ref}", body,
                                 "View my bids", f"{config.FRONTEND_URL}/vendor")
    except Exception as e:
        import logging
        logging.getLogger("bids").warning("bid-confirmation email failed for %s: %s", bid_ref, e)
    return _out(doc)


@router.get("/mine")
async def list_my_bids(vendor=Depends(current_vendor)) -> List[dict]:
    """List a vendor's own bids, enriched with the parent notice's title and
    submission deadline so the vendor's "My bids" page can render a usable
    table without a second round-trip per row."""
    cursor = db.bids.find({"vendor_id": vendor["id"]}).sort("created_at", -1).limit(200)
    rows = [_out(b) async for b in cursor]
    # v50s — join each bid with its notice (title + submission_deadline).
    refs = sorted({r.get("notice_ref") for r in rows if r.get("notice_ref")})
    if refs:
        notices = {}
        async for n in db.notices.find({"notice_ref": {"$in": list(refs)}},
                                       {"notice_ref": 1, "title": 1, "submission_deadline": 1}):
            notices[n["notice_ref"]] = n
        for r in rows:
            n = notices.get(r.get("notice_ref")) or {}
            if n.get("title"):
                r["notice_title"] = n["title"]
            if n.get("submission_deadline"):
                r["submission_deadline"] = n["submission_deadline"]
    return rows


@router.get("/{bid_id}")
async def get_bid(bid_id: str, vendor=Depends(current_vendor)) -> dict:
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b or b.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Bid not found")
    return _out(await _enrich_docs(b))


@router.patch("/{bid_id}")
async def update_bid(bid_id: str, payload: BidUpdateIn,
                     vendor=Depends(current_vendor)) -> dict:
    """v51ai — vendor updates their own bid's envelope documents (and notes)
    after submission, while the bid is still editable and before the tender
    deadline. Fixes the dead-end where a bid created without technical /
    commercial PDFs could never be completed from the workspace."""
    try:
        bid_oid = ObjectId(bid_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed bid id")
    b = await db.bids.find_one({"_id": bid_oid})
    if not b or b.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Bid not found")
    # v51aj — envelope edits stay open while the bid is anywhere BEFORE admin
    # evaluation starts (incl. emd_paid / escrow_accepted). A vendor who paid
    # EMD but forgot the commercial PDF can still fix it until the deadline;
    # on_hold stays locked until the admin resumes.
    if b.get("status") not in ("draft", "submitted", "emd_pending",
                               "emd_paid", "escrow_accepted"):
        raise HTTPException(status_code=400,
            detail=f"Bid is {b.get('status')} — documents can no longer be changed")
    notice = await db.notices.find_one({"notice_ref": b.get("notice_ref")}) or {}
    deadline = notice.get("submission_deadline") or b.get("submission_deadline")
    if deadline:
        try:
            dl = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            if dl < datetime.now(timezone.utc):
                raise HTTPException(status_code=400,
                    detail="Submission deadline has passed — envelopes are sealed")
        except ValueError:
            pass
    updates = {}
    if payload.documents is not None:
        docs = [d.model_dump() for d in payload.documents]
        for d in docs:
            if d.get("kind") not in ("technical", "commercial", "supporting") or not d.get("key"):
                raise HTTPException(status_code=422,
                    detail="Each document needs kind (technical/commercial/supporting) and an upload key")
        updates["documents"] = docs
    if payload.technical_notes is not None:
        updates["technical_notes"] = payload.technical_notes
    if payload.commercial_notes is not None:
        updates["commercial_notes"] = payload.commercial_notes
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = now_iso()
    await db.bids.update_one({"_id": bid_oid}, {"$set": updates})
    await audit_log("bid.documents_update", None, "bid", b.get("bid_ref"),
                    {"vendor": vendor["email"],
                     "doc_count": len(updates.get("documents", []))})
    return _out(await _enrich_docs(await db.bids.find_one({"_id": bid_oid})))


@router.get("/admin/{bid_id}")
async def admin_get_bid(bid_id: str,
                          admin=Depends(require_role("admin", "reviewer",
                                                     "escrow_agent", "certifier",
                                                     "legal_counsel", "accounting",
                                                     "committee_member"))) -> dict:
    """v47f — admin-scoped bid detail: any staff role that acts on bids can
    view the full submission, attachments, technical/commercial notes and the
    complete workflow history."""
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    return _out(await _enrich_docs(b))


# v51al — Admin cleanup for orphan bids. Only deletes bids that have no
# quoted price, no documents, no EMD paid, and are still in a draft-ish
# status. Everything else must go through the normal reject/withdraw path.
@router.delete("/admin/{bid_id}")
async def admin_delete_orphan_bid(bid_id: str,
                                    admin=Depends(require_role("admin"))) -> dict:
    try:
        oid = ObjectId(bid_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed bid id")
    b = await db.bids.find_one({"_id": oid})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    is_orphan = (
        (not b.get("price_amount") or float(b.get("price_amount") or 0) <= 0)
        and not (b.get("documents") or [])
        and float(b.get("emd_paid_amount") or 0) <= 0
        and b.get("status") in ("draft", "submitted", "emd_pending")
    )
    if not is_orphan:
        raise HTTPException(status_code=400,
            detail="Only orphan bids (no price, no documents, no EMD paid) can be deleted this way. Use reject/withdraw for live bids.")
    await db.bids.delete_one({"_id": oid})
    await audit_log("bid.admin_delete_orphan", admin, "bid", b.get("bid_ref"),
                    {"deleted_doc": {"notice_ref": b.get("notice_ref"),
                                       "vendor_id": b.get("vendor_id"),
                                       "status": b.get("status")}})
    return {"ok": True, "deleted": b.get("bid_ref")}


@router.post("/{bid_id}/emd/send-link")
async def send_emd_payment_link(bid_id: str,
                                 admin=Depends(require_role("admin", "reviewer"))):
    """v47b — admin sends the bidder a direct EMD-payment link by email after
    reviewing the bid. The link deep-opens the vendor portal, auto-starts the
    Stripe checkout for this bid, and returns the vendor to the success page.
    This complements (not replaces) the in-dashboard Pay EMD button — both
    paths are live so a vendor can never miss the step."""
    from emails import send_email, wrap
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    due = float(b.get("emd_due_amount") or 0)
    if due <= 0:
        raise HTTPException(status_code=400, detail="No EMD due on this bid")
    if b.get("status") not in ("emd_pending", "submitted"):
        raise HTTPException(status_code=400,
            detail=f"EMD link only valid while payment is pending (current: {b.get('status')})")
    if float(b.get("emd_paid_amount") or 0) >= due:
        raise HTTPException(status_code=400, detail="EMD already paid for this bid")
    link = f"{config.FRONTEND_URL}/vendor/bids/{bid_id}/pay"
    body = wrap(
        f"EMD payment link — {b.get('bid_ref')}",
        f"<p>Dear {b.get('company_name') or 'Vendor'},</p>"
        f"<p>Your bid <strong>{b.get('bid_ref')}</strong> on tender "
        f"<code>{b.get('notice_ref')}</code> has been reviewed by PMC and is "
        f"approved to proceed to the EMD (Earnest Money Deposit) step.</p>"
        f"<p>EMD due: <strong>{b.get('emd_currency')} {due:,.2f}</strong></p>"
        f"<p>Click the button below to pay securely. You can also pay any time "
        f"from Vendor Portal → My bids → Pay EMD.</p>",
        "Pay EMD securely", link,
    )
    await send_email(
        b.get("vendor_email"),
        f"[PMC] EMD payment link — {b.get('bid_ref')}",
        body,
    )
    await audit_log("bid.emd_link_sent", admin, "bid", b.get("bid_ref"),
                    {"to": b.get("vendor_email"), "amount": due})
    return {"ok": True, "emailed_to": b.get("vendor_email"), "link": link}


@router.post("/{bid_id}/withdraw")
async def withdraw_bid(bid_id: str, vendor=Depends(current_vendor)) -> dict:
    b = await db.bids.find_one({"_id": ObjectId(bid_id), "vendor_id": vendor["id"]})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    if b.get("status") in ("awarded", "closed", "withdrawn"):
        raise HTTPException(status_code=400, detail="Cannot withdraw at this stage")
    await db.bids.update_one({"_id": ObjectId(bid_id)},
                             {"$set": {"status": "withdrawn", "withdrawn_at": now_iso()}})
    await audit_log("bid.withdraw", None, "bid", b.get("bid_ref"), {})
    # v47c — confirmatory email to the bidder
    try:
        from notify import vendor_confirm
        await vendor_confirm(
            vendor.get("email"), f"Bid withdrawn — {b.get('bid_ref')}",
            f"<p>Your bid <strong>{b.get('bid_ref')}</strong> on tender "
            f"<code>{b.get('notice_ref')}</code> has been withdrawn at your request. "
            f"If you paid an EMD, it will be refunded per the tender terms.</p>",
            "View my bids", f"{config.FRONTEND_URL}/vendor")
    except Exception:
        pass
    return {"ok": True}


# ---------- Staff endpoints (multi-role) ----------

@router.get("")
async def list_all_bids(
    notice_ref: Optional[str] = None,
    status: Optional[str] = None,
    admin=Depends(require_role("admin", "reviewer", "escrow_agent", "certifier",
                               "legal_counsel", "accounting", "committee_member", "auditor")),
) -> List[dict]:
    from matrix_helper import active_step
    q: dict = {}
    if notice_ref:
        q["notice_ref"] = notice_ref
    if status:
        q["status"] = status
    viewer_roles = _viewer_role_set(admin)
    rows: List[dict] = []
    async for b in db.bids.find(q).sort("created_at", -1).limit(300):
        row = _out(_redact_commercial(b, viewer_roles))
        row["active_step"] = await active_step(b)
        rows.append(row)
    return rows


# ---------- Wave 39: Two-Cover flow control -----------------------------

@router.post("/{bid_id}/technical-clear")
async def technical_clear(bid_id: str,
                           admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    """Mark technical envelope as cleared — bid is qualified to move to
    commercial evaluation. Idempotent."""
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    if b.get("technical_cleared_at"):
        return {"ok": True, "already": True,
                "technical_cleared_at": b.get("technical_cleared_at")}
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"technical_cleared_at": now_iso(),
                  "technical_cleared_by": admin.get("email")}},
    )
    await audit_log("bid.technical_clear", admin, "bid", b.get("bid_ref"), {})
    return {"ok": True, "technical_cleared_at": now_iso()}


@router.post("/{bid_id}/financial-open")
async def financial_open(bid_id: str,
                          admin=Depends(require_role("admin", "committee_member"))):
    """Open (unseal) the commercial envelope. GATED on technical clearance."""
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    if not b.get("technical_cleared_at"):
        raise HTTPException(status_code=412,
            detail="Technical envelope must be cleared before opening the commercial envelope")
    if b.get("financial_opened_at"):
        return {"ok": True, "already": True,
                "financial_opened_at": b.get("financial_opened_at")}
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"financial_opened_at": now_iso(),
                  "financial_opened_by": admin.get("email")}},
    )
    await audit_log("bid.financial_open", admin, "bid", b.get("bid_ref"), {})
    return {"ok": True, "financial_opened_at": now_iso()}


_ROLE_TO_TARGET_STATUS = {
    "escrow_agent":   ("emd_paid",            "escrow_accepted"),
    "admin":          ("escrow_accepted",     "admin_flagged"),
    "certifier":      ("admin_flagged",       "certifier_cleared"),
    "legal_counsel":  ("certifier_cleared",   "legal_cleared"),
    "accounting":     ("legal_cleared",       "accounting_cleared"),
    "committee":      ("accounting_cleared",  "awarded"),  # or "rejected"
}


@router.post("/{bid_id}/decision")
async def decide_bid(bid_id: str, payload: BidDecisionIn,
                     admin=Depends(require_role("admin", "reviewer", "escrow_agent", "certifier",
                                                "legal_counsel", "accounting", "committee_member"))):
    """Sequential approval step. The active role in the JWT must match `payload.role`."""
    from routers.bids_helpers import (
        check_role_match, resolve_matrix_next_status,
        resolve_action_next_status, validate_transition,
    )

    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    check_role_match(admin.get("role"), payload.role)

    prev_status = b.get("status")

    # v47a — Hold / Resume. Admin-only; pauses a bid at any in-flight stage
    # and remembers the prior stage so Resume restores it exactly.
    if payload.action in ("hold", "resume"):
        if payload.role != "admin":
            raise HTTPException(status_code=403, detail="Only admin can hold or resume a bid")
        if payload.action == "hold":
            if prev_status in ("awarded", "rejected", "withdrawn", "closed", "on_hold"):
                raise HTTPException(status_code=400,
                    detail=f"Cannot hold a bid in status '{prev_status}'")
            next_status = "on_hold"
            extra_set = {"held_from_status": prev_status,
                         "hold_reason": payload.notes or None,
                         "held_by": admin.get("email"), "held_at": now_iso()}
        else:
            if prev_status != "on_hold":
                raise HTTPException(status_code=400,
                    detail=f"Cannot resume a bid in status '{prev_status}'")
            next_status = b.get("held_from_status") or "escrow_accepted"
            extra_set = {"held_from_status": None, "resumed_by": admin.get("email"),
                         "resumed_at": now_iso()}
        expected = None
    else:
        expected, next_status = _ROLE_TO_TARGET_STATUS.get(payload.role, (None, None))

        # Matrix override on accept: matrix ordering supersedes the fixed pipeline.
        if payload.action == "accept":
            matrix_next, matrix_used = await resolve_matrix_next_status(b, payload.role)
            if matrix_used:
                next_status = matrix_next
                expected = None

        next_status = resolve_action_next_status(payload.action, payload.role, next_status)
        validate_transition(payload.action, expected, prev_status, payload.role)
        extra_set = {}

    entry = {
        "role": payload.role, "action": payload.action, "from_status": prev_status,
        "to_status": next_status, "notes": payload.notes, "by": admin.get("email"),
        "at": now_iso(),
    }
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"status": next_status, "updated_at": now_iso(), **extra_set},
         "$push": {"workflow_history": entry}},
    )
    await audit_log(f"bid.{payload.role}.{payload.action}", admin, "bid", b.get("bid_ref"), entry)
    # Fire in-app + email notification to the NEXT role in the pipeline.
    try:
        from notify import notify_bid_transition
        b_updated = await db.bids.find_one({"_id": ObjectId(bid_id)})
        await notify_bid_transition(b_updated, next_status)
    except Exception:
        pass
    # Wave 39 — Auto-generate Post-Award documents on award.
    if next_status == "awarded":
        try:
            from routers.awards import generate_award_documents
            await generate_award_documents(bid_id, admin.get("email"))
        except Exception as e:
            import logging
            logging.warning(f"Award document auto-generation failed for bid {bid_id}: {e}")
        # v46t — fan out a Web Push to the awarded vendor + any admins subscribed.
        try:
            from routers.push import fanout as _push_fanout
            b_now = await db.bids.find_one({"_id": ObjectId(bid_id)}) or {}
            title = "Contract awarded"
            body = f"Your bid for {b_now.get('notice_ref','')} is the L1 winner. Open to sign the PO."
            url = f"/vendor/bids/{bid_id}"
            await _push_fanout(title, body, url, user_ref=b_now.get("vendor_ref"))
        except Exception as e:
            import logging
            logging.info("push: award notify skipped (%s)", e)
    return {"ok": True, "status": next_status}


@router.post("/{bid_id}/assign-certifier")
async def assign_certifier(bid_id: str, certifier_id: str,
                           admin=Depends(require_role("admin"))) -> dict:
    """Admin assigns a specific staff member (with certifier role) as responsible
    for the tender/bid verification incl. site inspection."""
    cert = await db.admin_users.find_one({"_id": ObjectId(certifier_id)})
    if not cert:
        raise HTTPException(status_code=404, detail="Certifier not found")
    roles = cert.get("roles") or [cert.get("role")]
    if "certifier" not in roles:
        raise HTTPException(status_code=400, detail="Assigned staff does not hold certifier role")
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"assigned_certifier_id": certifier_id,
                  "assigned_certifier_email": cert.get("email"),
                  "assigned_at": now_iso()}},
    )
    await audit_log("bid.assign_certifier", admin, "bid", b.get("bid_ref"),
                    {"certifier_id": certifier_id, "certifier_email": cert.get("email")})
    return {"ok": True}
