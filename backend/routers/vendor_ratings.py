"""v46 · Vendor Ratings & Reviews portal.

Peer vendors, PMC management and public buyers can all rate a vendor.
Reviewer identity is stored for audit/moderation but is NEVER exposed publicly —
public payloads only carry an anonymised reviewer_kind label plus the score,
approved comment and creation date. Trust badges are computed from approved
reviews only (Platinum / Gold / Silver / Bronze).

Design notes
------------
* Rubric reuse — a rating always references a `rating_criteria_sets` row from
  tender_pro.py so admins keep a single source of truth for criteria/weights.
* Anti-self-rating — peer vendors cannot rate themselves.
* One review per (vendor_ref, criteria_set_id, reviewer_key) — subsequent
  submissions upsert the previous one so users can revise their score.
* Moderation — PMC admin reviews go straight to approved; peer vendors approved
  if the vendor is verified; public buyer reviews start as pending and require
  admin approval before they count towards the aggregate.
"""
from typing import List, Optional, Literal
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/vendor-ratings", tags=["vendor-ratings"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _badge_tier(count: int, avg: float) -> str:
    if count >= 10 and avg >= 85:
        return "platinum"
    if count >= 5 and avg >= 70:
        return "gold"
    if count >= 3 and avg >= 55:
        return "silver"
    if count >= 1:
        return "bronze"
    return "none"


def _compute_score(criteria_set: dict, scores: dict) -> float:
    """Normalise per-criterion scores into a weighted 0-100 aggregate."""
    scale_by_code = {c["code"]: (c["scale_min"], c["scale_max"], float(c.get("weight") or 1))
                     for c in (criteria_set.get("criteria") or [])}
    weighted_total = 0.0
    weight_sum = 0.0
    for code, val in (scores or {}).items():
        if code not in scale_by_code:
            continue
        lo, hi, w = scale_by_code[code]
        v = max(lo, min(hi, float(val)))
        span = max(1, hi - lo)
        weighted_total += ((v - lo) / span) * w
        weight_sum += w
    return round((weighted_total / weight_sum) * 100, 2) if weight_sum else 0.0


async def _aggregate_for(vendor_ref: str) -> dict:
    """Compute the public aggregate over APPROVED reviews only."""
    cursor = db.vendor_reviews.find({"vendor_ref": vendor_ref, "status": "approved"})
    rows = [r async for r in cursor]
    if not rows:
        return {
            "vendor_ref": vendor_ref, "count": 0,
            "average_score": None, "badge": "none",
            "by_reviewer_kind": {"pmc_admin": 0, "peer_vendor": 0, "public_buyer": 0},
            "criteria_averages": {}, "recent_comments": [],
        }
    avg = round(sum(r.get("score_out_of_100") or 0 for r in rows) / len(rows), 2)
    kinds = {"pmc_admin": 0, "peer_vendor": 0, "public_buyer": 0}
    for r in rows:
        k = r.get("reviewer_kind") or "public_buyer"
        kinds[k] = kinds.get(k, 0) + 1
    # criteria averages (0-100 per code)
    crit_sum: dict = {}
    crit_ct: dict = {}
    for r in rows:
        for code, val in (r.get("normalised_scores") or {}).items():
            crit_sum[code] = crit_sum.get(code, 0.0) + float(val)
            crit_ct[code] = crit_ct.get(code, 0) + 1
    crit_avg = {c: round(crit_sum[c] / crit_ct[c], 2) for c in crit_sum}
    # 5 most recent approved comments, anonymised
    recent = sorted(
        [r for r in rows if (r.get("comment") or "").strip()],
        key=lambda r: r.get("created_at") or "",
        reverse=True,
    )[:5]
    recent_comments = [{
        "reviewer_kind": r.get("reviewer_kind"),
        "score": r.get("score_out_of_100"),
        "comment": r.get("comment"),
        "created_at": r.get("created_at"),
    } for r in recent]
    return {
        "vendor_ref": vendor_ref, "count": len(rows),
        "average_score": avg, "badge": _badge_tier(len(rows), avg),
        "by_reviewer_kind": kinds,
        "criteria_averages": crit_avg,
        "recent_comments": recent_comments,
    }


def _normalise_scores(criteria_set: dict, scores: dict) -> dict:
    """Return each score projected to 0-100 for cross-criterion averaging."""
    out = {}
    for c in criteria_set.get("criteria") or []:
        code = c["code"]
        if code not in (scores or {}):
            continue
        lo, hi = c.get("scale_min", 1), c.get("scale_max", 5)
        try:
            v = max(lo, min(hi, float(scores[code])))
        except (TypeError, ValueError):
            continue
        span = max(1, hi - lo)
        out[code] = round(((v - lo) / span) * 100, 2)
    return out


async def _load_default_criteria() -> Optional[dict]:
    """Locate the default criteria set (falls back to first active)."""
    d = await db.rating_criteria_sets.find_one({"is_default": True, "is_active": True})
    if d:
        return d
    return await db.rating_criteria_sets.find_one({"is_active": True})


# ---------------------------------------------------------------------------
# Public endpoints — no auth, safe payloads only
# ---------------------------------------------------------------------------

@router.get("/public/top")
async def public_top_rated(limit: int = 12):
    """Landing-page listing of best-rated vendors."""
    limit = max(1, min(50, int(limit)))
    # aggregation: only vendors with >=1 approved review
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$vendor_ref",
                    "count": {"$sum": 1},
                    "average_score": {"$avg": "$score_out_of_100"}}},
        {"$sort": {"average_score": -1, "count": -1}},
        {"$limit": limit},
    ]
    rows = [r async for r in db.vendor_reviews.aggregate(pipeline)]
    if not rows:
        return {"items": []}
    refs = [r["_id"] for r in rows]
    vendors = {}
    async for v in db.vendors.find({"vendor_ref": {"$in": refs}}):
        vendors[v["vendor_ref"]] = v
    out = []
    for r in rows:
        v = vendors.get(r["_id"])
        if not v:
            continue
        avg = round(r["average_score"], 2)
        out.append({
            "vendor_ref": r["_id"],
            "company_name": v.get("company_name") or v.get("email"),
            "country": v.get("country"),
            "count": r["count"],
            "average_score": avg,
            "badge": _badge_tier(r["count"], avg),
        })
    return {"items": out}


@router.get("/public/{vendor_ref}")
async def public_aggregate(vendor_ref: str):
    """Anonymised aggregate + trust badge for a single vendor."""
    v = await db.vendors.find_one({"vendor_ref": vendor_ref})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    agg = await _aggregate_for(vendor_ref)
    agg["company_name"] = v.get("company_name") or v.get("email")
    agg["country"] = v.get("country")
    agg["categories"] = v.get("categories") or []
    return agg


class PublicReviewIn(BaseModel):
    vendor_ref: str
    criteria_set_id: Optional[str] = None
    reviewer_name: str = Field(min_length=2, max_length=120)
    reviewer_email: EmailStr
    reviewer_company: Optional[str] = None
    scores: dict = Field(default_factory=dict)  # {code: int}
    comment: Optional[str] = Field(default=None, max_length=2000)
    tender_ref: Optional[str] = None


@router.post("/public/submit")
async def public_submit(payload: PublicReviewIn, request: Request):
    """Public buyer submits a review. Goes to pending until admin approves.

    Simple abuse guard: max 3 pending submissions per email/day.
    """
    v = await db.vendors.find_one({"vendor_ref": payload.vendor_ref})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if payload.criteria_set_id:
        try:
            cset = await db.rating_criteria_sets.find_one({"_id": ObjectId(payload.criteria_set_id)})
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid criteria_set_id")
    else:
        cset = await _load_default_criteria()
    if not cset:
        raise HTTPException(status_code=400, detail="No rating criteria configured — ask the platform admin to publish a rubric first")

    # Rate limiting: 3 pending per email/day.
    today = now_iso()[:10]
    pending_today = await db.vendor_reviews.count_documents({
        "reviewer_email": payload.reviewer_email.lower(),
        "created_at": {"$regex": f"^{today}"},
        "status": "pending",
    })
    if pending_today >= 3:
        raise HTTPException(status_code=429, detail="Too many pending reviews from this email today")

    score_100 = _compute_score(cset, payload.scores)
    norm = _normalise_scores(cset, payload.scores)
    now = now_iso()
    doc = {
        "vendor_ref": payload.vendor_ref,
        "criteria_set_id": str(cset["_id"]),
        "reviewer_kind": "public_buyer",
        "reviewer_email": payload.reviewer_email.lower(),
        "reviewer_name": payload.reviewer_name.strip(),
        "reviewer_company": (payload.reviewer_company or "").strip() or None,
        "reviewer_ip": (request.client.host if request and request.client else None),
        "scores": payload.scores,
        "normalised_scores": norm,
        "score_out_of_100": score_100,
        "comment": (payload.comment or "").strip() or None,
        "tender_ref": payload.tender_ref,
        "status": "pending",
        "created_at": now, "updated_at": now,
    }
    # Upsert per (vendor_ref, criteria_set_id, reviewer_email)
    filt = {
        "vendor_ref": doc["vendor_ref"],
        "criteria_set_id": doc["criteria_set_id"],
        "reviewer_email": doc["reviewer_email"],
        "reviewer_kind": "public_buyer",
    }
    existing = await db.vendor_reviews.find_one(filt)
    if existing:
        await db.vendor_reviews.update_one({"_id": existing["_id"]},
                                            {"$set": {**doc, "created_at": existing.get("created_at") or now}})
        rid = existing["_id"]
    else:
        r = await db.vendor_reviews.insert_one(doc)
        rid = r.inserted_id
    return {"ok": True, "review_id": str(rid), "status": "pending",
            "message": "Thanks — your review is pending PMC moderation before it appears publicly."}


# ---------------------------------------------------------------------------
# Peer-vendor endpoints — authenticated vendor
# ---------------------------------------------------------------------------

class PeerReviewIn(BaseModel):
    vendor_ref: str
    criteria_set_id: Optional[str] = None
    scores: dict = Field(default_factory=dict)
    comment: Optional[str] = Field(default=None, max_length=2000)
    tender_ref: Optional[str] = None


@router.post("/peer/submit")
async def peer_submit(payload: PeerReviewIn, vendor=Depends(current_vendor)):
    """Verified vendor rates another vendor. Auto-approved once the vendor is
    active/verified — otherwise held for moderation."""
    if payload.vendor_ref == vendor.get("vendor_ref"):
        raise HTTPException(status_code=400, detail="You cannot rate your own company")
    target = await db.vendors.find_one({"vendor_ref": payload.vendor_ref})
    if not target:
        raise HTTPException(status_code=404, detail="Target vendor not found")

    if payload.criteria_set_id:
        try:
            cset = await db.rating_criteria_sets.find_one({"_id": ObjectId(payload.criteria_set_id)})
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid criteria_set_id")
    else:
        cset = await _load_default_criteria()
    if not cset:
        raise HTTPException(status_code=400, detail="No rating criteria configured — ask the platform admin to publish a rubric first")

    verified = bool(vendor.get("is_active")) and not vendor.get("blacklisted")
    status = "approved" if verified else "pending"

    score_100 = _compute_score(cset, payload.scores)
    norm = _normalise_scores(cset, payload.scores)
    now = now_iso()
    doc = {
        "vendor_ref": payload.vendor_ref,
        "criteria_set_id": str(cset["_id"]),
        "reviewer_kind": "peer_vendor",
        "reviewer_email": (vendor.get("email") or "").lower(),
        "reviewer_name": vendor.get("company_name") or vendor.get("email"),
        "reviewer_vendor_ref": vendor.get("vendor_ref"),
        "scores": payload.scores,
        "normalised_scores": norm,
        "score_out_of_100": score_100,
        "comment": (payload.comment or "").strip() or None,
        "tender_ref": payload.tender_ref,
        "status": status,
        "created_at": now, "updated_at": now,
    }
    filt = {
        "vendor_ref": doc["vendor_ref"],
        "criteria_set_id": doc["criteria_set_id"],
        "reviewer_vendor_ref": doc["reviewer_vendor_ref"],
        "reviewer_kind": "peer_vendor",
    }
    existing = await db.vendor_reviews.find_one(filt)
    if existing:
        await db.vendor_reviews.update_one({"_id": existing["_id"]},
                                            {"$set": {**doc, "created_at": existing.get("created_at") or now}})
        rid = existing["_id"]
    else:
        r = await db.vendor_reviews.insert_one(doc)
        rid = r.inserted_id
    return {"ok": True, "review_id": str(rid), "status": status}


@router.get("/peer/mine")
async def peer_list_mine(vendor=Depends(current_vendor)):
    """Reviews the calling vendor has authored (for their own history)."""
    cursor = db.vendor_reviews.find({"reviewer_vendor_ref": vendor.get("vendor_ref")}).sort("created_at", -1)
    return [_out(r) async for r in cursor]


# ---------------------------------------------------------------------------
# PMC admin endpoints — moderation + management scoring
# ---------------------------------------------------------------------------

class AdminReviewIn(BaseModel):
    vendor_ref: str
    criteria_set_id: Optional[str] = None
    scores: dict = Field(default_factory=dict)
    comment: Optional[str] = Field(default=None, max_length=2000)


@router.post("/admin/submit")
async def admin_submit(payload: AdminReviewIn, admin=Depends(require_role("admin", "reviewer"))):
    target = await db.vendors.find_one({"vendor_ref": payload.vendor_ref})
    if not target:
        raise HTTPException(status_code=404, detail="Target vendor not found")

    if payload.criteria_set_id:
        try:
            cset = await db.rating_criteria_sets.find_one({"_id": ObjectId(payload.criteria_set_id)})
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid criteria_set_id")
    else:
        cset = await _load_default_criteria()
    if not cset:
        raise HTTPException(status_code=400, detail="No rating criteria configured — publish a rubric under Masters → Rating & Fees first")

    score_100 = _compute_score(cset, payload.scores)
    norm = _normalise_scores(cset, payload.scores)
    now = now_iso()
    doc = {
        "vendor_ref": payload.vendor_ref,
        "criteria_set_id": str(cset["_id"]),
        "reviewer_kind": "pmc_admin",
        "reviewer_email": (admin.get("email") or "").lower(),
        "reviewer_name": admin.get("email"),
        "reviewer_admin_id": admin.get("id"),
        "scores": payload.scores,
        "normalised_scores": norm,
        "score_out_of_100": score_100,
        "comment": (payload.comment or "").strip() or None,
        "status": "approved",
        "created_at": now, "updated_at": now,
    }
    filt = {
        "vendor_ref": doc["vendor_ref"],
        "criteria_set_id": doc["criteria_set_id"],
        "reviewer_admin_id": doc["reviewer_admin_id"],
        "reviewer_kind": "pmc_admin",
    }
    existing = await db.vendor_reviews.find_one(filt)
    if existing:
        await db.vendor_reviews.update_one({"_id": existing["_id"]},
                                            {"$set": {**doc, "created_at": existing.get("created_at") or now}})
        rid = existing["_id"]
    else:
        r = await db.vendor_reviews.insert_one(doc)
        rid = r.inserted_id
    await audit_log("vendor_rating.admin_submit", admin, "vendor",
                    payload.vendor_ref, {"score": score_100})
    return {"ok": True, "review_id": str(rid), "status": "approved"}


@router.get("/admin/reviews")
async def admin_list_reviews(
    vendor_ref: Optional[str] = None,
    status: Optional[Literal["pending", "approved", "hidden"]] = None,
    limit: int = 200,
    admin=Depends(require_role("admin", "reviewer")),
):
    q: dict = {}
    if vendor_ref:
        q["vendor_ref"] = vendor_ref
    if status:
        q["status"] = status
    limit = max(1, min(500, int(limit)))
    cursor = db.vendor_reviews.find(q).sort("created_at", -1).limit(limit)
    return [_out(r) async for r in cursor]


class ModerationIn(BaseModel):
    action: Literal["approve", "hide"]
    reason: Optional[str] = None


@router.post("/admin/reviews/{review_id}/moderate")
async def admin_moderate(review_id: str, payload: ModerationIn,
                          admin=Depends(require_role("admin", "reviewer"))):
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid review id")
    existing = await db.vendor_reviews.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    new_status = "approved" if payload.action == "approve" else "hidden"
    await db.vendor_reviews.update_one({"_id": oid}, {"$set": {
        "status": new_status,
        "moderated_by": admin.get("email"),
        "moderated_at": now_iso(),
        "moderation_reason": payload.reason,
    }})
    await audit_log("vendor_rating.moderate", admin, "review", review_id,
                    {"action": payload.action, "vendor_ref": existing.get("vendor_ref")})
    return {"ok": True, "status": new_status}


@router.delete("/admin/reviews/{review_id}")
async def admin_delete_review(review_id: str, admin=Depends(require_role("admin"))):
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid review id")
    r = await db.vendor_reviews.delete_one({"_id": oid})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Review not found")
    await audit_log("vendor_rating.delete", admin, "review", review_id, {})
    return {"ok": True}


@router.get("/admin/pending-count")
async def admin_pending_count(admin=Depends(require_role("admin", "reviewer"))):
    c = await db.vendor_reviews.count_documents({"status": "pending"})
    return {"pending": c}
