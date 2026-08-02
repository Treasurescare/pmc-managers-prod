"""Internal chat router — thread per (context_type, context_id).

Messages support attachments (files, photos, videos) using the existing uploads
router. Attachments carry {kind, key, filename, content_type, size_bytes}.
Delete is soft (message.deleted=true) so the audit trail is preserved.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.chat import ChatMessageIn
from models.base import BaseDocument, now_iso
from security import current_admin, require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.post("/messages")
async def send_message(payload: ChatMessageIn, admin=Depends(current_admin)) -> dict:
    doc = {
        "context_type": payload.context_type,
        "context_id": payload.context_id,
        "body": payload.body,
        "attachments": payload.attachments,
        "reply_to": payload.reply_to,
        "by_id": admin["id"],
        "by_email": admin["email"],
        "by_name": admin.get("name"),
        "deleted": False,
        "created_at": now_iso(),
    }
    res = await db.chat_messages.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _out(doc)


@router.get("/messages")
async def list_messages(context_type: str, context_id: str,
                        admin=Depends(current_admin)) -> List[dict]:
    q = {"context_type": context_type, "context_id": context_id}
    cursor = db.chat_messages.find(q).sort("created_at", 1).limit(500)
    return [_out(m) async for m in cursor]


@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, admin=Depends(current_admin)) -> dict:
    m = await db.chat_messages.find_one({"_id": ObjectId(message_id)})
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    # Only author or admin may delete
    if m.get("by_id") != admin["id"] and admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.chat_messages.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"deleted": True, "deleted_at": now_iso(), "deleted_by": admin["email"]}},
    )
    return {"ok": True}
