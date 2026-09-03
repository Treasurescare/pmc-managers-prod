"""BOQ & Contracts — export, filter, version history (Bucket B follow-through).

Companion to /api/v1/contracts. Provides:
  GET /api/v1/contracts-export/list?status=&vendor_id=&q=       — filter
  GET /api/v1/contracts-export/{contract_id}/versions           — history
  GET /api/v1/contracts-export/list.csv                         — CSV dump
"""
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from bson import ObjectId

from db import db
from security import require_role
from models.base import BaseDocument

router = APIRouter(prefix="/api/v1/contracts-export", tags=["contracts-export"])


def _out(d: dict) -> dict:
    return BaseDocument.out(d)


@router.get("/list")
async def list_filtered(
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    q: Optional[str] = None,
    admin=Depends(require_role("admin", "accounting", "reviewer", "auditor")),
):
    query: dict = {}
    if status:
        query["status"] = status
    if vendor_id:
        query["vendor_id"] = vendor_id
    if q:
        query["$or"] = [
            {"contract_ref": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
        ]
    items = [_out(c) async for c in db.contracts.find(query).sort("created_at", -1).limit(500)]
    return {"count": len(items), "items": items}


@router.get("/list.csv")
async def list_csv(
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    admin=Depends(require_role("admin", "accounting", "reviewer", "auditor")),
):
    query: dict = {}
    if status:
        query["status"] = status
    if vendor_id:
        query["vendor_id"] = vendor_id
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["contract_ref", "bid_id", "vendor_id", "title", "value",
                "currency", "start_date", "end_date", "milestones",
                "variation_orders", "status", "created_at"])
    async for c in db.contracts.find(query).sort("created_at", -1).limit(2000):
        w.writerow([
            c.get("contract_ref", ""), c.get("bid_id", ""), c.get("vendor_id", ""),
            (c.get("title") or "")[:100], c.get("value", ""),
            c.get("currency", ""), (c.get("start_date") or "")[:10],
            (c.get("end_date") or "")[:10],
            len(c.get("milestones") or []),
            len(c.get("variation_orders") or []),
            c.get("status", ""), (c.get("created_at") or "")[:19],
        ])
    return Response(
        content=buf.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="contracts-export.csv"',
                 "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{contract_id}/versions")
async def contract_versions(
    contract_id: str,
    admin=Depends(require_role("admin", "accounting", "reviewer", "auditor")),
):
    if not ObjectId.is_valid(contract_id):
        raise HTTPException(400, "Invalid contract id")
    c = await db.contracts.find_one({"_id": ObjectId(contract_id)})
    if not c:
        raise HTTPException(404, "Contract not found")
    # Variation orders + milestone completions serve as the version story.
    events = []
    events.append({"at": c.get("created_at"), "event": "created",
                   "by": c.get("created_by"), "value": c.get("value")})
    for m in (c.get("milestones") or []):
        if m.get("status") == "completed":
            events.append({"at": m.get("completed_at"),
                           "event": f"milestone_{m.get('order')}_completed",
                           "by": None, "value": m.get("amount")})
    for v in (c.get("variation_orders") or []):
        events.append({"at": v.get("at"), "event": "variation_order",
                       "by": v.get("by"), "value": v.get("amount_delta"),
                       "reason": v.get("reason")})
    events.sort(key=lambda e: e.get("at") or "")
    return {"contract_ref": c.get("contract_ref"),
            "events": events, "total_events": len(events)}
