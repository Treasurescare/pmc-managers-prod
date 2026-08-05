from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from bson import ObjectId
import base64, uuid

import config
from db import db, next_sequence
from models import NoticeIn
from models.base import BaseDocument, now_iso
from security import require_role
from routers.permissions import require_notice_permission
from audit import audit_log

router = APIRouter(prefix="/api/v1/notices", tags=["notices"])


# ---- Magic-byte sniffing so uploads can't be plain text disguised as PDF ---
_MIN_DOC_BYTES = 200  # anything smaller is almost certainly a placeholder


def _validate_document_bytes(body: bytes, filename: str, declared_ct: str) -> None:
    """Reject placeholder/corrupt files. Raises 400 with a clear message.

    Rules:
    * File must be at least 200 bytes (no plain-text stubs).
    * If the extension is a well-known office/pdf format, the file's magic
      bytes must match, otherwise the browser can't render it.
    """
    if len(body) < _MIN_DOC_BYTES:
        raise HTTPException(status_code=400,
            detail=f"File is too small ({len(body)} bytes). Real tender documents are typically several KB or more.")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    magic_pdf = body[:5] == b"%PDF-"
    magic_zip = body[:4] == b"PK\x03\x04"  # docx/xlsx/pptx/zip
    magic_png = body[:8] == b"\x89PNG\r\n\x1a\n"
    magic_jpg = body[:3] == b"\xff\xd8\xff"
    magic_ole = body[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .doc/.xls
    if ext == "pdf" and not magic_pdf:
        raise HTTPException(status_code=400,
            detail="File has a .pdf extension but is not a valid PDF (missing '%PDF-' header). Please re-export as PDF.")
    if ext in ("docx", "xlsx", "pptx") and not magic_zip:
        raise HTTPException(status_code=400,
            detail=f"File has a .{ext} extension but is not a valid Office document.")
    if ext in ("doc", "xls", "ppt") and not (magic_ole or magic_zip):
        raise HTTPException(status_code=400,
            detail=f"File has a .{ext} extension but does not look like a Microsoft Office file.")
    if ext == "png" and not magic_png:
        raise HTTPException(status_code=400, detail="File has a .png extension but is not a valid PNG image.")
    if ext in ("jpg", "jpeg") and not magic_jpg:
        raise HTTPException(status_code=400, detail="File has a .jpg extension but is not a valid JPEG image.")


def _out(doc: dict) -> dict:
    d = BaseDocument.out(doc)
    d.pop("tenant_id", None)
    d.pop("created_by", None)
    return d


@router.get("")
async def list_notices(
    country: Optional[str] = None,
    category: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
):
    """PUBLIC — list published tender notices. No auth."""
    q: dict = {"is_published": True}
    if country:
        q["delivery_country"] = country.upper()
    if category:
        q["category"] = category
    if document_type in ("tender", "rfp", "rfq"):
        q["document_type"] = document_type

    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    cursor = db.notices.find(q).sort("published_at", -1).skip(offset).limit(limit)
    total = await db.notices.count_documents(q)
    items = [_out(t) async for t in cursor]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{notice_ref}")
async def get_notice(notice_ref: str):
    """PUBLIC — notice detail. No auth. Returns 404 if unpublished or missing."""
    doc = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Notice not found")
    return _out(doc)


@router.post("")
async def create_notice(payload: NoticeIn, admin=Depends(require_role(
        "admin", "reviewer", "legal_counsel", "committee_member"))):
    """Create + optionally publish a notice. Permissions Matrix enforced."""
    await require_notice_permission(admin, "create", payload.document_type)
    if payload.is_published:
        await require_notice_permission(admin, "publish", payload.document_type)
    seq = await next_sequence("notice_seq")
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    notice_ref = f"PMC-NOT-{year}-{seq:04d}"

    doc = payload.model_dump()

    # Auto-attach KZ required licenses per category
    if (doc.get("delivery_country") or "").upper() == "KZ":
        auto = config.KZ_CATEGORY_LICENSE_MAP.get(doc.get("category"), [])
        doc["required_licenses"] = list({*(doc.get("required_licenses") or []), *auto})

    doc.update({
        "notice_ref": notice_ref,
        "tenant_id": admin["tenant_id"],
        "created_by": admin["id"],
        "created_at": now_iso(),
        "published_at": now_iso() if doc.get("is_published") else None,
    })
    res = await db.notices.insert_one(doc)
    doc["_id"] = res.inserted_id

    await audit_log(
        "notice.publish" if doc.get("is_published") else "notice.create",
        admin, "notice", notice_ref,
        {"title": doc["title"], "category": doc.get("category"), "is_published": doc.get("is_published")},
    )
    return _out(doc)


@router.post("/{notice_ref}/document")
async def upload_notice_document(notice_ref: str,
                                   kind: str = Form("primary"),
                                   file: UploadFile = File(...),
                                   admin=Depends(require_role(
                                       "admin", "reviewer", "legal_counsel"))):
    """Upload the primary tender/RFP/RFQ document, or an additional attachment.
    kind: 'primary' (single canonical doc, overwrites) | 'attachment' (appended)."""
    notice = await db.notices.find_one({"notice_ref": notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    await require_notice_permission(admin, "modify", notice.get("document_type", "*"))

    body = await file.read()
    if len(body) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds pilot upload limit")
    _validate_document_bytes(body, file.filename or "", file.content_type or "")
    key = f"notice-docs/{notice_ref}/{uuid.uuid4().hex}_{file.filename}"
    await db.uploads.insert_one({
        "key": key, "content_type": file.content_type,
        "size_bytes": len(body),
        "data_b64": base64.b64encode(body).decode("ascii"),
        "created_at": now_iso(),
    })
    meta = {"file_name": file.filename, "url": f"/api/v1/uploads/files/{key}",
            "content_type": file.content_type or "application/octet-stream",
            "size_bytes": len(body), "uploaded_at": now_iso(),
            "uploaded_by": admin["email"]}
    if kind == "primary":
        await db.notices.update_one({"notice_ref": notice_ref},
                                     {"$set": {"primary_document": meta}})
    else:
        await db.notices.update_one({"notice_ref": notice_ref},
                                     {"$push": {"attachments": meta}})
    await audit_log("notice.document_upload", admin, "notice", notice_ref,
                    {"kind": kind, "file_name": file.filename})
    return {"ok": True, "kind": kind, **meta}


@router.delete("/{notice_ref}")
async def delete_notice(notice_ref: str,
                         admin=Depends(require_role("admin"))):
    notice = await db.notices.find_one({"notice_ref": notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    await require_notice_permission(admin, "delete", notice.get("document_type", "*"))
    await db.notices.delete_one({"notice_ref": notice_ref})
    await audit_log("notice.delete", admin, "notice", notice_ref, {})
    return {"ok": True}


@router.post("/admin/cleanup-bogus-documents")
async def cleanup_bogus_documents(admin=Depends(require_role("admin"))):
    """One-shot admin cleanup. Detach any primary_document or attachment whose
    stored bytes are too small (< 200 bytes) OR whose stored magic bytes do
    not match the declared extension. Doesn't delete the underlying uploads
    document (in case admin wants to inspect), it just detaches from notices.
    """
    cleaned = []
    async for notice in db.notices.find({}):
        changed = False
        upd: dict = {}
        pd = notice.get("primary_document") or {}
        if pd:
            key = (pd.get("url") or "").replace("/api/v1/uploads/files/", "", 1)
            u = await db.uploads.find_one({"key": key}) if key else None
            body = base64.b64decode(u["data_b64"]) if u else b""
            if not _looks_valid(body, pd.get("file_name") or ""):
                upd["primary_document"] = None
                changed = True
                cleaned.append({"notice_ref": notice["notice_ref"], "kind": "primary",
                                 "file_name": pd.get("file_name"),
                                 "size_bytes": len(body)})
        kept_att = []
        removed_att = []
        for a in (notice.get("attachments") or []):
            key = (a.get("url") or "").replace("/api/v1/uploads/files/", "", 1)
            u = await db.uploads.find_one({"key": key}) if key else None
            body = base64.b64decode(u["data_b64"]) if u else b""
            if _looks_valid(body, a.get("file_name") or ""):
                kept_att.append(a)
            else:
                removed_att.append(a)
                cleaned.append({"notice_ref": notice["notice_ref"], "kind": "attachment",
                                 "file_name": a.get("file_name"),
                                 "size_bytes": len(body)})
        if removed_att:
            upd["attachments"] = kept_att
            changed = True
        if changed:
            await db.notices.update_one({"_id": notice["_id"]}, {"$set": upd})
    await audit_log("notice.cleanup_bogus", admin, "notice", "*", {"count": len(cleaned)})
    return {"ok": True, "cleaned_count": len(cleaned), "cleaned": cleaned[:100]}


def _looks_valid(body: bytes, filename: str) -> bool:
    """Best-effort validation used by the cleanup pass. Rejects tiny files
    and mismatched magic bytes; unknown extensions pass-through so we never
    accidentally erase a legitimate but exotic upload."""
    if len(body) < _MIN_DOC_BYTES:
        return False
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return body[:5] == b"%PDF-"
    if ext in ("docx", "xlsx", "pptx"):
        return body[:4] == b"PK\x03\x04"
    if ext == "png":
        return body[:8] == b"\x89PNG\r\n\x1a\n"
    if ext in ("jpg", "jpeg"):
        return body[:3] == b"\xff\xd8\xff"
    return True  # unknown extension → don't touch it


@router.get("/{notice_ref}/admin")
async def admin_get_notice(notice_ref: str, admin=Depends(require_role("admin", "reviewer"))):
    """ADMIN — see notice regardless of publish state."""
    doc = await db.notices.find_one({"notice_ref": notice_ref})
    if not doc:
        raise HTTPException(status_code=404, detail="Notice not found")
    return _out(doc)


@router.post("/{notice_ref}/publish")
async def publish_notice(notice_ref: str, admin=Depends(require_role("admin"))):
    r = await db.notices.update_one(
        {"notice_ref": notice_ref, "is_published": False},
        {"$set": {"is_published": True, "published_at": now_iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notice not found or already published")
    await audit_log("notice.publish", admin, "notice", notice_ref, {})
    return {"ok": True}
