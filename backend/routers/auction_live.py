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
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from bson import ObjectId
import json
import hashlib

from pymongo.errors import DuplicateKeyError

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
    # v57e — notice_ref is now optional. Omit it to create a STANDALONE
    # reverse auction (not backed by an existing published tender). A synthetic
    # reference is generated and a backing procurement record is lazily created
    # at award time so standalone winners still flow through the same
    # EMD -> escrow -> legal -> accounting governance pipeline as tenders.
    notice_ref: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
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


async def _stamp_outcome(out: dict, raw: dict, vendor_id: str) -> None:
    """v53b — on closed auctions, tell THIS vendor whether they won, plus the
    winning price. Winner identity (company name) stays masked to losers.

    v53i — invited vendors who NEVER registered get a distinct outcome
    `not_participated` so the vendor UI shows a correct "you were invited but
    did not take part" reference instead of the misleading "your bid was not
    the lowest" losing message."""
    if raw.get("status") != "closed":
        return
    w = raw.get("winner") or {}
    out["winning_price"] = raw.get("current_price")
    out["awarded_bid_id"] = raw.get("awarded_bid_id")
    if w.get("vendor_id") == vendor_id:
        out["outcome"] = "won"
        return
    # Did this vendor actually register as a participant?
    p = await db.reverse_auction_participants.find_one(
        {"auction_id": str(raw["_id"]), "vendor_id": vendor_id},
        {"_id": 1})
    out["outcome"] = "lost" if p else "not_participated"


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
    aid_str = str(a["_id"])
    public_winner, award_status = await _public_winner(a)
    invite_count = await db.reverse_auction_invitations.count_documents({"auction_id": aid_str})
    viewer_count = await _active_viewers(aid_str)
    compliant = await _compliant_bidder_count(aid_str)
    return {
        "id": aid_str,
        "title": a["title"],
        "notice_ref": a["notice_ref"],
        "is_standalone": bool(a.get("is_standalone")),
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
        "anti_snipe_extended_count": int(a.get("anti_snipe_extended_count") or 0),
        "participant_count": len(aliases),
        "invite_count": invite_count,
        "viewer_count": viewer_count,
        "compliant_bidder_count": compliant,
        "award_status": award_status,
        "award_published": award_status == "awarded_published",
        "winner": public_winner,
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

    # Atomic duplicate-price guard: the (auction_id, price) unique index makes
    # exactly one bid at a given price win under simultaneous bids. Insert
    # FIRST so the price is reserved before the auction row is mutated.
    try:
        await db.reverse_auction_bids.insert_one({
            "auction_id": aid,
            "vendor_id": vendor_id,
            "price": price,
            "is_auto": is_auto,
            "at": now.isoformat(),
        })
    except DuplicateKeyError:
        cur_sym = auction.get("currency", "USD")
        raise HTTPException(status_code=409,
            detail=f"Another bidder already placed {cur_sym} {price:,.0f} in this "
                   f"auction. Enter a different amount — each price can be used "
                   f"only once.")
    await db.reverse_auctions.update_one(
        {"_id": auction["_id"]}, {"$set": updates})
    # Public hash-chained timeline event (masked alias only).
    try:
        p = await db.reverse_auction_participants.find_one(
            {"auction_id": aid, "vendor_id": vendor_id}, {"alias": 1})
        await _append_auction_event(aid, "bid", {
            "alias": (p or {}).get("alias") or "Bidder ?",
            "price": price, "auto": bool(is_auto),
            "currency": auction.get("currency", "USD")})
        if updates.get("end_at"):
            await _append_auction_event(aid, "extension", {
                "new_end_at": updates["end_at"],
                "anti_snipe_seconds": anti_snipe})
    except Exception:
        pass
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


# ---------- Public reverse-auction helpers (v57e) ---------------------

_RA_EVENT_LOCK = asyncio.Lock()


def _ra_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


async def _append_auction_event(aid: str, kind: str, data: dict) -> None:
    """Append a SHA-256 hash-chained PUBLIC event for one auction (masked)."""
    async with _RA_EVENT_LOCK:
        last = await db.reverse_auction_events.find_one(
            {"auction_id": aid}, sort=[("seq", -1)])
        seq = int((last or {}).get("seq") or 0) + 1
        prev = (last or {}).get("current_hash", "GENESIS")
        body = {"auction_id": aid, "seq": seq, "kind": kind,
                "data": data, "at": now_iso(), "previous_hash": prev}
        body["current_hash"] = _ra_hash(body)
        await db.reverse_auction_events.insert_one(body)


async def _active_viewers(aid: str) -> int:
    from datetime import timedelta
    cutoff = (_now() - timedelta(seconds=20)).isoformat()
    return await db.reverse_auction_viewers.count_documents(
        {"auction_id": aid, "last_seen": {"$gte": cutoff}})


async def _compliant_bidder_count(aid: str) -> int:
    ids = await db.reverse_auction_bids.distinct("vendor_id", {"auction_id": aid})
    return len(ids)


async def _public_winner(a: dict):
    """Reveal the winning COMPANY only after the award is PUBLISHED (the
    awarded bid reached status=awarded through governance). Until then the
    public sees only that the result 'has gone for approvals'."""
    status = a.get("status") or "draft"
    if status != "closed":
        return None, status
    bid_id = a.get("awarded_bid_id")
    if not bid_id:
        return None, "closed_unawarded"
    try:
        bid = await db.bids.find_one({"_id": ObjectId(bid_id)},
                                     {"status": 1, "company_name": 1})
    except Exception:
        bid = None
    if bid and bid.get("status") == "awarded":
        return ({"company_name": bid.get("company_name"),
                 "winning_price": a.get("current_price"),
                 "currency": a.get("currency", "USD")}, "awarded_published")
    return None, "in_approvals"


async def _public_card(a: dict) -> dict:
    aid = str(a["_id"])
    start = float(a.get("starting_price") or 0)
    final = float(a.get("current_price") or start)
    saving = round(((start - final) / start * 100.0), 1) if start > 0 else 0.0
    winner, award_status = await _public_winner(a)
    return {
        "id": aid,
        "title": a.get("title"),
        "notice_ref": a.get("notice_ref"),
        "currency": a.get("currency", "USD"),
        "status": a.get("status"),
        "is_standalone": bool(a.get("is_standalone")),
        "starting_price": start,
        "current_price": final,
        "floor_price": a.get("floor_price"),
        "end_at": a.get("end_at"),
        "start_at": a.get("start_at"),
        "closed_at": a.get("closed_at"),
        "participant_count": await db.reverse_auction_participants.count_documents({"auction_id": aid}),
        "invite_count": await db.reverse_auction_invitations.count_documents({"auction_id": aid}),
        "saving_pct": saving,
        "award_status": award_status,
        "winner": winner,
    }


async def _notify_duplicate_price(a: dict, vendor: dict, price: float) -> None:
    """Duplicate-price rejection — in-app notification + email to the vendor
    whose equal-price bid lost the atomic race. They keep watching and rebid."""
    aid = str(a["_id"])
    cur = a.get("currency", "USD")
    title = a.get("title") or aid
    subject = f"Your bid wasn't placed — {cur} {price:,.0f} is already taken"
    body = (f"<p>Your bid of <strong>{cur} {price:,.0f}</strong> on "
            f"<strong>{title}</strong> could not be placed because another "
            f"bidder had already used that exact price.</p>"
            f"<p>Each price can be used only once in a reverse auction. You are "
            f"still in the round — enter a different (lower) amount to stay "
            f"competitive.</p>")
    try:
        await db.notifications.insert_one({
            "user_email": vendor.get("email"),
            "user_ref": vendor.get("vendor_ref"),
            "role": "vendor",
            "subject": subject,
            "body": body,
            "related_type": "auction", "related_id": aid,
            "read": False, "created_at": now_iso(),
        })
    except Exception:
        pass
    try:
        if vendor.get("email"):
            await send_email(vendor["email"], f"[PMC] {subject}",
                             email_wrap(subject, body))
    except Exception:
        pass


async def _close_auction_core(a: dict, closed_by: str) -> dict:
    """Shared close logic used by the admin close endpoint and the cron-ready
    reconciliation endpoint. Returns the (masked) winner dict or None."""
    aid = str(a["_id"])
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
    compliant = await _compliant_bidder_count(aid)
    await db.reverse_auctions.update_one(
        {"_id": a["_id"]},
        {"$set": {"status": "closed", "closed_at": now_iso(),
                   "closed_by": closed_by, "winner": winner,
                   "compliant_bidder_count": compliant}})
    await audit_log("reverse_auction.close", {"email": closed_by}, "auction", aid,
                    {"winning_price": a.get("current_price"),
                     "winner_alias": winner["alias"] if winner else None,
                     "compliant_bidder_count": compliant})
    try:
        await _append_auction_event(aid, "close", {
            "final_price": a.get("current_price"),
            "currency": a.get("currency", "USD"),
            "compliant_bidder_count": compliant,
            "winner_alias": winner.get("alias") if winner else None})
    except Exception:
        pass
    # Close fan-out (winner / losers / invitees). Email failures never block.
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
            participant_emails = set()
            async for pp in db.reverse_auction_participants.find(
                    {"auction_id": aid}, {"vendor_email": 1}):
                if pp.get("vendor_email"):
                    participant_emails.add(pp["vendor_email"].lower())
            async for inv in db.reverse_auction_invitations.find(
                    {"auction_id": aid}):
                em = (inv.get("email") or "").lower()
                if not em or em in participant_emails:
                    continue
                await send_email(
                    em,
                    f"Reverse auction closed — {title}",
                    email_wrap("Reverse auction closed",
                        f"<p>You were invited to participate in <strong>{title}</strong> "
                        f"({ref}), but did not register for this round.</p>"
                        f"<p>The auction has now closed and will be awarded to another "
                        f"bidder. The invitation record stays visible under "
                        f"<em>Reverse auctions</em> in your supplier portal for your "
                        f"reference. Watch there for future rounds.</p>"))
    except Exception:
        pass
    return winner


# ---------- Admin endpoints -------------------------------------------

@router.post("")
async def create_reverse_auction(payload: ReverseAuctionIn,
                                  admin=Depends(require_role("admin"))):
    if payload.floor_price >= payload.starting_price:
        raise HTTPException(status_code=400,
            detail="Floor price must be lower than starting price")
    # v57e — notice_ref optional → STANDALONE auction. Tender-backed auctions
    # still validate the notice exists; standalone auctions get a synthetic
    # reference and a backing notice is lazily created at award time.
    if payload.notice_ref:
        notice = await db.notices.find_one({"notice_ref": payload.notice_ref})
        if not notice:
            raise HTTPException(status_code=404, detail="Notice not found")
        notice_ref = payload.notice_ref
        is_standalone = False
    else:
        notice_ref = f"RA-{secrets.token_hex(4).upper()}"
        is_standalone = True

    doc = payload.model_dump()
    doc.update({
        "notice_ref": notice_ref,
        "is_standalone": is_standalone,
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
                    {"notice": notice_ref, "standalone": is_standalone})
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
async def list_reverse_auctions(admin=Depends(require_role("admin", "reviewer", "auditor")),
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
            await _stamp_outcome(out, a, vendor["id"])
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
        await _stamp_outcome(out, a, vendor["id"])
        rows.append(out); seen.add(out["id"])
    # #60 — also match auctions the vendor joined via the public register link
    # (reverse_auction_participants). Without this a vendor who registered for
    # a live auction could not find it on /vendor/auctions to place a bid.
    async for part in db.reverse_auction_participants.find(
        {"vendor_id": vendor["id"]}
    ).limit(100):
        aid = part.get("auction_id")
        if not aid or str(aid) in seen:
            continue
        try:
            a = await db.reverse_auctions.find_one({"_id": ObjectId(str(aid))})
        except Exception:
            a = None
        if not a:
            continue
        out = _out_auction(a)
        out["why"] = "You registered for this auction"
        await _stamp_outcome(out, a, vendor["id"])
        rows.append(out); seen.add(out["id"])
    return {"items": rows, "count": len(rows)}


@router.get("/{aid}")
async def get_reverse_auction_admin(aid: str, admin=Depends(require_role("admin", "reviewer", "auditor"))):
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
    try:
        await _append_auction_event(aid, "start", {"end_at": end, "participants": n})
    except Exception:
        pass
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
    winner = await _close_auction_core(a, admin.get("email"))
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
    # v53h — auctions closed before v53b stored no winner email; backfill it
    # from the participant record so the created bid is complete (else the
    # vendor pipeline notifications have nobody to address).
    if not winner.get("vendor_email"):
        _p = await db.reverse_auction_participants.find_one(
            {"auction_id": aid, "vendor_id": winner.get("vendor_id")})
        if _p and _p.get("vendor_email"):
            winner["vendor_email"] = _p["vendor_email"]
    if a.get("awarded_bid_id"):
        return {"ok": True, "already_awarded": True, "bid_id": a["awarded_bid_id"]}
    existing = await db.bids.find_one({"auction_id": aid})
    if existing:
        bid_id = str(existing["_id"])
        await db.reverse_auctions.update_one(
            {"_id": ObjectId(aid)}, {"$set": {"awarded_bid_id": bid_id}})
        return {"ok": True, "already_awarded": True, "bid_id": bid_id}
    bid_ref = f"BID-AUC-{aid[-6:].upper()}"
    # v53f — zero-EMD logic: an auction award collects no EMD, so no money is
    # held in escrow and there is nothing for an escrow officer (institution)
    # or escrow agent (staff) to sign off. Auto-clear the escrow step with
    # system-stamped history and land the bid at escrow_accepted (next
    # action: admin flags to certifier). EMD-bearing bids keep the manual
    # escrow step untouched.
    emd_due = float(a.get("emd_due_amount") or 0)
    skip_escrow = emd_due <= 0
    initial_status = "escrow_accepted" if skip_escrow else "emd_paid"
    bid = {
        "bid_ref": bid_ref,
        "notice_ref": a.get("notice_ref"),
        "vendor_id": winner["vendor_id"],
        "vendor_email": winner.get("vendor_email"),
        "company_name": winner.get("company_name"),
        "status": initial_status,
        "price_amount": winner.get("winning_price"),
        "price_currency": a.get("currency", "USD"),
        "source": "reverse_auction",
        "auction_id": aid,
        "created_at": now_iso(),
        "created_by_email": admin.get("email"),
    }
    if skip_escrow:
        bid["escrow_auto_cleared"] = True
        bid["escrow_accepted_at"] = now_iso()
        bid["workflow_history"] = [
            {"role": "system", "action": "emd_paid", "from_status": None,
             "to_status": "emd_paid",
             "notes": "Auto-cleared: no EMD due on this bid (auction award).",
             "by": "system", "at": now_iso()},
            {"role": "system", "action": "escrow_accepted",
             "from_status": "emd_paid", "to_status": "escrow_accepted",
             "notes": "Auto-cleared: no EMD held, so no escrow sign-off is required.",
             "by": "system", "at": now_iso()},
        ]
    res = await db.bids.insert_one(bid)
    bid_id = str(res.inserted_id)
    await db.reverse_auctions.update_one(
        {"_id": ObjectId(aid)},
        {"$set": {"awarded_bid_id": bid_id, "awarded_at": now_iso(),
                   "awarded_by": admin.get("email")}})
    # Notify whoever owns the step we landed on: escrow agent when EMD is
    # due, otherwise straight to the admin/tender desk.
    try:
        bid["id"] = bid_id
        await notify_bid_transition(bid, initial_status)
    except Exception:
        pass
    await audit_log("reverse_auction.award", admin, "auction", aid,
                    {"bid_id": bid_id, "bid_ref": bid_ref,
                     "winner": winner.get("company_name"),
                     "winning_price": winner.get("winning_price"),
                     "escrow_auto_cleared": skip_escrow})
    # v53i — for auctions closed before v53i the loser/invitee fan-out never
    # ran. Running it here on award means a historical auction's non-winners
    # still receive a clean "auction awarded to another bidder" mail, and the
    # specific gap the user reported — invitees who never registered got no
    # mail at all — is backfilled at award time.
    try:
        cur = a.get("currency", "USD")
        money = (f"{cur} {winner.get('winning_price'):,.0f}"
                 if winner.get("winning_price") else "—")
        title = a.get("title") or aid
        ref = a.get("notice_ref") or ""
        subject = f"Reverse auction awarded — {title}"
        body_loser = email_wrap("Reverse auction awarded",
            f"<p><strong>{title}</strong> ({ref}) has been awarded to another "
            f"bidder at <strong>{money}</strong>. Thank you for participating — "
            f"watch the supplier portal for future rounds.</p>")
        body_invited = email_wrap("Reverse auction awarded",
            f"<p>You were invited to <strong>{title}</strong> ({ref}) but did "
            f"not register for the round. The auction has now been awarded to "
            f"another bidder at <strong>{money}</strong>. The invitation stays "
            f"on your Reverse auctions page for reference; watch there for "
            f"future rounds.</p>")
        participant_emails = set()
        async for lp in db.reverse_auction_participants.find(
                {"auction_id": aid, "vendor_id": {"$ne": winner["vendor_id"]}}):
            if lp.get("vendor_email"):
                participant_emails.add(lp["vendor_email"].lower())
                await send_email(lp["vendor_email"], subject, body_loser)
        # Winner email too so participant_emails is complete for dedup below
        if winner.get("vendor_email"):
            participant_emails.add(winner["vendor_email"].lower())
        async for inv in db.reverse_auction_invitations.find({"auction_id": aid}):
            em = (inv.get("email") or "").lower()
            if not em or em in participant_emails:
                continue
            await send_email(em, subject, body_invited)
    except Exception:
        pass  # email failures must never block the award itself
    return {"ok": True, "bid_id": bid_id, "bid_ref": bid_ref,
            "status": initial_status,
            "next_step": ("Bid created at escrow_accepted (no EMD — escrow "
                          "auto-cleared) — flag it to the certifier in Bidding Ops."
                          if skip_escrow else
                          "Bid created at emd_paid — continue in Bidding Ops.")}


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
    try:
        await _place_bid_inner(a, vendor["id"], float(payload.price))
    except HTTPException as e:
        if e.status_code == 409:
            await _notify_duplicate_price(a, vendor, float(payload.price))
        raise
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
    # v53h — once the admin has awarded, tell the WINNING vendor the bid ref
    # so the room can deep-link to My bids. Only the winner sees this.
    try:
        a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)},
                                               {"winner": 1, "awarded_bid_id": 1})
        w = (a or {}).get("winner") or {}
        if w.get("vendor_id") == vendor["id"] and (a or {}).get("awarded_bid_id"):
            bid = await db.bids.find_one({"_id": ObjectId(a["awarded_bid_id"])},
                                         {"bid_ref": 1})
            state["me"]["awarded_bid_id"] = a["awarded_bid_id"]
            state["me"]["awarded_bid_ref"] = (bid or {}).get("bid_ref")
    except Exception:
        pass
    # v53j — surface the vendor's own invite token (if they have one) so the
    # auction room can offer "Decline with reason" to the right token.
    try:
        inv = await db.reverse_auction_invitations.find_one(
            {"auction_id": aid,
             "email": (vendor.get("email") or "").lower()},
            {"token": 1, "status": 1, "decline_reason": 1})
        if inv:
            state["me"]["invite_token"] = inv.get("token")
            state["me"]["invite_status"] = inv.get("status")
            state["me"]["decline_reason"] = inv.get("decline_reason")
    except Exception:
        pass
    return state


# ---------- Public discovery / live transport (v57e) ------------------

@router.get("/public/list")
async def public_list_auctions(status: Optional[str] = None, limit: int = 100):
    """PUBLIC — anonymized auction cards for landing-page discovery.
    status: live | upcoming | closed | awarded (omit = live + upcoming + closed).
    Winner company is only ever present when the award has been PUBLISHED."""
    q: dict = {}
    if status == "live":
        q["status"] = "live"
    elif status == "upcoming":
        q["status"] = "draft"
    elif status in ("closed", "awarded"):
        q["status"] = "closed"
    cards = []
    async for a in db.reverse_auctions.find(q).sort("created_at", -1)\
                     .limit(min(int(limit), 200)):
        card = await _public_card(a)
        if status == "awarded" and card["award_status"] != "awarded_published":
            continue
        if status == "closed" and card["award_status"] == "awarded_published":
            continue
        cards.append(card)
    return {"items": cards, "count": len(cards)}


@router.get("/{aid}/events")
async def public_auction_events(aid: str, limit: int = 200):
    """PUBLIC — SHA-256 hash-chained timeline of masked auction events."""
    evs = []
    async for e in db.reverse_auction_events.find({"auction_id": aid})\
                     .sort("seq", 1).limit(min(int(limit), 500)):
        evs.append({
            "seq": e.get("seq"),
            "kind": e.get("kind"),
            "data": e.get("data"),
            "at": e.get("at"),
            "hash": e.get("current_hash"),
            "previous_hash": e.get("previous_hash"),
        })
    return {"items": evs, "count": len(evs)}


class HeartbeatIn(BaseModel):
    viewer_id: str = Field(min_length=6, max_length=64)


@router.post("/{aid}/heartbeat")
async def auction_heartbeat(aid: str, payload: HeartbeatIn):
    """PUBLIC — anonymous presence ping (no identity). Powers the viewer count."""
    await db.reverse_auction_viewers.update_one(
        {"auction_id": aid, "viewer_id": payload.viewer_id},
        {"$set": {"last_seen": _now().isoformat()}}, upsert=True)
    return {"ok": True, "viewer_count": await _active_viewers(aid)}


@router.get("/{aid}/stream")
async def stream_auction_state(aid: str, request: Request):
    """PUBLIC — Server-Sent Events stream of masked live state. The frontend
    falls back to polling /state if SSE is unavailable. Bounded per-connection
    (NOT a perpetual server loop): ends on client disconnect, once the auction
    is closed, or after a hard cap."""
    async def gen():
        for _ in range(900):  # ~30 min hard cap at 2s cadence
            if await request.is_disconnected():
                break
            try:
                s = await _public_state(aid)
            except HTTPException:
                yield f"event: gone\ndata: {json.dumps({'detail': 'Auction not found'})}\n\n"
                break
            yield f"data: {json.dumps(s, default=str)}\n\n"
            if s.get("status") == "closed":
                break
            await asyncio.sleep(2)
    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"})


@router.post("/{aid}/invite/{token}/resend")
async def resend_invite(aid: str, token: str,
                         admin=Depends(require_role("admin")),
                         origin_url: Optional[str] = None):
    """v53j — one-click resend for an existing invitation. Reuses the stored
    token (same join URL stays valid) and the default invite template."""
    a = await db.reverse_auctions.find_one({"_id": ObjectId(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Auction not found")
    inv = await db.reverse_auction_invitations.find_one(
        {"auction_id": aid, "token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    tpl = await db.auction_invite_templates.find_one({"is_default": True}) or {
        "subject": _DEFAULT_INVITE_SUBJECT, "body_html": _DEFAULT_INVITE_BODY,
    }
    invite_url = f"{(origin_url or '').rstrip('/')}/vendor/auction/invite/{token}"
    raw_body = tpl.get("body_html") or ""
    if "{{invite_url}}" not in raw_body:
        raw_body = raw_body + (
            f'<p style="margin-top:16px"><a href="{{{{invite_url}}}}" '
            f'style="display:inline-block;padding:10px 18px;background:#0F3B2E;'
            f'color:#ffffff;text-decoration:none;font-weight:600;'
            f'letter-spacing:0.5px;text-transform:uppercase;font-size:12px;">'
            f'Join the auction</a></p>'
            f'<p style="font-size:12px;color:#64748B">Or paste this link into '
            f'your browser: {{{{invite_url}}}}</p>')
    body_html = raw_body\
        .replace("{{invite_url}}", invite_url)\
        .replace("{{auction_title}}", a.get("title", ""))\
        .replace("{{notice_ref}}", a.get("notice_ref", ""))\
        .replace("{{vendor_email}}", inv["email"])\
        .replace("{{starting_price}}", str(a.get("starting_price", "")))\
        .replace("{{currency}}", a.get("currency", ""))\
        .replace("{{admin_note}}", inv.get("note") or "")
    subject = (tpl.get("subject") or f"Reminder: {a.get('title')}")\
        .replace("{{auction_title}}", a.get("title", ""))\
        .replace("{{notice_ref}}", a.get("notice_ref", ""))
    # Soft tag so the vendor sees this is a nudge, not a new invite.
    subject = f"Reminder — {subject}"
    wrapped = email_wrap(subject, body_html, "Join auction", invite_url)
    ok = await send_email(inv["email"], subject, wrapped)
    resent_count = int(inv.get("resent_count") or 0) + (1 if ok else 0)
    await db.reverse_auction_invitations.update_one(
        {"_id": inv["_id"]},
        {"$set": {"resent_at": now_iso(),
                   "resent_by": admin.get("email"),
                   "resent_count": resent_count}})
    await audit_log("reverse_auction.invite_resend", admin, "auction", aid,
                    {"email": inv["email"], "sent": ok})
    return {"ok": ok, "email": inv["email"], "resent_count": resent_count}


class DeclineIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


@router.post("/invite/decline/{token}")
async def decline_invite(token: str, payload: DeclineIn,
                           vendor=Depends(current_vendor)):
    """v53j — invited vendor can soft-decline an open invitation with a
    free-text reason. Admin sees the decline + reason on the auction
    detail panel. Captures soft-no feedback instead of silent no-shows."""
    inv = await db.reverse_auction_invitations.find_one({"token": token})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.get("email") and inv["email"].lower() != (vendor.get("email") or "").lower():
        raise HTTPException(status_code=403,
            detail=f"This invitation is for {inv['email']}. Sign in as that vendor first.")
    if inv.get("status") == "accepted":
        raise HTTPException(status_code=400,
            detail="You already joined this auction — leave it to the admin to close.")
    await db.reverse_auction_invitations.update_one(
        {"_id": inv["_id"]},
        {"$set": {"status": "declined",
                   "declined_at": now_iso(),
                   "decline_reason": payload.reason.strip()}})
    # Soft notification to admin so the reason is seen immediately.
    try:
        a = await db.reverse_auctions.find_one({"_id": ObjectId(inv["auction_id"])})
        title = (a or {}).get("title") or inv["auction_id"]
        ref = (a or {}).get("notice_ref") or ""
        await notify_role("admin",
            f"Reverse auction invite declined — {title}",
            email_wrap("Invitation declined",
                f"<p><strong>{inv['email']}</strong> declined the invite for "
                f"<strong>{title}</strong> ({ref}).</p>"
                f"<p><strong>Reason:</strong> {payload.reason.strip()}</p>"),
            related_type="auction", related_id=inv["auction_id"])
    except Exception:
        pass
    return {"ok": True, "status": "declined"}


@router.get("/awarded/list")
async def list_awarded_auctions(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """v53j — admin digest of all awarded reverse auctions with winner,
    saving %, pipeline stage. Powers the new 'Recently awarded' panel."""
    out = []
    async for a in db.reverse_auctions.find(
        {"status": "closed", "awarded_bid_id": {"$ne": None}}
    ).sort("awarded_at", -1).limit(200):
        aid = str(a["_id"])
        start = float(a.get("starting_price") or 0)
        final = float(a.get("current_price") or 0)
        saving_pct = ((start - final) / start * 100.0) if start > 0 else 0.0
        bid = None
        try:
            bid = await db.bids.find_one({"_id": ObjectId(a["awarded_bid_id"])})
        except Exception:
            pass
        w = a.get("winner") or {}
        out.append({
            "auction_id": aid,
            "title": a.get("title"),
            "notice_ref": a.get("notice_ref"),
            "currency": a.get("currency"),
            "starting_price": start,
            "winning_price": final,
            "saving_pct": round(saving_pct, 2),
            "winner_company": w.get("company_name"),
            "winner_email": w.get("vendor_email"),
            "closed_at": a.get("closed_at"),
            "awarded_at": a.get("awarded_at"),
            "awarded_bid_id": a.get("awarded_bid_id"),
            "bid_ref": (bid or {}).get("bid_ref"),
            "pipeline_stage": (bid or {}).get("status") or "unknown",
        })
    return {"items": out, "count": len(out)}


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
async def list_invite_templates(admin=Depends(require_role("admin", "reviewer", "auditor"))):
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
async def list_invitations(aid: str, admin=Depends(require_role("admin", "reviewer", "auditor"))):
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
