"""Per-tender commercial terms: public vs private tender, optional private-tender winner charge."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from audit import audit_log
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/notice-terms", tags=["notice-terms"])
WINNER_FEE_PCT = 0.30


async def is_public_tender(notice: dict) -> bool:
    if notice.get("buyer_type") == "public_sector":
        return True
    c = await db.buyer_classifications.find_one({"notice_ref": notice.get("notice_ref")}, {"buyer_type": 1})
    return bool(c and c.get("buyer_type") == "public_sector")


async def terms(notice: dict) -> dict:
    public = await is_public_tender(notice)
    on = bool(notice.get("winner_fee_enabled")) and not public
    return {"public_tender": public, "winner_fee_enabled": on, "winner_fee_pct": WINNER_FEE_PCT if on else 0}


def winner_charge(notice: dict, price: float) -> float:
    return round(float(price or 0) * WINNER_FEE_PCT / 100.0, 2) if notice.get("winner_fee_enabled") else 0.0


class WinnerFeeIn(BaseModel):
    enabled: bool


@router.get("/{notice_ref}")
async def get_terms(notice_ref: str) -> dict:
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    return await terms(n)


@router.put("/{notice_ref}/winner-fee")
async def set_winner_fee(notice_ref: str, body: WinnerFeeIn, admin=Depends(require_role("admin"))) -> dict:
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    if n.get("is_published"):
        raise HTTPException(status_code=409, detail="The winner charge can only be set before the tender is published")
    if body.enabled and await is_public_tender(n):
        raise HTTPException(status_code=409, detail="Public tenders never charge the winning supplier")
    await db.notices.update_one({"notice_ref": notice_ref}, {"$set": {
        "winner_fee_enabled": body.enabled, "winner_fee_pct": WINNER_FEE_PCT if body.enabled else 0, "winner_fee_set_at": now_iso()}})
    await audit_log("notice.winner_fee", admin, "notice", notice_ref, {"enabled": body.enabled, "pct": WINNER_FEE_PCT})
    return await terms(await db.notices.find_one({"notice_ref": notice_ref}))
