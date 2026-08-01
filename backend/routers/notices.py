from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

import config
from db import db, next_sequence
from models import NoticeIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/notices", tags=["notices"])


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
async def create_notice(payload: NoticeIn, admin=Depends(require_role("admin"))):
    """ADMIN — create + optionally publish a notice."""
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
