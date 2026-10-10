"""Wave 4 — Vendor Intelligence (rating / blacklist / watchlist / ESG)."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

import config
from db import db
from models.vendor_intel import (
    VendorRatingIn, BlacklistIn, WatchlistIn, ESGDeclarationIn,
    BlacklistEvidenceIn, BlacklistAppealIn,
)
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log
from routers.vendor_auth import current_vendor

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
    v = await db.vendors.find_one({"vendor_ref": vendor_ref},
                                    {"email": 1}) or {}
    await db.vendor_blacklist.delete_one({"vendor_ref": vendor_ref})
    await audit_log("vendor_intel.unblacklist", admin, "vendor", vendor_ref, {})
    # v51bd — fire the decision email to the vendor + staff notification
    await _notify_appeal_decided(vendor_ref, "whitelisted",
                                   v.get("email") or "")
    return {"ok": True}


@router.get("/blacklist")
async def list_blacklist(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    return [_out(b) async for b in db.vendor_blacklist.find({})]


# v51bd — Admin triage dashboard: one row per blacklisted vendor with
# evidence + appeal counts so compliance can prioritise without opening
# each record.
@router.get("/blacklist-dashboard")
async def blacklist_dashboard(admin=Depends(require_role("admin", "reviewer", "auditor"))) -> List[dict]:
    out: List[dict] = []
    vendors_by_ref: dict = {}
    async for v in db.vendors.find({}, {"company_name": 1, "vendor_ref": 1,
                                          "email": 1, "country": 1,
                                          "kyc_status": 1, "is_active": 1}):
        vendors_by_ref[v.get("vendor_ref")] = v
    async for bl in db.vendor_blacklist.find({}).sort("at", -1):
        ref = bl.get("vendor_ref")
        v = vendors_by_ref.get(ref) or {}
        appeals = bl.get("appeals") or []
        pending = [a for a in appeals if (a.get("status") or "pending") == "pending"]
        last = appeals[-1] if appeals else None
        out.append({
            "vendor_ref": ref,
            "company_name": v.get("company_name") or bl.get("company_name"),
            "email": v.get("email"),
            "country": v.get("country"),
            "kyc_status": v.get("kyc_status"),
            "reason": bl.get("reason"),
            "blacklisted_at": bl.get("at"),
            "until": bl.get("until"),
            "evidence_count": len(bl.get("evidence") or []),
            "appeal_count": len(appeals),
            "pending_appeal_count": len(pending),
            "latest_appeal_at": (last or {}).get("at"),
            "latest_appeal_status": (last or {}).get("status"),
            "latest_appeal_evidence_count": len((last or {}).get("evidence") or []),
        })
    return out


async def _notify_appeal_filed(vendor_ref: str, appeal_msg: str, vendor_email: str) -> None:
    """v51bd — email the vendor an acknowledgement + every admin/reviewer."""
    try:
        from notify import notify_role, vendor_confirm
        detail_url = f"{config.FRONTEND_URL}/admin?tab=vintel&ref={vendor_ref}"
        html = (f"<p>Vendor <b>{vendor_ref}</b> has filed a blacklist appeal.</p>"
                 f"<blockquote>{(appeal_msg or '')[:600]}</blockquote>")
        await notify_role("admin", f"Blacklist appeal filed — {vendor_ref}",
                           html + f"<p><a href='{detail_url}'>Review in Vendor Intel</a></p>",
                           related_type="vendor_blacklist", related_id=vendor_ref)
        if vendor_email:
            await vendor_confirm(
                vendor_email,
                "Your blacklist appeal has been received",
                "<p>We've received your appeal and our compliance team will "
                "review it along with any evidence you attached. You'll get "
                "another email once a decision is made.</p>",
                "Open supplier portal", f"{config.FRONTEND_URL}/vendor")
    except Exception as e:
        import logging
        logging.getLogger("vendor_intel").warning("appeal notify failed: %s", e)


async def _notify_appeal_decided(vendor_ref: str, decision: str, vendor_email: str,
                                   note: str = "") -> None:
    """v51bd — email the vendor on whitelist / appeal decision."""
    try:
        from notify import vendor_confirm, notify_role
        if decision == "whitelisted":
            subject = "Your account has been whitelisted"
            body = ("<p>Good news — your account has been removed from the "
                     "PMC blacklist. You can resume submitting bids immediately.</p>")
            if note:
                body += f"<p><b>Decision note:</b> {note}</p>"
        else:
            subject = f"Update on your blacklist appeal · {decision}"
            body = (f"<p>Your blacklist appeal has been <b>{decision}</b>.</p>"
                     + (f"<p>{note}</p>" if note else ""))
        if vendor_email:
            await vendor_confirm(vendor_email, subject, body,
                                   "Open supplier portal",
                                   f"{config.FRONTEND_URL}/vendor")
        await notify_role("admin",
                           f"Blacklist decision — {vendor_ref} · {decision}",
                           f"<p>Admin decision: <b>{decision}</b> for vendor "
                           f"<b>{vendor_ref}</b>.</p>" + (f"<p>{note}</p>" if note else ""),
                           related_type="vendor_blacklist", related_id=vendor_ref)
    except Exception as e:
        import logging
        logging.getLogger("vendor_intel").warning("decision notify failed: %s", e)


# -------- v51bd — Blacklist evidence + vendor-side appeal ---------

async def _bl_or_404(vendor_ref: str) -> dict:
    bl = await db.vendor_blacklist.find_one({"vendor_ref": vendor_ref})
    if not bl:
        raise HTTPException(status_code=404, detail="Vendor is not on the blacklist")
    return _out(bl)


@router.get("/blacklist/{vendor_ref}")
async def get_blacklist(vendor_ref: str,
                         admin=Depends(require_role("admin", "reviewer", "auditor"))) -> dict:
    bl = await _bl_or_404(vendor_ref)
    return _out(bl)

@router.post("/blacklist/{vendor_ref}/evidence")
async def add_evidence(vendor_ref: str, payload: BlacklistEvidenceIn,
                        admin=Depends(require_role("admin", "reviewer"))) -> dict:
    """Admin attaches an evidence file (document OR captured image) to a
    blacklist record. The file itself was already uploaded via
    /uploads/presign + /uploads/direct; here we just link it."""
    bl = await _bl_or_404(vendor_ref)
    entry = payload.model_dump()
    entry.update({"added_by": admin.get("email"), "added_at": now_iso(),
                   "source": "admin"})
    await db.vendor_blacklist.update_one(
        {"vendor_ref": vendor_ref},
        {"$push": {"evidence": entry}})
    await audit_log("vendor_intel.evidence_add", admin, "vendor", vendor_ref,
                    {"filename": payload.filename, "key": payload.key})
    return _out(await db.vendor_blacklist.find_one({"vendor_ref": vendor_ref}))


@router.patch("/blacklist/{vendor_ref}/evidence/{idx}")
async def update_evidence(vendor_ref: str, idx: int,
                           payload: BlacklistEvidenceIn,
                           admin=Depends(require_role("admin"))) -> dict:
    bl = await _bl_or_404(vendor_ref)
    ev = list(bl.get("evidence") or [])
    if idx < 0 or idx >= len(ev):
        raise HTTPException(status_code=404, detail="Evidence not found")
    ev[idx] = {**ev[idx], **payload.model_dump(exclude_none=True),
                "updated_by": admin.get("email"), "updated_at": now_iso()}
    await db.vendor_blacklist.update_one(
        {"vendor_ref": vendor_ref}, {"$set": {"evidence": ev}})
    await audit_log("vendor_intel.evidence_update", admin, "vendor", vendor_ref,
                    {"idx": idx})
    return _out(await db.vendor_blacklist.find_one({"vendor_ref": vendor_ref}))


@router.delete("/blacklist/{vendor_ref}/evidence/{idx}")
async def delete_evidence(vendor_ref: str, idx: int,
                           admin=Depends(require_role("admin"))) -> dict:
    bl = await _bl_or_404(vendor_ref)
    ev = list(bl.get("evidence") or [])
    if idx < 0 or idx >= len(ev):
        raise HTTPException(status_code=404, detail="Evidence not found")
    removed = ev.pop(idx)
    await db.vendor_blacklist.update_one(
        {"vendor_ref": vendor_ref}, {"$set": {"evidence": ev}})
    await audit_log("vendor_intel.evidence_delete", admin, "vendor", vendor_ref,
                    {"filename": removed.get("filename"), "key": removed.get("key")})
    return _out(await db.vendor_blacklist.find_one({"vendor_ref": vendor_ref}))


# ---- Vendor-side appeal: a blacklisted vendor can see & evidence an appeal ----

@router.get("/my-blacklist")
async def my_blacklist(vendor=Depends(current_vendor)) -> dict:
    """Returns the vendor's own blacklist record (if any). Vendors do not
    see the raw admin evidence list — only their own appeal messages +
    appeal evidence. Admins keep full visibility via /blacklist/{ref}."""
    bl = await db.vendor_blacklist.find_one({"vendor_ref": vendor.get("vendor_ref")})
    if not bl:
        return {"blacklisted": False}
    appeals = bl.get("appeals") or []
    return {
        "blacklisted": True,
        "vendor_ref": bl.get("vendor_ref"),
        "reason": bl.get("reason"),
        "at": bl.get("at"),
        "until": bl.get("until"),
        "appeals": appeals,
    }


@router.post("/my-blacklist/appeal")
async def submit_appeal(payload: BlacklistAppealIn,
                         vendor=Depends(current_vendor)) -> dict:
    bl = await db.vendor_blacklist.find_one({"vendor_ref": vendor.get("vendor_ref")})
    if not bl:
        raise HTTPException(status_code=400, detail="You are not on the blacklist")
    appeal = {"message": payload.message, "at": now_iso(),
               "by": vendor.get("email"), "status": "pending",
               "evidence": []}
    await db.vendor_blacklist.update_one(
        {"vendor_ref": vendor.get("vendor_ref")},
        {"$push": {"appeals": appeal}})
    await audit_log("vendor_intel.appeal_submit", vendor, "vendor",
                    vendor.get("vendor_ref"), {"len": len(payload.message)})
    # v51bd — notify vendor + every admin so compliance sees it immediately
    await _notify_appeal_filed(vendor.get("vendor_ref"), payload.message,
                                 vendor.get("email") or "")
    return {"ok": True}


@router.post("/my-blacklist/appeal/evidence")
async def add_appeal_evidence(payload: BlacklistEvidenceIn,
                               vendor=Depends(current_vendor)) -> dict:
    """Vendor attaches a document OR a camera-captured photo to their most
    recent appeal (or creates an empty appeal shell if none exist)."""
    bl = await db.vendor_blacklist.find_one({"vendor_ref": vendor.get("vendor_ref")})
    if not bl:
        raise HTTPException(status_code=400, detail="You are not on the blacklist")
    appeals = list(bl.get("appeals") or [])
    if not appeals:
        appeals.append({"message": "", "at": now_iso(),
                         "by": vendor.get("email"), "status": "pending",
                         "evidence": []})
    entry = payload.model_dump()
    entry.update({"added_by": vendor.get("email"), "added_at": now_iso(),
                   "source": "vendor"})
    appeals[-1].setdefault("evidence", []).append(entry)
    await db.vendor_blacklist.update_one(
        {"vendor_ref": vendor.get("vendor_ref")},
        {"$set": {"appeals": appeals}})
    await audit_log("vendor_intel.appeal_evidence", vendor, "vendor",
                    vendor.get("vendor_ref"),
                    {"filename": payload.filename, "key": payload.key})
    return {"ok": True, "count": len(appeals[-1]["evidence"])}


@router.delete("/my-blacklist/appeal/evidence/{idx}")
async def delete_appeal_evidence(idx: int,
                                   vendor=Depends(current_vendor)) -> dict:
    bl = await db.vendor_blacklist.find_one({"vendor_ref": vendor.get("vendor_ref")})
    if not bl or not (bl.get("appeals") or []):
        raise HTTPException(status_code=404, detail="No appeal evidence found")
    appeals = list(bl["appeals"])
    ev = list(appeals[-1].get("evidence") or [])
    if idx < 0 or idx >= len(ev):
        raise HTTPException(status_code=404, detail="Evidence not found")
    ev.pop(idx)
    appeals[-1]["evidence"] = ev
    await db.vendor_blacklist.update_one(
        {"vendor_ref": vendor.get("vendor_ref")},
        {"$set": {"appeals": appeals}})
    return {"ok": True}


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
