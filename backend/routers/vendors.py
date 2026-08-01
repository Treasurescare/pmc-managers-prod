"""Vendors router — list approved vendors + per-vendor KPI dashboard.

Phase-1 KPI is intentionally lightweight (registration age, KZ licenses count,
categories claimed). When bidding activates in Phase-2 we'll add win-rate,
avg turnaround, package awards etc. — API contract stays the same.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from db import db
from models.base import BaseDocument
from security import require_role

router = APIRouter(prefix="/api/v1/vendors", tags=["vendors"])


def _out(doc: dict) -> dict:
    d = BaseDocument.out(doc)
    d.pop("password_hash", None)
    return d


@router.get("")
async def list_vendors(
    search: Optional[str] = Query(None, description="Match against company_name or vendor_ref"),
    limit: int = 100,
    admin: Dict[str, Any] = Depends(require_role("admin", "reviewer")),
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"tenant_id": admin["tenant_id"]}
    if search:
        q["$or"] = [
            {"company_name": {"$regex": search, "$options": "i"}},
            {"vendor_ref": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    limit = max(1, min(int(limit), 500))
    return [_out(v) async for v in db.vendors.find(q).sort("created_at", -1).limit(limit)]


@router.get("/{vendor_ref}")
async def get_vendor(vendor_ref: str, admin: Dict[str, Any] = Depends(require_role("admin", "reviewer"))) -> Dict[str, Any]:
    v = await db.vendors.find_one({"vendor_ref": vendor_ref})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _out(v)


def _days_since(iso_str: Optional[str]) -> Optional[int]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return None


@router.get("/{vendor_ref}/kpi")
async def vendor_kpi(vendor_ref: str, admin: Dict[str, Any] = Depends(require_role("admin", "reviewer"))) -> Dict[str, Any]:
    v = await db.vendors.find_one({"vendor_ref": vendor_ref})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    profile = v.get("profile") or {}
    kz_licenses = v.get("kz_licenses") or profile.get("kz_licenses") or []
    categories = profile.get("business_categories") or []
    regions = profile.get("operating_regions") or []

    # Registration timeline
    submitted_at = profile.get("submitted_at")
    reviewed_at = profile.get("reviewed_at")
    approved_days_ago = _days_since(v.get("created_at"))
    time_to_decision = None
    if submitted_at and reviewed_at:
        try:
            s = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            r = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
            time_to_decision = max(0, int((r - s).total_seconds() / 3600))  # hours
        except Exception:
            pass

    return {
        "vendor_ref": v["vendor_ref"],
        "company_name": v.get("company_name"),
        "email": v.get("email"),
        "country": v.get("country"),
        "approved_at": v.get("created_at"),
        "approved_days_ago": approved_days_ago,
        "time_to_decision_hours": time_to_decision,
        "kz_licenses_held": kz_licenses,
        "kz_licenses_count": len(kz_licenses),
        "categories_declared": categories,
        "categories_count": len(categories),
        "operating_regions": regions,
        "primary_sector": profile.get("primary_sector"),
        "employees_count": profile.get("employees_count"),
        # Placeholders for Phase-2 (bidding / awards)
        "bids_submitted": 0,
        "bids_won": 0,
        "packages_awarded": 0,
        "phase_2_metrics": "Bidding metrics activate in Phase-2 (AWS + PostgreSQL migration).",
    }
