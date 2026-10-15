from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response
from bson import ObjectId
import base64, uuid, io, zipfile

import config
from db import db, next_sequence
from models import NoticeIn, NoticePatchIn
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
    # v52bl — compute a flat emd_amount + emd_currency on the public response
    # so the Notice detail page shows the real EMD instead of "—". Backward
    # compatible: we keep emd_config as the source of truth.
    cfg = d.get("emd_config") or {}
    budget = d.get("budget_amount") or 0
    fixed = float(cfg.get("fixed_amount") or 0)
    pct = float(cfg.get("percentage") or 0)
    cur = cfg.get("currency") or d.get("budget_currency") or "USD"
    emd_amt = None
    if fixed > 0:
        emd_amt = fixed
    elif pct > 0 and budget:
        emd_amt = round(float(budget) * (pct / 100.0), 2)
    # Always expose the key so public consumers (landing cards + tests) can
    # read a stable shape; emd_amount may be None when no EMD is configured.
    d["emd_amount"] = emd_amt
    d["emd_currency"] = cur
    d["emd_percentage"] = pct if pct > 0 else None
    return d


@router.get("/admin/all")
async def list_notices_admin(
    limit: int = 200,
    offset: int = 0,
    created_by_email: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    admin=Depends(require_role("admin", "reviewer", "auditor", "legal_counsel",
                                "committee_member", "certifier", "accounting")),
):
    """Admin-only — list EVERY notice (published + draft) so the Notices tab
    reflects newly-created drafts immediately after creation.
    Bucket A fix — the public `GET /` filters by is_published=true, hiding
    drafts from the admin panel and giving the impression that "Create Notice"
    is broken."""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    q = {"tenant_id": admin["tenant_id"]}
    # v52v — Created-by/from/to filters for the shared admin filter bar.
    if created_by_email:
        q["created_by_email"] = {"$regex": created_by_email.strip(), "$options": "i"}
    if created_from or created_to:
        rng: dict = {}
        if created_from: rng["$gte"] = f"{created_from[:10]}T00:00:00"
        if created_to:   rng["$lte"] = f"{created_to[:10]}T23:59:59.999"
        q["created_at"] = rng
    cursor = db.notices.find(q).sort("created_at", -1).skip(offset).limit(limit)
    total = await db.notices.count_documents(q)
    items = [_out(t) async for t in cursor]
    # Bug #57/#58/#66 fix — force no-store so newly-created drafts appear
    # instantly. CloudFront was caching /admin/all responses briefly and
    # making testers think their draft "disappeared".
    return JSONResponse(
        content={"items": items, "total": total, "limit": limit, "offset": offset},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate",
                 "Pragma": "no-cache", "Expires": "0"},
    )


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
    # v52cu — no-store so a notice appears on the landing page the moment the
    # admin hits Publish. Previously this route sent no cache headers, so
    # CloudFront / the browser could serve a briefly-stale list.
    return JSONResponse(
        content={"items": items, "total": total, "limit": limit, "offset": offset},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate",
                 "Pragma": "no-cache", "Expires": "0"},
    )


@router.get("/{notice_ref}")
async def get_notice(notice_ref: str):
    """PUBLIC — notice detail. No auth. Returns 404 if unpublished or missing."""
    doc = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Notice not found")
    out = _out(doc)
    # Wave 39 — attach active corrigenda so the public page can show the banner.
    cursor = db.corrigenda.find({"notice_ref": notice_ref, "is_active": True})\
                          .sort("corrigendum_no", 1)
    corrigenda = []
    async for c in cursor:
        c_out = BaseDocument.out(c)
        c_out.pop("pdf_bytes", None)
        corrigenda.append(c_out)
    out["corrigenda"] = corrigenda
    out["corrigenda_count"] = len(corrigenda)
    return out


@router.post("")
async def create_notice(payload: NoticeIn, admin=Depends(require_role(
        "admin", "reviewer", "legal_counsel", "committee_member"))):
    """Create + optionally publish a notice. Permissions Matrix enforced."""
    await require_notice_permission(admin, "create", payload.document_type)
    if payload.is_published:
        await require_notice_permission(admin, "publish", payload.document_type)
    # v52bl — refuse notices with no indicative value. Budget must be > 0.
    if not payload.budget_amount or float(payload.budget_amount) <= 0:
        raise HTTPException(status_code=422,
            detail="Budget amount must be greater than zero. A tender with no indicative value cannot be published.")
    # v52bo — EMD is allowed to be zero (walk-in tenders, free RFQs, pre-qualifications).
    # Only budget stays mandatory.
    # v52t — date-chain: a brand-new notice cannot open with a past deadline,
    # and the pre-bid meeting must happen on or before the deadline.
    from routers.date_rules import require_future, require_order
    require_future(payload.submission_deadline, "Bid submission deadline")
    require_order(payload.submission_deadline, "Bid submission deadline",
                  payload.pre_bid_meeting_date, "Pre-bid meeting date")
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
        # v51w — surface the creator's email so admins/vendors can see who
        # posted the notice without a join. created_by (the id) stays
        # internal-only (_out strips it).
        "created_by_email": admin.get("email"),
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
        # v52cz rev3 — tag as a public notice attachment so anonymous bidders
        # can download individual files from the Documents tab via
        # /api/v1/uploads/public-files/{key} (publication still enforced).
        "scope": "notice-attachments", "notice_ref": notice_ref,
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


@router.patch("/{notice_ref}")
async def update_notice(notice_ref: str, payload: NoticePatchIn,
                         admin=Depends(require_role(
                             "admin", "reviewer", "legal_counsel", "committee_member"))):
    """Edit an existing notice. Published notices can be edited by admins but
    the publish-state can only be flipped by callers with publish rights.
    Partial body: only keys present in the request are $set, so callers like
    the Escrow routing picker can PATCH just `escrow_account_id`."""
    notice = await db.notices.find_one({"notice_ref": notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    await require_notice_permission(admin, "modify", notice.get("document_type", "*"))

    updates = payload.model_dump(exclude_unset=True)
    # v52t — date-chain on edits: ordering only (legacy notices may
    # legitimately carry past dates, so no "must be ≥ today" here).
    if "submission_deadline" in updates or "pre_bid_meeting_date" in updates:
        from routers.date_rules import require_order
        require_order(
            updates.get("submission_deadline", notice.get("submission_deadline")),
            "Bid submission deadline",
            updates.get("pre_bid_meeting_date", notice.get("pre_bid_meeting_date")),
            "Pre-bid meeting date",
        )
    # Primary document / attachments are managed through the dedicated upload
    # routes — never let a PATCH overwrite them, so a plain "save edits" never
    # drops a file the admin uploaded via the edit modal.
    updates.pop("primary_document", None)
    updates.pop("attachments", None)
    # tenant_id is immutable after creation.
    updates.pop("tenant_id", None)

    was_published = bool(notice.get("is_published"))
    now_pub = bool(updates.get("is_published"))
    if (not was_published) and now_pub:
        await require_notice_permission(admin, "publish", updates.get("document_type"))
        updates["published_at"] = now_iso()

    # Re-apply KZ auto-licence attach so category changes refresh licences too.
    if (updates.get("delivery_country") or "").upper() == "KZ":
        auto = config.KZ_CATEGORY_LICENSE_MAP.get(updates.get("category"), [])
        updates["required_licenses"] = list({*(updates.get("required_licenses") or []), *auto})

    updates["updated_at"] = now_iso()
    updates["updated_by"] = admin["id"]
    await db.notices.update_one({"notice_ref": notice_ref}, {"$set": updates})
    await audit_log("notice.update", admin, "notice", notice_ref,
                    {"title": updates.get("title"), "is_published": now_pub,
                     "fields_changed": sorted(k for k in updates if k not in ("updated_at", "updated_by"))})
    doc = await db.notices.find_one({"notice_ref": notice_ref})
    return _out(doc)


@router.delete("/{notice_ref}/document")
async def delete_notice_document(notice_ref: str,
                                   kind: str,
                                   file_name: Optional[str] = None,
                                   admin=Depends(require_role(
                                       "admin", "reviewer", "legal_counsel"))):
    """Detach a notice document.
    kind='primary' -> clears primary_document.
    kind='attachment' -> removes the attachment matching file_name."""
    notice = await db.notices.find_one({"notice_ref": notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    await require_notice_permission(admin, "modify", notice.get("document_type", "*"))
    if kind == "primary":
        await db.notices.update_one({"notice_ref": notice_ref},
                                     {"$set": {"primary_document": None}})
    elif kind == "attachment":
        if not file_name:
            raise HTTPException(status_code=400, detail="file_name required for attachment delete")
        await db.notices.update_one({"notice_ref": notice_ref},
                                     {"$pull": {"attachments": {"file_name": file_name}}})
    else:
        raise HTTPException(status_code=400, detail="kind must be 'primary' or 'attachment'")
    await audit_log("notice.document_delete", admin, "notice", notice_ref,
                    {"kind": kind, "file_name": file_name})
    return {"ok": True}


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


# v52cy — PUBLIC "Download pack" endpoint. Builds a zip of the primary
# document + every attachment on a published notice. No auth required —
# this is how the public Notice Board exposes a one-click download for all
# tender documents (the earlier flow tried `/api/v1/uploads/files/{key}`
# which is protected and 401s for anonymous visitors).
@router.get("/{notice_ref}/pack")
async def download_notice_pack(notice_ref: str):
    doc = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Notice not found or not yet published")

    files: list[tuple[str, bytes]] = []
    seen_names: set[str] = set()

    def _pick_name(fn: str) -> str:
        base = (fn or "document").replace("/", "_").replace("\\", "_")
        name = base
        i = 1
        while name in seen_names:
            if "." in base:
                stem, ext = base.rsplit(".", 1)
                name = f"{stem} ({i}).{ext}"
            else:
                name = f"{base} ({i})"
            i += 1
        seen_names.add(name)
        return name

    async def _load(url_or_key: Optional[str]) -> bytes:
        if not url_or_key:
            return b""
        key = (url_or_key or "").replace("/api/v1/uploads/files/", "", 1)
        u = await db.uploads.find_one({"key": key}) if key else None
        return base64.b64decode(u["data_b64"]) if u and u.get("data_b64") else b""

    pd = doc.get("primary_document") or {}
    if pd:
        body = await _load(pd.get("url"))
        if body:
            files.append((_pick_name(pd.get("file_name") or "notice.pdf"), body))

    for a in (doc.get("attachments") or []):
        body = await _load(a.get("url"))
        if body:
            files.append((_pick_name(a.get("file_name") or "attachment"), body))

    if not files:
        raise HTTPException(status_code=404, detail="No documents have been published against this notice yet")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in files:
            zf.writestr(name, body)
        # README manifest helps the recipient know what's inside.
        manifest = (
            f"PMC Managers — Tender Pack\n"
            f"Notice reference: {notice_ref}\n"
            f"Title: {doc.get('title') or ''}\n"
            f"Published at: {doc.get('published_at') or ''}\n"
            f"Delivery country: {doc.get('delivery_country') or ''}\n"
            f"Files included:\n"
            + "".join(f"  - {name}\n" for name, _ in files)
        )
        zf.writestr("README.txt", manifest)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{notice_ref}-tender-pack.zip"',
            "Cache-Control": "no-store",
        },
    )
