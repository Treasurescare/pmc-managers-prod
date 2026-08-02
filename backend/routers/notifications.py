"""In-app notifications router — created by _notify_role() when bid state changes."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import current_admin

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.get("")
async def list_my_notifications(admin=Depends(current_admin)):
    # A staff member sees notifications addressed to any of their roles.
    roles = admin.get("roles") or [admin.get("role")]
    q = {"$or": [
        {"user_id": admin["id"]},
        {"role": {"$in": roles}},
    ]}
    return [_out(n) async for n in db.notifications.find(q).sort("created_at", -1).limit(50)]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, admin=Depends(current_admin)):
    r = await db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True, "read_at": now_iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(admin=Depends(current_admin)):
    roles = admin.get("roles") or [admin.get("role")]
    await db.notifications.update_many(
        {"$or": [{"user_id": admin["id"]}, {"role": {"$in": roles}}]},
        {"$set": {"read": True, "read_at": now_iso()}},
    )
    return {"ok": True}
