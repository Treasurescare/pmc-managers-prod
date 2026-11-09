"""Growth features: supplier AI summary & bid readiness (pay-per-use), saved tender alerts, supplier directory
with featured listings, consultancy services, buyer organisation applications and the tender data API."""
import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, EmailStr, Field

from audit import audit_log
from db import db
from models.base import BaseDocument, now_iso
from routers._fees import compute_amount, find_rule
from routers.vendor_auth import current_vendor
from security import require_role

router = APIRouter(prefix="/api/v1", tags=["growth"])
STAFF = ("admin", "reviewer")
LIVE_VENDOR = {"status": {"$in": ["approved", "active"]}}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _out(d: dict) -> dict:
    return BaseDocument.out(d)


# ----------------------------- pay per use -----------------------------

async def charge_or_pass(v: dict, code: str, ref: str, label: str) -> None:
    """Free when no fee rule or the supplier's fee is waived; otherwise consume a paid credit or ask for payment (402)."""
    from routers.pricing import vendor_waived
    vd = await db.vendors.find_one({"_id": ObjectId(v["id"])}, {"fee_plan": 1})
    if vendor_waived(vd, code):
        return
    rule = await find_rule(code, v.get("country") or "ZZ")
    amt = compute_amount(rule, 0) if rule else None
    if not amt:
        return
    if await db.paid_uses.find_one_and_update({"vendor_id": v["id"], "code": code, "ref": ref, "used": False},
                                              {"$set": {"used": True, "used_at": now_iso()}}):
        return
    from routers.payments_extra import _checkout, _site
    cur = (rule.get("currency") or "USD").upper()
    chk = await _checkout(amt, cur, "paid_use", "/pay/complete", "/pay/complete?cancel=1", _site(), {"code": code},
                          {"vendor_id": v["id"], "code": code, "ref": ref, "buyer_email": v.get("email"), "buyer_role": "vendor",
                           "product_code": code, "fee_kind": code, "label": label, "context_ref": ref})
    raise HTTPException(status_code=402, detail={"message": f"{label} costs {cur} {amt:,.2f}. Pay, then run it again.",
                                                 "checkout_url": chk["checkout_url"], "amount": amt, "currency": cur})


async def apply_paid_use(tx: dict) -> None:
    if await db.paid_uses.find_one({"session_id": tx["session_id"]}):
        return
    used = tx.get("code") == "featured_listing"
    await db.paid_uses.insert_one({"session_id": tx["session_id"], "vendor_id": tx.get("vendor_id"), "code": tx.get("code"),
                                   "ref": tx.get("ref"), "used": used, "created_at": now_iso()})
    if used:
        await _extend_featured(tx.get("vendor_id"), 30)


# ----------------------------- 1 + 2: supplier AI -----------------------------

SUMMARY_SYS = (
    "You read tender documents for suppliers. Reply with ONLY a JSON object, no markdown, with keys: "
    "summary (3-5 sentences), buyer, scope (list), eligibility (list), turnover (string or null), experience (string or null), "
    "emd (string or null), fees (list of strings), key_dates (list of {label, date}), documents_required (list), "
    "evaluation (string or null), risks (list of short warnings for a bidder). Use only facts in the text; use null or [] when absent. "
    "Write in the language requested.")
READY_SYS = (
    "You check whether a supplier is ready to bid. Compare the TENDER REQUIREMENTS with the SUPPLIER PROFILE. Reply with ONLY a JSON "
    "object: score (0-100), verdict (ready|gaps|high_risk), met (list), missing (list of documents or facts the supplier has not shown), "
    "risks (list of {item, severity: high|medium|low, fix}). Never invent supplier facts; anything not in the profile is missing.")


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:
        raise HTTPException(status_code=422, detail="The AI reply could not be read. Please try again.")


def _notice_text(n: dict) -> str:
    keep = ("title", "notice_ref", "category", "delivery_country", "description", "budget_amount", "currency",
            "submission_deadline", "bid_opening_date", "emd_config", "tender_criteria", "consortium_allowed")
    return json.dumps({k: n.get(k) for k in keep if n.get(k) is not None}, default=str)[:60000]


async def _llm(system: str, user: str) -> str:
    from routers.tender_pro import _llm_complete
    return await _llm_complete(system, user)


async def _vision_summary(name: str, mime: str, body: bytes, lang: str) -> str:
    """Scanned PDFs / photos: let a vision model read the pages directly."""
    import os
    import tempfile
    from pmc_lib.llm.chat import FileContentWithMimeType, LlmChat, UserMessage
    from routers.tender_pro import _llm_key
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(name)[1] or ".pdf")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(body)
        chat = LlmChat(api_key=_llm_key(), session_id=f"scan-{secrets.token_hex(6)}",
                       system_message=SUMMARY_SYS).with_model("gemini", "gemini-3.1-pro-preview")
        return await chat.send_message(UserMessage(
            text=f"Language: {lang}\n\nThe attached file is a scanned or photographed tender document. Read every page and reply with the JSON object.",
            file_contents=[FileContentWithMimeType(file_path=path, mime_type=mime)]))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="We could not read this scanned document. Please try again, or upload a clearer copy.")
    finally:
        os.remove(path)


IMAGE_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


@router.post("/supplier-ai/summary")
async def ai_summary(notice_ref: Optional[str] = Form(None), lang: str = Form("English"),
                     file: Optional[UploadFile] = File(None), v=Depends(current_vendor)):
    scan = None
    if file:
        body = await file.read()
        if len(body) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 15 MB)")
        from routers.tender_pro import _extract_text_from_upload
        name = (file.filename or "").lower()
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        ref, title = "file-" + hashlib.sha256(body).hexdigest()[:20], file.filename
        if ext in IMAGE_MIME:
            text, scan = "", IMAGE_MIME[ext]
        else:
            try:
                text = _extract_text_from_upload(file.filename, body)
            except HTTPException:
                if ext != ".pdf" or not body.lstrip()[:5].startswith(b"%PDF"):
                    raise
                text = ""
            if ext == ".pdf" and len(text.strip()) < 80:
                try:
                    from io import BytesIO
                    from pypdf import PdfReader
                    ok = len(PdfReader(BytesIO(body), strict=False).pages) > 0
                except Exception:
                    ok = False
                if not ok:
                    raise HTTPException(status_code=400, detail="This PDF looks damaged or only partly downloaded. Please try another copy, or enter the tender reference instead.")
                scan = "application/pdf"
    elif notice_ref:
        n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
        if not n:
            raise HTTPException(status_code=404, detail="Tender not found")
        text, ref, title = _notice_text(n), notice_ref, n.get("title")
    else:
        raise HTTPException(status_code=422, detail="Upload a tender document or choose a tender")
    if not scan and len((text or "").strip()) < 80:
        raise HTTPException(status_code=422, detail="Could not read enough text from this document.")
    old = await db.ai_reports.find_one({"vendor_id": v["id"], "kind": "summary", "ref": ref, "lang": lang})
    if old:
        return _out(old)
    await charge_or_pass(v, "ai_tender_summary", ref, "AI tender summary")
    if scan:
        data = _json(await _vision_summary(file.filename, scan, body, lang))
        text = "[scanned document read by AI vision] " + json.dumps(data, default=str)
    else:
        text = text.replace("\x00", " ")
        data = _json(await _llm(SUMMARY_SYS, f"Language: {lang}\n\nTENDER TEXT:\n{text[:120000]}"))
    doc = {"vendor_id": v["id"], "kind": "summary", "ref": ref, "lang": lang, "title": title, "notice_ref": notice_ref,
           "result": data, "source_text": text[:40000], "created_at": now_iso()}
    await db.ai_reports.insert_one(doc)
    doc.pop("source_text")
    return _out(doc)


class ReadinessIn(BaseModel):
    notice_ref: Optional[str] = None
    report_id: Optional[str] = None


async def _supplier_profile(v: dict) -> str:
    vd = await db.vendors.find_one({"_id": ObjectId(v["id"])}, {"password_hash": 0, "fee_plan": 0, "token_generation": 0}) or {}
    lic = [x.get("name") or x.get("license_type") or x.get("title") async for x in db.vendor_licenses.find({"vendor_id": v["id"]}).limit(50)]
    kyc = await db.kyc_cases.find_one({"vendor_id": v["id"]}, {"documents": 1, "status": 1}) or {}
    docs = [d.get("name") or d.get("type") for d in kyc.get("documents") or [] if isinstance(d, dict)]
    prof = {"company": vd.get("company_name"), "country": vd.get("country"), "kyc_status": vd.get("kyc_status"),
            "categories": vd.get("business_categories"), "profile": vd.get("profile"), "licences": lic, "kyc_documents": docs}
    return json.dumps(prof, default=str)[:30000]


@router.post("/supplier-ai/readiness")
async def ai_readiness(body: ReadinessIn, v=Depends(current_vendor)):
    if body.notice_ref:
        n = await db.notices.find_one({"notice_ref": body.notice_ref, "is_published": True})
        if not n:
            raise HTTPException(status_code=404, detail="Tender not found")
        req, ref, title = _notice_text(n), body.notice_ref, n.get("title")
    elif body.report_id and ObjectId.is_valid(body.report_id):
        r = await db.ai_reports.find_one({"_id": ObjectId(body.report_id), "vendor_id": v["id"], "kind": "summary"})
        if not r:
            raise HTTPException(status_code=404, detail="Summary not found")
        req, ref, title = json.dumps(r["result"]) + "\n" + (r.get("source_text") or "")[:30000], "rep-" + body.report_id, r.get("title")
    else:
        raise HTTPException(status_code=422, detail="Choose a tender or a saved summary")
    await charge_or_pass(v, "ai_bid_readiness", ref, "AI bid readiness check")
    data = _json(await _llm(READY_SYS, f"TENDER REQUIREMENTS:\n{req}\n\nSUPPLIER PROFILE:\n{await _supplier_profile(v)}"))
    doc = {"vendor_id": v["id"], "kind": "readiness", "ref": ref, "title": title, "notice_ref": body.notice_ref,
           "result": data, "created_at": now_iso()}
    await db.ai_reports.insert_one(doc)
    return _out(doc)


@router.get("/supplier-ai/reports")
async def ai_reports(v=Depends(current_vendor)):
    return {"items": [_out(d) async for d in db.ai_reports.find({"vendor_id": v["id"]}, {"source_text": 0}).sort("created_at", -1).limit(50)]}


@router.get("/supplier-ai/prices")
async def ai_prices(v=Depends(current_vendor)):
    from routers.pricing import vendor_waived
    vd = await db.vendors.find_one({"_id": ObjectId(v["id"])}, {"fee_plan": 1})
    out = {}
    for code in ("ai_tender_summary", "ai_bid_readiness", "featured_listing"):
        rule = None if vendor_waived(vd, code) else await find_rule(code, v.get("country") or "ZZ")
        amt = compute_amount(rule, 0) if rule else None
        out[code] = {"amount": amt or 0, "currency": (rule or {}).get("currency")}
    return out


# ----------------------------- 3: saved alerts -----------------------------

class AlertIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    countries: list[str] = Field(default_factory=list, max_length=60)
    categories: list[str] = Field(default_factory=list, max_length=30)
    min_value: Optional[float] = Field(default=None, ge=0)
    max_value: Optional[float] = Field(default=None, ge=0)
    frequency: Literal["instant", "daily", "weekly"] = "daily"
    include_global: bool = True
    is_active: bool = True


def _match(a: dict, t: dict) -> bool:
    txt = f"{t.get('title', '')} {t.get('description', '')} {t.get('buyer', '')} {t.get('category', '')}".lower()
    if a.get("keywords") and not any(k.lower() in txt for k in a["keywords"] if k.strip()):
        return False
    if a.get("countries") and (t.get("country") or "").upper() not in [c.upper() for c in a["countries"]]:
        return False
    if a.get("categories") and not any(c.lower() in (t.get("category") or "").lower() for c in a["categories"]):
        return False
    val = t.get("value")
    if a.get("min_value") and (val is None or val < a["min_value"]):
        return False
    return not (a.get("max_value") and val is not None and val > a["max_value"])


def _pmc_item(n: dict) -> dict:
    return {"title": n.get("title"), "description": n.get("description"), "category": n.get("category"), "buyer": "PMC Managers",
            "country": n.get("delivery_country"), "value": n.get("budget_amount"), "currency": n.get("currency"),
            "deadline": n.get("submission_deadline"), "url": f"/notices/{n['notice_ref']}", "source": "PMC", "ref": n["notice_ref"]}


@router.get("/vendor-alerts/saved")
async def list_alerts(v=Depends(current_vendor)):
    return {"items": [_out(a) async for a in db.saved_alerts.find({"vendor_id": v["id"]}).sort("created_at", -1)]}


@router.post("/vendor-alerts/saved")
async def create_alert(body: AlertIn, v=Depends(current_vendor)):
    if await db.saved_alerts.count_documents({"vendor_id": v["id"]}) >= 20:
        raise HTTPException(status_code=409, detail="You can keep up to 20 saved alerts")
    doc = {**body.model_dump(), "vendor_id": v["id"], "email": v["email"], "created_at": now_iso(), "last_sent_at": now_iso()}
    await db.saved_alerts.insert_one(doc)
    return _out(doc)


@router.put("/vendor-alerts/saved/{aid}")
async def update_alert(aid: str, body: AlertIn, v=Depends(current_vendor)):
    if not ObjectId.is_valid(aid):
        raise HTTPException(status_code=404, detail="Alert not found")
    r = await db.saved_alerts.update_one({"_id": ObjectId(aid), "vendor_id": v["id"]}, {"$set": body.model_dump()})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _out(await db.saved_alerts.find_one({"_id": ObjectId(aid)}))


@router.delete("/vendor-alerts/saved/{aid}")
async def delete_alert(aid: str, v=Depends(current_vendor)):
    if ObjectId.is_valid(aid):
        await db.saved_alerts.delete_one({"_id": ObjectId(aid), "vendor_id": v["id"]})
    return {"ok": True}


@router.get("/vendor-alerts/saved/{aid}/preview")
async def preview_alert(aid: str, v=Depends(current_vendor)):
    a = await db.saved_alerts.find_one({"_id": ObjectId(aid), "vendor_id": v["id"]}) if ObjectId.is_valid(aid) else None
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"items": (await _matches(a, None))[:25]}


async def _matches(a: dict, since: Optional[str]) -> list:
    out = []
    q = {"is_published": True, **({"published_at": {"$gte": since}} if since else {})}
    async for n in db.notices.find(q).sort("created_at", -1).limit(500):
        it = _pmc_item(n)
        if _match(a, it):
            out.append(it)
    if a.get("include_global"):
        gq = {"status": {"$ne": "cancelled"}, "duplicate_of": None, **({"first_seen_at": {"$gte": since}} if since else {})}
        async for t in db.external_tenders.find(gq).sort("first_seen_at", -1).limit(2000):
            if _match(a, t):
                out.append({k: t.get(k) for k in ("title", "buyer", "country", "value", "currency", "deadline", "url", "source", "ref")})
    return out


async def _send_alert(a: dict, items: list) -> None:
    from notify import vendor_confirm
    from routers.payments_extra import _site
    rows = "".join(f"<li><b>{i['title']}</b> — {i.get('buyer') or ''} · {i.get('country') or ''}"
                   f"{' · closes ' + str(i['deadline'])[:10] if i.get('deadline') else ''} · source {i.get('source')}</li>" for i in items[:30])
    await vendor_confirm(a["email"], f"{len(items)} new tenders match '{a['name']}'",
                         f"<p>New tenders matching your saved alert <b>{a['name']}</b>:</p><ul>{rows}</ul>",
                         "See tenders", f"{_site()}/vendor/saved-alerts")
    from routers.apns import send_to_vendor
    first = items[0]
    await send_to_vendor(a.get("vendor_id"), f"{len(items)} new tender{'s' if len(items) > 1 else ''}: {a['name']}",
                         f"{first['title']}" + (f" + {len(items) - 1} more" if len(items) > 1 else ""), "/vendor/saved-alerts")
    await db.saved_alerts.update_one({"_id": a["_id"]}, {"$set": {"last_sent_at": now_iso()}, "$inc": {"sent_count": 1}})


async def run_instant_alerts(notice_ref: str) -> None:
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        return
    it = _pmc_item(n)
    async for a in db.saved_alerts.find({"frequency": "instant", "is_active": True}):
        if _match(a, it):
            await _send_alert(a, [it])


async def run_digest_alerts(freq: str) -> int:
    sent = 0
    async for a in db.saved_alerts.find({"frequency": freq, "is_active": True}):
        items = await _matches(a, a.get("last_sent_at"))
        if items:
            await _send_alert(a, items)
            sent += 1
    return sent


# ----------------------------- 4: supplier directory -----------------------------

class ListingIn(BaseModel):
    listed: bool
    headline: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1500)
    website: Optional[str] = Field(default=None, max_length=200)


async def _extend_featured(vendor_id: Optional[str], days: int) -> None:
    if not vendor_id or not ObjectId.is_valid(vendor_id):
        return
    v = await db.vendors.find_one({"_id": ObjectId(vendor_id)}, {"directory": 1}) or {}
    cur = (v.get("directory") or {}).get("featured_until")
    base = max(_now(), datetime.fromisoformat(cur)) if cur else _now()
    await db.vendors.update_one({"_id": ObjectId(vendor_id)}, {"$set": {"directory.featured_until": (base + timedelta(days=days)).isoformat()}})


def _listing(v: dict) -> dict:
    d = v.get("directory") or {}
    feat = bool(d.get("featured_until") and d["featured_until"] > now_iso())
    return {"vendor_ref": v.get("vendor_ref"), "company_name": v.get("company_name"), "country": v.get("country"),
            "categories": v.get("business_categories") or [], "headline": d.get("headline"), "description": d.get("description"),
            "website": d.get("website"), "kyc_verified": v.get("kyc_status") == "verified", "featured": feat}


@router.get("/directory")
async def public_directory(q: Optional[str] = None, country: Optional[str] = None, category: Optional[str] = None,
                           limit: int = Query(60, ge=1, le=100), offset: int = Query(0, ge=0)):
    f = {**LIVE_VENDOR, "directory.listed": True}
    if country:
        f["country"] = country.upper()
    if category:
        f["business_categories"] = {"$regex": re.escape(category), "$options": "i"}
    if q:
        rx = {"$regex": re.escape(q[:80]), "$options": "i"}
        f["$or"] = [{"company_name": rx}, {"directory.headline": rx}, {"business_categories": rx}]
    rows = [_listing(v) async for v in db.vendors.find(f, {"vendor_ref": 1, "company_name": 1, "country": 1, "business_categories": 1,
                                                           "kyc_status": 1, "directory": 1}).limit(1000)]
    rows.sort(key=lambda r: (not r["featured"], (r["company_name"] or "").lower()))
    return {"total": len(rows), "items": rows[offset:offset + limit]}


@router.get("/directory/me")
async def my_listing(v=Depends(current_vendor)):
    vd = await db.vendors.find_one({"_id": ObjectId(v["id"])})
    return {**_listing(vd), "listed": bool((vd.get("directory") or {}).get("listed")),
            "featured_until": (vd.get("directory") or {}).get("featured_until")}


@router.put("/directory/me")
async def set_my_listing(body: ListingIn, v=Depends(current_vendor)):
    upd = {f"directory.{k}": val for k, val in body.model_dump().items()}
    await db.vendors.update_one({"_id": ObjectId(v["id"])}, {"$set": upd})
    return await my_listing(v)


@router.post("/directory/me/feature")
async def buy_feature(v=Depends(current_vendor)):
    from routers.pricing import vendor_waived
    vd = await db.vendors.find_one({"_id": ObjectId(v["id"])}, {"fee_plan": 1})
    if vendor_waived(vd, "featured_listing"):
        await _extend_featured(v["id"], 30)
        return {"ok": True, "featured": True}
    rule = await find_rule("featured_listing", v.get("country") or "ZZ")
    if not rule or not compute_amount(rule, 0):
        raise HTTPException(status_code=409, detail="Featured listings are not on sale right now. Contact PMC to be featured.")
    await charge_or_pass(v, "featured_listing", f"feature-{_now().strftime('%Y%m%d%H%M%S')}", "Featured listing (30 days)")
    await _extend_featured(v["id"], 30)
    return {"ok": True, "featured": True}


class FeatureIn(BaseModel):
    days: int = Field(ge=0, le=730)


@router.put("/directory/admin/{vendor_ref}/feature")
async def admin_feature(vendor_ref: str, body: FeatureIn, admin=Depends(require_role(*STAFF))):
    v = await db.vendors.find_one({"vendor_ref": vendor_ref}, {"_id": 1})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if body.days:
        await _extend_featured(str(v["_id"]), body.days)
    else:
        await db.vendors.update_one({"_id": v["_id"]}, {"$set": {"directory.featured_until": None}})
    await audit_log("directory.feature", admin, "vendor", vendor_ref, {"days": body.days})
    return {"ok": True}


@router.get("/directory/admin")
async def admin_directory(admin=Depends(require_role(*STAFF))):
    return {"items": [{**_listing(v), "listed": bool((v.get("directory") or {}).get("listed")),
                       "featured_until": (v.get("directory") or {}).get("featured_until")}
                      async for v in db.vendors.find(LIVE_VENDOR, {"vendor_ref": 1, "company_name": 1, "country": 1,
                                                                    "business_categories": 1, "kyc_status": 1, "directory": 1}).limit(2000)]}


# ----------------------------- 5: consultancy services -----------------------------

class ServiceIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=1200)
    price: Optional[float] = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    price_note: Optional[str] = Field(default=None, max_length=120)
    is_active: bool = True
    order: int = 0


class ServiceRequestIn(BaseModel):
    service_id: str
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: Optional[str] = Field(default=None, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=40)
    country: Optional[str] = Field(default=None, max_length=2)
    message: str = Field(min_length=5, max_length=3000)
    notice_ref: Optional[str] = Field(default=None, max_length=60)
    pay_now: bool = False


@router.get("/consulting/services")
async def public_services():
    return {"items": [_out(s) async for s in db.consulting_services.find({"is_active": True}).sort([("order", 1), ("name", 1)])]}


@router.get("/consulting/admin/services")
async def admin_services(admin=Depends(require_role(*STAFF))):
    return {"items": [_out(s) async for s in db.consulting_services.find({}).sort([("order", 1), ("name", 1)])]}


@router.post("/consulting/admin/services")
async def create_service(body: ServiceIn, admin=Depends(require_role("admin"))):
    doc = {**body.model_dump(), "currency": body.currency.upper(), "created_at": now_iso()}
    await db.consulting_services.insert_one(doc)
    await audit_log("consulting.service_create", admin, "consulting_service", body.name, {})
    return _out(doc)


@router.put("/consulting/admin/services/{sid}")
async def update_service(sid: str, body: ServiceIn, admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(sid):
        raise HTTPException(status_code=404, detail="Service not found")
    r = await db.consulting_services.update_one({"_id": ObjectId(sid)}, {"$set": {**body.model_dump(), "currency": body.currency.upper()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Service not found")
    return _out(await db.consulting_services.find_one({"_id": ObjectId(sid)}))


@router.post("/consulting/requests")
async def create_request(body: ServiceRequestIn, request: Request):
    s = await db.consulting_services.find_one({"_id": ObjectId(body.service_id), "is_active": True}) if ObjectId.is_valid(body.service_id) else None
    if not s:
        raise HTTPException(status_code=404, detail="Service not found")
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0]
    if await db.consulting_requests.count_documents({"ip": ip, "created_at": {"$gte": (_now() - timedelta(hours=1)).isoformat()}}) >= 5:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    doc = {**body.model_dump(exclude={"pay_now"}), "email": body.email.lower(), "service_name": s["name"], "ip": ip,
           "status": "new", "price": s.get("price"), "currency": s.get("currency"), "payment": "none", "created_at": now_iso()}
    r = await db.consulting_requests.insert_one(doc)
    from notify import notify_role
    await notify_role("admin", f"New consultancy request — {s['name']}",
                      f"<p>{body.name} ({body.email}, {body.company or 'no company'}) requested <b>{s['name']}</b>.</p><p>{body.message}</p>",
                      "consulting", str(r.inserted_id))
    out = {"ok": True, "id": str(r.inserted_id)}
    if body.pay_now and s.get("price"):
        from routers.payments_extra import _checkout, _site
        chk = await _checkout(s["price"], s.get("currency") or "USD", "consulting", "/pay/complete", "/pay/complete?cancel=1", _site(),
                              {"request_id": str(r.inserted_id)}, {"request_id": str(r.inserted_id), "buyer_email": doc["email"],
                                                                 "buyer_role": "client", "product_code": "consulting", "label": s["name"],
                                                                 "context_ref": s["name"]})
        await db.consulting_requests.update_one({"_id": r.inserted_id}, {"$set": {"payment": "pending", "session_id": chk["session_id"]}})
        out["checkout_url"] = chk["checkout_url"]
    return out


async def apply_consulting_payment(tx: dict) -> None:
    if tx.get("request_id") and ObjectId.is_valid(tx["request_id"]):
        await db.consulting_requests.update_one({"_id": ObjectId(tx["request_id"])}, {"$set": {"payment": "paid", "paid_at": now_iso()}})


class RequestUpdateIn(BaseModel):
    status: Literal["new", "assigned", "in_progress", "done", "cancelled"]
    assigned_to: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=2000)


@router.get("/consulting/admin/requests")
async def admin_requests(admin=Depends(require_role(*STAFF))):
    return {"items": [_out(d) async for d in db.consulting_requests.find({}, {"ip": 0}).sort("created_at", -1).limit(500)]}


@router.patch("/consulting/admin/requests/{rid}")
async def update_request(rid: str, body: RequestUpdateIn, admin=Depends(require_role(*STAFF))):
    if not ObjectId.is_valid(rid):
        raise HTTPException(status_code=404, detail="Request not found")
    await db.consulting_requests.update_one({"_id": ObjectId(rid)}, {"$set": {**body.model_dump(), "updated_at": now_iso(),
                                                                              "updated_by": admin["email"]}})
    await audit_log("consulting.request_update", admin, "consulting_request", rid, body.model_dump())
    return {"ok": True}


# ----------------------------- 6: buyer organisation applications -----------------------------

class BuyerAppIn(BaseModel):
    org_name: str = Field(min_length=2, max_length=160)
    org_type: Literal["bank", "government", "psu", "private", "ngo", "other"]
    country: str = Field(min_length=2, max_length=2)
    contact_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    website: Optional[str] = Field(default=None, max_length=200)
    tenders_per_year: Optional[int] = Field(default=None, ge=0, le=100000)
    message: Optional[str] = Field(default=None, max_length=2000)


@router.post("/buyer-applications")
async def apply_buyer(body: BuyerAppIn, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0]
    if await db.buyer_applications.count_documents({"ip": ip, "created_at": {"$gte": (_now() - timedelta(hours=1)).isoformat()}}) >= 5:
        raise HTTPException(status_code=429, detail="Too many applications. Please try again later.")
    doc = {**body.model_dump(), "email": body.email.lower(), "country": body.country.upper(), "ip": ip, "status": "pending", "created_at": now_iso()}
    r = await db.buyer_applications.insert_one(doc)
    from notify import notify_role, vendor_confirm
    await notify_role("admin", f"New buyer organisation application — {body.org_name}",
                      f"<p>{body.org_name} ({body.org_type}, {doc['country']}) applied to issue tenders. Contact: {body.contact_name} &lt;{doc['email']}&gt;.</p>"
                      "<p>Review in Admin → Buyer applications.</p>", "buyer_application", str(r.inserted_id))
    await vendor_confirm(doc["email"], "We received your application — PMC Managers",
                         f"<p>Thank you, {body.contact_name}. We have received the application for <b>{body.org_name}</b> to issue tenders on the "
                         "Global Tender Grid. Our team will review it and contact you within two working days.</p>", None, None)
    return {"ok": True, "id": str(r.inserted_id)}


class BuyerDecisionIn(BaseModel):
    action: Literal["approve", "reject"]
    code: Optional[str] = Field(default=None, min_length=3, max_length=32)
    tier: Optional[str] = Field(default=None, max_length=40)
    notes: Optional[str] = Field(default=None, max_length=1000)


@router.get("/buyer-applications")
async def list_buyer_apps(admin=Depends(require_role(*STAFF))):
    return {"items": [_out(d) async for d in db.buyer_applications.find({}, {"ip": 0}).sort("created_at", -1).limit(500)]}


@router.post("/buyer-applications/{aid}/decision")
async def decide_buyer(aid: str, body: BuyerDecisionIn, admin=Depends(require_role(*STAFF))):
    a = await db.buyer_applications.find_one({"_id": ObjectId(aid)}) if ObjectId.is_valid(aid) else None
    if not a or a["status"] != "pending":
        raise HTTPException(status_code=409, detail="Only pending applications can be decided")
    from notify import vendor_confirm
    upd = {"status": "approved" if body.action == "approve" else "rejected", "decided_by": admin["email"], "decided_at": now_iso(),
           "notes": body.notes, "tier": body.tier}
    if body.action == "approve":
        code = re.sub(r"[^A-Z0-9]+", "", (body.code or a["org_name"]).upper())[:16] or "ORG"
        if len(code) < 3 or await db.tenants.find_one({"code": code}):
            code = f"{code[:10]}{secrets.randbelow(9000) + 1000}"
        await db.tenants.insert_one({"code": code, "name": a["org_name"], "kind": "government" if a["org_type"] in ("government", "psu") else "corporate",
                                     "country": a["country"], "primary_contact_email": a["email"], "primary_contact_name": a["contact_name"],
                                     "org_type": a["org_type"], "pricing_tier": body.tier, "is_active": True, "created_at": now_iso(),
                                     "created_by": admin["id"], "source": "buyer_application"})
        upd["tenant_code"] = code
        await vendor_confirm(a["email"], "Your PMC Managers buyer account is approved",
                             f"<p>Good news — <b>{a['org_name']}</b> is approved to issue tenders on the Global Tender Grid. Your organisation code is "
                             f"<b>{code}</b>. Our onboarding team will send your administrator sign-in and walk you through your first tender.</p>", None, None)
    else:
        await vendor_confirm(a["email"], "Your PMC Managers application",
                             f"<p>Thank you for applying. We are unable to approve <b>{a['org_name']}</b> at this time."
                             f"{(' ' + body.notes) if body.notes else ''} You can reply to this email with any questions.</p>", None, None)
    await db.buyer_applications.update_one({"_id": a["_id"]}, {"$set": upd})
    await audit_log("buyer_application.decide", admin, "buyer_application", aid, upd)
    return {"ok": True, **upd}


# ----------------------------- 7: tender data API -----------------------------

class ApiClientIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    plan: str = Field(default="Standard", max_length=40)
    daily_limit: int = Field(default=1000, ge=10, le=1_000_000)
    is_active: bool = True


def _hash(k: str) -> str:
    return hashlib.sha256(k.encode()).hexdigest()


@router.get("/data-api/clients")
async def list_clients(admin=Depends(require_role("admin"))):
    return {"items": [_out(c) async for c in db.api_clients.find({}, {"key_hash": 0}).sort("created_at", -1)]}


@router.post("/data-api/clients")
async def create_client(body: ApiClientIn, admin=Depends(require_role("admin"))):
    key = "pmc_" + secrets.token_urlsafe(32)
    doc = {**body.model_dump(), "email": body.email.lower(), "key_hash": _hash(key), "key_hint": key[-4:], "created_at": now_iso()}
    await db.api_clients.insert_one(doc)
    await audit_log("data_api.client_create", admin, "api_client", body.name, {"plan": body.plan})
    doc.pop("key_hash")
    return {**_out(doc), "api_key": key}


@router.put("/data-api/clients/{cid}")
async def update_client(cid: str, body: ApiClientIn, admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(cid):
        raise HTTPException(status_code=404, detail="Client not found")
    await db.api_clients.update_one({"_id": ObjectId(cid)}, {"$set": {**body.model_dump(), "email": body.email.lower()}})
    return {"ok": True}


@router.post("/data-api/clients/{cid}/rotate")
async def rotate_client(cid: str, admin=Depends(require_role("admin"))):
    key = "pmc_" + secrets.token_urlsafe(32)
    r = await db.api_clients.update_one({"_id": ObjectId(cid)}, {"$set": {"key_hash": _hash(key), "key_hint": key[-4:]}}) if ObjectId.is_valid(cid) else None
    if not r or not r.matched_count:
        raise HTTPException(status_code=404, detail="Client not found")
    await audit_log("data_api.rotate", admin, "api_client", cid, {})
    return {"api_key": key}


async def _api_client(key: str) -> dict:
    c = await db.api_clients.find_one({"key_hash": _hash(key or ""), "is_active": True}) if key else None
    if not c:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    day = _now().strftime("%Y-%m-%d")
    u = await db.api_usage.find_one_and_update({"client_id": str(c["_id"]), "day": day}, {"$inc": {"count": 1}},
                                               upsert=True, return_document=True)
    if (u or {}).get("count", 0) > c.get("daily_limit", 1000):
        raise HTTPException(status_code=429, detail="Daily request limit reached")
    return c


@router.get("/data/tenders")
async def data_tenders(x_api_key: str = Header(default=""), q: Optional[str] = None, country: Optional[str] = None,
                       source: Literal["all", "pmc", "global"] = "all", updated_since: Optional[str] = None,
                       limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    await _api_client(x_api_key)
    rx = {"$regex": re.escape(q[:80]), "$options": "i"} if q else None
    pf = {"is_published": True, **({"delivery_country": country.upper()} if country else {}), **({"title": rx} if rx else {})}
    gf = {"duplicate_of": None, **({"country": country.upper()} if country else {}), **({"title": rx} if rx else {}),
          **({"updated_at": {"$gte": updated_since}} if updated_since else {})}
    pt = await db.notices.count_documents(pf) if source in ("all", "pmc") else 0
    gt = await db.external_tenders.count_documents(gf) if source in ("all", "global") else 0
    items = []
    if offset < pt:
        async for n in db.notices.find(pf).sort("created_at", -1).skip(offset).limit(limit):
            items.append({**_pmc_item(n), "status": n.get("status")})
    left = limit - len(items)
    if left > 0 and gt:
        async for t in db.external_tenders.find(gf, {"_id": 0, "raw": 0, "dedupe_key": 0}).sort("first_seen_at", -1).skip(max(0, offset - pt)).limit(left):
            items.append(t)
    return {"total": pt + gt, "count": len(items), "offset": offset, "items": items}


async def ensure_indexes() -> None:
    await db.paid_uses.create_index([("vendor_id", 1), ("code", 1), ("ref", 1)])
    await db.ai_reports.create_index([("vendor_id", 1), ("created_at", -1)])
    await db.saved_alerts.create_index([("frequency", 1), ("is_active", 1)])
    await db.api_clients.create_index("key_hash")
    await db.api_usage.create_index([("client_id", 1), ("day", 1)], unique=True)
