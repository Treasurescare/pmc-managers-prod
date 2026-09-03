"""Dashboard drill-through endpoints (Wave E-2).

Powers the AdminDashboard AI Anomaly + Pipeline Funnel + Top-Priced Bids
click-through: instead of dead widgets, each card now exposes a JSON drill
endpoint the UI links to `/admin?tab=bidding&filter=…`.
"""
from typing import Optional
from fastapi import APIRouter, Depends

from db import db
from security import require_role

router = APIRouter(prefix="/api/v1/dashboard-drill", tags=["dashboard-drill"])


@router.get("/anomalies")
async def anomalies(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """Return every bid the AI copilot has flagged as anomalous (persisted on
    the bid doc as `anomaly.flag=true` by the AI compare job).

    Included fields let the frontend render a mini table without another round-trip.
    """
    items = []
    async for b in db.bids.find({"anomaly.flag": True}).sort("_id", -1).limit(200):
        items.append({
            "bid_id": str(b.get("_id")),
            "bid_ref": b.get("bid_ref"),
            "notice_ref": b.get("notice_ref"),
            "vendor": b.get("company_name") or b.get("vendor_email") or "",
            "price": b.get("price_amount"),
            "currency": b.get("price_currency") or "USD",
            "reason": (b.get("anomaly") or {}).get("reason") or "AI flagged",
            "detected_at": (b.get("anomaly") or {}).get("at"),
        })
    return {"count": len(items), "items": items}


@router.get("/pipeline")
async def pipeline(status: Optional[str] = None,
                    admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """Return bids grouped or filtered by status — used by the Pipeline Funnel
    card as its click-through payload."""
    q: dict = {}
    if status:
        q["status"] = status
    items = []
    async for b in db.bids.find(q).sort("_id", -1).limit(500):
        items.append({
            "bid_id": str(b.get("_id")),
            "bid_ref": b.get("bid_ref"),
            "notice_ref": b.get("notice_ref"),
            "vendor": b.get("company_name") or b.get("vendor_email") or "",
            "status": b.get("status"),
            "price": b.get("price_amount"),
            "currency": b.get("price_currency") or "USD",
        })
    return {"filter": status, "count": len(items), "items": items}


@router.get("/top-priced")
async def top_priced(limit: int = 10,
                      admin=Depends(require_role("admin", "reviewer", "auditor"))):
    limit = max(1, min(int(limit), 100))
    items = []
    cursor = db.bids.find({"price_amount": {"$ne": None}}).sort("price_amount", -1).limit(limit)
    async for b in cursor:
        items.append({
            "bid_id": str(b.get("_id")),
            "bid_ref": b.get("bid_ref"),
            "notice_ref": b.get("notice_ref"),
            "vendor": b.get("company_name") or b.get("vendor_email") or "",
            "status": b.get("status"),
            "price": b.get("price_amount"),
            "currency": b.get("price_currency") or "USD",
        })
    return {"count": len(items), "items": items}
