"""Share cards (OG image + share page) and buyer invites."""
import io
import os
import secrets
from html import escape as h
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from emails import send_email, wrap
from models.base import now_iso
from routers.marketing import ADMIN, CSRF, _api_base, _id, _oid

router = APIRouter(tags=["marketing"])
FONTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
LOGO = os.path.join(os.path.dirname(FONTS), "pmc-logo-mark.png")
GREEN, CREAM, GOLD = (15, 59, 46), (243, 239, 228), (201, 162, 75)


def _font(bold: bool, size: int):
    try:
        return ImageFont.truetype(os.path.join(FONTS, "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"), size)
    except Exception:
        return ImageFont.load_default(size=size)


def _wrap_text(draw, text: str, font, width: int, max_lines: int):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and " ".join(lines) != text:
        lines[-1] = lines[-1].rstrip(".,") + "…"
    return lines


async def _public_notice(ref: str) -> dict:
    n = await db.notices.find_one({"notice_ref": ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    return n


def _render_card(n: dict) -> bytes:
    img = Image.new("RGB", (1200, 630), GREEN)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1200, 10], fill=GOLD)
    try:
        mark = Image.open(LOGO).convert("RGB")
        img.paste(mark, (1200 - 70 - mark.width, 44))
    except OSError:
        pass
    d.text((70, 60), "PMC MANAGERS · GLOBAL TENDER BOARD", font=_font(True, 26), fill=GOLD)
    kind = str(n.get("kind") or n.get("notice_type") or "Tender").upper()
    d.text((70, 112), f"{kind}  ·  {n.get('notice_ref')}", font=_font(False, 26), fill=CREAM)
    y = 175
    for line in _wrap_text(d, str(n.get("title") or ""), _font(True, 58), 1060, 3):
        d.text((70, y), line, font=_font(True, 58), fill=(255, 255, 255))
        y += 70
    facts = []
    if n.get("category"):
        facts.append(str(n["category"]))
    if n.get("delivery_country"):
        facts.append(f"Delivery: {n['delivery_country']}")
    if n.get("submission_deadline"):
        facts.append(f"Closes {str(n['submission_deadline'])[:10]}")
    d.text((70, 455), "   ·   ".join(facts)[:90], font=_font(False, 30), fill=CREAM)
    d.rectangle([70, 520, 470, 584], fill=GOLD)
    d.text((92, 535), "View & bid on PMC", font=_font(True, 30), fill=GREEN)
    d.text((500, 538), "pmcmanagers.com", font=_font(False, 28), fill=CREAM)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


@router.get("/api/v1/share/notice/{ref}.png")
async def share_card(ref: str):
    n = await _public_notice(ref)
    return Response(_render_card(n), media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/api/v1/share/notice/{ref}", response_class=HTMLResponse)
async def share_page(ref: str):
    """Link people share: crawlers read the preview tags, people are sent on to the tender."""
    n = await _public_notice(ref)
    url = f"{config.FRONTEND_URL}/notices/{ref}"
    img = f"{_api_base()}/api/v1/share/notice/{ref}.png"
    title = h(str(n.get("title") or "Tender"))
    desc = h(f"{n.get('category') or 'Tender'} · {n.get('delivery_country') or ''} · published on PMC Managers. View the notice and bid online.")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<meta property='og:type' content='website'><meta property='og:title' content='{title}'>"
            f"<meta property='og:description' content='{desc}'><meta property='og:image' content='{img}'>"
            f"<meta property='og:image:width' content='1200'><meta property='og:image:height' content='630'>"
            f"<meta property='og:url' content='{h(_api_base())}/api/v1/share/notice/{h(ref)}'>"
            f"<meta name='twitter:card' content='summary_large_image'><meta name='twitter:image' content='{img}'>"
            f"<meta http-equiv='refresh' content='0;url={url}'></head>"
            f"<body><a href='{url}'>Open the tender on PMC Managers</a></body></html>")


# ---------- buyer invites ----------

class InviteIn(BaseModel):
    organisation: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(default="", max_length=120)
    email: EmailStr
    country: str = Field(default="", max_length=2)
    note: str = Field(default="", max_length=1500)


def _status(inv: dict, joined: set) -> str:
    if inv.get("joined_at") or inv["email"] in joined:
        return "joined"
    return "clicked" if inv.get("clicked_at") else inv.get("status", "sent")


@router.get("/api/v1/marketing/buyer-invites")
async def list_invites(admin=ADMIN):
    rows = await db.mkt_buyer_invites.find({}, {"token": 0}).sort("created_at", -1).limit(300).to_list(300)
    emails = [r["email"] for r in rows]
    joined = {t["primary_contact_email"] async for t in db.tenants.find({"primary_contact_email": {"$in": emails}}, {"primary_contact_email": 1})}
    joined |= {u["email"] async for u in db.admin_users.find({"email": {"$in": emails}, "is_active": {"$ne": False}}, {"email": 1})}
    return {"items": [{**_id(i), "status": _status(i, joined), "clicked": bool(i.get("clicked_at"))} for i in rows]}


@router.post("/api/v1/marketing/buyer-invites", dependencies=CSRF)
async def send_invite(body: InviteIn, admin=ADMIN):
    email = body.email.lower()
    if await db.mkt_contacts.find_one({"email": email, "unsubscribed": True}):
        raise HTTPException(status_code=409, detail="This person unsubscribed from PMC emails.")
    token = secrets.token_urlsafe(16)
    hello = f"Dear {h(body.contact_name)}," if body.contact_name else "Hello,"
    note = "".join(f"<p>{h(p)}</p>" for p in body.note.split("\n") if p.strip())
    link = f"{_api_base()}/api/v1/marketing/buyer-invites/go/{token}"
    html = wrap(f"Post {h(body.organisation)}'s tenders on PMC Managers — free",
                f"<p>{hello}</p>{note or '<p>We would like to invite ' + h(body.organisation) + ' to publish its tenders on PMC Managers free of charge.</p>'}"
                "<p>PMC Managers is a global e-tendering platform: publish notices, receive sealed bids from registered suppliers, "
                "evaluate with your committee and award, with every step recorded on a tamper-evident audit ledger.</p>",
                "See how it works", link)
    ok = await send_email(email, f"Invitation: post {body.organisation}'s tenders on PMC Managers free"[:150], html)
    await db.mkt_buyer_invites.insert_one({**body.model_dump(), "email": email, "country": body.country.upper(),
                                           "token": token, "status": "sent" if ok else "failed",
                                           "invited_by": admin.get("email"), "created_at": now_iso()})
    await audit_log("marketing.buyer_invite", admin, "buyer_invite", email, {"organisation": body.organisation, "sent": ok})
    return {"email_sent": ok}


@router.post("/api/v1/marketing/buyer-invites/{iid}/joined", dependencies=CSRF)
async def mark_joined(iid: str, admin=ADMIN):
    await db.mkt_buyer_invites.update_one({"_id": _oid(iid)}, {"$set": {"joined_at": now_iso()}})
    return {"ok": True}


@router.get("/api/v1/marketing/buyer-invites/go/{token}")
async def invite_click(token: str):
    inv = await db.mkt_buyer_invites.find_one({"token": token})
    if inv and not inv.get("clicked_at"):
        await db.mkt_buyer_invites.update_one({"_id": inv["_id"]}, {"$set": {"clicked_at": now_iso()}})
    return RedirectResponse(f"{config.FRONTEND_URL}/buyers")
