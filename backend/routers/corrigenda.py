"""Wave 39 — Corrigendum / Amendment publisher.

A corrigendum is a formal, versioned addendum to an already-published notice
(deadline change, scope tweak, price-basis correction, etc.). Every bidder
gets to see it before the deadline — mirrors CPPP / GeM / eGP behaviour.

Endpoints (admin unless noted):
  POST   /api/v1/notices/{notice_ref}/corrigenda            create + publish
  GET    /api/v1/notices/{notice_ref}/corrigenda            list PUBLISHED  (public)
  GET    /api/v1/notices/{notice_ref}/corrigenda/admin      list ALL        (incl. withdrawn)
  DELETE /api/v1/notices/{notice_ref}/corrigenda/{cid}      withdraw (soft-delete)
"""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field
from bson import ObjectId
import base64, uuid

from db import db, next_sequence
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/notices", tags=["corrigenda"])


# v51ad — vendor-facing endpoints (not admin-only). Live under
# /api/v1/corrigenda/* so they don't collide with the notice tree.
_vendor_router = APIRouter(prefix="/api/v1/corrigenda", tags=["corrigenda-vendor"])


class CorrigendumIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=8, max_length=4000)
    effective_from: Optional[str] = None       # ISO — when the change is in force
    new_submission_deadline: Optional[str] = None  # optional deadline extension
    # v51ad — optional "extend by N days" shortcut. If supplied with no
    # new_submission_deadline, the backend computes the new deadline from the
    # notice's current submission_deadline + N days.
    extend_deadline_days: Optional[int] = Field(default=None, ge=0, le=365)
    # v51ad — field-level amendments. Each item: {field, before, after, note?}
    # Lets admins show a versioned diff on the public corrigendum page rather
    # than just a free-text note.
    field_amendments: Optional[List[dict]] = None


def _out(d: dict) -> dict:
    o = BaseDocument.out(d)
    o.pop("pdf_bytes", None)  # never leak raw bytes
    return o


@router.post("/{notice_ref}/corrigenda")
async def publish_corrigendum(
    notice_ref: str,
    payload: CorrigendumIn,
    admin=Depends(require_role("admin", "reviewer")),
) -> dict:
    """Publish a new corrigendum on a published notice. Auto-numbered."""
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found or not published")

    # Auto-increment per-notice corrigendum number
    existing = await db.corrigenda.count_documents({"notice_ref": notice_ref})
    corr_no = existing + 1

    # v51ad — if admin picked "extend by N days", compute the new deadline from
    # the parent notice's current submission_deadline + N days (so admins don't
    # have to open a calendar).
    new_deadline = payload.new_submission_deadline
    if not new_deadline and payload.extend_deadline_days:
        from datetime import timedelta
        current_dl = n.get("submission_deadline")
        if current_dl:
            try:
                base = datetime.fromisoformat(current_dl.replace("Z", "+00:00"))
                new_deadline = (base + timedelta(days=int(payload.extend_deadline_days))).isoformat()
            except Exception:
                pass

    doc = {
        "notice_ref": notice_ref,
        "tenant_id": n.get("tenant_id"),
        "corrigendum_no": corr_no,
        "title": payload.title,
        "summary": payload.summary,
        "effective_from": payload.effective_from,
        "new_submission_deadline": new_deadline,
        "extend_deadline_days": payload.extend_deadline_days,
        "field_amendments": payload.field_amendments or [],
        "attachments": [],
        "is_active": True,
        # v51ad — vendors that have an active bid must acknowledge each
        # corrigendum before any next bid action. Starts empty.
        "acknowledgements": [],
        "published_at": now_iso(),
        "published_by": admin.get("email"),
        "created_at": now_iso(),
    }
    res = await db.corrigenda.insert_one(doc)
    doc["_id"] = res.inserted_id

    # If a new deadline was supplied/computed, also update the parent notice.
    if new_deadline:
        await db.notices.update_one(
            {"notice_ref": notice_ref},
            {"$set": {"submission_deadline": new_deadline,
                      "deadline_last_amended_at": now_iso(),
                      "deadline_last_amended_by_corr": corr_no}},
        )

    await audit_log("corrigendum.publish", admin, "notice", notice_ref,
                    {"corrigendum_no": corr_no, "title": payload.title})
    # v52bo — build the one-page corrigendum PDF ONCE and reuse for every
    # bidder email + expose it via GET …/pdf. Any failure is logged but never
    # blocks publish — the diff still renders in-app.
    pdf_bytes: Optional[bytes] = None
    try:
        from routers.corrigenda_pdf import build_corrigendum_pdf
        pdf_bytes = build_corrigendum_pdf(n, doc)
        await db.corrigenda.update_one(
            {"_id": res.inserted_id},
            {"$set": {"pdf_generated_at": now_iso(),
                      "pdf_bytes_len": len(pdf_bytes)}},
        )
    except Exception as e:
        import logging
        logging.exception("corrigendum pdf build failed: %s", e)

    # v52bo — email every active bidder on this notice with the diff PDF
    # attached. Only vendors who have an un-withdrawn bid are notified.
    # v52bp — also drop a vendor-bell notification per bidder with a
    # deep-link to the diff PDF so bidders can open it from the alerts bell.
    try:
        import asyncio, base64 as _b64
        from emails import send_email, wrap as _wrap
        attachments = None
        if pdf_bytes:
            attachments = [{
                "filename": f"Corrigendum-{corr_no}-{notice_ref}.pdf",
                "content_b64": _b64.b64encode(pdf_bytes).decode(),
                "content_type": "application/pdf",
            }]
        pdf_url = f"/api/v1/notices/{notice_ref}/corrigenda/{res.inserted_id}/pdf"
        emails_seen = set()
        cursor = db.bids.find(
            {"notice_ref": notice_ref, "status": {"$ne": "withdrawn"}},
            {"vendor_email": 1, "vendor_ref": 1, "bid_ref": 1},
        )
        async for b in cursor:
            em = b.get("vendor_email")
            if not em or em in emails_seen:
                continue
            emails_seen.add(em)
            subject = f"Corrigendum {corr_no} · {notice_ref}"
            # v52bp — bell notification with a deep link; vendor UI renders
            # "Open PDF" as a button next to the alert.
            try:
                await db.notifications.insert_one({
                    "user_email": em,
                    "user_ref": b.get("vendor_ref"),
                    "role": "vendor",
                    "subject": subject,
                    "body": (f"<p>Corrigendum {corr_no} issued on "
                             f"<code>{notice_ref}</code>. "
                             f"The one-page diff PDF is attached.</p>"),
                    "related_type": "corrigendum",
                    "related_id": str(res.inserted_id),
                    "related_url": pdf_url,
                    "related_notice_ref": notice_ref,
                    "read": False,
                    "created_at": now_iso(),
                })
            except Exception as _e:
                import logging as _lg
                _lg.warning("bell notify failed for %s: %s", em, _e)
            body_html = _wrap(
                f"Corrigendum {corr_no} — {payload.title}",
                (f"<p>A formal amendment has been issued on tender "
                 f"<code>{notice_ref}</code>.</p>"
                 f"<p>{(payload.summary or '')}</p>"
                 f"<p>The attached one-page diff sheet shows every field "
                 f"that changed, with before / after values and the reason.</p>"),
                cta_label="Open notice",
                cta_url=f"{config.FRONTEND_URL}/notices/{notice_ref}" if hasattr(config, "FRONTEND_URL") else f"/notices/{notice_ref}",
            )
            asyncio.create_task(send_email(em, subject, body_html, attachments=attachments))
        import logging as _lg
        _lg.info("corrigendum %s/%s: emailed %d bidders", notice_ref, corr_no, len(emails_seen))
    except Exception as e:
        import logging
        logging.exception("corrigendum email fan-out failed: %s", e)
    # v46t — fan out a Web Push to every subscription so bidders learn instantly.
    try:
        from routers.push import fanout as _push_fanout
        await _push_fanout(
            f"Corrigendum #{corr_no} · {notice_ref}",
            (payload.summary or payload.title or "A material amendment has been published.")[:200],
            f"/notices/{notice_ref}",
        )
    except Exception as e:
        import logging
        logging.info("push: corrigendum notify skipped (%s)", e)
    return {"ok": True, "corrigendum": _out(doc)}


@router.get("/{notice_ref}/corrigenda")
async def list_public_corrigenda(notice_ref: str) -> dict:
    """PUBLIC — list every ACTIVE corrigendum for a published notice."""
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    cursor = db.corrigenda.find({"notice_ref": notice_ref, "is_active": True})\
                          .sort("corrigendum_no", 1)
    items = [_out(d) async for d in cursor]
    return {"notice_ref": notice_ref, "items": items, "total": len(items)}


@router.get("/{notice_ref}/corrigenda/admin")
async def list_admin_corrigenda(
    notice_ref: str,
    admin=Depends(require_role("admin", "reviewer", "auditor")),
) -> dict:
    cursor = db.corrigenda.find({"notice_ref": notice_ref})\
                          .sort("corrigendum_no", -1)
    items = [_out(d) async for d in cursor]
    return {"notice_ref": notice_ref, "items": items, "total": len(items)}


from pydantic import BaseModel, Field


class WithdrawReasonIn(BaseModel):
    reason: str = Field(..., min_length=8, description="Reason required for audit")


@router.delete("/{notice_ref}/corrigenda/{cid}")
async def withdraw_corrigendum(
    notice_ref: str,
    cid: str,
    reason: str | None = None,
    admin=Depends(require_role("admin")),
) -> dict:
    """Soft-delete — bidders can still see it was published but marked withdrawn.
    Reason is REQUIRED (≥8 chars) so the audit log carries a rationale.
    """
    if not reason or len(reason.strip()) < 8:
        raise HTTPException(status_code=400,
            detail="Withdraw reason is required (min 8 characters) — this is recorded in the audit log.")
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed corrigendum id")
    c = await db.corrigenda.find_one({"_id": oid, "notice_ref": notice_ref})
    if not c:
        raise HTTPException(status_code=404, detail="Corrigendum not found")
    await db.corrigenda.update_one(
        {"_id": oid},
        {"$set": {"is_active": False, "withdrawn_at": now_iso(),
                  "withdrawn_by": admin.get("email"),
                  "withdrawn_reason": reason.strip()}},
    )
    await audit_log("corrigendum.withdraw", admin, "notice", notice_ref,
                    {"corrigendum_no": c.get("corrigendum_no"),
                     "reason": reason.strip()})
    # Bug #12 / #23 fix — return the fresh document so the frontend has
    # the authoritative is_active=false without a second round-trip.
    fresh = await db.corrigenda.find_one({"_id": oid})
    return {"ok": True, "corrigendum": _out(fresh) if fresh else None}


@router.get("/{notice_ref}/corrigenda/{cid}/pdf")
async def download_corrigendum_pdf(notice_ref: str, cid: str):
    """v52bo — one-page diff PDF for a single corrigendum. Public — this
    is the same artefact bidders receive by email on publish."""
    from fastapi.responses import Response
    if not ObjectId.is_valid(cid):
        raise HTTPException(status_code=400, detail="Invalid corrigendum id")
    doc = await db.corrigenda.find_one({"_id": ObjectId(cid),
                                         "notice_ref": notice_ref})
    if not doc:
        raise HTTPException(status_code=404, detail="Corrigendum not found")
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    from routers.corrigenda_pdf import build_corrigendum_pdf
    pdf_bytes = build_corrigendum_pdf(n, doc)
    fname = f"Corrigendum-{doc.get('corrigendum_no', '')}-{notice_ref}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )


@router.post("/{notice_ref}/corrigenda/{cid}/attachment")
async def attach_corrigendum_file(
    notice_ref: str,
    cid: str,
    file: UploadFile = File(...),
    admin=Depends(require_role("admin")),
) -> dict:
    """Attach a supporting document (revised BOQ, drawing, etc.) to a corrigendum."""
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed corrigendum id")
    c = await db.corrigenda.find_one({"_id": oid, "notice_ref": notice_ref})
    if not c:
        raise HTTPException(status_code=404, detail="Corrigendum not found")

    body = await file.read()
    if len(body) < 100:
        raise HTTPException(status_code=400, detail="File is too small to be valid")

    key = f"corrigendum-docs/{notice_ref}/{uuid.uuid4().hex}_{file.filename}"
    await db.uploads.insert_one({
        "key": key,
        "file_name": file.filename,
        # v52bp — mark the scope + parent notice so the public uploads
        # endpoint can serve it to anonymous bidders (previously the frontend
        # was pointing at /api/v1/uploads/files which required a signed-in
        # user → bidders got 401 on the public corrigendum page).
        "scope": "corrigendum-attachments",
        "notice_ref": notice_ref,
        "corrigendum_id": str(oid),
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(body),
        "bytes_b64": base64.b64encode(body).decode("ascii"),
        "data_b64":  base64.b64encode(body).decode("ascii"),
        "uploaded_at": now_iso(),
        "uploaded_by": admin.get("email"),
    })
    attachment = {
        "key": key,
        "file_name": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(body),
        # v52bp — serve the attachment through the PUBLIC uploads endpoint
        # so the diff-table attachment chip works for every visitor.
        "url": f"/api/v1/uploads/public-files/{key}",
    }
    await db.corrigenda.update_one({"_id": oid}, {"$push": {"attachments": attachment}})
    await audit_log("corrigendum.attach", admin, "notice", notice_ref,
                    {"corrigendum_no": c.get("corrigendum_no"), "file": file.filename})
    return {"ok": True, "attachment": attachment}


# =========================================================================
# v51ad — vendor-facing acknowledge flow.
# A vendor with an active bid on a notice MUST acknowledge every active
# corrigendum before they take their next bid action (submit / withdraw / etc).
# These endpoints also back the vendor dashboard banner ("2 corrigenda await
# your acknowledgement").
# =========================================================================
from routers.vendor_auth import current_vendor  # noqa: E402


async def _unacknowledged_for_vendor(notice_ref: str, vendor_id: str) -> list:
    rows = []
    async for d in db.corrigenda.find({"notice_ref": notice_ref, "is_active": True})\
                                  .sort("corrigendum_no", 1):
        acks = d.get("acknowledgements") or []
        if not any(a.get("vendor_id") == vendor_id for a in acks):
            rows.append(_out(d))
    return rows


@_vendor_router.get("/outstanding")
async def my_outstanding_corrigenda(vendor=Depends(current_vendor)):
    """Vendor dashboard call — list every corrigendum on every notice where
    this vendor has an active bid that they have NOT yet acknowledged."""
    out = []
    async for b in db.bids.find({"vendor_id": vendor["id"],
                                 "status": {"$nin": ["withdrawn", "rejected"]}}):
        unack = await _unacknowledged_for_vendor(b["notice_ref"], vendor["id"])
        if unack:
            out.append({"notice_ref": b["notice_ref"], "bid_ref": b.get("bid_ref"),
                        "corrigenda": unack})
    return {"items": out, "total": sum(len(x["corrigenda"]) for x in out)}


@_vendor_router.post("/{cid}/acknowledge")
async def acknowledge_corrigendum(cid: str, vendor=Depends(current_vendor)):
    try: oid = ObjectId(cid)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed corrigendum id")
    c = await db.corrigenda.find_one({"_id": oid, "is_active": True})
    if not c:
        raise HTTPException(status_code=404, detail="Corrigendum not found or withdrawn")
    # v52bh — allow acknowledgement BEFORE a bid exists. The submission gate
    # (ensure_corrigenda_acknowledged) blocks bid creation until every active
    # corrigendum is acknowledged, so requiring an active bid here deadlocked
    # new vendors: no bid → can't acknowledge → can't create the bid.
    bid = await db.bids.find_one({"notice_ref": c["notice_ref"],
                                    "vendor_id": vendor["id"],
                                    "status": {"$nin": ["withdrawn", "rejected"]}})
    acks = c.get("acknowledgements") or []
    if not any(a.get("vendor_id") == vendor["id"] for a in acks):
        acks.append({"vendor_id": vendor["id"],
                     "vendor_email": vendor.get("email"),
                     "vendor_ref": vendor.get("vendor_ref"),
                     "acknowledged_at": now_iso()})
        await db.corrigenda.update_one({"_id": oid},
                                        {"$set": {"acknowledgements": acks}})
    await audit_log("corrigendum.acknowledge", vendor, "notice", c["notice_ref"],
                    {"corrigendum_no": c.get("corrigendum_no")})
    return {"ok": True, "corrigendum_no": c.get("corrigendum_no")}


# Admin-only — see WHO acknowledged which corrigendum.
@router.get("/{notice_ref}/corrigenda/{cid}/acknowledgements")
async def list_corr_acks(notice_ref: str, cid: str,
                           admin=Depends(require_role("admin", "reviewer", "auditor"))):
    try: oid = ObjectId(cid)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed corrigendum id")
    c = await db.corrigenda.find_one({"_id": oid, "notice_ref": notice_ref})
    if not c: raise HTTPException(status_code=404, detail="Corrigendum not found")
    return {"items": c.get("acknowledgements") or [],
            "total": len(c.get("acknowledgements") or []),
            "corrigendum_no": c.get("corrigendum_no")}


# Called by bids.py to BLOCK a vendor action until every active corrigendum on
# that notice has been acknowledged by this vendor.
async def ensure_corrigenda_acknowledged(notice_ref: str, vendor_id: str):
    unack = await _unacknowledged_for_vendor(notice_ref, vendor_id)
    if unack:
        raise HTTPException(status_code=412, detail={
            "code": "corrigenda_unacknowledged",
            "message": f"{len(unack)} active corrigend{'um' if len(unack) == 1 else 'a'} on this notice need your acknowledgement before you can act.",
            "corrigenda": [{"id": c["id"], "corrigendum_no": c["corrigendum_no"],
                             "title": c["title"]} for c in unack],
        })
