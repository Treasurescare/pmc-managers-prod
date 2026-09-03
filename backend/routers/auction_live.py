"""Wave 40 — Reverse Auction Live Room.

Real-time reverse-auction bidding room with:
  * Masked bidder identity (`Bidder A`, `Bidder B`…) — never expose the real vendor
    name/email during the live round
  * Minimum decrement + hard price floor enforcement
  * Anti-snipe timer extension (any bid inside the last N seconds extends the
    close time by N seconds)
  * Auto-bid (bidders pre-declare a floor they'll accept — engine places
    counter-bids automatically when they get outbid)
  * Polling `/state` endpoint every ~2s from the vendor UI (no websocket)

Data model:
  `reverse_auctions`             — the round itself
  `reverse_auction_participants` — one row per vendor who joined the round
  `reverse_auction_bids`         — immutable ledger of every bid (manual + auto)
"""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/reverse-auctions", tags=["reverse-auctions"])


# ---------- Models ----------------------------------------------------

class ReverseAuctionIn(BaseModel):
    notice_ref: str
    title: str = Field(min_length=3, max_length=200)
    currency: str = "USD"
    starting_price: float = Field(gt=0)
    floor_price: float = Field(ge=0)          # cannot bid below this
    min_decrement: float = Field(gt=0)         # each new bid must beat by ≥ this
    duration_minutes: int = Field(ge=1, le=1440, default=30)
    anti_snipe_seconds: int = Field(ge=0, le=600, default=120)


class BidIn(BaseModel):
    price: float = Field(gt=0)


class AutobidIn(BaseModel):
    floor: float = Field(gt=0)   # I'll accept as low as this price (my walk-away)
    enabled: bool = True


# ---------- Helpers ---------------------------------------------------

def _alias_for_index(i: int) -> str:
    """0 → 'Bidder A', 25 → 'Bidder Z', 26 → 'Bidder AA'."""
    letters = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        letters = chr(65 + r) + letters
    return f"Bidder {letters}"


def _end_at_from_duration(now: datetime, minutes: int) -> str:
    from datetime import timedelta
    return (now + timedelta(minutes=minutes)).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_to_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _out_auction(a: dict) -> dict:
    o = BaseDocument.out(dict(a))
    return o


async def _mask_participants(aid: str) -> dict:
    """Return {vendor_id: alias} for a given auction."""
    mapping = {}
    async for p in db.reverse_auction_participants.find({"auction_id": aid}):
        mapping[p["vendor_id"]] = p.get("alias") or "Bidder ?"
    return mapping


async def _public_state(aid: str) -> dict:
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    aliases = await _mask_participants(aid)
    # last 30 bids, masked
    bids: list = []
    async for b in db.reverse_auction_bids.find({"auction_id": aid})\
                     .sort("at", -1).limit(30):
        bids.append({
            "alias": aliases.get(b["vendor_id"], "Bidder ?"),
            "price": b["price"],
            "at": b["at"],
            "auto": bool(b.get("is_auto")),
        })
    now = _now()
    end_at = _iso_to_dt(a["end_at"]) if a.get("end_at") else now
    remaining = max(0, int((end_at - now).total_seconds()))
    return {
        "id": str(a["_id"]),
        "title": a["title"],
        "notice_ref": a["notice_ref"],
        "currency": a["currency"],
        "starting_price": a["starting_price"],
        "floor_price": a["floor_price"],
        "min_decrement": a["min_decrement"],
        "status": a["status"],
        "current_price": a.get("current_price", a["starting_price"]),
        "leader_alias": aliases.get(a.get("current_leader_id"), None),
        "start_at": a.get("start_at"),
        "end_at": a.get("end_at"),
        "seconds_remaining": remaining if a["status"] == "live" else 0,
        "anti_snipe_seconds": a.get("anti_snipe_seconds", 0),
        "participant_count": len(aliases),
        "bids": bids,
    }


async def _place_bid_inner(auction: dict, vendor_id: str, price: float,
                            is_auto: bool = False) -> dict:
    """Core bid placement — validates and persists. Returns updated auction."""
    aid = str(auction["_id"])
    if auction["status"] != "live":
        raise HTTPException(status_code=400, detail="Auction is not live")
    end_at = _iso_to_dt(auction["end_at"])
    now = _now()
    if now >= end_at:
        raise HTTPException(status_code=400, detail="Auction has closed")
    current = float(auction.get("current_price", auction["starting_price"]))
    decrement = float(auction["min_decrement"])
    floor = float(auction["floor_price"])
    if price < floor:
        raise HTTPException(status_code=400,
            detail=f"Bid is below floor price {floor}")
    if price > current - decrement + 1e-9:
        raise HTTPException(status_code=400,
            detail=f"Bid must be at least {decrement} lower than current {current}")

    # Anti-snipe extension: if we're inside the anti-snipe window, push the
    # close time out.
    anti_snipe = int(auction.get("anti_snipe_seconds") or 0)
    updates = {"current_price": price, "current_leader_id": vendor_id,
               "last_bid_at": now.isoformat()}
    if anti_snipe > 0 and (end_at - now).total_seconds() < anti_snipe:
        from datetime import timedelta
        new_end = now + timedelta(seconds=anti_snipe)
        updates["end_at"] = new_end.isoformat()
        updates["anti_snipe_extended_count"] = int(
            auction.get("anti_snipe_extended_count") or 0) + 1

    await db.reverse_auctions.update_one(
        {"_id": auction["_id"]}, {"$set": updates})
    await db.reverse_auction_bids.insert_one({
        "auction_id": aid,
        "vendor_id": vendor_id,
        "price": price,
        "is_auto": is_auto,
        "at": now.isoformat(),
    })
    return await db.reverse_auctions.find_one({"_id": auction["_id"]})


async def _run_autobid_cascade(aid: str, max_iterations: int = 30):
    """After any human bid, walk the participants who have autobid enabled
    and let them undercut the current leader — one participant per iteration —
    until nobody can (or wants) to undercut."""
    for _ in range(max_iterations):
        a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
        if not a or a["status"] != "live":
            return
        current = float(a.get("current_price", a["starting_price"]))
        decrement = float(a["min_decrement"])
        target = current - decrement
        if target < float(a["floor_price"]):
            return
        # Any participant, not the current leader, with autobid enabled + floor ≤ target
        candidate = await db.reverse_auction_participants.find_one({
            "auction_id": aid,
            "autobid_enabled": True,
            "autobid_floor": {"$lte": target},
            "vendor_id": {"$ne": a.get("current_leader_id")},
        }, sort=[("autobid_floor", 1)])   # deepest walk-away goes first
        if not candidate:
            return
        try:
            await _place_bid_inner(a, candidate["vendor_id"], target, is_auto=True)
        except HTTPException:
            return


# ---------- Admin endpoints -------------------------------------------

@router.post("")
async def create_reverse_auction(payload: ReverseAuctionIn,
                                  admin=Depends(require_role("admin"))):
    if payload.floor_price >= payload.starting_price:
        raise HTTPException(status_code=400,
            detail="Floor price must be lower than starting price")
    notice = await db.notices.find_one({"notice_ref": payload.notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    doc = payload.model_dump()
    doc.update({
        "status": "draft",
        "current_price": payload.starting_price,
        "current_leader_id": None,
        "start_at": None,
        "end_at": None,
        "created_by": admin.get("email"),
        "created_at": now_iso(),
    })
    r = await db.reverse_auctions.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log("reverse_auction.create", admin, "auction", str(r.inserted_id),
                    {"notice": payload.notice_ref})
    return _out_auction(doc)


@router.get("")
async def list_reverse_auctions(admin=Depends(current_admin)):
    rows = []
    async for a in db.reverse_auctions.find({}).sort("created_at", -1).limit(200):
        rows.append(_out_auction(a))
    return {"items": rows, "total": len(rows)}


@router.get("/{aid}")
async def get_reverse_auction_admin(aid: str, admin=Depends(current_admin)):
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    parts = [BaseDocument.out(p) async for p in db.reverse_auction_participants.find({"auction_id": aid})]
    return {"auction": _out_auction(a), "participants": parts}


@router.post("/{aid}/start")
async def start_reverse_auction(aid: str, admin=Depends(require_role("admin"))):
    # Bug #43 — user reported "Start button doesn't work". Root cause: silent
    # 400 due to <2 registered participants. Now returns a very clear message
    # naming the specific gate that failed.
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a["status"] != "draft":
        raise HTTPException(status_code=400,
            detail=f"Cannot start auction — it is already in status '{a['status']}'. Only draft auctions can be started.")
    n = await db.reverse_auction_participants.count_documents({"auction_id": aid})
    if n < 2:
        raise HTTPException(status_code=400,
            detail=f"Cannot start auction — need at least 2 registered participants, currently {n}. Ask vendors to register first via the public link.")
    now = _now()
    end = _end_at_from_duration(now, int(a["duration_minutes"]))
    await db.reverse_auctions.update_one(
        {"_id": ObjectId(aid)},
        {"$set": {"status": "live", "start_at": now.isoformat(),
                   "end_at": end, "started_by": admin.get("email")}})
    await audit_log("reverse_auction.start", admin, "auction", aid,
                    {"end_at": end, "participants": n})
    return {"ok": True, "status": "live", "end_at": end}


@router.post("/{aid}/close")
async def close_reverse_auction(aid: str, admin=Depends(require_role("admin"))):
    # Bug #44 — clearer response so admin knows why nothing changed.
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a["status"] == "closed":
        return {"ok": True, "already_closed": True, "status": "closed"}
    if a["status"] == "draft":
        raise HTTPException(status_code=400,
            detail="Cannot close a draft auction — it was never started.")
    winner = None
    if a.get("current_leader_id"):
        p = await db.reverse_auction_participants.find_one({
            "auction_id": aid, "vendor_id": a["current_leader_id"]})
        winner = {
            "vendor_id": a["current_leader_id"],
            "company_name": p.get("company_name") if p else None,
            "alias": p.get("alias") if p else None,
            "winning_price": a.get("current_price"),
        }
    await db.reverse_auctions.update_one(
        {"_id": ObjectId(aid)},
        {"$set": {"status": "closed", "closed_at": now_iso(),
                   "closed_by": admin.get("email"), "winner": winner}})
    await audit_log("reverse_auction.close", admin, "auction", aid,
                    {"winning_price": a.get("current_price"),
                     "winner_alias": winner["alias"] if winner else None})
    return {"ok": True, "status": "closed", "winner": winner}


# ---------- Vendor endpoints ------------------------------------------

@router.post("/{aid}/register")
async def register_for_auction(aid: str, vendor=Depends(current_vendor)):
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a["status"] not in ("draft", "live"):
        raise HTTPException(status_code=400, detail="Auction is closed")
    existing = await db.reverse_auction_participants.find_one({
        "auction_id": aid, "vendor_id": vendor["id"]})
    if existing:
        return {"ok": True, "already_registered": True,
                "alias": existing.get("alias")}
    idx = await db.reverse_auction_participants.count_documents({"auction_id": aid})
    alias = _alias_for_index(idx)
    doc = {
        "auction_id": aid,
        "vendor_id": vendor["id"],
        "vendor_email": vendor["email"],
        "company_name": vendor.get("company_name"),
        "alias": alias,
        "autobid_enabled": False,
        "autobid_floor": None,
        "registered_at": now_iso(),
    }
    await db.reverse_auction_participants.insert_one(doc)
    return {"ok": True, "alias": alias, "id": str(a["_id"])}


@router.post("/{aid}/bid")
async def place_bid(aid: str, payload: BidIn, vendor=Depends(current_vendor)):
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    p = await db.reverse_auction_participants.find_one({
        "auction_id": aid, "vendor_id": vendor["id"]})
    if not p:
        raise HTTPException(status_code=403,
            detail="You must register for this auction before bidding")
    await _place_bid_inner(a, vendor["id"], float(payload.price))
    await _run_autobid_cascade(aid)
    return await _public_state(aid)


@router.post("/{aid}/autobid")
async def set_autobid(aid: str, payload: AutobidIn, vendor=Depends(current_vendor)):
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    p = await db.reverse_auction_participants.find_one({
        "auction_id": aid, "vendor_id": vendor["id"]})
    if not p:
        raise HTTPException(status_code=403, detail="Register first")
    if payload.floor < float(a["floor_price"]):
        raise HTTPException(status_code=400,
            detail=f"Autobid floor cannot be below auction floor {a['floor_price']}")
    await db.reverse_auction_participants.update_one(
        {"_id": p["_id"]},
        {"$set": {"autobid_enabled": bool(payload.enabled),
                   "autobid_floor": float(payload.floor),
                   "autobid_updated_at": now_iso()}})
    # Trigger cascade in case the new autobid should immediately act.
    await _run_autobid_cascade(aid)
    return {"ok": True, "autobid_enabled": payload.enabled,
            "autobid_floor": payload.floor}


@router.get("/{aid}/state")
async def get_state(aid: str):
    """PUBLIC — masked live state. Polled every ~2s by the vendor UI."""
    return await _public_state(aid)


@router.get("/{aid}/state-mine")
async def get_state_mine(aid: str, vendor=Depends(current_vendor)):
    """Same as /state but adds this vendor's own alias + autobid config."""
    state = await _public_state(aid)
    p = await db.reverse_auction_participants.find_one({
        "auction_id": aid, "vendor_id": vendor["id"]})
    state["me"] = {
        "registered": bool(p),
        "alias": p.get("alias") if p else None,
        "autobid_enabled": bool(p.get("autobid_enabled")) if p else False,
        "autobid_floor": p.get("autobid_floor") if p else None,
        "is_leader": bool(p and state.get("leader_alias") == p.get("alias")),
    }
    return state
