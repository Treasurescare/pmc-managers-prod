"""Formal bid challenges: standstill before contract signing, committee review,
resolution meeting when upheld, and one appeal to a senior officer."""
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
import html as _html

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import BaseDocument, now_iso
from routers.vendor_auth import current_vendor
from security import require_role

router = APIRouter(prefix="/api/v1/bid-challenges", tags=["bid-challenges"])

DEFAULT_STANDSTILL_DAYS = 10
APPEAL_DAYS = 5
OPEN = ["lodged", "under_review", "upheld", "meeting_scheduled", "appealed"]
GROUNDS = Literal["criteria", "evaluation", "proof_review", "price", "process", "other"]
STAFF = Depends(require_role("admin", "committee_member", "reviewer", "auditor"))


class ChallengeIn(BaseModel):
    grounds: GROUNDS
    details: str = Field(min_length=20, max_length=4000)


class VoteIn(BaseModel):
    decision: Literal["uphold", "dismiss"]
    comment: str = Field(min_length=3, max_length=2000)


class MeetingIn(BaseModel):
    scheduled_at: str = Field(min_length=10)
    location: str = Field(min_length=2, max_length=300)


class ResolutionIn(BaseModel):
    outcome: Literal["confirm_award", "re_evaluate"]
    minutes: str = Field(min_length=10, max_length=6000)


class AppealIn(BaseModel):
    reason: str = Field(min_length=20, max_length=4000)


class AppealDecisionIn(BaseModel):
    decision: Literal["uphold", "dismiss"]
    reason: str = Field(min_length=10, max_length=2000)


class StandstillIn(BaseModel):
    days: int = Field(ge=1, le=60)
    reason: str = Field(min_length=5, max_length=1000)


def _dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


async def _members(ref: str) -> list:
    from routers.proof_ai import _members as m
    return await m(ref)


async def standstill(notice_ref: str) -> dict:
    n = await db.notices.find_one({"notice_ref": notice_ref}, {"standstill_days": 1, "award_suspended": 1}) or {}
    days = int(n.get("standstill_days") or DEFAULT_STANDSTILL_DAYS)
    win = await db.bids.find_one({"notice_ref": notice_ref, "status": "awarded"}, {"awarded_at": 1, "bid_ref": 1})
    start = _dt((win or {}).get("awarded_at"))
    ends = start + timedelta(days=days) if start else None
    now = datetime.now(timezone.utc)
    return {"days": days, "awarded": bool(win), "winning_bid_id": str(win["_id"]) if win else None,
            "started_at": start.isoformat() if start else None, "ends_at": ends.isoformat() if ends else None,
            "running": bool(ends and now < ends), "award_suspended": bool(n.get("award_suspended"))}


async def contract_block_reason(notice_ref: str) -> Optional[str]:
    s = await standstill(notice_ref)
    if s["award_suspended"]:
        return "The award is suspended because a bid challenge was upheld. Contract signing waits for the resolution meeting."
    now = datetime.now(timezone.utc).isoformat()
    if await db.bid_challenges.find_one({"notice_ref": notice_ref, "$or": [
            {"status": {"$in": OPEN}}, {"status": "dismissed", "appeal_deadline": {"$gt": now}}]}, {"_id": 1}):
        return "A bid challenge on this tender is still open (or inside its appeal window). Contract signing is blocked until it is closed."
    if s["running"]:
        return f"The standstill period runs until {s['ends_at'][:16].replace('T', ' ')} UTC. Contracts can be signed after it ends."
    return None


async def assert_contract_allowed(bid_id: str) -> None:
    b = await db.bids.find_one({"_id": ObjectId(bid_id)}, {"notice_ref": 1}) if ObjectId.is_valid(bid_id) else None
    if not b:
        return
    why = await contract_block_reason(b.get("notice_ref"))
    if why:
        raise HTTPException(status_code=409, detail=why)


def _out(c: dict, vendor_view: bool = False) -> dict:
    o = BaseDocument.out(c)
    if vendor_view:
        votes = o.pop("votes", {}) or {}
        o["committee_votes"] = {"uphold": sum(v["decision"] == "uphold" for v in votes.values()),
                                "dismiss": sum(v["decision"] == "dismiss" for v in votes.values())}
        o.pop("appeal_decided_by", None)
        if o.get("meeting"):
            m = o["meeting"]
            o["meeting"] = {"scheduled_at": m.get("scheduled_at"), "location": m.get("location"), "invited": len(m.get("attendees") or [])}
        if o.get("resolution"):
            o["resolution"] = {k: o["resolution"].get(k) for k in ("outcome", "at")}
    return o


async def _mail(to: Optional[str], subject: str, body: str) -> None:
    if not to:
        return
    import asyncio
    from emails import send_email

    async def go():
        try:
            await send_email(to, subject, f"<p>{body}</p>")
        except Exception:
            pass
    asyncio.create_task(go())


async def _get(cid: str) -> dict:
    c = await db.bid_challenges.find_one({"_id": ObjectId(cid)}) if ObjectId.is_valid(cid) else None
    if not c:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return c


async def _suspend(c: dict, actor: dict, why: str) -> None:
    await db.notices.update_one({"notice_ref": c["notice_ref"]}, {"$set": {"award_suspended": True, "award_suspended_at": now_iso()}})
    await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {"status": "upheld", "upheld_at": now_iso(), "upheld_reason": why}})
    await audit_log("bid_challenge.upheld", actor, "notice", c["notice_ref"], {"challenge": c["challenge_ref"], "why": why})
    await _mail(c.get("vendor_email"), f"Your challenge {c['challenge_ref']} was upheld",
                f"Your challenge on tender {_html.escape(c['notice_ref'])} was upheld. The award is suspended for re-evaluation, "
                "and a resolution meeting with the committee, the issuer and the bidding teams will be scheduled.")


# ---------- vendor ----------

async def _own_bid(bid_id: str, vendor: dict) -> dict:
    b = await db.bids.find_one({"_id": ObjectId(bid_id), "vendor_id": vendor["id"]}) if ObjectId.is_valid(bid_id) else None
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    return b


@router.get("/mine/{bid_id}")
async def my_challenge_state(bid_id: str, vendor=Depends(current_vendor)) -> dict:
    b = await _own_bid(bid_id, vendor)
    s = await standstill(b["notice_ref"])
    rows = [_out(c, True) async for c in db.bid_challenges.find({"notice_ref": b["notice_ref"], "vendor_id": vendor["id"]}).sort("created_at", -1)]
    has_open = any(r["status"] in OPEN for r in rows)
    can = s["running"] and b.get("status") != "awarded" and b.get("status") not in ("withdrawn", "draft") and not has_open
    why = None if can else ("Your bid was awarded" if b.get("status") == "awarded" else "You already have an open challenge on this tender"
                            if has_open else "Challenges can be lodged only during the standstill period")
    return {"standstill": s, "can_lodge": can, "why_not": why, "challenges": rows, "appeal_days": APPEAL_DAYS}


@router.post("/mine/{bid_id}")
async def lodge_challenge(bid_id: str, body: ChallengeIn, vendor=Depends(current_vendor)) -> dict:
    state = await my_challenge_state(bid_id, vendor)
    if not state["can_lodge"]:
        raise HTTPException(status_code=409, detail=state["why_not"])
    b = await _own_bid(bid_id, vendor)
    n = await db.bid_challenges.count_documents({"notice_ref": b["notice_ref"]})
    doc = {"challenge_ref": f"CH-{b['notice_ref']}-{n + 1:02d}", "notice_ref": b["notice_ref"], "bid_id": bid_id,
           "bid_ref": b.get("bid_ref"), "vendor_id": vendor["id"], "vendor_email": vendor.get("email"),
           "company_name": b.get("company_name"), "grounds": body.grounds, "details": body.details.strip(),
           "status": "lodged", "votes": {}, "created_at": now_iso()}
    r = await db.bid_challenges.insert_one(doc)
    await audit_log("bid_challenge.lodged", {"id": vendor["id"], "email": vendor.get("email"), "role": "vendor"},
                    "notice", b["notice_ref"], {"challenge": doc["challenge_ref"], "grounds": body.grounds})
    return _out(await db.bid_challenges.find_one({"_id": r.inserted_id}), True)


@router.post("/mine/challenge/{cid}/appeal")
async def appeal(cid: str, body: AppealIn, vendor=Depends(current_vendor)) -> dict:
    c = await _get(cid)
    if c["vendor_id"] != vendor["id"]:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if c["status"] != "dismissed" or c.get("appealed_at"):
        raise HTTPException(status_code=409, detail="Only a dismissed challenge can be appealed, and only once")
    if (c.get("appeal_deadline") or "") < now_iso():
        raise HTTPException(status_code=409, detail=f"The {APPEAL_DAYS}-day appeal window has closed")
    await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {"status": "appealed", "appealed_at": now_iso(), "appeal_reason": body.reason.strip()}})
    await audit_log("bid_challenge.appealed", {"id": vendor["id"], "email": vendor.get("email"), "role": "vendor"},
                    "notice", c["notice_ref"], {"challenge": c["challenge_ref"]})
    return _out(await _get(cid), True)


# ---------- staff ----------

@router.get("")
async def list_challenges(admin=STAFF) -> dict:
    rows = [_out(c) async for c in db.bid_challenges.find({}).sort("created_at", -1).limit(300)]
    me = admin.get("id")
    is_admin = admin.get("role") in ("admin", "reviewer", "auditor")
    kept = []
    for r in rows:
        mem = await _members(r["notice_ref"])
        if not is_admin and me not in mem:
            continue
        kept.append(r)
        r["committee_size"] = len(mem)
        r["i_can_vote"] = me in mem and me not in (r.get("votes") or {}) and r["status"] in ("lodged", "under_review")
        r["i_can_decide_appeal"] = admin.get("role") == "admin" and me not in mem and r["status"] == "appealed"
    tenders = []
    async for b in db.bids.find({"status": "awarded"}, {"notice_ref": 1}).sort("awarded_at", -1).limit(50):
        s = await standstill(b["notice_ref"])
        tenders.append({"notice_ref": b["notice_ref"], **s, "contract_block": await contract_block_reason(b["notice_ref"])})
    return {"challenges": kept, "tenders": tenders}


@router.post("/{cid}/vote")
async def vote(cid: str, body: VoteIn, admin=Depends(require_role("admin", "committee_member"))) -> dict:
    c = await _get(cid)
    mem = await _members(c["notice_ref"])
    if admin.get("id") not in mem:
        raise HTTPException(status_code=403, detail="Only members of this tender's committee can decide a challenge")
    if c["status"] not in ("lodged", "under_review"):
        raise HTTPException(status_code=409, detail="This challenge is no longer under committee review")
    if admin["id"] in (c.get("votes") or {}):
        raise HTTPException(status_code=409, detail="You have already voted on this challenge")
    v = {"decision": body.decision, "comment": body.comment.strip(), "by": admin.get("email"), "at": now_iso()}
    await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {f"votes.{admin['id']}": v, "status": "under_review"}})
    await audit_log("bid_challenge.vote", admin, "notice", c["notice_ref"], {"challenge": c["challenge_ref"], "decision": body.decision})
    c = await _get(cid)
    votes = c.get("votes") or {}
    if all(m in votes for m in mem):
        up = sum(x["decision"] == "uphold" for x in votes.values())
        if up * 2 >= len(votes):
            await _suspend(c, admin, f"Committee upheld ({up} of {len(votes)})")
        else:
            deadline = (datetime.now(timezone.utc) + timedelta(days=APPEAL_DAYS)).isoformat()
            await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {"status": "dismissed", "decided_at": now_iso(), "appeal_deadline": deadline}})
            await audit_log("bid_challenge.dismissed", admin, "notice", c["notice_ref"], {"challenge": c["challenge_ref"]})
            await _mail(c.get("vendor_email"), f"Your challenge {c['challenge_ref']} was dismissed",
                        f"The committee dismissed your challenge on tender {_html.escape(c['notice_ref'])}. You may appeal once to a "
                        f"senior officer within {APPEAL_DAYS} days from your bid debrief page.")
    return _out(await _get(cid))


@router.post("/{cid}/meeting")
async def schedule_meeting(cid: str, body: MeetingIn, admin=Depends(require_role("admin", "committee_member"))) -> dict:
    c = await _get(cid)
    if c["status"] not in ("upheld", "meeting_scheduled"):
        raise HTTPException(status_code=409, detail="A resolution meeting is scheduled only after a challenge is upheld")
    if admin.get("role") != "admin" and admin.get("id") not in await _members(c["notice_ref"]):
        raise HTTPException(status_code=403, detail="Only an admin or a member of this tender's committee can schedule the meeting")
    when = _dt(body.scheduled_at)
    if not when or when < datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Choose a future date and time for the meeting")
    n = await db.notices.find_one({"notice_ref": c["notice_ref"]}, {"created_by": 1, "created_by_email": 1}) or {}
    mem = await _members(c["notice_ref"])
    staff = [u.get("email") async for u in db.admin_users.find(
        {"_id": {"$in": [ObjectId(m) for m in mem + [n.get("created_by")] if m and ObjectId.is_valid(m)]}}, {"email": 1})]
    bidders = [b.get("vendor_email") async for b in db.bids.find(
        {"notice_ref": c["notice_ref"], "status": {"$nin": ["withdrawn", "draft"]}}, {"vendor_email": 1, "company_name": 1})]
    attendees = sorted({e for e in staff + bidders + [n.get("created_by_email")] if e})
    meeting = {"scheduled_at": when.isoformat(), "location": body.location.strip(), "attendees": attendees,
               "scheduled_by": admin.get("email"), "scheduled_on": now_iso()}
    await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {"status": "meeting_scheduled", "meeting": meeting}})
    await audit_log("bid_challenge.meeting", admin, "notice", c["notice_ref"], {"challenge": c["challenge_ref"], "at": meeting["scheduled_at"]})
    for e in attendees:
        await _mail(e, f"Resolution meeting · tender {c['notice_ref']}",
                    f"A bid challenge ({_html.escape(c['challenge_ref'])}) on tender {_html.escape(c['notice_ref'])} was upheld and the award is "
                    f"suspended. The committee, the issuer and the bidding teams meet on {meeting['scheduled_at'][:16].replace('T', ' ')} UTC "
                    f"at {_html.escape(meeting['location'])} to resolve it.")
    return _out(await _get(cid))


@router.post("/{cid}/resolution")
async def record_resolution(cid: str, body: ResolutionIn, admin=Depends(require_role("admin"))) -> dict:
    c = await _get(cid)
    if c["status"] != "meeting_scheduled":
        raise HTTPException(status_code=409, detail="Schedule the resolution meeting first")
    if _dt(c["meeting"]["scheduled_at"]) > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="The outcome can be recorded after the meeting has taken place")
    ref = c["notice_ref"]
    await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {
        "status": "resolved", "resolution": {"outcome": body.outcome, "minutes": body.minutes.strip(), "by": admin.get("email"), "at": now_iso()}}})
    if body.outcome == "re_evaluate":
        await db.bids.update_one({"notice_ref": ref, "status": "awarded"},
                                 {"$set": {"status": "accounting_cleared", "award_withdrawn_at": now_iso(), "award_withdrawn_reason": c["challenge_ref"]},
                                  "$unset": {"awarded_at": ""}})
        await db.notices.update_one({"notice_ref": ref}, {"$set": {"re_evaluation_required": True}})
    if not await db.bid_challenges.find_one({"notice_ref": ref, "status": {"$in": ["upheld", "meeting_scheduled"]}}, {"_id": 1}):
        await db.notices.update_one({"notice_ref": ref}, {"$set": {"award_suspended": False}})
    await audit_log("bid_challenge.resolved", admin, "notice", ref, {"challenge": c["challenge_ref"], "outcome": body.outcome})
    for e in (c.get("meeting") or {}).get("attendees") or []:
        await _mail(e, f"Challenge {c['challenge_ref']} resolved",
                    f"Outcome of the resolution meeting on tender {_html.escape(ref)}: "
                    + ("the award is confirmed." if body.outcome == "confirm_award" else "the award is withdrawn and the tender goes back to evaluation."))
    return _out(await _get(cid))


@router.post("/{cid}/appeal-decision")
async def decide_appeal(cid: str, body: AppealDecisionIn, admin=Depends(require_role("admin"))) -> dict:
    c = await _get(cid)
    if c["status"] != "appealed":
        raise HTTPException(status_code=409, detail="This challenge has no pending appeal")
    if admin.get("id") in await _members(c["notice_ref"]):
        raise HTTPException(status_code=403, detail="A member of this tender's committee cannot decide the appeal")
    await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {"appeal_decision": body.decision, "appeal_decision_reason": body.reason.strip(),
                                                                  "appeal_decided_by": admin.get("email"), "appeal_decided_at": now_iso()}})
    await audit_log("bid_challenge.appeal_decided", admin, "notice", c["notice_ref"], {"challenge": c["challenge_ref"], "decision": body.decision})
    if body.decision == "uphold":
        await _suspend(c, admin, "Upheld on appeal by a senior officer")
    else:
        await db.bid_challenges.update_one({"_id": c["_id"]}, {"$set": {"status": "closed"}})
        await _mail(c.get("vendor_email"), f"Appeal on {c['challenge_ref']} dismissed",
                    "A senior officer dismissed your appeal. This decision is final within the platform.")
    return _out(await _get(cid))


@router.put("/notice/{notice_ref}/standstill")
async def change_standstill(notice_ref: str, body: StandstillIn, admin=Depends(require_role("admin"))) -> dict:
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found or not published")
    old = int(n.get("standstill_days") or DEFAULT_STANDSTILL_DAYS)
    if old == body.days:
        raise HTTPException(status_code=409, detail=f"The standstill period is already {old} days")
    s = await standstill(notice_ref)
    if s["awarded"] and not s["running"]:
        raise HTTPException(status_code=409, detail="The standstill period has already ended for this tender")
    no = await db.corrigenda.count_documents({"notice_ref": notice_ref}) + 1
    await db.corrigenda.insert_one({
        "notice_ref": notice_ref, "tenant_id": n.get("tenant_id"), "corrigendum_no": no,
        "title": f"Standstill period changed from {old} to {body.days} days",
        "summary": body.reason.strip(), "effective_from": now_iso(), "new_submission_deadline": None,
        "extend_deadline_days": None, "field_amendments": [{"field_key": "standstill_days", "before": old, "after": body.days}],
        "attachments": [], "is_active": True, "acknowledgements": [], "published_at": now_iso(),
        "published_by": admin.get("email"), "created_at": now_iso()})
    await db.notices.update_one({"notice_ref": notice_ref}, {"$set": {"standstill_days": body.days}})
    await audit_log("bid_challenge.standstill_changed", admin, "notice", notice_ref, {"from": old, "to": body.days, "corrigendum": no})
    async for b in db.bids.find({"notice_ref": notice_ref, "status": {"$nin": ["withdrawn", "draft"]}}, {"vendor_email": 1}):
        await _mail(b.get("vendor_email"), f"Corrigendum {no} · tender {notice_ref}",
                    f"The standstill period before contract signing changed from {old} to {body.days} days. Reason: {_html.escape(body.reason.strip())}")
    return {"corrigendum_no": no, **await standstill(notice_ref)}
