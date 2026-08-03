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
    from routers.committee_helpers import (
        validate_and_tag_committee_staff, build_external_records, dispatch_committee_invites,
    )
    notice = await db.notices.find_one({"notice_ref": payload.notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    if await db.committees.find_one({"notice_ref": payload.notice_ref, "status": "open"}):
        raise HTTPException(status_code=409, detail="Open committee already exists for this tender")

    await validate_and_tag_committee_staff(payload.chairperson_id, payload.member_ids)
    ext_records = build_external_records(payload.external_invitees)

    doc = {
        "notice_ref": payload.notice_ref,
        "chairperson_id": payload.chairperson_id,
        "member_ids": payload.member_ids,
        "external_invitees": ext_records,
        "quorum": payload.quorum,
        "notes": payload.notes,
        "votes": [],
        "status": "open",
        "created_by": admin["id"],
        "created_at": now_iso(),
    }
    res = await db.committees.insert_one(doc)
    doc["_id"] = res.inserted_id

    dispatch_committee_invites(notice, payload.notice_ref, ext_records)

    await audit_log("committee.create", admin, "committee", payload.notice_ref,
                    {"chair": payload.chairperson_id,
                     "members": payload.member_ids,
                     "external_count": len(ext_records)})
    return _out(doc)


@router.get("")
async def list_committees(admin=Depends(require_role("admin", "committee_member", "reviewer", "auditor"))) -> List[dict]:
    return [_out(c) async for c in db.committees.find({}).sort("created_at", -1).limit(200)]


# ---------- External invitee accept/decline (PUBLIC by token) ----------

@router.get("/external/{token}")
async def external_invite_meta(token: str):
    """PUBLIC — resolve accept token to a snapshot of the invitation."""
    c = await db.committees.find_one({"external_invitees.accept_token": token})
    if not c:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    inv = next((i for i in c.get("external_invitees", []) if i.get("accept_token") == token), None)
    notice = await db.notices.find_one({"notice_ref": c["notice_ref"]})
    return {
        "notice_ref": c["notice_ref"],
        "tender_title": (notice or {}).get("title"),
        "budget_currency": (notice or {}).get("budget_currency"),
        "budget_amount": (notice or {}).get("budget_amount"),
        "submission_deadline": (notice or {}).get("submission_deadline"),
        "invitee": {"email": inv.get("email"), "name": inv.get("name"),
                    "designation": inv.get("designation"),
                    "status": inv.get("status")} if inv else None,
    }


@router.post("/external/{token}/decision")
async def external_decision(token: str, payload: dict):
    """PUBLIC — external invitee accepts or declines. `payload` = {decision: 'accepted'|'declined'}."""
    decision = payload.get("decision")
    if decision not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="decision must be 'accepted' or 'declined'")
    c = await db.committees.find_one({"external_invitees.accept_token": token})
    if not c:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    await db.committees.update_one(
        {"_id": c["_id"], "external_invitees.accept_token": token},
        {"$set": {"external_invitees.$.status": decision,
                  "external_invitees.$.decided_at": now_iso()}},
    )
    await audit_log(f"committee.external.{decision}", None, "committee",
                    c.get("notice_ref"), {"token_tail": token[-6:]})
    return {"ok": True, "decision": decision}


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
