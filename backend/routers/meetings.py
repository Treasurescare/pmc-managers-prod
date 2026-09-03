"""Wave 41 — Meeting Scheduler with Jitsi Meet + Zoom video conferencing.

Admin schedules a meeting (pre-bid meeting, evaluation panel, kickoff, etc.),
invites participants (bidders / staff / external observers). Each invitee
gets a magic-link `/meet/{token}` that drops them into the picked provider:

  * **Jitsi** (default) — embedded iframe, unlimited free, local recording
  * **Zoom**            — Server-to-Server OAuth creates a real Zoom meeting;
                          participants click through to zoom.us to join

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
import secrets, os, base64, httpx, logging

from db import db
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from audit import audit_log

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


# ----------- Zoom Server-to-Server OAuth client ---------------------------

class ZoomError(Exception):
    pass


async def _zoom_token() -> Optional[str]:
    account_id = os.environ.get("ZOOM_ACCOUNT_ID")
    client_id = os.environ.get("ZOOM_CLIENT_ID")
    client_secret = os.environ.get("ZOOM_CLIENT_SECRET")
    if not (account_id and client_id and client_secret):
        return None
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=10) as cx:
        r = await cx.post(
            f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}",
            headers={"Authorization": f"Basic {creds}"},
        )
    if r.status_code != 200:
        raise ZoomError(f"Zoom auth failed: {r.text}")
    return r.json().get("access_token")


async def _zoom_create_meeting(subject: str, agenda: Optional[str],
                                start_iso: str, duration_min: int) -> dict:
    tok = await _zoom_token()
    if not tok:
        raise ZoomError("Zoom is not configured on this server (ZOOM_* env vars missing)")
    host = os.environ.get("ZOOM_HOST_EMAIL", "me")
    body = {
        "topic": subject[:200],
        "type": 2,                 # 2 = scheduled meeting
        "start_time": start_iso,
        "duration": max(15, min(int(duration_min), 480)),
        "timezone": "UTC",
        "agenda": (agenda or "")[:2000],
        "settings": {
            "host_video": True, "participant_video": True,
            "join_before_host": True, "mute_upon_entry": True,
            "waiting_room": False, "approval_type": 2,
            "auto_recording": "none",
        },
    }
    async with httpx.AsyncClient(timeout=15) as cx:
        r = await cx.post(
            f"https://api.zoom.us/v2/users/{host}/meetings",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json=body,
        )
    if r.status_code not in (200, 201):
        raise ZoomError(f"Zoom create meeting failed: HTTP {r.status_code} · {r.text}")
    d = r.json()
    return {
        "zoom_meeting_id": str(d.get("id")),
        "zoom_join_url": d.get("join_url"),
        "zoom_start_url": d.get("start_url"),
        "zoom_password": d.get("password"),
    }


# ---------------- Models ------------------------------------------------

class Invitee(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = "attendee"


class MeetingIn(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    agenda: Optional[str] = None
    notice_ref: Optional[str] = None
    scheduled_at: str
    duration_min: int = Field(ge=5, le=480, default=45)
    invitees: List[Invitee] = []
    provider: str = Field(default="jitsi", pattern="^(jitsi|zoom)$")


class MinutesIn(BaseModel):
    minutes: str = Field(min_length=1, max_length=20000)


def _out(d: dict) -> dict:
    o = BaseDocument.out(d)
    for i in o.get("invitees", []):
        i.pop("token", None)
    o.pop("zoom_start_url", None)   # never leak the host-start URL on list responses
    return o


def _jitsi_room_for(mid: str) -> str:
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
        "subject": payload.subject, "agenda": payload.agenda,
        "notice_ref": payload.notice_ref,
        "scheduled_at": payload.scheduled_at, "duration_min": payload.duration_min,
        "invitees": invitees, "minutes": None,
        "status": "scheduled",
        "provider": payload.provider,
        "host_email": admin.get("email"),
        "created_by": admin.get("email"),
        "created_at": now_iso(),
    }

    if payload.provider == "zoom":
        try:
            zoom = await _zoom_create_meeting(
                payload.subject, payload.agenda,
                payload.scheduled_at, payload.duration_min)
            doc.update(zoom)
        except ZoomError as e:
            logging.warning(f"Zoom create failed: {e}")
            raise HTTPException(status_code=502,
                detail=f"Zoom API call failed — verify ZOOM_* env vars, scopes and app activation. {e}")

    r = await db.meetings.insert_one(doc)
    doc["_id"] = r.inserted_id
    doc["jitsi_room"] = _jitsi_room_for(str(r.inserted_id))
    await db.meetings.update_one({"_id": r.inserted_id},
                                  {"$set": {"jitsi_room": doc["jitsi_room"]}})

    await audit_log("meeting.create", admin, "meeting", str(r.inserted_id),
                    {"subject": payload.subject, "invitees": len(invitees),
                     "provider": payload.provider})
    out = BaseDocument.out(doc)
    out.pop("zoom_start_url", None)
    out["invite_links"] = [
        {"email": i["email"], "name": i["name"], "role": i["role"],
         "url": f"/meet/{i['token']}"}
        for i in invitees
    ]
    return out


@router.get("")
async def list_meetings(include_cancelled: bool = False,
                        admin=Depends(current_admin)):
    # Bug #54 — hide cancelled meetings by default; toggle to include.
    q = {} if include_cancelled else {"status": {"$ne": "cancelled"}}
    rows = []
    async for m in db.meetings.find(q).sort("scheduled_at", -1).limit(200):
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
        "provider": m.get("provider", "jitsi"),
        "jitsi_room": m.get("jitsi_room") or _jitsi_room_for(str(m["_id"])),
        "zoom_join_url": m.get("zoom_join_url"),
        "zoom_meeting_id": m.get("zoom_meeting_id"),
        "zoom_password": m.get("zoom_password"),
        "display_name": invitee.get("name") if invitee else "Guest",
        "role": invitee.get("role") if invitee else "attendee",
        "status": m.get("status", "scheduled"),
    }
