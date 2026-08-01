import csv
import io
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from bson import ObjectId
from pydantic import BaseModel

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
                        limit: int = 500, offset: int = 0,
                        admin=Depends(require_role("admin", "reviewer"))):
    q: dict = {"tenant_id": admin["tenant_id"]}
    if status:
        q["status"] = status
    if category:
        q["category"] = category
    limit = max(1, min(int(limit), 1000))
    total = await db.packages.count_documents(q)
    items = [_out(p) async for p in db.packages.find(q).sort("float_target_date", 1).skip(offset).limit(limit)]
    return {"items": items, "total": total}


async def _next_package_ref() -> str:
    from datetime import datetime, timezone
    seq = await next_sequence("package_seq")
    year = datetime.now(timezone.utc).year
    return f"PMC-PKG-{year}-{seq:04d}"


@router.post("")
async def create_package(payload: PackageIn, admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc.update({
        "package_ref": await _next_package_ref(),
        "tenant_id": admin["tenant_id"],
        "created_by": admin["id"],
        "created_at": now_iso(),
    })
    res = await db.packages.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("package.create", admin, "package", doc["package_ref"],
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


class StatusUpdate(BaseModel):
    status: str


VALID_STATUSES = ("backlog", "scoping", "sbd_draft", "ready", "published", "cancelled")


@router.post("/{package_id}/status")
async def move_package_status(package_id: str, payload: StatusUpdate,
                              admin=Depends(require_role("admin"))):
    """Fast endpoint used by the drag-status board."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
    existing = await db.packages.find_one({"_id": ObjectId(package_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    if existing["status"] == payload.status:
        return _out(existing)
    await db.packages.update_one(
        {"_id": ObjectId(package_id)},
        {"$set": {"status": payload.status, "updated_at": now_iso()}},
    )
    await audit_log("package.status", admin, "package", existing["package_ref"],
                    {"from": existing["status"], "to": payload.status})
    fresh = await db.packages.find_one({"_id": ObjectId(package_id)})
    return _out(fresh)


@router.post("/import")
async def import_packages_csv(file: UploadFile = File(...),
                              admin=Depends(require_role("admin"))):
    """Bulk import from CSV.

    Expected columns (case-insensitive, order-independent):
      title, category, phase, value, currency, float_target_date, status

    `status` defaults to `backlog` if omitted or invalid.
    Rows with missing `title` or `category` are skipped and reported.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    body = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(body))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty or invalid CSV")
    header_map = {name.lower().strip(): name for name in reader.fieldnames}

    def col(row: dict, name: str) -> Optional[str]:
        real = header_map.get(name)
        return row.get(real) if real else None

    created, skipped, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        title = (col(row, "title") or "").strip()
        category = (col(row, "category") or "").strip()
        if not title or not category:
            skipped += 1
            errors.append({"row": i, "reason": "missing title or category"})
            continue
        status_val = (col(row, "status") or "backlog").strip().lower()
        if status_val not in VALID_STATUSES:
            status_val = "backlog"
        value_str = (col(row, "value") or "").replace(",", "").strip()
        try:
            value_num = float(value_str) if value_str else None
        except ValueError:
            value_num = None
        doc = {
            "title": title,
            "category": category,
            "phase": (col(row, "phase") or None),
            "value": value_num,
            "currency": (col(row, "currency") or "USD").strip() or "USD",
            "float_target_date": (col(row, "float_target_date") or None),
            "status": status_val,
            "attached_documents": [],
            "package_ref": await _next_package_ref(),
            "tenant_id": admin["tenant_id"],
            "created_by": admin["id"],
            "created_at": now_iso(),
        }
        await db.packages.insert_one(doc)
        created += 1

    await audit_log("package.import", admin, "package_batch", "csv",
                    {"created": created, "skipped": skipped})
    return {"ok": True, "created": created, "skipped": skipped, "errors": errors[:20]}
