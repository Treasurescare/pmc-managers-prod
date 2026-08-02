"""CRM: Tasks + Followups router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.task import TaskCreateIn, TaskUpdateIn, FollowupIn
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from audit import audit_log

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.post("")
async def create_task(payload: TaskCreateIn, admin=Depends(current_admin)) -> dict:
    doc = payload.model_dump()
    doc.update({
        "status": "open", "created_by": admin["id"],
        "created_by_email": admin["email"], "created_at": now_iso(),
        "followups": [],
    })
    res = await db.tasks.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("task.create", admin, "task", str(res.inserted_id),
                    {"title": payload.title, "assignee": payload.assignee_id})
    return _out(doc)


@router.get("")
async def list_tasks(assignee_id: Optional[str] = None, status: Optional[str] = None,
                     related_type: Optional[str] = None, related_id: Optional[str] = None,
                     admin=Depends(current_admin)) -> List[dict]:
    q: dict = {}
    if assignee_id == "me":
        q["assignee_id"] = admin["id"]
    elif assignee_id:
        q["assignee_id"] = assignee_id
    if status:
        q["status"] = status
    if related_type:
        q["related_type"] = related_type
    if related_id:
        q["related_id"] = related_id
    return [_out(t) async for t in db.tasks.find(q).sort("created_at", -1).limit(200)]


@router.patch("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdateIn, admin=Depends(current_admin)) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = now_iso()
    r = await db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    fresh = await db.tasks.find_one({"_id": ObjectId(task_id)})
    await audit_log("task.update", admin, "task", task_id, updates)
    return _out(fresh)


@router.delete("/{task_id}")
async def delete_task(task_id: str, admin=Depends(require_role("admin"))) -> dict:
    r = await db.tasks.delete_one({"_id": ObjectId(task_id)})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit_log("task.delete", admin, "task", task_id, {})
    return {"ok": True}


@router.post("/{task_id}/followups")
async def add_followup(task_id: str, payload: FollowupIn, admin=Depends(current_admin)) -> dict:
    entry = {"message": payload.message, "attachments": payload.attachments,
             "by_id": admin["id"], "by_email": admin["email"], "at": now_iso()}
    r = await db.tasks.update_one({"_id": ObjectId(task_id)}, {"$push": {"followups": entry}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    await audit_log("task.followup", admin, "task", task_id, {"len": len(payload.message)})
    return {"ok": True, "followup": entry}


@router.delete("/{task_id}/followups/{index}")
async def delete_followup(task_id: str, index: int, admin=Depends(require_role("admin"))) -> dict:
    t = await db.tasks.find_one({"_id": ObjectId(task_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    followups = t.get("followups", [])
    if index < 0 or index >= len(followups):
        raise HTTPException(status_code=400, detail="Bad index")
    followups.pop(index)
    await db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {"followups": followups}})
    return {"ok": True}
