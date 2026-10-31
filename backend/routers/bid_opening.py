"""Committee bid opening: envelopes open only on/after the opening date and only when every member approves."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from audit import audit_log
from bid_seal import EMD_CONFIRMED, _parse, dec_text, opening_at
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/bid-opening", tags=["bid-opening"])
VIEW = Depends(require_role("admin", "reviewer", "committee_member", "auditor"))
LIVE = {"$nin": ["withdrawn", "rejected", "draft"]}


class ApproveIn(BaseModel):
    stage: Literal["technical", "commercial"]


async def _ctx(notice_ref: str):
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    c = await db.committees.find_one({"notice_ref": notice_ref, "status": "open"})
    return n, c


def _members(c) -> list:
    if not c:
        return []
    return [m for m in dict.fromkeys([c.get("chairperson_id"), *(c.get("member_ids") or [])]) if m]


async def _blockers(n: dict, c, stage: str) -> list:
    now = datetime.now(timezone.utc)
    out = []
    if not c:
        out.append("No open committee has been formed for this tender")
    dl = _parse(n.get("submission_deadline"))
    if dl and now < dl:
        out.append("Bid submission is still open")
    oa = opening_at(n)
    if oa and now < oa:
        out.append(f"Bid opening date is {oa.isoformat()[:16].replace('T', ' ')} UTC")
    if stage == "commercial" and not n.get("technical_opened_at"):
        out.append("The technical envelopes must be opened first")
    if stage == "commercial" and n.get("technical_opened_at") and not n.get("commercial_opened_at"):
        base = {"notice_ref": n["notice_ref"], "seal_v": 1, "auction_id": None, "technical_unsealed_at": {"$ne": None}}
        if not await db.bids.count_documents({**base, "technical_cleared_at": {"$ne": None}, "status": LIVE}):
            out.append("No bid has passed technical evaluation yet")
        pending = await db.bids.count_documents({**base, "technical_cleared_at": None, "status": LIVE})
        if pending:
            out.append(f"Technical evaluation is still pending for {pending} bid(s) — clear or reject each one first")
    if n.get(f"{stage}_opened_at"):
        out.append(f"The {stage} envelopes are already open")
    return out


@router.get("/{notice_ref}")
async def opening_state(notice_ref: str, admin=VIEW):
    n, c = await _ctx(notice_ref)
    members = _members(c)
    names = {}
    if members:
        async for u in db.admin_users.find({"_id": {"$in": [ObjectId(m) for m in members if ObjectId.is_valid(m)]}},
                                           {"email": 1, "full_name": 1, "name": 1}):
            names[str(u["_id"])] = u.get("full_name") or u.get("name") or u.get("email")
    q = {"notice_ref": notice_ref, "seal_v": 1, "auction_id": None, "status": LIVE}
    stages = {}
    for st in ("technical", "commercial"):
        appr = (n.get("opening_approvals") or {}).get(st) or []
        done = {a["by_id"] for a in appr}
        stages[st] = {"opened_at": n.get(f"{st}_opened_at"), "blockers": await _blockers(n, c, st),
                      "approvals": appr, "pending": [{"id": m, "name": names.get(m, m)} for m in members if m not in done],
                      "i_can_approve": admin.get("id") in members and admin.get("id") not in done}
    return {"notice_ref": notice_ref, "opening_at": (opening_at(n) or None) and opening_at(n).isoformat(),
            "submission_deadline": n.get("submission_deadline"),
            "committee": [{"id": m, "name": names.get(m, m)} for m in members],
            "bids_total": await db.bids.count_documents(q),
            "bids_emd_confirmed": await db.bids.count_documents({**q, "status": {"$in": list(EMD_CONFIRMED)}}),
            "stages": stages}


@router.post("/{notice_ref}/approve")
async def approve_opening(notice_ref: str, body: ApproveIn,
                          admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    n, c = await _ctx(notice_ref)
    members = _members(c)
    if admin.get("id") not in members:
        raise HTTPException(status_code=403, detail="Only members of this tender's committee can approve the opening")
    blockers = await _blockers(n, c, body.stage)
    if blockers:
        raise HTTPException(status_code=412, detail="; ".join(blockers))
    appr = (n.get("opening_approvals") or {}).get(body.stage) or []
    if any(a["by_id"] == admin["id"] for a in appr):
        raise HTTPException(status_code=409, detail="You have already approved this opening")
    appr.append({"by_id": admin["id"], "by": admin.get("email"), "at": now_iso()})
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {f"opening_approvals.{body.stage}": appr}})
    await audit_log(f"bid_opening.{body.stage}_approved", admin, "notice", notice_ref,
                    {"approved": len(appr), "required": len(members)})
    if {a["by_id"] for a in appr} >= set(members):
        opened = await _open(n, body.stage, admin)
        return {"opened": True, "bids_opened": opened, "approvals": appr}
    return {"opened": False, "approvals": appr, "remaining": len(set(members) - {a["by_id"] for a in appr})}


async def _open(n: dict, stage: str, admin: dict) -> int:
    ref, now = n["notice_ref"], now_iso()
    q = {"notice_ref": ref, "seal_v": 1, "auction_id": None, "status": LIVE}
    if stage == "technical":
        q["status"] = {"$in": list(EMD_CONFIRMED)}
    else:
        q |= {"technical_unsealed_at": {"$ne": None}, "technical_cleared_at": {"$ne": None}}
    count = 0
    async for b in db.bids.find(q):
        s = b.get("sealed") or {}
        if stage == "technical":
            upd = {"technical_notes": dec_text(s.get("technical_notes")), "technical_unsealed_at": now}
        else:
            price = dec_text(s.get("price_amount"))
            upd = {"price_amount": float(price) if price else None, "commercial_notes": dec_text(s.get("commercial_notes")),
                   "commercial_unsealed_at": now, "financial_opened_at": now, "financial_opened_by": "committee"}
        await db.bids.update_one({"_id": b["_id"]}, {"$set": upd})
        count += 1
    await db.notices.update_one({"_id": n["_id"]}, {"$set": {f"{stage}_opened_at": now}})
    await audit_log(f"bid_opening.{stage}_opened", admin, "notice", ref, {"bids_opened": count})
    return count
