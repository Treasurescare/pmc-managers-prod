"""Wave 4 — Vendor Intelligence (rating / blacklist / watchlist / ESG)."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.vendor_intel import VendorRatingIn, BlacklistIn, WatchlistIn, ESGDeclarationIn
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/vendor-intel", tags=["vendor-intelligence"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


@router.post("/ratings")
async def upsert_rating(payload: VendorRatingIn, admin=Depends(require_role("admin", "reviewer"))):
    doc = payload.model_dump()
    doc.update({"rated_by": admin["id"], "rated_by_email": admin["email"], "at": now_iso()})
    await db.vendor_ratings.update_one(
        {"vendor_ref": payload.vendor_ref}, {"$set": doc}, upsert=True,
    )
    await audit_log("vendor_intel.rating", admin, "vendor", payload.vendor_ref,
                    {"score": payload.score, "band": payload.band})
    return {"ok": True}


@router.get("/ratings")
async def list_ratings(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    return [_out(r) async for r in db.vendor_ratings.find({}).sort("score", -1)]


@router.post("/blacklist")
async def blacklist(payload: BlacklistIn, admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc.update({"blacklisted_by": admin["id"], "at": now_iso()})
    await db.vendor_blacklist.update_one(
        {"vendor_ref": payload.vendor_ref}, {"$set": doc}, upsert=True,
    )
    await audit_log("vendor_intel.blacklist", admin, "vendor", payload.vendor_ref,
                    {"reason": payload.reason})
    return {"ok": True}


@router.delete("/blacklist/{vendor_ref}")
async def unblacklist(vendor_ref: str, admin=Depends(require_role("admin"))):
    await db.vendor_blacklist.delete_one({"vendor_ref": vendor_ref})
    await audit_log("vendor_intel.unblacklist", admin, "vendor", vendor_ref, {})
    return {"ok": True}


@router.get("/blacklist")
async def list_blacklist(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    return [_out(b) async for b in db.vendor_blacklist.find({})]


@router.post("/watchlist")
async def watchlist(payload: WatchlistIn, admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc.update({"at": now_iso(), "by": admin["email"]})
    await db.vendor_watchlist.update_one(
        {"vendor_ref": payload.vendor_ref}, {"$set": doc}, upsert=True,
    )
    return {"ok": True}


@router.get("/watchlist")
async def list_watchlist(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    return [_out(w) async for w in db.vendor_watchlist.find({})]


@router.post("/esg")
async def upsert_esg(payload: ESGDeclarationIn, admin=Depends(require_role("admin", "reviewer"))):
    doc = payload.model_dump()
    doc.update({"at": now_iso(), "by": admin["email"]})
    await db.vendor_esg.update_one(
        {"vendor_ref": payload.vendor_ref}, {"$set": doc}, upsert=True,
    )
    return {"ok": True}


@router.get("/summary")
async def vendor_intel_summary(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """Combined view for the admin console."""
    ratings = {r["vendor_ref"]: _out(r) async for r in db.vendor_ratings.find({})}
    blacklist = {b["vendor_ref"]: _out(b) async for b in db.vendor_blacklist.find({})}
    watchlist = {w["vendor_ref"]: _out(w) async for w in db.vendor_watchlist.find({})}
    esg = {e["vendor_ref"]: _out(e) async for e in db.vendor_esg.find({})}
    vendors = [_out(v) async for v in db.vendors.find({}, {"password_hash": 0}).limit(500)]
    out = []
    for v in vendors:
        ref = v.get("vendor_ref")
        out.append({
            **v,
            "rating": ratings.get(ref, {}).get("score"),
            "band": ratings.get(ref, {}).get("band"),
            "blacklisted": ref in blacklist,
            "watchlisted": ref in watchlist,
            "esg": esg.get(ref, {}),
        })
    return out
