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

router = APIRouter(prefix="/api/v1/notices", tags=["corrigenda"])


class CorrigendumIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=8, max_length=4000)
    effective_from: Optional[str] = None       # ISO — when the change is in force
    new_submission_deadline: Optional[str] = None  # optional deadline extension


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

    doc = {
        "notice_ref": notice_ref,
        "tenant_id": n.get("tenant_id"),
        "corrigendum_no": corr_no,
        "title": payload.title,
        "summary": payload.summary,
        "effective_from": payload.effective_from,
        "new_submission_deadline": payload.new_submission_deadline,
        "attachments": [],
        "is_active": True,
        "published_at": now_iso(),
        "published_by": admin.get("email"),
        "created_at": now_iso(),
    }
    res = await db.corrigenda.insert_one(doc)
    doc["_id"] = res.inserted_id

    # If a new deadline was supplied, also update the parent notice.
    if payload.new_submission_deadline:
        await db.notices.update_one(
            {"notice_ref": notice_ref},
            {"$set": {"submission_deadline": payload.new_submission_deadline,
                      "deadline_last_amended_at": now_iso(),
                      "deadline_last_amended_by_corr": corr_no}},
        )

    await audit_log("corrigendum.publish", admin, "notice", notice_ref,
                    {"corrigendum_no": corr_no, "title": payload.title})
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


@router.delete("/{notice_ref}/corrigenda/{cid}")
async def withdraw_corrigendum(
    notice_ref: str,
    cid: str,
    admin=Depends(require_role("admin")),
) -> dict:
    """Soft-delete — bidders can still see it was published but marked withdrawn."""
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
                  "withdrawn_by": admin.get("email")}},
    )
    await audit_log("corrigendum.withdraw", admin, "notice", notice_ref,
                    {"corrigendum_no": c.get("corrigendum_no")})
    return {"ok": True}


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
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": len(body),
        "bytes_b64": base64.b64encode(body).decode("ascii"),
        "uploaded_at": now_iso(),
        "uploaded_by": admin.get("email"),
    })
    attachment = {
        "key": key,
        "file_name": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(body),
        "url": f"/api/v1/uploads/files/{key}",
    }
    await db.corrigenda.update_one({"_id": oid}, {"$push": {"attachments": attachment}})
    await audit_log("corrigendum.attach", admin, "notice", notice_ref,
                    {"corrigendum_no": c.get("corrigendum_no"), "file": file.filename})
    return {"ok": True, "attachment": attachment}
