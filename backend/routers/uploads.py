"""Upload endpoint — Phase 1 pilot.

Contract mirrors Build Sheet v2 Part 4 `POST /v1/uploads/presign` so the
frontend flow is unchanged when we swap to real S3 presign in Phase 2.

Phase 1: returns a direct-upload URL on this backend (`/api/v1/uploads/direct`)
+ a synthetic key. Phase 2: returns a real S3 presigned PUT URL from AWS.

v50k — Download gating:
Any file byte stream served by `/api/v1/uploads/files/{key}` now requires
an authenticated session (admin bearer token OR vendor cookie). Public
notice JSON remains open so the Notice Board can list titles; only the
attachment downloads themselves are gated. This closes the pre-launch
security requirement that "without supplier or vendor login no one can
download any document or notice".
"""
import base64
import io
import uuid
import zipfile
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
import config
from db import db
from models.base import now_iso
from security import current_admin as _bearer_admin
from routers.vendor_auth import current_vendor

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


async def _require_any_signed_in(request: Request) -> dict:
    """Pass if the caller is a signed-in admin (Bearer token) OR a signed-in
    vendor (vendor_token cookie). Raise 401 otherwise so the browser's auth
    UX kicks in cleanly."""
    # Try admin bearer first (no CSRF required for a safe GET).
    try:
        admin = await _bearer_admin(request)
        if admin:
            return {"kind": "admin", "id": admin.get("id"), "email": admin.get("email")}
    except Exception:
        pass
    # Try vendor cookie.
    try:
        vendor = await current_vendor(request)
        if vendor:
            return {"kind": "vendor", "id": vendor.get("id"), "email": vendor.get("email")}
    except HTTPException:
        pass
    except Exception:
        pass
    raise HTTPException(status_code=401,
                         detail="Sign in to download tender documents")


class PresignRequest(BaseModel):
    file_name: str
    content_type: str = "application/octet-stream"
    scope: str = "vendor-docs"  # vendor-docs | registration-docs | notice-attachments | milestone-evidence
    size_bytes: int = 0


@router.post("/presign")
async def presign_upload(req: PresignRequest):
    """Phase-1 pilot: returns a direct-upload endpoint URL + storage key.
    Frontend uploads to `direct_url` with the returned `key` as a header/param.
    Phase 2: this will return a real S3 presigned PUT URL."""
    if req.size_bytes and req.size_bytes > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {config.MAX_UPLOAD_BYTES} bytes limit")
    key = f"{req.scope}/{uuid.uuid4().hex}_{req.file_name}"
    # In pilot we return our own upload endpoint. In Phase 2, replace with boto3 presigned URL.
    return {
        "key": key,
        "direct_url": f"/api/v1/uploads/direct",
        "phase": "pilot",  # frontend switches behavior only if phase == "s3"
    }


@router.post("/direct")
async def upload_direct(key: str = Form(...), file: UploadFile = File(...)):
    """Pilot direct-upload — stores the file inline in Mongo as base64.
    Replace with S3 in Phase 2. Kept small (5 MB max)."""
    body = await file.read()
    if len(body) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds pilot upload limit")
    encoded = base64.b64encode(body).decode("ascii")
    await db.uploads.insert_one({
        "key": key,
        "content_type": file.content_type,
        "size_bytes": len(body),
        "data_b64": encoded,
        "created_at": now_iso(),
    })
    # Public URL to retrieve later (see /files/{key})
    return {"key": key, "url": f"/api/v1/uploads/files/{key}", "size_bytes": len(body)}


@router.get("/files/{key:path}")
async def get_file(key: str, download: bool = False,
                    _who: dict = Depends(_require_any_signed_in)):
    return await _serve_file(key, download)


# v52cz — "Download all" for a set of previously-uploaded files. Vendors use
# this on the bid submission screen to pull every uploaded envelope/support
# document in one zip instead of clicking View on each row. Protected: only
# a signed-in admin OR vendor can bundle files they already know the keys
# for (same auth gate as /files/{key}).
class BundleRequest(BaseModel):
    keys: List[str] = Field(..., min_length=1, max_length=50)
    filename: Optional[str] = None  # output zip filename, without extension


@router.post("/bundle")
async def download_bundle(req: BundleRequest,
                           _who: dict = Depends(_require_any_signed_in)):
    """Zip the files identified by `keys` and stream the archive back.
    Keys that no longer exist are skipped and listed in the README manifest.
    Clear 404 if nothing resolves (never a silent empty zip)."""
    found: list[tuple[str, bytes]] = []
    missing: list[str] = []
    seen: set[str] = set()

    def _pick_name(fn: str) -> str:
        base = (fn or "document").replace("/", "_").replace("\\", "_")
        name = base
        i = 1
        while name in seen:
            if "." in base:
                stem, ext = base.rsplit(".", 1)
                name = f"{stem} ({i}).{ext}"
            else:
                name = f"{base} ({i})"
            i += 1
        seen.add(name)
        return name

    for raw_key in req.keys:
        key = (raw_key or "").replace("/api/v1/uploads/files/", "", 1)
        if not key:
            continue
        doc = await db.uploads.find_one({"key": key})
        if not doc or not doc.get("data_b64"):
            missing.append(key)
            continue
        body = base64.b64decode(doc["data_b64"])
        display = key.rsplit("/", 1)[-1]
        if "_" in display:
            display = display.split("_", 1)[1]
        found.append((_pick_name(display), body))

    if not found:
        raise HTTPException(status_code=404,
            detail="None of the requested files are available anymore")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in found:
            zf.writestr(name, body)
        manifest_lines = [
            "PMC Managers — Bundled download",
            f"Files included: {len(found)}",
            *(f"  - {name}" for name, _ in found),
        ]
        if missing:
            manifest_lines.append("")
            manifest_lines.append(f"Missing / expired keys ({len(missing)}):")
            manifest_lines.extend(f"  - {k}" for k in missing)
        zf.writestr("README.txt", "\n".join(manifest_lines) + "\n")
    buf.seek(0)
    out_name = (req.filename or "documents").strip() or "documents"
    # Sanitize filename: strip path separators + quotes
    safe = "".join(c for c in out_name if c.isalnum() or c in "-_. ")[:80] or "documents"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.zip"',
            "Cache-Control": "no-store",
        },
    )


# v51au — Public endpoint for notice attachments (xlsx #3, #8). The old
# /files/{key} endpoint required a signed-in user, so downloading NIT PDFs
# from the public tender page returned 401 and the frontend bounced the
# anonymous visitor back to the sign-in screen. This endpoint allows
# anonymous access ONLY for files uploaded against the "notice-attachments"
# scope AND whose parent notice is published.
@router.get("/public-files/{key:path}")
async def get_public_file(key: str, download: bool = False):
    doc = await db.uploads.find_one({"key": key})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    # Allow only notice-attachment files whose parent notice is published.
    # v52bp — corrigendum attachments are also public on a published notice.
    # v52cz rev3 — files uploaded via POST /notices/{ref}/document land under
    # notice-docs/<ref>/... WITHOUT a scope tag (legacy). Treat those as
    # public attachments of that notice, still gated on publication.
    scoped_public = doc.get("scope") in ("notice-attachments", "corrigendum-attachments")
    notice_ref = doc.get("notice_ref")
    if not scoped_public and key.startswith("notice-docs/"):
        parts = key.split("/")
        if len(parts) >= 3:
            notice_ref = notice_ref or parts[1]
            scoped_public = True
    if not scoped_public:
        raise HTTPException(status_code=403,
            detail="This file is not publicly downloadable")
    if notice_ref:
        notice = await db.notices.find_one({"notice_ref": notice_ref})
        if not notice or not notice.get("is_published"):
            raise HTTPException(status_code=403,
                detail="Parent notice is not published")
    return await _serve_file(key, download)


async def _serve_file(key: str, download: bool):
    doc = await db.uploads.find_one({"key": key})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    body = base64.b64decode(doc["data_b64"])
    display_name = key.rsplit("/", 1)[-1]
    if "_" in display_name:
        display_name = display_name.split("_", 1)[1]
    disposition = "attachment" if download else "inline"
    return Response(
        content=body,
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'{disposition}; filename="{display_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# Legacy inline body preserved below for reference; replaced by _serve_file.
async def _legacy_get_file_body(key: str, download: bool = False):
    doc = await db.uploads.find_one({"key": key})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    body = base64.b64decode(doc["data_b64"])
    # Default: serve inline so browsers render PDFs/images in a tab.
    # ?download=1 forces an attachment so the file saves to disk.
    display_name = key.rsplit("/", 1)[-1]
    if "_" in display_name:
        display_name = display_name.split("_", 1)[1]  # strip the uuid prefix
    disposition = "attachment" if download else "inline"
    return Response(
        content=body,
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'{disposition}; filename="{display_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
