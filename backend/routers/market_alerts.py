"""v61f — Home advert view/click counts and marketplace category alerts for verified buyers."""
import asyncio
import csv
import hashlib
import html
import io
import logging
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

import config
from db import db
from emails import send_email, wrap
from routers.marketplace import STAFF, _bidder
from security import require_role

router = APIRouter(prefix="/api/v1", tags=["market-alerts"])
log = logging.getLogger("market_alerts")
_TASKS: set = set()
SALT = config.JWT_SECRET


# ---------------- advert views / clicks ----------------
class AdEvent(BaseModel):
    id: str = Field(min_length=24, max_length=24)
    kind: str = Field(pattern="^(view|click)$")


def _visitor(request: Request, day: str) -> str:
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (request.client.host if request.client else "")
    raw = f"{SALT}|{day}|{ip}|{request.headers.get('user-agent', '')[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@router.post("/market/showcase/ad-event")
async def ad_event(body: AdEvent, request: Request):
    if not ObjectId.is_valid(body.id) or not await db.home_adverts.find_one({"_id": ObjectId(body.id), "deleted": {"$ne": True}}, {"_id": 1}):
        return {"ok": False}
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    try:
        await db.home_ad_seen.insert_one({"_id": f"{body.id}:{day}:{body.kind}:{_visitor(request, day)}", "at": now})
    except DuplicateKeyError:
        return {"ok": True, "counted": False}
    await db.home_ad_stats.update_one({"ad_id": body.id, "day": day}, {"$inc": {"views" if body.kind == "view" else "clicks": 1}}, upsert=True)
    return {"ok": True, "counted": True}


async def ad_totals(ids: list) -> dict:
    out = {}
    async for r in db.home_ad_stats.aggregate([{"$match": {"ad_id": {"$in": ids}}},
                                               {"$group": {"_id": "$ad_id", "views": {"$sum": "$views"}, "clicks": {"$sum": "$clicks"}}}]):
        out[r["_id"]] = {"views": r.get("views", 0), "clicks": r.get("clicks", 0)}
    return out


@router.get("/admin/home-adverts/{aid}/stats")
async def ad_stats(aid: str, format: str = "json", admin=Depends(require_role(*STAFF))):
    a = await db.home_adverts.find_one({"_id": ObjectId(aid)}) if ObjectId.is_valid(aid) else None
    if not a:
        raise HTTPException(status_code=404, detail="Advert not found")
    rows = [{"day": r["day"], "views": r.get("views", 0), "clicks": r.get("clicks", 0)}
            async for r in db.home_ad_stats.find({"ad_id": aid}).sort("day", 1)]
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Advert", a["title"]])
        w.writerow(["Day", "People who saw it", "People who clicked", "Click rate %"])
        for r in rows:
            w.writerow([r["day"], r["views"], r["clicks"], round(100 * r["clicks"] / r["views"], 1) if r["views"] else 0])
        tv, tc = sum(r["views"] for r in rows), sum(r["clicks"] for r in rows)
        w.writerow(["Total", tv, tc, round(100 * tc / tv, 1) if tv else 0])
        safe = "".join(ch if ch.isalnum() else "-" for ch in a["title"])[:40]
        return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="advert-{safe}.csv"'})
    return {"title": a["title"], "rows": rows}


# ---------------- category alerts ----------------
async def _buyer(request: Request) -> dict:
    who = await _bidder(request)
    if who["kind"] != "buyer":
        raise HTTPException(status_code=403, detail="Category alerts are for verified buyer organisations")
    return who


class AlertsIn(BaseModel):
    categories: list[str] = Field(default_factory=list, max_length=30)


@router.get("/market/alerts")
async def get_alerts(request: Request):
    who = await _buyer(request)
    f = await db.mkt_follows.find_one({"_id": who["id"]}) or {}
    return {"categories": f.get("categories", []), "email": who.get("email")}


@router.put("/market/alerts")
async def put_alerts(body: AlertsIn, request: Request):
    who = await _buyer(request)
    names = sorted({c.strip() for c in body.categories if c.strip()})
    if names:
        ok = {c["name"] async for c in db.categories.find({"name": {"$in": names}, "is_active": {"$ne": False}}, {"name": 1})}
        if set(names) - ok:
            raise HTTPException(status_code=400, detail="Please choose categories from the list")
    prev = await db.mkt_follows.find_one({"_id": who["id"]}, {"token": 1})
    await db.mkt_follows.update_one({"_id": who["id"]}, {"$set": {
        "email": who["email"], "org": who["name"], "categories": names, "updated_at": datetime.now(timezone.utc).isoformat(),
        "token": (prev or {}).get("token") or secrets.token_urlsafe(24)}}, upsert=True)
    return {"categories": names}


@router.get("/market/alerts/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(t: str = ""):
    r = await db.mkt_follows.update_one({"token": t}, {"$set": {"categories": []}}) if len(t) > 20 else None
    msg = "You will no longer receive marketplace category alerts." if r and r.matched_count else "This link is not valid any more."
    return HTMLResponse(f"<html><body style='font-family:sans-serif;padding:40px'><h2>PMC Managers</h2><p>{msg}</p></body></html>")


async def _notify(lst: dict) -> None:
    cat = lst.get("category")
    if not cat:
        return
    base = (config.FRONTEND_URL or "").rstrip("/")
    api_base = base
    sent = 0
    async for f in db.mkt_follows.find({"categories": cat, "email": {"$nin": ["", None]}}):
        try:
            await db.mkt_alert_log.insert_one({"_id": f"{lst['_id']}:{f['_id']}", "at": datetime.now(timezone.utc)})
        except DuplicateKeyError:
            continue
        t = html.escape(lst["title"])
        body = (f"<p>A new product in <b>{html.escape(cat)}</b> has just been approved on the PMC Marketplace:</p>"
                f"<p style='font-size:18px'><b>{t}</b><br>from {html.escape(lst.get('seller_name') or 'a verified supplier')}</p>"
                f"<p style='font-size:12px;color:#5A5A57'>You get this because your organisation follows this category. "
                f"<a href='{api_base}/api/v1/market/alerts/unsubscribe?t={f['token']}'>Stop these alerts</a></p>")
        try:
            await send_email(f["email"], f"New on the PMC Marketplace: {lst['title'][:80]}",
                             wrap("New product in a category you follow", body, "View the product", f"{base}/market/{lst['_id']}"))
            sent += 1
        except Exception:
            log.exception("category alert failed")
    await db.mkt_listings.update_one({"_id": lst["_id"]}, {"$set": {"alerts_sent": sent}})


def notify_new_listing(lst: dict) -> None:
    t = asyncio.create_task(_notify(lst))
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)


async def ensure_indexes():
    await db.home_ad_seen.create_index("at", expireAfterSeconds=40 * 86400)
    await db.home_ad_stats.create_index([("ad_id", 1), ("day", 1)], unique=True)
    await db.mkt_follows.create_index("categories")
    await db.mkt_follows.create_index("token")
