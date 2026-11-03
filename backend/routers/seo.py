import re
from html import escape as h
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from audit import audit_log
from config import FRONTEND_URL
from db import db
from models.base import now_iso
from security import require_csrf, require_role

router = APIRouter(tags=["seo"])

STATIC_ROUTES = [("/", "daily", "1.0"), ("/tenders/live", "hourly", "0.9"), ("/tenders/completed", "daily", "0.6"),
                 ("/buyers", "weekly", "0.8"), ("/suppliers", "weekly", "0.8"), ("/pricing", "weekly", "0.7"),
                 ("/trust", "monthly", "0.6"), ("/about", "monthly", "0.6"), ("/vision", "monthly", "0.5"),
                 ("/contact", "monthly", "0.5"), ("/help", "monthly", "0.4"), ("/register", "monthly", "0.6")]
TEST_TITLE = re.compile(r"\btest|demo\b|sample\b|dummy", re.I)
_URL = re.compile(r"^(https://[^\s<>\"']+|/[^\s<>\"']*)?$")

DEFAULT_PROGRAMME = {
    "enabled": True,
    "eyebrow": "Programme spotlight",
    "title": "Kazakhstan Integrated Development Programme",
    "summary": "Modular medical, education, hostel and utilities packages, published for global supply. Suppliers from any country can register, qualify and bid.",
    "stat_label": "work packages in the featured programme",
    "tenders_link": "/tenders/live",
    "brief_url": "",
    "highlights": [
        {"title": "Modular medical", "text": "Hospitals, OPD blocks, IVF and cleanroom labs, medical equipment and consumables."},
        {"title": "Education", "text": "University academic packages, digital learning and campus fit-out."},
        {"title": "Hostels & residential", "text": "Student and staff hostels, modular residential blocks."},
        {"title": "Utilities & infrastructure", "text": "Power, water, networks and site infrastructure."},
    ],
}


class Highlight(BaseModel):
    title: str
    text: str = ""


class ProgrammeIn(BaseModel):
    enabled: bool = True
    eyebrow: str = "Programme spotlight"
    title: str
    summary: str = ""
    stat_label: str = ""
    tenders_link: Optional[str] = ""
    brief_url: Optional[str] = ""
    highlights: List[Highlight] = []


async def _programme() -> dict:
    doc = await db.site_settings.find_one({"_id": "featured_programme"}) or {}
    return {k: doc.get(k, v) for k, v in DEFAULT_PROGRAMME.items()}


@router.get("/api/v1/site/featured-programme")
async def public_programme():
    return await _programme()


@router.put("/api/v1/marketing/featured-programme", dependencies=[Depends(require_csrf)])
async def save_programme(body: ProgrammeIn, admin=Depends(require_role("admin"))):
    data = body.model_dump()
    data["title"] = data["title"].strip()
    if not data["title"]:
        raise HTTPException(status_code=422, detail="Programme name is required")
    for k in ("tenders_link", "brief_url"):
        data[k] = (data[k] or "").strip()
        if not _URL.match(data[k]):
            raise HTTPException(status_code=422, detail=f"{k.replace('_', ' ').title()} must start with https:// or /")
    data["highlights"] = [x for x in data["highlights"] if x["title"].strip()][:8]
    await db.site_settings.update_one({"_id": "featured_programme"}, {"$set": {**data, "updated_at": now_iso()}}, upsert=True)
    await audit_log("site.featured_programme_updated", admin, "site_settings", "featured_programme", {"title": data["title"]})
    return await _programme()


def _base() -> str:
    return FRONTEND_URL.rstrip("/")


@router.get("/api/v1/seo/sitemap.xml")
async def sitemap():
    base = _base()
    rows = [f"<url><loc>{base}{p}</loc><changefreq>{f}</changefreq><priority>{pr}</priority></url>"
            for p, f, pr in STATIC_ROUTES]
    cur = db.notices.find({"is_published": True}, {"notice_ref": 1, "title": 1, "updated_at": 1, "published_at": 1})
    async for n in cur:
        if not n.get("notice_ref") or TEST_TITLE.search(n.get("title") or ""):
            continue
        mod = str(n.get("updated_at") or n.get("published_at") or "")[:10]
        lm = f"<lastmod>{h(mod)}</lastmod>" if mod else ""
        rows.append(f"<url><loc>{base}/notices/{h(n['notice_ref'])}</loc>{lm}<changefreq>daily</changefreq><priority>0.8</priority></url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(rows) + "</urlset>"
    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/api/v1/seo/robots.txt")
async def robots():
    txt = (f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /staff\nDisallow: /vendor\nDisallow: /api/\n"
           f"Allow: /api/v1/seo/sitemap.xml\n\nSitemap: {_base()}/api/v1/seo/sitemap.xml\n")
    return Response(content=txt, media_type="text/plain")
