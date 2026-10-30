"""Marketing — contacts, segments, email campaigns (Resend), AI copy, new-tender alerts, referrals."""
import asyncio
import csv
import io
import logging
import re
import secrets
from typing import List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from emails import send_email, wrap
from models.base import now_iso
from routers.vendor_auth import current_vendor
from security import require_csrf, require_role

router = APIRouter(prefix="/api/v1/marketing", tags=["marketing"])
log = logging.getLogger("marketing")
ADMIN = Depends(require_role("admin"))
CSRF = [Depends(require_csrf)]
Audience = Literal["vendor", "buyer"]
PIXEL = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
         b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


def _id(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = str(doc["_id"])
    return out


def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")


def _api_base() -> str:
    return (getattr(config, "PUBLIC_API_URL", "") or config.FRONTEND_URL).rstrip("/")


async def _upsert_contact(email: str, **fields) -> bool:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False
    existing = await db.mkt_contacts.find_one({"email": email})
    if existing:
        upd = {k: v for k, v in fields.items() if v not in (None, "", [])}
        upd.pop("consent", None) if existing.get("consent") else None
        await db.mkt_contacts.update_one({"_id": existing["_id"]}, {"$set": {**upd, "updated_at": now_iso()}})
        return False
    await db.mkt_contacts.insert_one({"email": email, "name": "", "company": "", "audience": "vendor",
                                      "country": "", "categories": [], "source": "upload", "consent": False,
                                      **{k: v for k, v in fields.items() if v is not None},
                                      "unsubscribed": False, "unsub_token": secrets.token_urlsafe(18),
                                      "created_at": now_iso()})
    return True


# ---------- contacts ----------

class ContactIn(BaseModel):
    email: EmailStr
    name: str = ""
    company: str = ""
    audience: Audience = "vendor"
    country: str = ""
    categories: List[str] = Field(default_factory=list)
    consent: bool = False


class ImportIn(BaseModel):
    csv_text: str = Field(min_length=5, max_length=2_000_000)
    audience: Audience = "vendor"
    lawful_basis_confirmed: bool


@router.get("/contacts")
async def list_contacts(admin=ADMIN, audience: Optional[str] = None, country: Optional[str] = None,
                        category: Optional[str] = None, q: Optional[str] = None, limit: int = 200):
    flt: dict = {}
    if audience: flt["audience"] = audience
    if country: flt["country"] = country.upper()
    if category: flt["categories"] = category
    if q: flt["$or"] = [{"email": {"$regex": re.escape(q), "$options": "i"}},
                        {"company": {"$regex": re.escape(q), "$options": "i"}}]
    total = await db.mkt_contacts.count_documents(flt)
    rows = await db.mkt_contacts.find(flt, {"unsub_token": 0}).sort("created_at", -1).limit(min(limit, 1000)).to_list(1000)
    return {"total": total, "items": [_id(r) for r in rows]}


@router.post("/contacts", dependencies=CSRF)
async def add_contact(body: ContactIn, admin=ADMIN):
    d = body.model_dump()
    d["country"] = d["country"].upper()
    created = await _upsert_contact(d.pop("email"), source="manual", **d)
    return {"created": created}


@router.post("/contacts/import", dependencies=CSRF)
async def import_contacts(body: ImportIn, admin=ADMIN):
    if not body.lawful_basis_confirmed:
        raise HTTPException(status_code=422, detail="Confirm these contacts agreed to hear from you or are business contacts you may lawfully email.")
    reader = csv.DictReader(io.StringIO(body.csv_text.lstrip("\ufeff")))
    cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}
    if "email" not in cols:
        raise HTTPException(status_code=422, detail="The file needs an 'email' column.")
    created = updated = skipped = 0
    for row in reader:
        get = lambda k: (row.get(cols[k]) or "").strip() if k in cols else ""
        email = get("email")
        cats = [c.strip() for c in re.split(r"[;|]", get("categories")) if c.strip()]
        aud = get("audience").lower() if get("audience").lower() in ("vendor", "buyer") else body.audience
        consent_raw = get("consent").lower()
        ok = await _upsert_contact(email, name=get("name"), company=get("company"), audience=aud,
                                   country=get("country").upper(), categories=cats, source="upload",
                                   consent=consent_raw not in ("no", "false", "0", "n"))
        if ok: created += 1
        elif re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.lower()): updated += 1
        else: skipped += 1
    await audit_log("marketing.import", admin, "mkt_contacts", "-", {"created": created, "updated": updated})
    return {"created": created, "updated": updated, "skipped": skipped}


@router.post("/contacts/sync", dependencies=CSRF)
async def sync_platform(admin=ADMIN):
    """Pull registered vendors and buyer organisations in as contacts."""
    regs = {r["email"]: bool(r.get("marketing_consent")) async for r in
            db.registrations.find({}, {"email": 1, "marketing_consent": 1})}
    n = 0
    async for v in db.vendors.find({"email": {"$exists": True}}, {"email": 1, "company_name": 1, "country": 1,
                                                                   "business_categories": 1}):
        n += await _upsert_contact(v["email"], company=v.get("company_name", ""), audience="vendor",
                                   country=(v.get("country") or "").upper(), categories=v.get("business_categories") or [],
                                   source="platform", consent=regs.get(v["email"].lower(), True))
    async for t in db.tenants.find({"primary_contact_email": {"$nin": [None, ""]}}):
        n += await _upsert_contact(t["primary_contact_email"], name=t.get("primary_contact_name", ""),
                                   company=t.get("name", ""), audience="buyer",
                                   country=(t.get("country") or "").upper(), source="platform", consent=True)
    return {"created": n}


@router.delete("/contacts/{cid}", dependencies=CSRF)
async def delete_contact(cid: str, admin=ADMIN):
    await db.mkt_contacts.delete_one({"_id": _oid(cid)})
    return {"ok": True}


# ---------- segments ----------

class SegmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    audience: Literal["vendor", "buyer", "all"] = "vendor"
    countries: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


def _segment_filter(seg: dict) -> dict:
    f: dict = {"consent": True, "unsubscribed": {"$ne": True}}
    if seg.get("audience") in ("vendor", "buyer"): f["audience"] = seg["audience"]
    if seg.get("countries"): f["country"] = {"$in": [c.upper() for c in seg["countries"]]}
    if seg.get("categories"): f["categories"] = {"$in": seg["categories"]}
    if seg.get("sources"): f["source"] = {"$in": seg["sources"]}
    return f


@router.get("/segments")
async def list_segments(admin=ADMIN):
    out = []
    async for s in db.mkt_segments.find().sort("created_at", -1):
        out.append({**_id(s), "size": await db.mkt_contacts.count_documents(_segment_filter(s))})
    return {"items": out}


@router.post("/segments/preview", dependencies=CSRF)
async def preview_segment(body: SegmentIn, admin=ADMIN):
    return {"size": await db.mkt_contacts.count_documents(_segment_filter(body.model_dump()))}


@router.post("/segments", dependencies=CSRF)
async def create_segment(body: SegmentIn, admin=ADMIN):
    r = await db.mkt_segments.insert_one({**body.model_dump(), "created_at": now_iso()})
    return {"id": str(r.inserted_id)}


@router.delete("/segments/{sid}", dependencies=CSRF)
async def delete_segment(sid: str, admin=ADMIN):
    await db.mkt_segments.delete_one({"_id": _oid(sid)})
    return {"ok": True}


# ---------- AI copy ----------

class CopyIn(BaseModel):
    brief: str = Field(min_length=10, max_length=2000)
    audience: Audience = "vendor"
    tone: Literal["professional", "friendly", "urgent"] = "professional"


@router.post("/ai-copy", dependencies=CSRF)
async def ai_copy(body: CopyIn, admin=ADMIN):
    from routers.tender_pro import _llm_complete
    import json
    who = ("suppliers and contractors who could win tenders on PMC Managers" if body.audience == "vendor"
           else "organisations that issue tenders and could post them on PMC Managers")
    system = ("You write B2B marketing emails for PMC Managers, a global e-tendering and procurement platform. "
              f"Audience: {who}. Tone: {body.tone}. Never invent statistics, prices, customer names or awards. "
              "Return ONLY JSON: {\"subject\": str (max 70 chars), \"body_html\": str using only <p>, <ul>, <li>, <b>, <a href>}. "
              "Body 90-160 words, one clear call to action, no greeting placeholder.")
    raw = await _llm_complete(system, body.brief)
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        data = {}
    if not data.get("subject") or not data.get("body_html"):
        raise HTTPException(status_code=502, detail="The AI writer did not return a usable draft — try again.")
    return {"subject": data["subject"][:120], "body_html": data["body_html"]}


# ---------- campaigns ----------

class CampaignIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    subject: str = Field(min_length=2, max_length=150)
    body_html: str = Field(min_length=5, max_length=50_000)
    segment_id: str
    cta_label: str = ""
    cta_url: str = ""


def _links(html: str) -> List[str]:
    return re.findall(r'href="(https?://[^"]+)"', html)


def _personalise(c: dict, contact: dict, rid: str) -> str:
    base = _api_base()
    links = _links(c["body_html"])
    body = c["body_html"]
    for i, u in enumerate(links):
        body = body.replace(f'href="{u}"', f'href="{base}/api/v1/marketing/t/c/{rid}/{i}"', 1)
    cta = f"{base}/api/v1/marketing/t/c/{rid}/cta" if c.get("cta_url") else None
    unsub = f"{base}/api/v1/marketing/unsubscribe/{contact['unsub_token']}"
    foot = (f"<p style='font-size:11px;color:#888'>You are receiving this because you are a contact of PMC Managers. "
            f"<a href='{unsub}'>Unsubscribe</a></p><img src='{base}/api/v1/marketing/t/o/{rid}.gif' width='1' height='1' alt=''>")
    return wrap(c["subject"], body + foot, c.get("cta_label") or None, cta)


async def _run_campaign(cid: ObjectId) -> None:
    c = await db.mkt_campaigns.find_one({"_id": cid})
    seg = await db.mkt_segments.find_one({"_id": _oid(c["segment_id"])}) or {}
    sent = failed = 0
    async for contact in db.mkt_contacts.find(_segment_filter(seg)):
        if await db.mkt_sends.find_one({"campaign_id": str(cid), "email": contact["email"]}):
            continue
        rid = secrets.token_urlsafe(12)
        ok = await send_email(contact["email"], c["subject"], _personalise(c, contact, rid))
        await db.mkt_sends.insert_one({"campaign_id": str(cid), "rid": rid, "email": contact["email"],
                                       "status": "sent" if ok else "failed", "sent_at": now_iso()})
        sent += ok
        failed += (not ok)
        await asyncio.sleep(0.6)
    await db.mkt_campaigns.update_one({"_id": cid}, {"$set": {"status": "sent", "sent_at": now_iso(),
                                                              "sent_count": sent, "failed_count": failed}})


async def _stats(cid: str) -> dict:
    q = {"campaign_id": cid}
    return {"sent": await db.mkt_sends.count_documents({**q, "status": "sent"}),
            "failed": await db.mkt_sends.count_documents({**q, "status": "failed"}),
            "opened": await db.mkt_sends.count_documents({**q, "opened_at": {"$exists": True}}),
            "clicked": await db.mkt_sends.count_documents({**q, "clicked_at": {"$exists": True}})}


@router.get("/campaigns")
async def list_campaigns(admin=ADMIN):
    out = []
    async for c in db.mkt_campaigns.find().sort("created_at", -1).limit(200):
        out.append({**_id(c), "stats": await _stats(str(c["_id"]))})
    return {"items": out}


@router.post("/campaigns", dependencies=CSRF)
async def create_campaign(body: CampaignIn, admin=ADMIN):
    if not await db.mkt_segments.find_one({"_id": _oid(body.segment_id)}):
        raise HTTPException(status_code=422, detail="Pick a contact list (segment).")
    r = await db.mkt_campaigns.insert_one({**body.model_dump(), "status": "draft", "created_at": now_iso(),
                                           "created_by": admin.get("email")})
    return {"id": str(r.inserted_id)}


@router.put("/campaigns/{cid}", dependencies=CSRF)
async def update_campaign(cid: str, body: CampaignIn, admin=ADMIN):
    r = await db.mkt_campaigns.update_one({"_id": _oid(cid), "status": "draft"}, {"$set": body.model_dump()})
    if not r.matched_count:
        raise HTTPException(status_code=409, detail="Only drafts can be edited.")
    return {"ok": True}


@router.delete("/campaigns/{cid}", dependencies=CSRF)
async def delete_campaign(cid: str, admin=ADMIN):
    await db.mkt_campaigns.delete_one({"_id": _oid(cid), "status": "draft"})
    return {"ok": True}


class TestIn(BaseModel):
    email: EmailStr


@router.post("/campaigns/{cid}/test", dependencies=CSRF)
async def test_campaign(cid: str, body: TestIn, admin=ADMIN):
    c = await db.mkt_campaigns.find_one({"_id": _oid(cid)})
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    fake = {"unsub_token": "test-preview"}
    ok = await send_email(body.email, f"[TEST] {c['subject']}", _personalise(c, fake, "test"))
    return {"email_sent": ok}


@router.post("/campaigns/{cid}/send", dependencies=CSRF)
async def send_campaign(cid: str, bg: BackgroundTasks, admin=ADMIN):
    oid = _oid(cid)
    r = await db.mkt_campaigns.update_one({"_id": oid, "status": "draft"}, {"$set": {"status": "sending"}})
    if not r.matched_count:
        raise HTTPException(status_code=409, detail="This campaign was already sent.")
    c = await db.mkt_campaigns.find_one({"_id": oid})
    seg = await db.mkt_segments.find_one({"_id": _oid(c["segment_id"])}) or {}
    n = await db.mkt_contacts.count_documents(_segment_filter(seg))
    bg.add_task(_run_campaign, oid)
    await audit_log("marketing.campaign_send", admin, "mkt_campaign", cid, {"recipients": n})
    return {"queued": n}


# ---------- tracking + unsubscribe (public) ----------

@router.get("/t/o/{rid}.gif")
async def track_open(rid: str):
    await db.mkt_sends.update_one({"rid": rid, "opened_at": {"$exists": False}}, {"$set": {"opened_at": now_iso()}})
    return Response(content=PIXEL, media_type="image/gif", headers={"Cache-Control": "no-store"})


@router.get("/t/c/{rid}/{idx}")
async def track_click(rid: str, idx: str):
    s = await db.mkt_sends.find_one({"rid": rid})
    c = await db.mkt_campaigns.find_one({"_id": _oid(s["campaign_id"])}) if s else None
    if not c:
        return RedirectResponse(config.FRONTEND_URL)
    links = _links(c["body_html"])
    url = c.get("cta_url") if idx == "cta" else (links[int(idx)] if idx.isdigit() and int(idx) < len(links) else None)
    await db.mkt_sends.update_one({"_id": s["_id"], "clicked_at": {"$exists": False}},
                                  {"$set": {"clicked_at": now_iso(), "opened_at": s.get("opened_at") or now_iso()}})
    return RedirectResponse(url or config.FRONTEND_URL)


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str):
    r = await db.mkt_contacts.update_one({"unsub_token": token}, {"$set": {"unsubscribed": True, "unsubscribed_at": now_iso()}})
    msg = "You have been unsubscribed from PMC Managers marketing emails." if r.matched_count else "This link is no longer valid."
    return f"<html><body style='font-family:Georgia,serif;padding:48px;color:#1f3a2e'><h2>PMC Managers</h2><p>{msg}</p></body></html>"


# ---------- new-tender alerts ----------

class AlertSettingsIn(BaseModel):
    enabled: bool
    include_uploaded: bool = True


@router.get("/alerts")
async def alerts_overview(admin=ADMIN):
    s = await db.mkt_settings.find_one({"_id": "tender_alerts"}) or {}
    rows = await db.mkt_alert_log.find().sort("at", -1).limit(50).to_list(50)
    return {"enabled": bool(s.get("enabled")), "include_uploaded": s.get("include_uploaded", True),
            "items": [_id(r) for r in rows]}


@router.put("/alerts", dependencies=CSRF)
async def save_alerts(body: AlertSettingsIn, admin=ADMIN):
    await db.mkt_settings.update_one({"_id": "tender_alerts"}, {"$set": body.model_dump()}, upsert=True)
    return {"ok": True}


async def send_tender_alert(notice_ref: str) -> int:
    """Email vendors registered in (or interested in) the notice's category. Called after publish."""
    s = await db.mkt_settings.find_one({"_id": "tender_alerts"}) or {}
    if not s.get("enabled") or await db.mkt_alert_log.find_one({"notice_ref": notice_ref}):
        return 0
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n or not n.get("category"):
        return 0
    cat = n["category"]
    emails = {v["email"].lower() async for v in db.vendors.find({"business_categories": cat, "email": {"$exists": True}}, {"email": 1})}
    if s.get("include_uploaded", True):
        emails |= {c["email"] async for c in db.mkt_contacts.find(
            {"audience": "vendor", "categories": cat, "consent": True, "unsubscribed": {"$ne": True}}, {"email": 1})}
    blocked = {c["email"] async for c in db.mkt_contacts.find({"unsubscribed": True}, {"email": 1})}
    url = f"{config.FRONTEND_URL}/notices/{notice_ref}"
    sent = 0
    for e in sorted(emails - blocked):
        contact = await db.mkt_contacts.find_one({"email": e}, {"unsub_token": 1})
        unsub = (f"<p style='font-size:11px;color:#888'><a href='{_api_base()}/api/v1/marketing/unsubscribe/{contact['unsub_token']}'>"
                 "Stop tender alerts</a></p>") if contact else ""
        html = wrap(f"New tender: {n.get('title')}",
                    f"<p>A new tender in <b>{cat}</b> has been published on PMC Managers.</p>"
                    f"<p><b>{n.get('title')}</b><br>Country: {n.get('delivery_country', '')}"
                    f"{'<br>Closing: ' + str(n.get('submission_deadline'))[:10] if n.get('submission_deadline') else ''}</p>{unsub}",
                    "View tender", url)
        sent += await send_email(e, f"[PMC] New tender — {n.get('title')}"[:150], html)
        await asyncio.sleep(0.6)
    await db.mkt_alert_log.insert_one({"notice_ref": notice_ref, "title": n.get("title"), "category": cat,
                                       "recipients": sent, "at": now_iso()})
    return sent


# ---------- referrals ----------

async def _vendor_code(vendor: dict) -> str:
    v = await db.vendors.find_one({"vendor_ref": vendor.get("vendor_ref")}, {"referral_code": 1}) or {}
    if v.get("referral_code"):
        return v["referral_code"]
    code = secrets.token_hex(4).upper()
    await db.vendors.update_one({"vendor_ref": vendor.get("vendor_ref")}, {"$set": {"referral_code": code}})
    return code


@router.get("/referral/me")
async def my_referral(vendor=Depends(current_vendor)):
    code = await _vendor_code(vendor)
    rows = await db.mkt_referrals.find({"code": code}).sort("at", -1).to_list(200)
    return {"code": code, "link": f"{config.FRONTEND_URL}/register?ref={code}",
            "joined": len(rows), "items": [{"company": r.get("company") or "—", "at": r["at"],
                                             "status": r.get("status", "started")} for r in rows]}


@router.get("/referrals")
async def list_referrals(admin=ADMIN):
    board = await db.mkt_referrals.aggregate([
        {"$group": {"_id": "$code", "count": {"$sum": 1}, "last": {"$max": "$at"}}},
        {"$sort": {"count": -1}}, {"$limit": 100}]).to_list(100)
    out = []
    for b in board:
        v = await db.vendors.find_one({"referral_code": b["_id"]}, {"company_name": 1, "vendor_ref": 1}) or {}
        out.append({"code": b["_id"], "referrer": v.get("company_name") or v.get("vendor_ref") or "Unknown",
                    "count": b["count"], "last": b["last"]})
    recent = await db.mkt_referrals.find().sort("at", -1).limit(50).to_list(50)
    return {"leaders": out, "recent": [{**_id(r), "email": r["email"]} for r in recent]}


async def record_referral(code: Optional[str], email: str, company: Optional[str]) -> None:
    code = (code or "").strip().upper()[:16]
    if not code or not await db.vendors.find_one({"referral_code": code}, {"_id": 1}):
        return
    await db.mkt_referrals.update_one({"email": email.lower()},
                                      {"$setOnInsert": {"code": code, "email": email.lower(), "company": company or "",
                                                        "status": "started", "at": now_iso()}}, upsert=True)
