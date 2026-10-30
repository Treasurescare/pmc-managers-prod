"""Marketing — public website sign-up (double opt-in) and the weekly tender digest."""
import asyncio
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from html import escape as html_escape
from typing import List, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field

import config
from db import db
from emails import send_email, wrap
from models.base import now_iso
from routers.marketing import ADMIN, CSRF, _api_base, _upsert_contact

router = APIRouter(tags=["marketing"])


class SubscribeIn(BaseModel):
    email: EmailStr
    audience: Literal["vendor", "buyer"] = "vendor"
    country: str = Field(default="", max_length=2)
    categories: List[str] = Field(default_factory=list, max_length=10)
    consent: bool
    website: str = ""  # honeypot — real visitors leave this empty


def _page(msg: str) -> str:
    return (f"<html><body style='font-family:Georgia,serif;padding:48px;color:#1f3a2e'><h2>PMC Managers</h2>"
            f"<p>{msg}</p><p><a href='{config.FRONTEND_URL}'>Back to PMC Managers</a></p></body></html>")


@router.post("/api/v1/marketing/subscribe")
async def subscribe(body: SubscribeIn, request: Request):
    if body.website:
        return {"ok": True}
    if not body.consent:
        raise HTTPException(status_code=422, detail="Please tick the box to agree to receive tender alerts.")
    ip = ((request.headers.get("x-forwarded-for") or "").split(",")[-1].strip()
          or (request.client.host if request.client else ""))
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    if await db.mkt_subscribe_hits.count_documents({"ip": ip, "at_dt": {"$gte": since}}) >= 5:
        raise HTTPException(status_code=429, detail="Too many sign-ups from this connection. Try again later.")
    await db.mkt_subscribe_hits.insert_one({"ip": ip, "at_dt": datetime.now(timezone.utc)})
    email = body.email.lower()
    existing = await db.mkt_contacts.find_one({"email": email})
    if existing and existing.get("consent") and not existing.get("unsubscribed"):
        return {"ok": True}
    token = secrets.token_urlsafe(24)
    if not existing:
        await _upsert_contact(email, audience=body.audience, country=body.country.upper(),
                              categories=body.categories, source="website", consent=False)
    await db.mkt_contacts.update_one({"email": email}, {"$set": {
        "confirm_token": token, "pending_audience": body.audience, "pending_country": body.country.upper(),
        "pending_categories": body.categories, "signup_ip": ip, "signup_at": now_iso()}})
    link = f"{_api_base()}/api/v1/marketing/confirm/{token}"
    html = wrap("Confirm your tender alerts",
                "<p>Please confirm you want to receive tender alerts from PMC Managers. "
                "If you did not ask for this, ignore this email and nothing will be sent.</p>",
                "Confirm my alerts", link)
    await send_email(email, "[PMC] Confirm your tender alerts", html)
    return {"ok": True}


@router.get("/api/v1/marketing/confirm/{token}", response_class=HTMLResponse)
async def confirm(token: str):
    c = await db.mkt_contacts.find_one({"confirm_token": token})
    if not c:
        return _page("This confirmation link is no longer valid.")
    await db.mkt_contacts.update_one({"_id": c["_id"]}, {
        "$set": {"consent": True, "unsubscribed": False, "consent_at": now_iso(), "consent_source": "website double opt-in",
                 "audience": c.get("pending_audience") or c.get("audience"),
                 "country": c.get("pending_country") or c.get("country", ""),
                 "categories": sorted(set((c.get("categories") or []) + (c.get("pending_categories") or [])))},
        "$unset": {"confirm_token": "", "pending_audience": "", "pending_country": "", "pending_categories": ""}})
    return _page("Thank you — you're subscribed. You'll receive new tenders by email and can unsubscribe at any time.")


# ---------- weekly digest ----------

def _week_key(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


async def run_weekly_digest(force: bool = False) -> int:
    s = await db.mkt_settings.find_one({"_id": "tender_alerts"}) or {}
    if not force and (not s.get("enabled") or s.get("mode") != "weekly"):
        return 0
    now = datetime.now(timezone.utc)
    week = _week_key(now) + ("-manual-" + now.strftime("%H%M%S") if force else "")
    try:
        log_id = (await db.mkt_digest_log.insert_one({"week": week, "recipients": 0, "tenders": 0, "at": now_iso()})).inserted_id
    except Exception:
        return 0
    since = (now - timedelta(days=7)).isoformat()
    notices = await db.notices.find({"is_published": True, "published_at": {"$gte": since}},
                                    {"notice_ref": 1, "title": 1, "category": 1, "delivery_country": 1,
                                     "submission_deadline": 1}).sort("published_at", -1).to_list(500)
    if not notices:
        await db.mkt_digest_log.update_one({"_id": log_id}, {"$set": {"note": "no new tenders"}})
        return 0
    people: dict = {}
    async for v in db.vendors.find({"email": {"$exists": True}, "status": {"$nin": ["suspended", "rejected", "blocked", "deleted"]}},
                                   {"email": 1, "business_categories": 1, "company_name": 1}):
        e = v["email"].lower()
        await _upsert_contact(e, company=v.get("company_name", ""), audience="vendor", source="platform", consent=True)
        people[e] = set(v.get("business_categories") or [])
    q = {"audience": "vendor", "consent": True, "unsubscribed": {"$ne": True}}
    if not s.get("include_uploaded", True):
        q["source"] = "website"
    async for c in db.mkt_contacts.find(q, {"email": 1, "categories": 1}):
        people.setdefault(c["email"], set()).update(c.get("categories") or [])
    blocked = {c["email"] async for c in db.mkt_contacts.find({"unsubscribed": True}, {"email": 1})}
    sent = 0
    for email, cats in people.items():
        if email in blocked:
            continue
        mine = [n for n in notices if not cats or n.get("category") in cats][:15]
        if not mine:
            continue
        contact = await db.mkt_contacts.find_one({"email": email}, {"unsub_token": 1}) or {}
        rows = "".join(
            f"<li><a href='{config.FRONTEND_URL}/notices/{n['notice_ref']}'><b>{html_escape(str(n.get('title') or ''))}</b></a>"
            f"<br><span style='color:#666'>{html_escape(str(n.get('category') or ''))} · {html_escape(str(n.get('delivery_country') or ''))}"
            f"{' · closes ' + str(n.get('submission_deadline'))[:10] if n.get('submission_deadline') else ''}</span></li>"
            for n in mine)
        unsub = (f"<p style='font-size:11px;color:#888'><a href='{_api_base()}/api/v1/marketing/unsubscribe/{contact['unsub_token']}'>"
                 "Unsubscribe</a></p>") if contact.get("unsub_token") else ""
        html = wrap(f"{len(mine)} new tender{'s' if len(mine) != 1 else ''} this week",
                    f"<p>New tenders published on PMC Managers in the last 7 days{' in your categories' if cats else ''}:</p>"
                    f"<ul>{rows}</ul>{unsub}", "See all open tenders", f"{config.FRONTEND_URL}/notices")
        sent += await send_email(email, f"[PMC] {len(mine)} new tender{'s' if len(mine) != 1 else ''} this week", html)
        await asyncio.sleep(0.6)
    await db.mkt_digest_log.update_one({"_id": log_id}, {"$set": {"recipients": sent, "tenders": len(notices)}})
    return sent


@router.post("/api/v1/marketing/alerts/digest-now", dependencies=CSRF)
async def digest_now(bg: BackgroundTasks, admin=ADMIN):
    bg.add_task(run_weekly_digest, True)
    return {"queued": True}


@router.post("/api/v1/cron/marketing-weekly-digest")
async def cron_weekly_digest(request: Request, bg: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    if not secret or not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    run_id = request.headers.get("X-Webhook-Id") or ""
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id}):
            return {"ok": True, "duplicate": True}
        await db.cron_runs.insert_one({"run_id": run_id, "job": "marketing-weekly-digest", "at": now_iso()})
    bg.add_task(run_weekly_digest)
    return {"ok": True}
