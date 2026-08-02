"""Bid Committee router — per-tender committee, formed from admin pool."""
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.committee import CommitteeCreateIn, CommitteeVoteIn, CommitteeCloseIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/committees", tags=["committees"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.post("")
async def create_committee(payload: CommitteeCreateIn,
                           admin=Depends(require_role("admin"))) -> dict:
    notice = await db.notices.find_one({"notice_ref": payload.notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    if await db.committees.find_one({"notice_ref": payload.notice_ref, "status": "open"}):
        raise HTTPException(status_code=409, detail="Open committee already exists for this tender")
    # Ensure all referenced staff exist and mark them with `committee_member` role
    all_ids = list({payload.chairperson_id, *payload.member_ids})
    staff_docs = await db.admin_users.find({"_id": {"$in": [ObjectId(x) for x in all_ids]}}).to_list(length=100)
    if len(staff_docs) != len(all_ids):
        raise HTTPException(status_code=400, detail="One or more staff IDs are invalid")
    for s in staff_docs:
        roles = s.get("roles") or [s.get("role") or "admin"]
        if "committee_member" not in roles:
            roles.append("committee_member")
            await db.admin_users.update_one({"_id": s["_id"]}, {"$set": {"roles": roles}})

    doc = {
        "notice_ref": payload.notice_ref,
        "chairperson_id": payload.chairperson_id,
        "member_ids": payload.member_ids,
        "quorum": payload.quorum,
        "notes": payload.notes,
        "votes": [],  # [{bid_id, staff_id, vote, remarks, at}]
        "status": "open",
        "created_by": admin["id"],
        "created_at": now_iso(),
    }
    res = await db.committees.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("committee.create", admin, "committee", payload.notice_ref,
                    {"chair": payload.chairperson_id, "members": payload.member_ids})
    return _out(doc)


@router.get("")
async def list_committees(admin=Depends(require_role("admin", "committee_member", "reviewer", "auditor"))) -> List[dict]:
    return [_out(c) async for c in db.committees.find({}).sort("created_at", -1).limit(200)]


@router.post("/vote")
async def cast_vote(payload: CommitteeVoteIn,
                    admin=Depends(require_role("admin", "committee_member"))) -> dict:
    c = await db.committees.find_one({"_id": ObjectId(payload.committee_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Committee not found")
    if c.get("status") != "open":
        raise HTTPException(status_code=400, detail="Committee closed")
    if admin["id"] not in ({c.get("chairperson_id"), *c.get("member_ids", [])}):
        raise HTTPException(status_code=403, detail="Not a member of this committee")
    entry = {"bid_id": payload.bid_id, "staff_id": admin["id"], "staff_email": admin["email"],
             "vote": payload.vote, "remarks": payload.remarks, "at": now_iso()}
    await db.committees.update_one({"_id": ObjectId(payload.committee_id)},
                                   {"$push": {"votes": entry}})
    await audit_log("committee.vote", admin, "committee", payload.committee_id, entry)
    return {"ok": True}


@router.post("/close")
async def close_committee(payload: CommitteeCloseIn,
                          admin=Depends(require_role("admin", "committee_member"))) -> dict:
    c = await db.committees.find_one({"_id": ObjectId(payload.committee_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Committee not found")
    if c.get("chairperson_id") != admin["id"] and admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only chair or admin can close")
    updates = {"status": payload.decision, "closed_at": now_iso(),
               "closed_by": admin["id"], "close_remarks": payload.remarks}
    if payload.decision == "closed_awarded":
        if not payload.awarded_bid_id:
            raise HTTPException(status_code=400, detail="awarded_bid_id required when awarding")
        updates["awarded_bid_id"] = payload.awarded_bid_id
        await db.bids.update_one({"_id": ObjectId(payload.awarded_bid_id)},
                                 {"$set": {"status": "awarded", "awarded_at": now_iso()}})
        # Mark other bids on same tender as closed
        await db.bids.update_many(
            {"notice_ref": c["notice_ref"], "_id": {"$ne": ObjectId(payload.awarded_bid_id)},
             "status": {"$nin": ["rejected", "withdrawn", "awarded"]}},
            {"$set": {"status": "closed", "closed_at": now_iso()}},
        )
    await db.committees.update_one({"_id": ObjectId(payload.committee_id)}, {"$set": updates})
    await audit_log("committee.close", admin, "committee", payload.committee_id, updates)
    return {"ok": True}


@router.post("/{committee_id}/deadline-close")
async def deadline_auto_close(committee_id: str,
                              admin=Depends(require_role("admin"))) -> dict:
    """Manual trigger of the "close on deadline" rule.
    Reads the notice.submission_deadline; if past, marks the committee status
    as `deadline_closed` (no award). Committee still needs to run a final vote."""
    c = await db.committees.find_one({"_id": ObjectId(committee_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Committee not found")
    notice = await db.notices.find_one({"notice_ref": c["notice_ref"]})
    deadline = (notice or {}).get("submission_deadline")
    if not deadline or deadline > datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Submission deadline not yet reached")
    await db.committees.update_one({"_id": ObjectId(committee_id)},
                                   {"$set": {"deadline_locked": True, "deadline_locked_at": now_iso()}})
    return {"ok": True, "deadline_locked": True}
