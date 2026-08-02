"""Wave 6 — Auction module (reverse/forward/live/sealed) + Helpdesk."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.auction import AuctionIn, AuctionBidIn, TicketIn, TicketReplyIn
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1", tags=["auctions-helpdesk"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- Auctions ----------

@router.post("/auctions")
async def create_auction(payload: AuctionIn, admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc.update({"status": "scheduled", "current_price": payload.starting_price,
                "bids": [], "created_by": admin["id"], "created_at": now_iso()})
    res = await db.auctions.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("auction.create", admin, "auction", str(res.inserted_id),
                    {"type": payload.auction_type})
    return _out(doc)


@router.get("/auctions")
async def list_auctions(admin=Depends(current_admin)):
    return [_out(a) async for a in db.auctions.find({}).sort("start_at", -1)]


@router.post("/auctions/bid")
async def place_auction_bid(payload: AuctionBidIn, vendor=Depends(current_vendor)):
    a = await db.auctions.find_one({"_id": ObjectId(payload.auction_id)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.get("status") not in ("scheduled", "live"):
        raise HTTPException(status_code=400, detail="Auction not accepting bids")
    kind = a.get("auction_type")
    cur = float(a.get("current_price", 0))
    price = float(payload.price)
    if kind == "reverse" and price >= cur - float(a.get("minimum_decrement", 0)):
        raise HTTPException(status_code=400, detail="Must beat current price by at least minimum_decrement")
    if kind == "forward" and price <= cur:
        raise HTTPException(status_code=400, detail="Must beat current price upward")

    entry = {"vendor_id": vendor["id"],
             "vendor_ref": vendor.get("vendor_ref"),
             "vendor_name": vendor.get("company_name") if not a.get("is_anonymous") else "Anonymous",
             "price": price, "at": now_iso()}
    await db.auctions.update_one(
        {"_id": ObjectId(payload.auction_id)},
        {"$set": {"current_price": price, "leading_vendor_id": vendor["id"]},
         "$push": {"bids": entry}},
    )
    return {"ok": True, "current_price": price}


# ---------- Helpdesk / Tickets ----------

@router.post("/support/tickets")
async def create_ticket(payload: TicketIn, admin=Depends(current_admin)):
    doc = payload.model_dump()
    doc.update({"raised_by": admin["id"], "raised_by_email": admin["email"],
                "status": "open", "replies": [], "created_at": now_iso()})
    res = await db.tickets.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _out(doc)


@router.get("/support/tickets")
async def list_tickets(admin=Depends(current_admin)):
    q = {} if admin.get("role") in ("admin", "support") else {"raised_by": admin["id"]}
    return [_out(t) async for t in db.tickets.find(q).sort("created_at", -1).limit(200)]


@router.post("/support/tickets/reply")
async def reply_ticket(payload: TicketReplyIn, admin=Depends(current_admin)):
    entry = {"body": payload.body, "attachments": payload.attachments,
             "by_id": admin["id"], "by_email": admin["email"], "at": now_iso()}
    r = await db.tickets.update_one(
        {"_id": ObjectId(payload.ticket_id)}, {"$push": {"replies": entry}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True, "reply": entry}


@router.post("/support/tickets/{ticket_id}/close")
async def close_ticket(ticket_id: str, admin=Depends(require_role("admin", "support"))):
    r = await db.tickets.update_one({"_id": ObjectId(ticket_id)},
                                    {"$set": {"status": "closed", "closed_at": now_iso()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}
