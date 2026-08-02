"""Site Inspection router (Certifier role)."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.inspection import InspectionAssignIn, InspectionUpdateIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/inspections", tags=["inspections"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.post("")
async def assign_inspection(payload: InspectionAssignIn,
                            admin=Depends(require_role("admin"))) -> dict:
    cert = await db.admin_users.find_one({"_id": ObjectId(payload.certifier_id)})
    if not cert:
        raise HTTPException(status_code=404, detail="Certifier staff not found")
    roles = cert.get("roles") or [cert.get("role")]
    if "certifier" not in roles:
        raise HTTPException(status_code=400, detail="Staff does not hold certifier role")

    doc = {
        "notice_ref": payload.notice_ref,
        "bid_id": payload.bid_id,
        "certifier_id": payload.certifier_id,
        "certifier_email": cert.get("email"),
        "certifier_name": cert.get("name"),
        "scheduled_at": payload.scheduled_at,
        "location": payload.location,
        "notes": payload.notes,
        "status": "scheduled",
        "result": "pending",
        "media": [],
        "created_by": admin["id"],
        "created_at": now_iso(),
    }
    res = await db.inspections.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("inspection.assign", admin, "inspection", str(res.inserted_id),
                    {"certifier": cert.get("email"), "notice": payload.notice_ref})
    return _out(doc)


@router.get("")
async def list_inspections(certifier_id: Optional[str] = None,
                           notice_ref: Optional[str] = None,
                           admin=Depends(require_role("admin", "certifier", "reviewer", "auditor"))) -> List[dict]:
    q: dict = {}
    if certifier_id == "me":
        q["certifier_id"] = admin["id"]
    elif certifier_id:
        q["certifier_id"] = certifier_id
    if notice_ref:
        q["notice_ref"] = notice_ref
    return [_out(i) async for i in db.inspections.find(q).sort("scheduled_at", -1).limit(200)]


@router.patch("/{inspection_id}")
async def update_inspection(inspection_id: str, payload: InspectionUpdateIn,
                            admin=Depends(require_role("admin", "certifier"))) -> dict:
    ins = await db.inspections.find_one({"_id": ObjectId(inspection_id)})
    if not ins:
        raise HTTPException(status_code=404, detail="Not found")
    if admin.get("role") == "certifier" and ins.get("certifier_id") != admin["id"]:
        raise HTTPException(status_code=403, detail="Not your inspection")

    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = now_iso()
    await db.inspections.update_one({"_id": ObjectId(inspection_id)}, {"$set": updates})
    fresh = await db.inspections.find_one({"_id": ObjectId(inspection_id)})
    await audit_log("inspection.update", admin, "inspection", inspection_id, updates)
    return _out(fresh)


@router.post("/{inspection_id}/media")
async def add_media(inspection_id: str, item: dict,
                    admin=Depends(require_role("admin", "certifier"))) -> dict:
    """Append a photo/video reference. `item` = {kind, key, filename, content_type, size_bytes}."""
    ins = await db.inspections.find_one({"_id": ObjectId(inspection_id)})
    if not ins:
        raise HTTPException(status_code=404, detail="Not found")
    if admin.get("role") == "certifier" and ins.get("certifier_id") != admin["id"]:
        raise HTTPException(status_code=403, detail="Not your inspection")
    item.setdefault("uploaded_at", now_iso())
    item.setdefault("uploaded_by", admin["email"])
    await db.inspections.update_one({"_id": ObjectId(inspection_id)}, {"$push": {"media": item}})
    return {"ok": True, "media": item}


@router.delete("/{inspection_id}/media/{index}")
async def delete_media(inspection_id: str, index: int,
                       admin=Depends(require_role("admin", "certifier"))) -> dict:
    ins = await db.inspections.find_one({"_id": ObjectId(inspection_id)})
    if not ins:
        raise HTTPException(status_code=404, detail="Not found")
    if admin.get("role") == "certifier" and ins.get("certifier_id") != admin["id"]:
        raise HTTPException(status_code=403, detail="Not your inspection")
    media = ins.get("media", [])
    if index < 0 or index >= len(media):
        raise HTTPException(status_code=400, detail="Bad index")
    removed = media.pop(index)
    await db.inspections.update_one({"_id": ObjectId(inspection_id)}, {"$set": {"media": media}})
    await audit_log("inspection.media_delete", admin, "inspection", inspection_id,
                    {"filename": removed.get("filename")})
    return {"ok": True}
