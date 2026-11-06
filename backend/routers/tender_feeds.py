"""Tender collection from open public sources (World Bank, EU TED) plus a configurable licensed-provider pipe."""
import asyncio
import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import BaseDocument, now_iso
from security import require_role

router = APIRouter(prefix="/api/v1", tags=["tender-feeds"])
log = logging.getLogger("tender_feeds")

SOURCES = [
    {"code": "WORLDBANK", "name": "World Bank procurement notices", "kind": "worldbank", "enabled": True, "licence": "Open data (World Bank terms)",
     "url": "https://search.worldbank.org/api/v2/procnotices"},
    {"code": "TED", "name": "EU Tenders Electronic Daily (TED)", "kind": "ted", "enabled": True, "licence": "Open data (EU reuse policy)",
     "url": "https://api.ted.europa.eu/v3/notices/search"},
    {"code": "PROVIDER", "name": "Licensed data provider (configure when subscribed)", "kind": "provider", "enabled": False,
     "licence": "Paid subscription", "url": "", "api_key_env": "TENDER_PROVIDER_API_KEY", "auth_header": "Authorization",
     "auth_prefix": "Bearer ", "items_path": "data",
     "mapping": {"ref": "id", "title": "title", "buyer": "buyer", "country": "country", "deadline": "deadline", "value": "value",
                 "currency": "currency", "url": "url", "status": "status", "description": "description"}},
]
CATS = {
    "Construction & Civil": ["construction", "civil", "road", "bridge", "building", "rehabilitation", "infrastructure", "works"],
    "Healthcare & Medical": ["medical", "hospital", "health", "pharma", "laboratory", "diagnostic", "vaccine"],
    "IT & Telecom": ["software", "it ", "information technology", "digital", "telecom", "network", "computer", "cloud", "system"],
    "Energy & Utilities": ["energy", "power", "solar", "electric", "water supply", "sanitation", "utility", "grid"],
    "Consultancy & Advisory": ["consult", "advisory", "technical assistance", "study", "audit", "supervision"],
    "Equipment & Vehicles": ["vehicle", "equipment", "machinery", "truck", "supply of", "goods"],
    "Education & Training": ["school", "education", "training", "university"],
    "Agriculture & Environment": ["agricultur", "irrigation", "forest", "environment", "climate", "fisher"],
}
ISO3 = {"Turkiye": "TR", "Brazil": "BR", "India": "IN", "Kenya": "KE", "Nigeria": "NG", "Pakistan": "PK", "Bangladesh": "BD",
        "Indonesia": "ID", "Philippines": "PH", "Viet Nam": "VN", "Vietnam": "VN", "Egypt, Arab Republic of": "EG", "Kazakhstan": "KZ",
        "Uzbekistan": "UZ", "Ethiopia": "ET", "Tanzania": "TZ", "Uganda": "UG", "Ghana": "GH", "Morocco": "MA", "Mexico": "MX",
        "Colombia": "CO", "Peru": "PE", "Argentina": "AR", "Ukraine": "UA", "Nepal": "NP", "Sri Lanka": "LK", "Malaysia": "MY",
        "China": "CN", "Mongolia": "MN", "Kyrgyz Republic": "KG", "Tajikistan": "TJ", "Rwanda": "RW", "Zambia": "ZM", "Mozambique": "MZ",
        "Cameroon": "CM", "Senegal": "SN", "Jordan": "JO", "Lebanon": "LB", "Iraq": "IQ", "Tunisia": "TN", "Ecuador": "EC",
        "Bolivia": "BO", "Honduras": "HN", "Guatemala": "GT", "Haiti": "HT", "Madagascar": "MG", "Malawi": "MW", "Afghanistan": "AF"}
TED3 = {"AUT": "AT", "BEL": "BE", "BGR": "BG", "HRV": "HR", "CYP": "CY", "CZE": "CZ", "DNK": "DK", "EST": "EE", "FIN": "FI", "FRA": "FR",
        "DEU": "DE", "GRC": "GR", "HUN": "HU", "IRL": "IE", "ITA": "IT", "LVA": "LV", "LTU": "LT", "LUX": "LU", "MLT": "MT", "NLD": "NL",
        "POL": "PL", "PRT": "PT", "ROU": "RO", "SVK": "SK", "SVN": "SI", "ESP": "ES", "SWE": "SE", "NOR": "NO", "CHE": "CH", "ISL": "IS"}


def categorise(text: str) -> Optional[str]:
    t = f" {(text or '').lower()} "
    best = max(CATS.items(), key=lambda kv: sum(t.count(w) for w in kv[1]))
    return best[0] if any(w in t for w in best[1]) else None


def _clean(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(str(s or "")))).strip()


def _dedupe_key(title: str, buyer: str, deadline: Optional[str]) -> str:
    norm = re.sub(r"[^a-z0-9]+", "", f"{title}|{buyer}".lower())[:200]
    return hashlib.sha1(f"{norm}|{(deadline or '')[:10]}".encode()).hexdigest()


def _first(v):
    if isinstance(v, dict):
        v = (v.get("eng") or v.get("ENG") or next(iter(v.values()), None))
    if isinstance(v, list):
        v = v[0] if v else None
    return v


async def _fetch_worldbank(src: dict) -> list:
    params = {"format": "json", "rows": 200, "os": 0, "srt": "submission_deadline_date", "order": "desc",
              "fl": "id,project_name,notice_type,submission_deadline_date,project_ctry_name,bid_description,procurement_group,notice_status,contact_organization,noticedate"}
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.get(src["url"], params=params)
        r.raise_for_status()
    out = []
    for n in r.json().get("procnotices") or []:
        if "Invitation" not in (n.get("notice_type") or "") and "Request for Expression" not in (n.get("notice_type") or ""):
            continue
        title = _clean(n.get("bid_description") or n.get("project_name"))
        out.append({"ref": n["id"], "title": title[:300], "buyer": _clean(n.get("contact_organization") or n.get("project_name"))[:200],
                    "country": ISO3.get(n.get("project_ctry_name") or ""), "country_name": n.get("project_ctry_name"),
                    "deadline": n.get("submission_deadline_date"), "notice_type": n.get("notice_type"),
                    "url": f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{n['id']}",
                    "status": "cancelled" if "cancel" in (n.get("notice_status") or "").lower() else "active",
                    "description": _clean(n.get("project_name"))[:500]})
    return out


async def _fetch_ted(src: dict) -> list:
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y%m%d")
    body = {"query": f"notice-type IN (cn-standard cn-social) AND publication-date>={since}", "limit": 250, "page": 1,
            "fields": ["publication-number", "notice-title", "buyer-name", "buyer-country", "deadline-receipt-tender-date-lot",
                       "estimated-value-lot", "estimated-value-cur-lot", "notice-type", "classification-cpv"]}
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post(src["url"], json=body)
        r.raise_for_status()
    out = []
    for n in r.json().get("notices") or []:
        pn = n.get("publication-number")
        val = _first(n.get("estimated-value-lot"))
        try:
            val = float(val) if val else None
        except ValueError:
            val = None
        out.append({"ref": pn, "title": _clean(_first(n.get("notice-title")))[:300], "buyer": _clean(_first(n.get("buyer-name")))[:200],
                    "country": TED3.get(_first(n.get("buyer-country")) or ""), "deadline": _first(n.get("deadline-receipt-tender-date-lot")),
                    "value": val, "currency": _first(n.get("estimated-value-cur-lot")), "notice_type": n.get("notice-type"),
                    "url": f"https://ted.europa.eu/en/notice/-/detail/{pn}", "status": "active"})
    return out


def _dig(obj, path: str):
    for p in [x for x in (path or "").split(".") if x]:
        obj = obj.get(p) if isinstance(obj, dict) else None
    return obj


async def _fetch_provider(src: dict) -> list:
    key = os.environ.get(src.get("api_key_env") or "")
    if not src.get("url") or not key:
        raise RuntimeError("Provider URL or API key not configured yet")
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(src["url"], headers={src.get("auth_header") or "Authorization": f"{src.get('auth_prefix') or ''}{key}"})
        r.raise_for_status()
    rows = _dig(r.json(), src.get("items_path") or "") or []
    m = src.get("mapping") or {}
    return [{k: _dig(row, m.get(k)) for k in ("ref", "title", "buyer", "country", "deadline", "value", "currency", "url", "status", "description")}
            for row in rows if isinstance(row, dict) and _dig(row, m.get("ref"))]


FETCHERS = {"worldbank": _fetch_worldbank, "ted": _fetch_ted, "provider": _fetch_provider}


async def _upsert(src: dict, it: dict) -> str:
    ref = str(it.get("ref"))
    now = now_iso()
    deadline = str(it["deadline"]) if it.get("deadline") else None
    doc = {**it, "ref": ref, "deadline": deadline, "source": src["code"], "source_name": src["name"],
           "country": (it.get("country") or "").upper() or None, "category": categorise(f"{it.get('title')} {it.get('description') or ''}"),
           "dedupe_key": _dedupe_key(it.get("title") or "", it.get("buyer") or "", deadline), "updated_at": now}
    old = await db.external_tenders.find_one({"source": src["code"], "ref": ref})
    if not old:
        dup = await db.external_tenders.find_one({"dedupe_key": doc["dedupe_key"], "duplicate_of": None}, {"source": 1, "ref": 1})
        doc.update({"first_seen_at": now, "history": [], "duplicate_of": f"{dup['source']}:{dup['ref']}" if dup else None})
        await db.external_tenders.insert_one(doc)
        return "new"
    changes = [{"field": f, "from": old.get(f), "to": doc.get(f), "at": now} for f in ("deadline", "status", "title", "value") if old.get(f) != doc.get(f)]
    if not changes:
        return "same"
    if any(c["field"] == "deadline" for c in changes) and doc.get("status") != "cancelled":
        doc["status"] = "amended"
    await db.external_tenders.update_one({"_id": old["_id"]}, {"$set": doc, "$push": {"history": {"$each": changes}}})
    return "updated"


async def run_source(code: str) -> dict:
    src = await db.tender_sources.find_one({"code": code})
    stats = {"new": 0, "updated": 0, "same": 0}
    try:
        items = await FETCHERS[src["kind"]](src)
        for it in items:
            if it.get("ref") and it.get("title"):
                stats[await _upsert(src, it)] += 1
        res = {"ok": True, **stats, "fetched": len(items)}
    except Exception as e:
        log.warning("tender feed %s failed: %s", code, e)
        res = {"ok": False, "error": str(e)[:300]}
    await db.tender_sources.update_one({"code": code}, {"$set": {"last_run_at": now_iso(), "last_result": res}})
    return res


async def run_all() -> dict:
    return {s["code"]: await run_source(s["code"]) async for s in db.tender_sources.find({"enabled": True})}


async def seed_sources() -> None:
    for s in SOURCES:
        await db.tender_sources.update_one({"code": s["code"]}, {"$setOnInsert": {**s, "created_at": now_iso()}}, upsert=True)
    await db.external_tenders.create_index([("source", 1), ("ref", 1)], unique=True)
    await db.external_tenders.create_index("dedupe_key")
    await db.external_tenders.create_index([("first_seen_at", -1)])


# ----------------------------- admin -----------------------------

class SourceIn(BaseModel):
    enabled: bool
    url: Optional[str] = Field(default=None, max_length=500)
    api_key_env: Optional[str] = Field(default=None, max_length=60, pattern=r"^[A-Z0-9_]*$")
    auth_header: Optional[str] = Field(default=None, max_length=60)
    auth_prefix: Optional[str] = Field(default=None, max_length=30)
    items_path: Optional[str] = Field(default=None, max_length=120)
    mapping: Optional[dict[str, str]] = None


@router.get("/tender-feeds/sources")
async def list_sources(admin=Depends(require_role("admin", "reviewer"))):
    out = []
    async for s in db.tender_sources.find({}).sort("code", 1):
        s = BaseDocument.out(s)
        s["key_set"] = bool(os.environ.get(s.get("api_key_env") or "")) if s.get("kind") == "provider" else None
        s["count"] = await db.external_tenders.count_documents({"source": s["code"]})
        out.append(s)
    return {"items": out}


@router.put("/tender-feeds/sources/{code}")
async def update_source(code: str, body: SourceIn, admin=Depends(require_role("admin"))):
    src = await db.tender_sources.find_one({"code": code})
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if src["kind"] != "provider":
        upd = {"enabled": body.enabled}
    await db.tender_sources.update_one({"code": code}, {"$set": upd})
    await audit_log("tender_feeds.source_update", admin, "tender_source", code, upd)
    return {"ok": True}


@router.post("/tender-feeds/sources/{code}/run")
async def run_now(code: str, admin=Depends(require_role("admin"))):
    if not await db.tender_sources.find_one({"code": code}):
        raise HTTPException(status_code=404, detail="Source not found")
    return await run_source(code)


@router.get("/global-tenders")
async def public_global(q: Optional[str] = None, country: Optional[str] = None, category: Optional[str] = None,
                        source: Optional[str] = None, include_closed: bool = False, limit: int = 30, offset: int = 0):
    f = {"duplicate_of": None, "status": {"$ne": "cancelled"}}
    if not include_closed:
        f["$or"] = [{"deadline": None}, {"deadline": {"$gte": now_iso()[:10]}}]
    if country:
        f["country"] = country.upper()
    if category:
        f["category"] = category
    if source:
        f["source"] = source.upper()
    if q:
        f["title"] = {"$regex": re.escape(q[:80]), "$options": "i"}
    limit = max(1, min(limit, 100))
    total = await db.external_tenders.count_documents(f)
    items = [t async for t in db.external_tenders.find(f, {"_id": 0, "dedupe_key": 0}).sort("first_seen_at", -1).skip(offset).limit(limit)]
    return {"total": total, "items": items, "categories": list(CATS), "sources": [{"code": s["code"], "name": s["name"]} for s in SOURCES]}


# ----------------------------- cron -----------------------------

def _bearer(authorization: str) -> None:
    secret = os.environ.get("WEBHOOK_CRON_SECRET")
    if not secret or not secrets.compare_digest(authorization or "", f"Bearer {secret}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/cron/tender-feeds")
async def cron_feeds(authorization: str = Header(default="")):
    _bearer(authorization)
    asyncio.create_task(run_all())
    return {"accepted": True}


@router.post("/cron/saved-alerts")
async def cron_alerts(freq: str = "daily", authorization: str = Header(default="")):
    _bearer(authorization)
    if freq not in ("daily", "weekly"):
        raise HTTPException(status_code=422, detail="freq must be daily or weekly")
    from routers.growth import run_digest_alerts
    asyncio.create_task(run_digest_alerts(freq))
    return {"accepted": True}
