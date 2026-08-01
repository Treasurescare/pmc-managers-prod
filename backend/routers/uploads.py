"""Upload endpoint — Phase 1 pilot.

Contract mirrors Build Sheet v2 Part 4 `POST /v1/uploads/presign` so the
frontend flow is unchanged when we swap to real S3 presign in Phase 2.

Phase 1: returns a direct-upload URL on this backend (`/api/v1/uploads/direct`)
+ a synthetic key. Phase 2: returns a real S3 presigned PUT URL from AWS.
"""
import base64
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import config
from db import db
from models.base import now_iso

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


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
async def get_file(key: str):
    doc = await db.uploads.find_one({"key": key})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import Response
    body = base64.b64decode(doc["data_b64"])
    return Response(content=body, media_type=doc.get("content_type", "application/octet-stream"))
