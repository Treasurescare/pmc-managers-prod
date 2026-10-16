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
import asyncio
import secrets
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
from emails import send_email, wrap as email_wrap
from notify import notify_role, notify_bid_transition

router = APIRouter(prefix="/api/v1/reverse-auctions", tags=["reverse-auctions"])


# ---------- Models ----------------------------------------------------

class ReverseAuctionIn(BaseModel):
    notice_ref: str
    title: str = Field(min_length=3, max_length=200)
    currency: str = "USD"
    starting_price: float = Field(gt=0)
    # v52by — bugs #64/#59/#60. Previously floor_price + min_decrement were
    # required which caused silent "field required" 422s when the frontend
    # left them blank. Give them sensible defaults so draft creation is
    # robust; downstream validation still rejects floor >= starting below.
    floor_price: float = Field(default=0.0, ge=0)
    min_decrement: float = Field(default=1.0, gt=0)
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


def _stamp_outcome(out: dict, raw: dict, vendor_id: str) -> None:
    """v53b — on closed auctions, tell THIS vendor whether they won, plus the
    winning price. Winner identity (company name) stays masked to losers."""
    if raw.get("status") != "closed":
        return
    w = raw.get("winner") or {}
    out["outcome"] = "won" if w.get("vendor_id") == vendor_id else "lost"
    out["winning_price"] = raw.get("current_price")
    out["awarded_bid_id"] = raw.get("awarded_bid_id")


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


class AuctionPatchIn(BaseModel):
    """v51ab — admin edits a draft reverse auction (title, prices, timing)."""
    title: Optional[str] = None
    starting_price: Optional[float] = Field(default=None, gt=0)
    floor_price: Optional[float] = Field(default=None, ge=0)
    min_decrement: Optional[float] = Field(default=None, gt=0)
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    currency: Optional[str] = None
    anti_snipe_seconds: Optional[int] = Field(default=None, ge=0)
    notice_ref: Optional[str] = None


@router.patch("/{aid}")
async def patch_reverse_auction(aid: str, payload: AuctionPatchIn,
                                 admin=Depends(require_role("admin"))):
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.get("status") != "draft":
        raise HTTPException(status_code=400,
                             detail="Only draft auctions can be edited. "
                                    "Close & recreate if the auction is live.")
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items()
               if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if "floor_price" in changes or "starting_price" in changes:
        sp = float(changes.get("starting_price", a.get("starting_price")))
        fp = float(changes.get("floor_price",    a.get("floor_price")))
        if fp >= sp:
            raise HTTPException(status_code=400,
                                 detail="Floor price must be lower than starting price")
    changes["updated_at"] = _now().isoformat()
    changes["updated_by"] = admin.get("email")
    await db.reverse_auctions.update_one({"_id": a["_id"]}, {"$set": changes})
    doc = await db.reverse_auctions.find_one({"_id": a["_id"]})
    return _out_auction(doc)


@router.get("")
async def list_reverse_auctions(admin=Depends(current_admin),
                                created_by_email: Optional[str] = None,
                                created_from: Optional[str] = None,
                                created_to: Optional[str] = None):
    # v51z — include participant_count on every row so the admin UI can show
    # a "0/2" / "1/2" / "✓ ready" readiness badge next to each Draft auction
    # without needing a second round-trip per row.
    # v52w — DB-side created-by / created-range filters (created_at is ISO str).
    q: dict = {}
    if created_by_email:
        q["created_by"] = {"$regex": created_by_email.strip(), "$options": "i"}
    if created_from or created_to:
        rng: dict = {}
        if created_from:
            rng["$gte"] = f"{created_from[:10]}T00:00:00"
        if created_to:
            rng["$lte"] = f"{created_to[:10]}T23:59:59.999"
        q["created_at"] = rng
    rows = []
    async for a in db.reverse_auctions.find(q).sort("created_at", -1).limit(200):
        out = _out_auction(a)
        out["participant_count"] = await db.reverse_auction_participants.count_documents(
            {"auction_id": out["id"]})
        rows.append(out)
    return {"items": rows, "total": len(rows)}


@router.get("/mine")
async def list_my_reverse_auctions(vendor=Depends(current_vendor)):
    """v52bx — vendor can see every reverse auction tied to a notice they
    bid on OR where they have been invited by email. Fixes "no option to
    see I've been invited to a reverse auction" (user feedback)."""
    bid_notice_refs = set()
    async for b in db.bids.find({"vendor_id": vendor["id"]}, {"notice_ref": 1}):
        if b.get("notice_ref"):
            bid_notice_refs.add(b["notice_ref"])
    rows = []
    seen = set()
    # Match by notice_ref (vendor bid on the parent notice).
    if bid_notice_refs:
        async for a in db.reverse_auctions.find(
            {"notice_ref": {"$in": list(bid_notice_refs)}}
        ).sort("created_at", -1).limit(100):
            out = _out_auction(a)
            out["why"] = "You bid on this tender"
            _stamp_outcome(out, a, vendor["id"])
            rows.append(out); seen.add(out["id"])
    # Also match any explicit invite row for this vendor's email.
    async for inv in db.reverse_auction_invitations.find(
        {"email": vendor.get("email", "").lower(), "accepted": {"$ne": False}}
    ).limit(100):
        aid = inv.get("auction_id")
        if not aid or aid in seen:
            continue
        a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
        if not a: continue
        out = _out_auction(a)
        out["why"] = "You were invited by PMC"
        _stamp_outcome(out, a, vendor["id"])
        rows.append(out); seen.add(out["id"])
    return {"items": rows, "count": len(rows)}


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
            "vendor_email": p.get("vendor_email") if p else None,
            "winning_price": a.get("current_price"),
        }
    await db.reverse_auctions.update_one(
        {"_id": ObjectId(aid)},
        {"$set": {"status": "closed", "closed_at": now_iso(),
                   "closed_by": admin.get("email"), "winner": winner}})
    await audit_log("reverse_auction.close", admin, "auction", aid,
                    {"winning_price": a.get("current_price"),
                     "winner_alias": winner["alias"] if winner else None})
    # v53b — close fan-out. Today closing an auction was silent: nobody was
    # told who won or what happens next. Now:
    #   admin  → winner summary + "click Award winner" next step
    #   winner → "you won" mail with the pipeline that follows
    #   losers → polite not-selected mail
    try:
        cur = a.get("currency", "USD")
        money = (f"{cur} {a.get('current_price'):,.0f}"
                 if a.get("current_price") else "—")
        start_money = f"{cur} {a.get('starting_price', 0):,.0f}"
        title = a.get("title") or aid
        ref = a.get("notice_ref") or ""
        if winner:
            await notify_role(
                "admin",
                f"Reverse auction closed — {title}",
                email_wrap("Reverse auction closed",
                    f"<p><strong>{title}</strong> ({ref}) has closed.</p>"
                    f"<p>Winner: <strong>{winner.get('company_name') or winner.get('alias')}</strong> "
                    f"({winner.get('alias')}) at <strong>{money}</strong> "
                    f"(started at {start_money}).</p>"
                    f"<p><strong>Next step:</strong> open this auction in the admin "
                    f"console (Reverse auctions) and click <strong>Award winner</strong> "
                    f"— the winning bid enters the standard EMD &rarr; escrow &rarr; "
                    f"legal &rarr; accounting pipeline before the award is final.</p>"),
                related_type="auction", related_id=aid)
            if winner.get("vendor_email"):
                await send_email(
                    winner["vendor_email"],
                    f"You won the reverse auction — {title}",
                    email_wrap("You won the reverse auction",
                        f"<p>Congratulations — your bid of <strong>{money}</strong> was "
                        f"the lowest in <strong>{title}</strong> ({ref}).</p>"
                        f"<p>PMC will now confirm the award. Once confirmed, your bid "
                        f"enters the standard pipeline (EMD verification &rarr; escrow "
                        f"&rarr; legal &rarr; accounting) and you'll receive the purchase "
                        f"order for e-signature. Track progress under "
                        f"<em>My bids</em> in the supplier portal.</p>"))
            async for lp in db.reverse_auction_participants.find(
                    {"auction_id": aid, "vendor_id": {"$ne": winner["vendor_id"]}}):
                if not lp.get("vendor_email"):
                    continue
                await send_email(
                    lp["vendor_email"],
                    f"Reverse auction closed — {title}",
                    email_wrap("Reverse auction closed",
                        f"<p><strong>{title}</strong> ({ref}) has closed. Your bid was "
                        f"not the lowest on this round, so you have not been selected.</p>"
                        f"<p>Thank you for participating — watch the supplier portal for "
                        f"future rounds.</p>"))
    except Exception:
        pass  # email failures must never block the close itself
    return {"ok": True, "status": "closed", "winner": winner}


@router.post("/{aid}/award")
async def award_reverse_auction(aid: str, admin=Depends(require_role("admin"))):
    """v53b — hand the winner into the standard bid pipeline.

    Creates a bids row at status=emd_paid (source=reverse_auction) linked to
    the parent notice. From there it flows through the normal chain
    (escrow → certifier → legal → accounting → awarded) exactly like a
    sealed-bid winner — user decision: reverse-auction awards must NOT skip
    governance sign-off. Idempotent: a second click returns the same bid.
    """
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.get("status") != "closed":
        raise HTTPException(status_code=400,
            detail="Award is only possible after the auction is closed.")
    winner = a.get("winner") or {}
    if not winner.get("vendor_id"):
        raise HTTPException(status_code=400,
            detail="This auction closed with no bids — there is no winner to award.")
    if a.get("awarded_bid_id"):
        return {"ok": True, "already_awarded": True, "bid_id": a["awarded_bid_id"]}
    existing = await db.bids.find_one({"auction_id": aid})
    if existing:
        bid_id = str(existing["_id"])
        await db.reverse_auctions.update_one(
            {"_id": ObjectId(aid)}, {"$set": {"awarded_bid_id": bid_id}})
        return {"ok": True, "already_awarded": True, "bid_id": bid_id}
    bid_ref = f"BID-AUC-{aid[-6:].upper()}"
    bid = {
        "bid_ref": bid_ref,
        "notice_ref": a.get("notice_ref"),
        "vendor_id": winner["vendor_id"],
        "vendor_email": winner.get("vendor_email"),
        "company_name": winner.get("company_name"),
        "status": "emd_paid",
        "price_amount": winner.get("winning_price"),
        "price_currency": a.get("currency", "USD"),
        "source": "reverse_auction",
        "auction_id": aid,
        "created_at": now_iso(),
        "created_by_email": admin.get("email"),
    }
    res = await db.bids.insert_one(bid)
    bid_id = str(res.inserted_id)
    await db.reverse_auctions.update_one(
        {"_id": ObjectId(aid)},
        {"$set": {"awarded_bid_id": bid_id, "awarded_at": now_iso(),
                   "awarded_by": admin.get("email")}})
    # emd_paid → escrow agent is the next stage in the standard pipeline;
    # reuse the same notification copy sealed bids use.
    try:
        bid["id"] = bid_id
        await notify_bid_transition(bid, "emd_paid")
    except Exception:
        pass
    await audit_log("reverse_auction.award", admin, "auction", aid,
                    {"bid_id": bid_id, "bid_ref": bid_ref,
                     "winner": winner.get("company_name"),
                     "winning_price": winner.get("winning_price")})
    return {"ok": True, "bid_id": bid_id, "bid_ref": bid_ref,
            "status": "emd_paid",
            "next_step": "Bid created at emd_paid — continue in Bidding Ops."}


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


# ---------- Invitations (v46b) ----------------------------------------
# Admin can invite specific vendors by email. Each invite generates a
# single-use token and a shareable URL. Vendors who click the URL land on
# the auction room and can register with one click. No SMTP dependency —
# admin can copy the URLs and share via any channel.

class InviteBatchIn(BaseModel):
    emails: List[str] = Field(min_length=1, max_length=200)
    note: Optional[str] = None
    template_id: Optional[str] = None   # v46c — reusable template
    auto_send: bool = False             # v46c — auto-email via managed proxy
    origin_url: Optional[str] = None    # for building invite URL in email


_DEFAULT_INVITE_SUBJECT = "You're invited to bid in a live reverse auction — {{auction_title}}"
_DEFAULT_INVITE_BODY = (
    "<p>You have been invited by <b>PMC Managers</b> to participate in the live "
    "reverse auction <b>{{auction_title}}</b> (tender <code>{{notice_ref}}</code>).</p>"
    "<p>Starting price: <b>{{currency}} {{starting_price}}</b>. The auction is "
    "descending-price — the lowest compliant bid at close wins.</p>"
    "<p>{{admin_note}}</p>"
    "<p>Click the button below to register. Each invite link is unique to your "
    "email address and auction.</p>"
)


@router.post("/{aid}/invite")
async def invite_bidders(aid: str, payload: InviteBatchIn,
                          admin=Depends(require_role("admin"))):
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    if a.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Auction is closed")
    # Resolve template (optional). v51z: if auto_send is on and no template_id
    # was supplied, fall back to the default template picked from Mongo, or to
    # the built-in default body. Admins should never have to pre-seed a
    # template just to email vendors.
    tpl = None
    if payload.template_id:
        try:
            tpl = await db.auction_invite_templates.find_one({"_id": ObjectId(payload.template_id)})
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid template_id")
        if not tpl:
            raise HTTPException(status_code=404, detail="Invitation template not found")
    elif payload.auto_send:
        tpl = await db.auction_invite_templates.find_one({"is_default": True}) or {
            "subject": _DEFAULT_INVITE_SUBJECT,
            "body_html": _DEFAULT_INVITE_BODY,
        }
    out = []
    sent_count = 0
    for raw in payload.emails:
        email = (raw or "").strip().lower()
        if not email or "@" not in email:
            continue
        # Reuse token if this email was already invited to this auction.
        existing = await db.reverse_auction_invitations.find_one({
            "auction_id": aid, "email": email})
        if existing:
            token = existing["token"]
            await db.reverse_auction_invitations.update_one(
                {"_id": existing["_id"]},
                {"$set": {"resent_at": now_iso(), "note": payload.note}})
        else:
            token = secrets.token_urlsafe(24)
            await db.reverse_auction_invitations.insert_one({
                "auction_id": aid, "email": email, "token": token,
                "status": "pending", "note": payload.note,
                "invited_by": admin.get("email"), "invited_at": now_iso(),
            })
        # Try to resolve vendor by email so we can autolink status later.
        v = await db.vendors.find_one({"email": email})
        out.append({
            "email": email, "token": token, "resent": bool(existing),
            "vendor_ref": v.get("vendor_ref") if v else None,
        })
        # v46c — auto-send via managed email proxy when requested
        if payload.auto_send and tpl:
            invite_url = f"{(payload.origin_url or '').rstrip('/')}/vendor/auction/invite/{token}"
            # v52n — any legacy template without the {{invite_url}} placeholder
            # left vendors with a mail that had NO join link ("shows sent but
            # emails not received/usable"). Append the join button when the
            # placeholder is missing.
            raw_body = tpl.get("body_html") or ""
            if "{{invite_url}}" not in raw_body:
                raw_body = raw_body + (
                    f'<p style="margin-top:16px"><a href="{{{{invite_url}}}}" '
                    f'style="display:inline-block;padding:10px 18px;background:#0F3B2E;'
                    f'color:#ffffff;text-decoration:none;font-weight:600;'
                    f'letter-spacing:0.5px;text-transform:uppercase;font-size:12px;">'
                    f'Join the auction</a></p>'
                    f'<p style="font-size:12px;color:#64748B">Or paste this link into your '
                    f'browser: {{{{invite_url}}}}</p>')
            body_html = raw_body\
                .replace("{{invite_url}}", invite_url)\
                .replace("{{auction_title}}", a.get("title", ""))\
                .replace("{{notice_ref}}", a.get("notice_ref", ""))\
                .replace("{{vendor_email}}", email)\
                .replace("{{starting_price}}", str(a.get("starting_price", "")))\
                .replace("{{currency}}", a.get("currency", ""))\
                .replace("{{admin_note}}", payload.note or "")
            subject = (tpl.get("subject") or f"Invitation: {a.get('title')}")\
                .replace("{{auction_title}}", a.get("title", ""))\
                .replace("{{notice_ref}}", a.get("notice_ref", ""))
            wrapped = email_wrap(subject, body_html, "Join auction", invite_url)
            # v52n — respect Resend's 10 req/s cap. A fast burst (10+ invites
            # pasted at once) was returning 429 on later rows and silently
            # dropping those invite emails. 120 ms stagger keeps us well under.
            if await send_email(email, subject, wrapped):
                sent_count += 1
            await asyncio.sleep(0.12)
    await audit_log("reverse_auction.invite", admin, "auction", aid,
                    {"count": len(out), "auto_sent": sent_count})
    return {"invited": out, "count": len(out), "auto_sent": sent_count}


# ---- Invitation templates (v46c) -----------------------------------------

class InviteTemplateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    subject: str = Field(min_length=2, max_length=200)
    body_html: str = Field(min_length=10)  # supports {{invite_url}}, {{auction_title}}, {{notice_ref}}, {{vendor_email}}, {{starting_price}}, {{currency}}, {{admin_note}}
    is_default: bool = False


@router.get("/invite/tpl")
async def list_invite_templates(admin=Depends(current_admin)):
    return [BaseDocument.out(t) async for t in db.auction_invite_templates.find({}).sort("name", 1)]


@router.post("/invite/tpl")
async def create_invite_template(payload: InviteTemplateIn,
                                   admin=Depends(require_role("admin"))):
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin.get("email")
    if doc.get("is_default"):
        await db.auction_invite_templates.update_many({}, {"$set": {"is_default": False}})
    r = await db.auction_invite_templates.insert_one(doc)
    return BaseDocument.out(await db.auction_invite_templates.find_one({"_id": r.inserted_id}))


@router.patch("/invite/tpl/{tid}")
async def update_invite_template(tid: str, payload: InviteTemplateIn,
                                   admin=Depends(require_role("admin"))):
    body = payload.model_dump()
    body["updated_at"] = now_iso()
    if body.get("is_default"):
        await db.auction_invite_templates.update_many({"_id": {"$ne": ObjectId(tid)}},
                                                        {"$set": {"is_default": False}})
    r = await db.auction_invite_templates.update_one({"_id": ObjectId(tid)}, {"$set": body})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Template not found")
    return BaseDocument.out(await db.auction_invite_templates.find_one({"_id": ObjectId(tid)}))


@router.delete("/invite/tpl/{tid}")
async def delete_invite_template(tid: str, admin=Depends(require_role("admin"))):
    r = await db.auction_invite_templates.delete_one({"_id": ObjectId(tid)})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


@router.get("/{aid}/invitations")
async def list_invitations(aid: str, admin=Depends(current_admin)):
    rows = []
    async for r in db.reverse_auction_invitations.find({"auction_id": aid}).sort("invited_at", -1):
        r["id"] = str(r.pop("_id"))
        # Check if invitee actually joined
        joined = False
        if r.get("email"):
            v = await db.vendors.find_one({"email": r["email"]})
            if v:
                p = await db.reverse_auction_participants.find_one({
                    "auction_id": aid, "vendor_id": v["id"] if "id" in v else str(v.get("_id"))})
                joined = bool(p)
                r["vendor_ref"] = v.get("vendor_ref")
        r["joined"] = joined
        rows.append(r)
    return {"items": rows, "count": len(rows)}


@router.get("/invite/resolve/{token}")
async def resolve_invite(token: str):
    """Public — resolves the auction referenced by the invite token.
    Frontend calls this from the invite landing page to know where to go."""
    inv = await db.reverse_auction_invitations.find_one({"token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    a = await db.reverse_auctions.find_one({"_id": ObjectId(inv["auction_id"])})
    if not a:
        raise HTTPException(status_code=404, detail="Auction no longer exists")
    return {
        "auction_id": inv["auction_id"],
        "email": inv.get("email"),
        "status": a.get("status"),
        "title": a.get("title"),
        "notice_ref": a.get("notice_ref"),
        "starting_price": a.get("starting_price"),
        "floor_price": a.get("floor_price"),
        "currency": a.get("currency"),
    }


@router.post("/invite/accept/{token}")
async def accept_invite(token: str, vendor=Depends(current_vendor)):
    """Vendor accepts an invitation — must be signed in as the invited email."""
    inv = await db.reverse_auction_invitations.find_one({"token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    if inv.get("email") and inv["email"].lower() != (vendor.get("email") or "").lower():
        raise HTTPException(status_code=403,
            detail=f"This invitation is for {inv['email']}. Sign in as that vendor first.")
    aid = inv["auction_id"]
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction no longer exists")
    # Auto-register the vendor to the auction (idempotent)
    existing = await db.reverse_auction_participants.find_one({
        "auction_id": aid, "vendor_id": vendor["id"]})
    if not existing:
        idx = await db.reverse_auction_participants.count_documents({"auction_id": aid})
        alias = _alias_for_index(idx)
        await db.reverse_auction_participants.insert_one({
            "auction_id": aid, "vendor_id": vendor["id"],
            "vendor_email": vendor["email"],
            "company_name": vendor.get("company_name"),
            "alias": alias, "autobid_enabled": False,
            "autobid_floor": None, "registered_at": now_iso(),
            "via_invitation_token": token,
        })
        alias_out = alias
    else:
        alias_out = existing.get("alias")
    await db.reverse_auction_invitations.update_one(
        {"_id": inv["_id"]},
        {"$set": {"status": "accepted", "accepted_at": now_iso(),
                  "accepted_by_vendor_id": vendor["id"]}})
    return {"ok": True, "auction_id": aid, "alias": alias_out}
