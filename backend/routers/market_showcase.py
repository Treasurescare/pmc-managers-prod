"""v61e — Home-page marketplace showcase + advert slot, and the supplier-category review queue."""
import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import now_iso
from routers.marketplace import _public, _top, pmc_staff
from routers.marketplace_media import IMG, MAX_PHOTO, _card, _ext, _store

router = APIRouter(prefix="/api/v1", tags=["market-showcase"])


def _oid(x: str) -> ObjectId:
    try:
        return ObjectId(x)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")


def _ad_out(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


@router.get("/market/showcase")
async def showcase():
    now = now_iso()
    products = []
    async for d in db.mkt_listings.find({"status": "live", "photos.0": {"$exists": True}}).sort("updated_at", -1).limit(24):
        if d.get("closes_at") and d["closes_at"] <= now and "fixed" not in d["sale_modes"]:
            continue
        products.append(_public(d, *(await _top(d["_id"]))))
        if len(products) >= 4:
            break
    ads = []
    async for a in db.home_adverts.find({"is_active": True, "deleted": {"$ne": True}}).sort([("sort", 1), ("created_at", -1)]):
        if (a.get("starts_at") or "") <= now and (not a.get("ends_at") or a["ends_at"] > now):
            ads.append({k: a.get(k) for k in ("title", "subtitle", "image_id", "link_url", "cta_label")} | {"id": str(a["_id"])})
    return {"products": products, "adverts": ads[:6]}


# ---------- adverts (admin) ----------
class AdvertIn(BaseModel):
    title: str = Field(min_length=2, max_length=90)
    subtitle: str = Field(default="", max_length=200)
    image_id: str = Field(default="", max_length=40)
    link_url: str = Field(default="", max_length=500)
    cta_label: str = Field(default="Learn more", max_length=30)
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    sort: int = 0
    is_active: bool = True


def _iso(v: Optional[str], label: str) -> Optional[str]:
    if not v:
        return None
    from datetime import datetime, timezone
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{label} is not a valid date")
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat()


async def _check_ad(b: AdvertIn) -> dict:
    if b.link_url and not re.match(r"^(https://|/)", b.link_url):
        raise HTTPException(status_code=400, detail="The link must start with https:// or / (a page on this site)")
    d = b.model_dump()
    d["starts_at"], d["ends_at"] = _iso(b.starts_at, "Show from"), _iso(b.ends_at, "Show until")
    if d["starts_at"] and d["ends_at"] and d["ends_at"] <= d["starts_at"]:
        raise HTTPException(status_code=400, detail="'Show until' must be after 'Show from'")
    if b.image_id and not await db.mkt_media.find_one({"_id": b.image_id, "owner": "admin"}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="Please upload the advert image again")
    return d


def _ad_state(a: dict) -> str:
    now = now_iso()
    if not a.get("is_active"):
        return "off"
    if a.get("starts_at") and a["starts_at"] > now:
        return "scheduled"
    if a.get("ends_at") and a["ends_at"] <= now:
        return "expired"
    return "showing"


@router.get("/admin/home-adverts")
async def list_ads(admin=Depends(pmc_staff)):
    from routers.market_alerts import ad_totals
    items = [{**_ad_out(a), "state": _ad_state(a)} async for a in db.home_adverts.find({"deleted": {"$ne": True}}).sort([("sort", 1), ("created_at", -1)])]
    tot = await ad_totals([a["id"] for a in items])
    return {"items": [{**a, **tot.get(a["id"], {"views": 0, "clicks": 0})} for a in items]}


@router.post("/admin/home-adverts/image")
async def ad_image(file: UploadFile = File(...), admin=Depends(pmc_staff)):
    body = await file.read()
    if _ext(file.filename) not in IMG or len(body) > MAX_PHOTO:
        raise HTTPException(status_code=400, detail="Advert images must be JPG, PNG or WEBP, up to 8 MB")
    try:
        body = _card(body)
    except Exception:
        raise HTTPException(status_code=400, detail="This image could not be opened — please try another file")
    return await _store("admin", "photo", file.filename, "image/jpeg", body)


@router.post("/admin/home-adverts")
async def create_ad(b: AdvertIn, admin=Depends(pmc_staff)):
    doc = {**(await _check_ad(b)), "created_at": now_iso(), "created_by": admin["email"]}
    r = await db.home_adverts.insert_one(doc)
    await audit_log("home.advert.create", admin, "home_advert", str(r.inserted_id), {"title": b.title})
    return {"id": str(r.inserted_id)}


@router.put("/admin/home-adverts/{aid}")
async def update_ad(aid: str, b: AdvertIn, admin=Depends(pmc_staff)):
    r = await db.home_adverts.update_one({"_id": _oid(aid), "deleted": {"$ne": True}}, {"$set": {**(await _check_ad(b)), "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Advert not found")
    await audit_log("home.advert.update", admin, "home_advert", aid, {"title": b.title, "is_active": b.is_active})
    return {"ok": True}


@router.delete("/admin/home-adverts/{aid}")
async def remove_ad(aid: str, admin=Depends(pmc_staff)):
    r = await db.home_adverts.update_one({"_id": _oid(aid), "deleted": {"$ne": True}}, {"$set": {"deleted": True, "is_active": False, "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Advert not found")
    await audit_log("home.advert.remove", admin, "home_advert", aid, {})
    return {"ok": True}


# ---------- supplier-added category review ----------
@router.get("/admin/category-review")
async def review_queue(admin=Depends(pmc_staff)):
    out = []
    async for c in db.categories.find({"source": "supplier", "needs_review": True}).sort("created_at", -1):
        v = await db.vendors.find_one({"_id": ObjectId(c["created_by_vendor"])}, {"company_name": 1}) if ObjectId.is_valid(c.get("created_by_vendor") or "") else None
        out.append({"id": str(c["_id"]), "name": c["name"], "created_at": c.get("created_at"),
                    "added_by": (v or {}).get("company_name") or "Supplier",
                    "listings": await db.mkt_listings.count_documents({"category": c["name"]})})
    return {"items": out}


class ReviewIn(BaseModel):
    action: str = Field(pattern="^(approve|rename|merge)$")
    name: str = Field(default="", max_length=120)
    target_id: str = Field(default="", max_length=40)


@router.post("/admin/category-review/{cid}")
async def review(cid: str, b: ReviewIn, admin=Depends(pmc_staff)):
    c = await db.categories.find_one({"_id": _oid(cid), "source": "supplier"})
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    moved = 0
    if b.action == "approve":
        upd = {"needs_review": False}
    elif b.action == "rename":
        name = re.sub(r"\s+", " ", b.name).strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Enter the new name")
        clash = await db.categories.find_one({"_id": {"$ne": c["_id"]}, "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
        if clash:
            raise HTTPException(status_code=409, detail=f"\"{clash['name']}\" already exists — use Merge instead")
        moved = (await db.mkt_listings.update_many({"category": c["name"]}, {"$set": {"category": name}})).modified_count
        upd = {"name": name, "needs_review": False, "renamed_from": c["name"]}
    else:
        t = await db.categories.find_one({"_id": _oid(b.target_id), "is_active": True})
        if not t or t["_id"] == c["_id"]:
            raise HTTPException(status_code=400, detail="Choose an existing category to merge into")
        moved = (await db.mkt_listings.update_many({"category": c["name"]}, {"$set": {"category": t["name"]}})).modified_count
        upd = {"needs_review": False, "is_active": False, "merged_into": str(t["_id"])}
    await db.categories.update_one({"_id": c["_id"]}, {"$set": {**upd, "reviewed_by": admin["email"], "reviewed_at": now_iso()}})
    await audit_log(f"category.review.{b.action}", admin, "category", cid, {"name": c["name"], **upd, "listings_moved": moved})
    return {"ok": True, "listings_moved": moved}
