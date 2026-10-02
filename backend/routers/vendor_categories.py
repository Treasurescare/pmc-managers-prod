"""Vendor Category Interest flow (v50l).

Suppliers add categories they're interested in bidding on; the admin
reviews and approves/rejects each request. Approved categories land
in the vendor's `business_categories` list so tender matching picks
them up on the next bid search.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(tags=["vendor-categories"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


class CategoryRequestIn(BaseModel):
    category_code: str = Field(min_length=1, max_length=60)
    category_name: str = Field(min_length=1, max_length=200)
    rationale: Optional[str] = Field(default=None, max_length=600)


# ---------- Vendor side ----------
@router.get("/api/v1/vendor/categories/mine")
async def my_categories(vendor=Depends(current_vendor)):
    """Approved categories + any pending requests, for the signed-in vendor."""
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    approved = list((v or {}).get("business_categories") or [])
    pending = [_out(r) async for r in db.vendor_category_requests.find(
        {"vendor_ref": vendor["vendor_ref"], "status": "pending"}
    ).sort("requested_at", -1)]
    recent = [_out(r) async for r in db.vendor_category_requests.find(
        {"vendor_ref": vendor["vendor_ref"], "status": {"$in": ["approved", "rejected"]}}
    ).sort("decided_at", -1).limit(10)]
    return {"approved": approved, "pending": pending, "recent": recent}


@router.post("/api/v1/vendor/categories/request")
async def request_category(payload: CategoryRequestIn, vendor=Depends(current_vendor)):
    """Vendor requests a new category. Dedupes by (vendor_ref, category_code)
    across pending/approved so the same category can't be queued twice."""
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if payload.category_name in ((v or {}).get("business_categories") or []):
        raise HTTPException(status_code=409, detail="Category already in your approved list")
    dup = await db.vendor_category_requests.find_one({
        "vendor_ref": vendor["vendor_ref"],
        "category_code": payload.category_code,
        "status": "pending",
    })
    if dup:
        raise HTTPException(status_code=409, detail="A pending request for this category already exists")
    # Verify the category exists in the master.
    master = await db.categories.find_one({"code": payload.category_code, "is_active": True})
    if not master:
        raise HTTPException(status_code=400, detail="Unknown or inactive category")
    doc = {
        "vendor_ref": vendor["vendor_ref"],
        "vendor_email": vendor["email"],
        "vendor_company": v.get("company_name") if v else None,
        "category_code": payload.category_code,
        "category_name": payload.category_name,
        "rationale": payload.rationale,
        "status": "pending",
        "requested_at": now_iso(),
    }
    res = await db.vendor_category_requests.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _out(doc)


# ---------- Admin side ----------
@router.get("/api/v1/vendors/category-requests")
async def list_category_requests(status: str = "pending",
                                   admin=Depends(require_role("admin", "reviewer"))):
    cursor = db.vendor_category_requests.find({"status": status})\
        .sort("requested_at", -1).limit(500)
    return [_out(r) async for r in cursor]


class DecisionIn(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=400)


@router.post("/api/v1/vendors/category-requests/{request_id}/approve")
async def approve_category_request(request_id: str, payload: DecisionIn,
                                      admin=Depends(require_role("admin", "reviewer"))):
    req = await db.vendor_category_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Already {req['status']}")
    now = now_iso()
    await db.vendor_category_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "approved", "decided_at": now,
                   "decided_by": admin["email"], "decision_notes": payload.notes}},
    )
    # Add to vendor's business_categories.
    await db.vendors.update_one(
        {"vendor_ref": req["vendor_ref"]},
        {"$addToSet": {"business_categories": req["category_name"]}},
    )
    await audit_log("vendor.category_approve", admin, "vendor", req["vendor_ref"],
                     {"category": req["category_name"], "code": req["category_code"]})
    return {"ok": True}


@router.post("/api/v1/vendors/category-requests/{request_id}/reject")
async def reject_category_request(request_id: str, payload: DecisionIn,
                                     admin=Depends(require_role("admin", "reviewer"))):
    req = await db.vendor_category_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Already {req['status']}")
    if not (payload.notes or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    await db.vendor_category_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "rejected", "decided_at": now_iso(),
                   "decided_by": admin["email"], "decision_notes": payload.notes}},
    )
    await audit_log("vendor.category_reject", admin, "vendor", req["vendor_ref"],
                     {"category": req["category_name"], "reason": payload.notes})
    return {"ok": True}
