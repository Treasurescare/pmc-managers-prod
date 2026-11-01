"""v51bd — Bid draft server sync.

Vendors can save their in-progress bid composition so they can resume
from any device. Draft documents are stored per (vendor_id, notice_ref)
pair and overwritten on every PUT. They are deleted the moment a real
bid is submitted so a stale draft never shadows a live submission.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import config
from db import db
from models.base import now_iso
from routers.vendor_auth import current_vendor


router = APIRouter(prefix="/api/v1/bids/drafts", tags=["bids-drafts"])


class DraftDocIn(BaseModel):
    kind: str
    key: str
    filename: str
    size_bytes: int = 0
    uploaded_at: Optional[str] = None
    content_type: Optional[str] = None
    criterion_id: Optional[str] = None


class BidDraftIn(BaseModel):
    price_amount: Optional[float] = None
    price_currency: Optional[str] = None
    technical_notes: Optional[str] = None
    commercial_notes: Optional[str] = None
    documents: List[DraftDocIn] = []
    criteria_answers: Optional[dict] = None


def _out(doc: dict) -> dict:
    return {
        "notice_ref": doc.get("notice_ref"),
        "price_amount": doc.get("price_amount"),
        "price_currency": doc.get("price_currency"),
        "technical_notes": doc.get("technical_notes"),
        "commercial_notes": doc.get("commercial_notes"),
        "documents": doc.get("documents") or [],
        "criteria_answers": doc.get("criteria_answers") or {},
        "updated_at": doc.get("updated_at"),
    }


@router.get("/{notice_ref}")
async def get_draft(notice_ref: str, vendor=Depends(current_vendor)) -> dict:
    """Return the vendor's stored draft for a notice, or `{found: false}`."""
    draft = await db.bid_drafts.find_one({
        "vendor_id": vendor["id"], "notice_ref": notice_ref})
    if not draft:
        return {"found": False, "notice_ref": notice_ref}
    return {"found": True, **_out(draft)}


@router.put("/{notice_ref}")
async def put_draft(notice_ref: str, payload: BidDraftIn,
                     vendor=Depends(current_vendor)) -> dict:
    """Overwrite / create the draft for this (vendor, notice) pair."""
    notice = await db.notices.find_one({"notice_ref": notice_ref},
                                         {"notice_ref": 1, "is_published": 1})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    doc = payload.model_dump()
    doc.update({
        "vendor_id": vendor["id"],
        "vendor_email": vendor["email"],
        "notice_ref": notice_ref,
        "updated_at": now_iso(),
    })
    await db.bid_drafts.update_one(
        {"vendor_id": vendor["id"], "notice_ref": notice_ref},
        {"$set": doc, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True)
    return {"ok": True, "updated_at": doc["updated_at"]}


@router.delete("/{notice_ref}")
async def delete_draft(notice_ref: str, vendor=Depends(current_vendor)) -> dict:
    await db.bid_drafts.delete_one({
        "vendor_id": vendor["id"], "notice_ref": notice_ref})
    return {"ok": True}


@router.get("")
async def list_my_drafts(vendor=Depends(current_vendor)) -> List[dict]:
    rows = []
    async for d in db.bid_drafts.find({"vendor_id": vendor["id"]}).sort("updated_at", -1):
        rows.append({**_out(d), "notice_ref": d.get("notice_ref")})
    return rows
