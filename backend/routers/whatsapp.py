"""WhatsApp Cloud API: tender alerts, payment messages, inbound inbox and AI auto-reply."""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

import config
from db import db
from models.base import now_iso
from routers.vendor_auth import current_vendor
from security import require_csrf, require_role

log = logging.getLogger(__name__)
router = APIRouter(tags=["whatsapp"])
ADMIN = Depends(require_role("admin"))
CSRF = [Depends(require_csrf)]

TPL_TENDER, TPL_REMIND, TPL_RECEIPT = "pmc_new_tender", "pmc_payment_reminder", "pmc_payment_receipt"
DEFAULTS = {"tender_alerts": True, "payment_msgs": True, "ai_autoreply": True, "template_lang": "en"}


def _env(k: str) -> str:
    return os.environ.get(k, "").strip()


def configured() -> bool:
    return all(_env(k) for k in ("WA_PHONE_NUMBER_ID", "WA_ACCESS_TOKEN", "WA_APP_SECRET", "WA_VERIFY_TOKEN"))


def norm_number(raw: str) -> str:
    d = re.sub(r"\D", "", raw or "")
    return d if 8 <= len(d) <= 15 else ""


async def _settings() -> dict:
    s = await db.mkt_settings.find_one({"_id": "whatsapp"}) or {}
    return {k: s.get(k, v) for k, v in DEFAULTS.items()}


def _site() -> str:
    return config.FRONTEND_URL.rstrip("/")


def _api() -> str:
    return (getattr(config, "PUBLIC_API_URL", "") or config.FRONTEND_URL).rstrip("/")


async def _send(to: str, body: dict, kind: str, preview: str, vendor_ref: Optional[str] = None) -> bool:
    if not configured():
        return False
    url = f"https://graph.facebook.com/{_env('WA_GRAPH_VERSION') or 'v24.0'}/{_env('WA_PHONE_NUMBER_ID')}/messages"
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, headers={"Authorization": f"Bearer {_env('WA_ACCESS_TOKEN')}"},
                             json={"messaging_product": "whatsapp", "to": to, **body})
        ok, data = r.is_success, (r.json() if r.content else {})
    except Exception as e:
        ok, data = False, {"error": str(e)}
    wamid = ((data.get("messages") or [{}])[0]).get("id") if ok else None
    await db.wa_messages.insert_one({"wa_id": to, "direction": "out", "kind": kind, "text": preview, "wamid": wamid,
                                     "status": "sent" if ok else "failed",
                                     "error": None if ok else json.dumps(data.get("error", data))[:500], "at": now_iso()})
    await db.wa_threads.update_one({"wa_id": to}, {"$set": {"last_at": now_iso(), "last_text": preview[:120]},
                                                   "$setOnInsert": {"vendor_ref": vendor_ref, "unread": 0}}, upsert=True)
    if not ok:
        log.warning("whatsapp send failed to %s: %s", to, data)
    return ok


async def _template(to: str, name: str, params: list, preview: str, vendor_ref=None, doc: Optional[dict] = None) -> bool:
    comps = [{"type": "body", "parameters": [{"type": "text", "text": str(p)[:900]} for p in params]}]
    if doc:
        comps.insert(0, {"type": "header", "parameters": [{"type": "document", "document": doc}]})
    lang = (await _settings())["template_lang"]
    return await _send(to, {"type": "template", "template": {"name": name, "language": {"code": lang}, "components": comps}},
                       name, preview, vendor_ref)


async def _opted_vendor(vendor_ref: Optional[str] = None, vendor_id: Optional[str] = None) -> Optional[dict]:
    q = {"vendor_ref": vendor_ref} if vendor_ref else {"_id": ObjectId(vendor_id)}
    v = await db.vendors.find_one({**q, "wa_opt_in": True, "wa_number": {"$nin": [None, ""]}})
    return v


# ---------- outbound hooks (fire-and-forget, never raise) ----------

async def notify_tender(notice_ref: str) -> int:
    try:
        if not configured() or not (await _settings())["tender_alerts"]:
            return 0
        n = await db.notices.find_one({"notice_ref": notice_ref})
        if not n or not n.get("category"):
            return 0
        if await db.wa_alert_log.find_one({"notice_ref": notice_ref}):
            return 0
        await db.wa_alert_log.insert_one({"notice_ref": notice_ref, "at": now_iso()})
        sent = 0
        closes = str(n.get("submission_deadline") or "")[:10] or "see tender"
        link = f"{_site()}/notices/{notice_ref}"
        async for v in db.vendors.find({"business_categories": n["category"], "wa_opt_in": True, "wa_number": {"$nin": [None, ""]}}):
            sent += await _template(v["wa_number"], TPL_TENDER, [n["category"], n.get("title") or notice_ref, closes, link],
                                    f"New tender: {n.get('title')}", v.get("vendor_ref"))
            await asyncio.sleep(0.2)
        await db.wa_alert_log.update_one({"notice_ref": notice_ref}, {"$set": {"recipients": sent}})
        return sent
    except Exception:
        log.exception("whatsapp tender alert failed for %s", notice_ref)
        return 0


async def notify_payment_reminder(vendor_ref: str, item: str, amount: str, link: str) -> bool:
    try:
        if not configured() or not (await _settings())["payment_msgs"]:
            return False
        v = await _opted_vendor(vendor_ref=vendor_ref)
        return bool(v) and await _template(v["wa_number"], TPL_REMIND, [amount, item, link], f"Payment reminder: {item} {amount}", vendor_ref)
    except Exception:
        log.exception("whatsapp reminder failed")
        return False


async def notify_receipt(vendor_id: str, rec: dict) -> bool:
    try:
        if not configured() or not (await _settings())["payment_msgs"]:
            return False
        v = await _opted_vendor(vendor_id=vendor_id)
        if not v:
            return False
        token = secrets.token_urlsafe(24)
        await db.wa_docs.insert_one({"token": token, "receipt_no": rec["receipt_no"], "vendor_id": vendor_id,
                                     "at_dt": datetime.now(timezone.utc)})
        doc = {"link": f"{_api()}/api/v1/whatsapp/doc/{token}.pdf", "filename": f"{rec['receipt_no']}.pdf"}
        amt = f"{rec['currency']} {float(rec['total']):,.2f}"
        items = ", ".join(x["name"] for x in rec.get("lines") or [])[:200] or "PMC fees"
        return await _template(v["wa_number"], TPL_RECEIPT, [amt, items, rec["receipt_no"]],
                               f"Receipt {rec['receipt_no']} {amt}", v.get("vendor_ref"), doc)
    except Exception:
        log.exception("whatsapp receipt failed")
        return False


@router.get("/api/v1/whatsapp/doc/{token}.pdf")
async def wa_doc(token: str):
    d = await db.wa_docs.find_one({"token": token})
    rec = d and await db.fee_receipts.find_one({"receipt_no": d["receipt_no"], "vendor_id": d["vendor_id"]})
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    from routers.site_settings import render_receipt_pdf
    v = await db.vendors.find_one({"_id": ObjectId(d["vendor_id"])}) or {}
    pdf = await asyncio.to_thread(render_receipt_pdf, rec, v)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{rec["receipt_no"]}.pdf"'})


# ---------- webhook ----------

@router.get("/api/v1/whatsapp/webhook")
async def wa_verify(mode: str = Query("", alias="hub.mode"), token: str = Query("", alias="hub.verify_token"),
                    challenge: str = Query("", alias="hub.challenge")):
    vt = _env("WA_VERIFY_TOKEN")
    if mode == "subscribe" and vt and hmac.compare_digest(token, vt):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/api/v1/whatsapp/webhook")
async def wa_webhook(request: Request, bg: BackgroundTasks):
    raw = await request.body()
    secret = _env("WA_APP_SECRET")
    got = request.headers.get("X-Hub-Signature-256", "")
    exp = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest() if secret else ""
    if not secret or not got or not hmac.compare_digest(got, exp):
        raise HTTPException(status_code=401, detail="Invalid signature")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad JSON")
    bg.add_task(_process, payload)
    return {"ok": True}


async def _process(payload: dict) -> None:
    for entry in payload.get("entry") or []:
        for ch in entry.get("changes") or []:
            val = ch.get("value") or {}
            for st in val.get("statuses") or []:
                if st.get("id"):
                    await db.wa_messages.update_one({"wamid": st["id"], "direction": "out"},
                                                    {"$set": {"status": st.get("status")}})
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in val.get("contacts") or []}
            for m in val.get("messages") or []:
                try:
                    await _inbound(m, names.get(m.get("from")))
                except Exception:
                    log.exception("whatsapp inbound failed")


async def _inbound(m: dict, name: Optional[str]) -> None:
    wa_id, wamid = m.get("from"), m.get("id")
    if not wa_id or not wamid or await db.wa_messages.find_one({"wamid": wamid}):
        return
    text = ((m.get("text") or {}).get("body") or (m.get("button") or {}).get("text") or "").strip()
    if not text:
        text = f"[{m.get('type', 'message')}]"
    v = await db.vendors.find_one({"wa_number": wa_id})
    await db.wa_messages.insert_one({"wa_id": wa_id, "direction": "in", "kind": m.get("type"), "text": text[:4000],
                                     "wamid": wamid, "at": now_iso()})
    await db.wa_threads.update_one({"wa_id": wa_id}, {
        "$set": {"last_at": now_iso(), "last_inbound_at": now_iso(), "last_text": text[:120], "name": name,
                 "vendor_ref": v.get("vendor_ref") if v else None, "company": v.get("company_name") if v else None},
        "$inc": {"unread": 1}}, upsert=True)
    if text.lower() in {"stop", "unsubscribe", "opt out", "stop all"}:
        await db.vendors.update_many({"wa_number": wa_id}, {"$set": {"wa_opt_in": False, "wa_opt_out_at": now_iso()}})
        await _send(wa_id, {"type": "text", "text": {"body": "You won't get any more PMC WhatsApp alerts. You can switch them back on in your supplier portal."}},
                    "text", "Opt-out confirmed")
        return
    if (await _settings())["ai_autoreply"] and not text.startswith("["):
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        if await db.wa_messages.count_documents({"wa_id": wa_id, "kind": "ai", "at": {"$gte": since}}) < 20:
            reply = await _ai_reply(wa_id, text, v)
            if reply:
                await _send(wa_id, {"type": "text", "text": {"body": reply}}, "ai", reply)


async def _ai_reply(wa_id: str, text: str, v: Optional[dict]) -> str:
    from routers.assistant import ABOUT, RULES, _context
    from routers.tender_pro import _llm_complete
    sid = f"wa:{wa_id}"
    s = await db.assistant_sessions.find_one({"session_id": sid}) or {}
    hist = (s.get("messages") or [])[-10:]
    convo = "\n".join(f"{x['role'].upper()}: {x['text']}" for x in hist)
    system = (f"{RULES} You are replying on WhatsApp; keep it short. For anything you can't answer, say a PMC team member "
              f"will reply here.\n\nABOUT PMC:\n{ABOUT}\n\n{await _context(v)}")
    try:
        reply = (await _llm_complete(system, f"{convo}\nUSER: {text}\nASSISTANT:") or "").strip()
    except Exception:
        log.exception("whatsapp ai reply failed")
        return ""
    if reply:
        msgs = hist + [{"role": "user", "text": text, "at": now_iso()}, {"role": "assistant", "text": reply, "at": now_iso()}]
        await db.assistant_sessions.update_one({"session_id": sid}, {"$set": {"messages": msgs, "channel": "whatsapp",
            "vendor_id": str(v["_id"]) if v else None, "updated_at": now_iso()}, "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
    return reply


# ---------- admin ----------

class WaSettingsIn(BaseModel):
    tender_alerts: bool = True
    payment_msgs: bool = True
    ai_autoreply: bool = True
    template_lang: str = Field("en", pattern=r"^[a-z]{2}(_[A-Z]{2})?$")


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class TestIn(BaseModel):
    number: str


def _o(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


@router.get("/api/v1/admin/whatsapp/status")
async def wa_status(admin=ADMIN):
    return {"configured": configured(), "settings": await _settings(),
            "webhook_url": f"{_api()}/api/v1/whatsapp/webhook",
            "opted_in": await db.vendors.count_documents({"wa_opt_in": True}),
            "templates": [TPL_TENDER, TPL_REMIND, TPL_RECEIPT]}


@router.put("/api/v1/admin/whatsapp/settings", dependencies=CSRF)
async def wa_save_settings(body: WaSettingsIn, admin=ADMIN):
    await db.mkt_settings.update_one({"_id": "whatsapp"}, {"$set": body.model_dump()}, upsert=True)
    return await _settings()


@router.post("/api/v1/admin/whatsapp/test", dependencies=CSRF)
async def wa_test(body: TestIn, admin=ADMIN):
    to = norm_number(body.number)
    if not to:
        raise HTTPException(status_code=422, detail="Enter the number with country code, digits only")
    if not configured():
        raise HTTPException(status_code=424, detail="WhatsApp is not connected yet")
    ok = await _send(to, {"type": "template", "template": {"name": "hello_world", "language": {"code": "en_US"}}},
                     "hello_world", "Test message (hello_world)")
    return {"sent": ok}


@router.get("/api/v1/admin/whatsapp/threads")
async def wa_threads(admin=ADMIN):
    rows = await db.wa_threads.find().sort("last_at", -1).limit(200).to_list(200)
    return {"items": [_o(r) for r in rows]}


@router.get("/api/v1/admin/whatsapp/threads/{wa_id}")
async def wa_thread(wa_id: str, admin=ADMIN):
    t = await db.wa_threads.find_one({"wa_id": wa_id})
    if not t:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.wa_threads.update_one({"wa_id": wa_id}, {"$set": {"unread": 0}})
    msgs = await db.wa_messages.find({"wa_id": wa_id}).sort("at", 1).limit(500).to_list(500)
    li = t.get("last_inbound_at")
    open_ = bool(li) and li >= (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return {"thread": _o(t), "messages": [_o(m) for m in msgs], "window_open": open_}


@router.post("/api/v1/admin/whatsapp/threads/{wa_id}/reply", dependencies=CSRF)
async def wa_reply(wa_id: str, body: ReplyIn, admin=ADMIN):
    t = await db.wa_threads.find_one({"wa_id": wa_id})
    li = (t or {}).get("last_inbound_at")
    if not li or li < (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat():
        raise HTTPException(status_code=409, detail="WhatsApp only allows free replies within 24 hours of their last message")
    if not configured():
        raise HTTPException(status_code=424, detail="WhatsApp is not connected yet")
    ok = await _send(wa_id, {"type": "text", "text": {"body": body.text}}, "staff", body.text)
    if not ok:
        raise HTTPException(status_code=502, detail="WhatsApp did not accept the message")
    await db.wa_messages.update_one({"wa_id": wa_id, "kind": "staff", "text": body.text},
                                    {"$set": {"by": admin.get("email")}})
    return {"sent": True}


# ---------- vendor opt-in ----------

class VendorWaIn(BaseModel):
    number: str = ""
    opt_in: bool = False


@router.get("/api/v1/vendor/whatsapp")
async def vendor_wa(vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])}) or {}
    return {"number": v.get("wa_number") or norm_number(v.get("contact_mobile") or ""), "opt_in": bool(v.get("wa_opt_in")),
            "available": configured()}


@router.put("/api/v1/vendor/whatsapp")
async def vendor_wa_save(body: VendorWaIn, vendor=Depends(current_vendor)):
    num = norm_number(body.number)
    if body.opt_in and not num:
        raise HTTPException(status_code=422, detail="Enter your WhatsApp number with country code, e.g. 447700900123")
    upd = {"wa_number": num or None, "wa_opt_in": bool(body.opt_in and num)}
    if upd["wa_opt_in"]:
        upd |= {"wa_opt_in_at": now_iso(), "wa_opt_in_source": "vendor_portal"}
    await db.vendors.update_one({"_id": ObjectId(vendor["id"])}, {"$set": upd})
    return {"number": num, "opt_in": upd["wa_opt_in"]}


async def ensure_indexes() -> None:
    await db.wa_messages.create_index("wamid", sparse=True)
    await db.wa_messages.create_index([("wa_id", 1), ("at", 1)])
    await db.wa_threads.create_index("wa_id", unique=True)
    await db.wa_docs.create_index("at_dt", expireAfterSeconds=7 * 86400)
    await db.wa_alert_log.create_index("notice_ref", unique=True)
