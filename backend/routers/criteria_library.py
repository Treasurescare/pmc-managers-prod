"""Master criteria library: admin/reviewer-managed criteria and named criteria sets."""
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import now_iso
from routers.tender_criteria import TEMPLATES, CriterionIn
from security import require_csrf, require_role

router = APIRouter(prefix="/api/v1/criteria-library", tags=["criteria-library"])
EDITOR = Depends(require_role("admin", "reviewer"))
CSRF = [Depends(require_csrf)]


class SetIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    criteria: List[CriterionIn] = Field(min_length=1, max_length=60)


def _out(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


def _oid(x: str) -> ObjectId:
    if not ObjectId.is_valid(x):
        raise HTTPException(status_code=404, detail="Not found")
    return ObjectId(x)


def _crit(c: CriterionIn) -> dict:
    d = c.model_dump()
    d.pop("id", None)
    return d


async def _seed() -> None:
    if await db.settings.find_one({"key": "criteria_library_seeded"}):
        return
    if not await db.criteria_master.count_documents({}):
        await db.criteria_master.insert_many([{**t, "status": "active", "created_at": now_iso(), "created_by": "system"} for t in TEMPLATES])
    await db.settings.update_one({"key": "criteria_library_seeded"}, {"$set": {"value": True}}, upsert=True)


async def library() -> dict:
    await _seed()
    items = [_out(d) async for d in db.criteria_master.find({"status": "active"}).sort("title", 1)]
    sets = [_out(d) async for d in db.criteria_sets.find({"status": "active"}).sort("name", 1)]
    return {"items": items, "sets": sets}


@router.get("")
async def get_library(request: Request):
    from routers._tender_access import tender_principal
    await tender_principal(request)
    return await library()


@router.post("/items", dependencies=CSRF)
async def add_item(body: CriterionIn, user=EDITOR):
    d = {**_crit(body), "status": "active", "created_at": now_iso(), "created_by": user.get("email")}
    d["_id"] = (await db.criteria_master.insert_one(d)).inserted_id
    await audit_log("criteria_master.add", user, "criteria_master", str(d["_id"]), {"title": d["title"]})
    return _out(d)


@router.put("/items/{iid}", dependencies=CSRF)
async def edit_item(iid: str, body: CriterionIn, user=EDITOR):
    r = await db.criteria_master.update_one({"_id": _oid(iid), "status": "active"},
                                            {"$set": {**_crit(body), "updated_at": now_iso(), "updated_by": user.get("email")}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Criterion not found")
    await audit_log("criteria_master.edit", user, "criteria_master", iid, {"title": body.title})
    return _out(await db.criteria_master.find_one({"_id": _oid(iid)}))


@router.delete("/items/{iid}", dependencies=CSRF)
async def archive_item(iid: str, user=EDITOR):
    r = await db.criteria_master.update_one({"_id": _oid(iid), "status": "active"}, {"$set": {"status": "archived", "archived_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Criterion not found")
    await audit_log("criteria_master.archive", user, "criteria_master", iid, {})
    return {"ok": True}


@router.post("/sets", dependencies=CSRF)
async def add_set(body: SetIn, user=EDITOR):
    name = body.name.strip()
    if await db.criteria_sets.find_one({"name": name, "status": "active"}):
        raise HTTPException(status_code=409, detail=f"A criteria set called '{name}' already exists")
    d = {"name": name, "criteria": [_crit(c) for c in body.criteria], "status": "active", "created_at": now_iso(), "created_by": user.get("email")}
    d["_id"] = (await db.criteria_sets.insert_one(d)).inserted_id
    await audit_log("criteria_set.add", user, "criteria_set", str(d["_id"]), {"name": name, "count": len(d["criteria"])})
    return _out(d)


@router.put("/sets/{sid}", dependencies=CSRF)
async def edit_set(sid: str, body: SetIn, user=EDITOR):
    name = body.name.strip()
    if await db.criteria_sets.find_one({"name": name, "status": "active", "_id": {"$ne": _oid(sid)}}):
        raise HTTPException(status_code=409, detail=f"A criteria set called '{name}' already exists")
    r = await db.criteria_sets.update_one({"_id": _oid(sid), "status": "active"},
                                          {"$set": {"name": name, "criteria": [_crit(c) for c in body.criteria], "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Set not found")
    await audit_log("criteria_set.edit", user, "criteria_set", sid, {"name": name})
    return _out(await db.criteria_sets.find_one({"_id": _oid(sid)}))


@router.delete("/sets/{sid}", dependencies=CSRF)
async def archive_set(sid: str, user=EDITOR):
    r = await db.criteria_sets.update_one({"_id": _oid(sid), "status": "active"}, {"$set": {"status": "archived", "archived_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Set not found")
    await audit_log("criteria_set.archive", user, "criteria_set", sid, {})
    return {"ok": True}
