"""Wave 41 — Meeting Scheduler with Jitsi Meet video conferencing.

Admin schedules a meeting (pre-bid meeting, evaluation panel, kickoff, etc.),
invites participants (bidders / staff / external observers). Each invitee
gets a magic-link `/meet/{token}` that drops them straight into an embedded
Jitsi room — no auth needed.

Endpoints:
  POST   /api/v1/meetings                            (admin) create
  GET    /api/v1/meetings                            (admin) list
  GET    /api/v1/meetings/{mid}                      (admin) get + invitees
  DELETE /api/v1/meetings/{mid}                      (admin) cancel
  POST   /api/v1/meetings/{mid}/minutes              (admin) upload text minutes
  POST   /api/v1/meetings/{mid}/invitees             (admin) add invitees
  GET    /api/v1/meetings/join/{token}               (public) resolve token → room
"""
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
import secrets

from db import db
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from audit import audit_log

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


class Invitee(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = "attendee"   # attendee | bidder | staff | observer | host


class MeetingIn(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    agenda: Optional[str] = None
    notice_ref: Optional[str] = None
    scheduled_at: str   # ISO
    duration_min: int = Field(ge=5, le=480, default=45)
    invitees: List[Invitee] = []


class MinutesIn(BaseModel):
    minutes: str = Field(min_length=1, max_length=20000)


def _out(d: dict) -> dict:
    o = BaseDocument.out(d)
    for i in o.get("invitees", []):
        i.pop("token", None)   # never expose tokens on list responses
    return o


def _jitsi_room_for(mid: str) -> str:
    """Deterministic unguessable Jitsi room name for a meeting."""
    return f"pmc-{mid}"


@router.post("")
async def create_meeting(payload: MeetingIn,
                          admin=Depends(require_role("admin", "reviewer"))):
    invitees = []
    for inv in payload.invitees:
        invitees.append({
            "email": inv.email.lower(),
            "name": inv.name or inv.email.split("@")[0],
            "role": inv.role,
            "token": secrets.token_urlsafe(24),
            "joined_at": None,
        })

    doc = {
        "subject": payload.subject,
        "agenda": payload.agenda,
        "notice_ref": payload.notice_ref,
        "scheduled_at": payload.scheduled_at,
        "duration_min": payload.duration_min,
        "invitees": invitees,
        "minutes": None,
        "status": "scheduled",
        "host_email": admin.get("email"),
        "created_by": admin.get("email"),
        "created_at": now_iso(),
    }
    r = await db.meetings.insert_one(doc)
    doc["_id"] = r.inserted_id
    doc["jitsi_room"] = _jitsi_room_for(str(r.inserted_id))
    await db.meetings.update_one({"_id": r.inserted_id},
                                  {"$set": {"jitsi_room": doc["jitsi_room"]}})
    await audit_log("meeting.create", admin, "meeting", str(r.inserted_id),
                    {"subject": payload.subject, "invitees": len(invitees)})
    # For admin response, include the raw tokens so they can copy invite links.
    out = BaseDocument.out(doc)
    out["invite_links"] = [
        {"email": i["email"], "name": i["name"], "role": i["role"],
         "url": f"/meet/{i['token']}"}
        for i in invitees
    ]
    return out


@router.get("")
async def list_meetings(admin=Depends(current_admin)):
    rows = []
    async for m in db.meetings.find({}).sort("scheduled_at", -1).limit(200):
        rows.append(_out(m))
    return {"items": rows, "total": len(rows)}


@router.get("/{mid}")
async def get_meeting(mid: str, admin=Depends(current_admin)):
    m = await db.meetings.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    out = BaseDocument.out(m)
    out["invite_links"] = [
        {"email": i["email"], "name": i["name"], "role": i["role"],
         "joined_at": i.get("joined_at"),
         "url": f"/meet/{i['token']}"}
        for i in m.get("invitees", [])
    ]
    return out


@router.post("/{mid}/invitees")
async def add_invitees(mid: str, payload: List[Invitee],
                        admin=Depends(require_role("admin", "reviewer"))):
    m = await db.meetings.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    new_invitees = []
    existing = {i["email"] for i in m.get("invitees", [])}
    for inv in payload:
        if inv.email.lower() in existing:
            continue
        new_invitees.append({
            "email": inv.email.lower(),
            "name": inv.name or inv.email.split("@")[0],
            "role": inv.role,
            "token": secrets.token_urlsafe(24),
            "joined_at": None,
        })
    if new_invitees:
        await db.meetings.update_one({"_id": ObjectId(mid)},
                                      {"$push": {"invitees": {"$each": new_invitees}}})
    await audit_log("meeting.invite", admin, "meeting", mid,
                    {"added": len(new_invitees)})
    return {"ok": True, "added": len(new_invitees),
            "invite_links": [{"email": i["email"], "url": f"/meet/{i['token']}"}
                             for i in new_invitees]}


@router.post("/{mid}/minutes")
async def upload_minutes(mid: str, payload: MinutesIn,
                          admin=Depends(require_role("admin", "reviewer"))):
    m = await db.meetings.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await db.meetings.update_one({"_id": ObjectId(mid)},
        {"$set": {"minutes": payload.minutes,
                   "minutes_uploaded_at": now_iso(),
                   "minutes_uploaded_by": admin.get("email"),
                   "status": "ended"}})
    await audit_log("meeting.minutes", admin, "meeting", mid, {})
    return {"ok": True}


@router.delete("/{mid}")
async def cancel_meeting(mid: str, admin=Depends(require_role("admin"))):
    r = await db.meetings.update_one({"_id": ObjectId(mid)},
                                      {"$set": {"status": "cancelled",
                                                 "cancelled_at": now_iso()}})
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await audit_log("meeting.cancel", admin, "meeting", mid, {})
    return {"ok": True}


@router.get("/join/{token}")
async def join_via_token(token: str):
    """PUBLIC — magic-link resolver. Returns the Jitsi room name + subject."""
    m = await db.meetings.find_one({"invitees.token": token})
    if not m:
        raise HTTPException(status_code=404, detail="Invalid or expired invite link")
    if m.get("status") == "cancelled":
        raise HTTPException(status_code=410, detail="Meeting was cancelled")
    # Mark this invitee as joined (idempotent).
    invitee = next((i for i in m.get("invitees", []) if i.get("token") == token), None)
    if invitee and not invitee.get("joined_at"):
        await db.meetings.update_one(
            {"_id": m["_id"], "invitees.token": token},
            {"$set": {"invitees.$.joined_at": now_iso()}})
    return {
        "meeting_id": str(m["_id"]),
        "subject": m["subject"],
        "agenda": m.get("agenda"),
        "notice_ref": m.get("notice_ref"),
        "scheduled_at": m["scheduled_at"],
        "duration_min": m["duration_min"],
        "jitsi_room": m.get("jitsi_room") or _jitsi_room_for(str(m["_id"])),
        "display_name": invitee.get("name") if invitee else "Guest",
        "role": invitee.get("role") if invitee else "attendee",
        "status": m.get("status", "scheduled"),
    }
