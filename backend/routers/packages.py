from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

import config
from db import db, next_sequence
from models import PackageIn, PackagePatchIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/packages", tags=["packages"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.get("")
async def list_packages(status: Optional[str] = None, category: Optional[str] = None,
                        limit: int = 100, offset: int = 0,
                        admin=Depends(require_role("admin", "reviewer"))):
    q: dict = {"tenant_id": admin["tenant_id"]}
    if status:
        q["status"] = status
    if category:
        q["category"] = category
    limit = max(1, min(int(limit), 500))
    total = await db.packages.count_documents(q)
    items = [_out(p) async for p in db.packages.find(q).sort("float_target_date", 1).skip(offset).limit(limit)]
    return {"items": items, "total": total}


@router.post("")
async def create_package(payload: PackageIn, admin=Depends(require_role("admin"))):
    seq = await next_sequence("package_seq")
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    package_ref = f"PMC-PKG-{year}-{seq:04d}"

    doc = payload.model_dump()
    doc.update({
        "package_ref": package_ref,
        "tenant_id": admin["tenant_id"],
        "created_by": admin["id"],
        "created_at": now_iso(),
    })
    res = await db.packages.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("package.create", admin, "package", package_ref,
                    {"title": doc["title"], "category": doc["category"]})
    return _out(doc)


@router.patch("/{package_id}")
async def update_package(package_id: str, payload: PackagePatchIn,
                         admin=Depends(require_role("admin"))):
    existing = await db.packages.find_one({"_id": ObjectId(package_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return _out(existing)
    updates["updated_at"] = now_iso()
    await db.packages.update_one({"_id": ObjectId(package_id)}, {"$set": updates})
    await audit_log("package.update", admin, "package", existing["package_ref"], updates)
    fresh = await db.packages.find_one({"_id": ObjectId(package_id)})
    return _out(fresh)
