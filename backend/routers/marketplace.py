"""v61a — Supplier Marketplace: product catalogues sold by timed auction, best offer or fixed price.

Flow: supplier lists products (draft) -> submits (listing fee via fee rules) -> admin approves (can waive
the sale fee) -> live -> bids / offers / buy-now -> order -> buyer pays PMC by Stripe link ->
PMC keeps its sale fee and pays the seller's net amount to the seller's bank account (payout ledger).
"""
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import now_iso
from routers.growth import charge_or_pass
from routers.payments_extra import _checkout, _site, _sync_status
from routers.vendor_auth import current_vendor
from security import current_admin, require_csrf, require_role

router = APIRouter(prefix="/api/v1/market", tags=["marketplace"])
STAFF = ("super_admin", "admin", "reviewer")


async def _seller(request: Request) -> dict:
    v = await current_vendor(request)
    await require_csrf(request)
    return v


def _oid(x: str) -> ObjectId:
    if not ObjectId.is_valid(x):
        raise HTTPException(status_code=404, detail="Not found")
    return ObjectId(x)


def _out(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    if isinstance(d.get("listing_id"), ObjectId):
        d["listing_id"] = str(d["listing_id"])
    return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ListingIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=6000)
    category: str = Field(default="", max_length=120)
    quantity: float = Field(default=1, gt=0)
    unit: str = Field(default="lot", max_length=30)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    location: str = Field(default="", max_length=200)
    country_code: str = Field(default="", max_length=2)
    state_code: str = Field(default="", max_length=20)
    state_name: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=120)
    zip: str = Field(default="", max_length=20)
    image_url: str = Field(default="", max_length=600)
    photos: list[str] = Field(default_factory=list, max_length=12)
    documents: list[dict] = Field(default_factory=list, max_length=6)
    sale_modes: list[Literal["auction", "best_offer", "fixed"]] = Field(min_length=1)
    start_price: Optional[float] = Field(default=None, ge=0)
    reserve_price: Optional[float] = Field(default=None, ge=0)
    min_increment: float = Field(default=1, gt=0)
    buy_now_price: Optional[float] = Field(default=None, gt=0)
    closes_at: Optional[str] = None
    eligibility: Literal["verified_buyers", "any_verified"] = "verified_buyers"


async def _bidder(request: Request) -> dict:
    """A verified supplier (vendor session) or a verified buyer organisation user (admin-console session)."""
    if not (request.cookies or {}):
        raise HTTPException(status_code=401, detail="Please sign in as a verified buyer or supplier to take part")
    await require_csrf(request)
    try:
        v = await current_vendor(request)
        if (v.get("kyc_status") or "verified") != "verified":
            raise HTTPException(status_code=403, detail="Your supplier account must be verified to bid")
        return {"kind": "supplier", "id": v["id"], "name": v.get("company_name") or v.get("email"), "email": v.get("email")}
    except HTTPException as e:
        if e.status_code == 403:
            raise
    try:
        a = await current_admin(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Please sign in as a verified buyer or supplier to take part")
    tid = a.get("tenant_id")
    t = await db.tenants.find_one({"_id": ObjectId(str(tid))}) if ObjectId.is_valid(str(tid)) else await db.tenants.find_one({"code": tid})
    if not t or not t.get("is_active", True) or t.get("source") != "buyer_application":
        raise HTTPException(status_code=403, detail="Only verified buyer organisations and suppliers can bid")
    return {"kind": "buyer", "id": a["id"], "name": t.get("name"), "email": a.get("email")}


async def _settings() -> dict:
    s = await db.mkt_settings.find_one({"_id": "default"}) or {}
    return {"fee_type": s.get("fee_type", "percent"), "fee_value": float(s.get("fee_value", 0)), "charge": bool(s.get("charge", True))}


def _fee(amount: float, s: dict, waived: bool) -> float:
    if waived or not s["charge"]:
        return 0.0
    return round(amount * s["fee_value"] / 100, 2) if s["fee_type"] == "percent" else min(round(s["fee_value"], 2), amount)


async def _close_if_due(lst: dict) -> dict:
    """Timed auctions settle on first read after closing: highest bid >= reserve wins."""
    if lst.get("status") != "live" or not lst.get("closes_at") or lst["closes_at"] > _now() or "auction" not in lst["sale_modes"]:
        return lst
    top = await db.mkt_bids.find_one({"listing_id": lst["_id"], "kind": "bid"}, sort=[("amount", -1)])
    if top and top["amount"] >= (lst.get("reserve_price") or 0):
        await _make_order(lst, top["bidder"], top["amount"], "auction")
    else:
        await db.mkt_listings.update_one({"_id": lst["_id"]}, {"$set": {"status": "closed_unsold", "updated_at": now_iso()}})
    return await db.mkt_listings.find_one({"_id": lst["_id"]})


async def _make_order(lst: dict, bidder: dict, amount: float, via: str) -> dict:
    res = await db.mkt_listings.update_one({"_id": lst["_id"], "status": "live"}, {"$set": {"status": "sold", "updated_at": now_iso()}})
    if res.modified_count == 0:
        raise HTTPException(status_code=409, detail="This listing is no longer available")
    s = await _settings()
    fee = _fee(amount, s, lst.get("sale_fee_waived", False))
    doc = {"listing_id": lst["_id"], "title": lst["title"], "seller_id": lst["seller_id"], "seller_name": lst.get("seller_name"),
           "buyer": bidder, "amount": round(amount, 2), "currency": lst["currency"], "via": via, "pmc_fee": fee,
           "fee_rule": {**s, "waived": lst.get("sale_fee_waived", False)}, "seller_net": round(amount - fee, 2),
           "status": "awaiting_payment", "payout_status": "not_due", "created_at": now_iso()}
    r = await db.mkt_orders.insert_one(doc)
    doc["_id"] = r.inserted_id
    await db.mkt_bids.update_many({"listing_id": lst["_id"], "kind": "offer", "status": "open"}, {"$set": {"status": "declined"}})
    await audit_log("market.order", {"email": bidder.get("email"), "id": bidder["id"]}, "mkt_order", str(r.inserted_id),
                    {"amount": amount, "fee": fee, "via": via})
    return doc


def _public(lst: dict, top: Optional[float], n: int) -> dict:
    o = _out(lst)
    for k in ("reserve_price", "review_notes", "sale_fee_waived", "decided_by", "decided_at", "submitted_at"):
        o.pop(k, None)
    o["reserve_met"] = top is not None and top >= (lst.get("reserve_price") or 0)
    o.update({"top_bid": top, "bid_count": n})
    return o


async def _top(lid: ObjectId) -> tuple[Optional[float], int]:
    top = await db.mkt_bids.find_one({"listing_id": lid, "kind": "bid"}, sort=[("amount", -1)])
    return (top["amount"] if top else None), await db.mkt_bids.count_documents({"listing_id": lid, "kind": "bid"})


# ---------- seller ----------
@router.get("/mine")
async def my_listings(v=Depends(current_vendor)):
    items = []
    async for d in db.mkt_listings.find({"seller_id": v["id"]}).sort("created_at", -1).limit(300):
        d = await _close_if_due(d)
        top, n = await _top(d["_id"])
        o = _out(d)
        o.update({"top_bid": top, "bid_count": n,
                  "offers": [_out(b) for b in await db.mkt_bids.find({"listing_id": d["_id"], "kind": "offer", "status": "open"}).sort("amount", -1).to_list(50)]})
        items.append(o)
    orders = [_out(o) for o in await db.mkt_orders.find({"seller_id": v["id"]}).sort("created_at", -1).to_list(200)]
    return {"items": items, "orders": orders, "fee": await _settings()}


async def _clean(body: ListingIn, v: dict) -> dict:
    from routers.marketplace_media import check_media
    d = body.model_dump()
    d["documents"] = [{"id": str(x.get("id")), "name": str(x.get("name") or "Spec sheet")[:160]} for x in body.documents]
    await check_media(v["id"], body.photos, d["documents"])
    d["currency"] = body.currency.upper()
    if not await db.currencies.find_one({"code": d["currency"], "is_active": True}):
        raise HTTPException(status_code=400, detail="Please choose a currency from the list")
    if body.country_code:
        c = await db.masters_countries.find_one({"code": body.country_code.upper()})
        if not c:
            raise HTTPException(status_code=400, detail="Please choose a country from the list")
        d["country_code"] = c["code"]
        if body.zip and c.get("postal_code_regex") and not re.match(c["postal_code_regex"], body.zip.strip()):
            raise HTTPException(status_code=400, detail=f"ZIP / postal code should look like {c.get('postal_code_format') or 'the local format'}")
        d["location"] = ", ".join(x for x in (body.city, body.state_name, c["name"]) if x)
    return d


@router.post("/listings")
async def create_listing(body: ListingIn, v=Depends(_seller)):
    _validate(body)
    doc = {**(await _clean(body, v)), "seller_id": v["id"], "seller_name": v.get("company_name") or v.get("email"),
           "status": "draft", "created_at": now_iso(), "updated_at": now_iso()}
    r = await db.mkt_listings.insert_one(doc)
    return {"id": str(r.inserted_id), "status": "draft"}


def _validate(b: ListingIn) -> None:
    if "auction" in b.sale_modes and (b.start_price is None or not b.closes_at):
        raise HTTPException(status_code=400, detail="Timed auction needs a starting price and a closing date/time")
    if "best_offer" in b.sale_modes and not b.closes_at:
        raise HTTPException(status_code=400, detail="Best offer needs a deadline (closing date/time)")
    if "fixed" in b.sale_modes and not b.buy_now_price:
        raise HTTPException(status_code=400, detail="Fixed price needs a buy-now price")
    if "auction" in b.sale_modes and b.reserve_price is not None and b.start_price is not None and b.reserve_price < b.start_price:
        raise HTTPException(status_code=400, detail="The reserve price cannot be lower than the starting price")
    if b.closes_at and b.closes_at <= _now():
        raise HTTPException(status_code=400, detail="The closing date/time must be in the future")


async def _own(lid: str, v: dict) -> dict:
    d = await db.mkt_listings.find_one({"_id": _oid(lid), "seller_id": v["id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Listing not found")
    return d


@router.put("/listings/{lid}")
async def update_listing(lid: str, body: ListingIn, v=Depends(_seller)):
    d = await _own(lid, v)
    if d["status"] not in ("draft", "rejected"):
        raise HTTPException(status_code=409, detail="Only draft or rejected listings can be edited")
    _validate(body)
    await db.mkt_listings.update_one({"_id": d["_id"]}, {"$set": {**(await _clean(body, v)), "status": "draft",
                                                                   "needs_details": False, "updated_at": now_iso()}})
    return {"ok": True}


@router.post("/listings/{lid}/submit")
async def submit_listing(lid: str, v=Depends(_seller)):
    d = await _own(lid, v)
    if d["status"] not in ("draft", "rejected"):
        raise HTTPException(status_code=409, detail="Already submitted")
    if d.get("needs_details"):
        raise HTTPException(status_code=400, detail="Open Edit to choose how to sell this product and set its price before submitting")
    vd = await db.vendors.find_one({"_id": ObjectId(v["id"])})
    await charge_or_pass({**v, **(vd or {}), "id": v["id"]}, "mkt_listing_fee", f"mkt-{lid}", f"Marketplace listing: {d['title'][:60]}")
    await db.mkt_listings.update_one({"_id": d["_id"]}, {"$set": {"status": "pending", "submitted_at": now_iso()}})
    return {"ok": True, "status": "pending"}


@router.post("/listings/{lid}/withdraw")
async def withdraw_listing(lid: str, v=Depends(_seller)):
    d = await _own(lid, v)
    if d["status"] not in ("draft", "pending", "rejected", "live") or await db.mkt_bids.count_documents({"listing_id": d["_id"], "kind": "bid"}):
        raise HTTPException(status_code=409, detail="Listings with bids or sales cannot be withdrawn")
    await db.mkt_listings.update_one({"_id": d["_id"]}, {"$set": {"status": "withdrawn", "updated_at": now_iso()}})
    return {"ok": True}


@router.post("/offers/{bid_id}/accept")
async def accept_offer(bid_id: str, v=Depends(_seller)):
    b = await db.mkt_bids.find_one({"_id": _oid(bid_id), "kind": "offer", "status": "open"})
    lst = b and await db.mkt_listings.find_one({"_id": b["listing_id"], "seller_id": v["id"]})
    if not lst:
        raise HTTPException(status_code=404, detail="Offer not found")
    order = await _make_order(lst, b["bidder"], b["amount"], "best_offer")
    await db.mkt_bids.update_one({"_id": b["_id"]}, {"$set": {"status": "accepted"}})
    await db.mkt_bids.update_many({"listing_id": lst["_id"], "kind": "offer", "status": "open"}, {"$set": {"status": "declined"}})
    return _out(order)


# ---------- public browse + bidding ----------
@router.get("/listings")
async def browse(q: str = "", category: str = ""):
    f = {"status": "live"}
    if category:
        f["category"] = category
    if q:
        f["title"] = {"$regex": q[:60], "$options": "i"}
    out = []
    async for d in db.mkt_listings.find(f).sort("closes_at", 1).limit(200):
        d = await _close_if_due(d)
        if d["status"] == "live" and not (d.get("closes_at") and d["closes_at"] <= _now() and "fixed" not in d["sale_modes"]):
            out.append(_public(d, *(await _top(d["_id"]))))
    return {"items": out}


@router.get("/listings/{lid}")
async def listing_detail(lid: str):
    d = await db.mkt_listings.find_one({"_id": _oid(lid), "status": {"$in": ["live", "sold", "closed_unsold"]}})
    if not d:
        raise HTTPException(status_code=404, detail="Listing not found")
    d = await _close_if_due(d)
    return _public(d, *(await _top(d["_id"])))


class BidIn(BaseModel):
    amount: float = Field(gt=0)
    note: str = Field(default="", max_length=500)


async def _live_for(lid: str, who: dict, mode: str) -> dict:
    d = await db.mkt_listings.find_one({"_id": _oid(lid)})
    d = d and await _close_if_due(d)
    if not d or d["status"] != "live":
        raise HTTPException(status_code=409, detail="This listing is not open")
    if mode not in d["sale_modes"]:
        raise HTTPException(status_code=400, detail="The seller has not enabled this way of buying")
    if mode == "best_offer" and d.get("closes_at") and d["closes_at"] <= _now():
        raise HTTPException(status_code=409, detail="The deadline for offers has passed")
    if d.get("eligibility") == "verified_buyers" and who["kind"] != "buyer":
        raise HTTPException(status_code=403, detail="The seller only accepts verified buyer organisations")
    if who["kind"] == "supplier" and who["id"] == d["seller_id"]:
        raise HTTPException(status_code=403, detail="You cannot bid on your own listing")
    return d


@router.post("/listings/{lid}/bid")
async def place_bid(lid: str, body: BidIn, request: Request):
    who = await _bidder(request)
    d = await _live_for(lid, who, "auction")
    top, _ = await _top(d["_id"])
    floor = (top + d.get("min_increment", 1)) if top is not None else (d.get("start_price") or 0)
    if body.amount < floor:
        raise HTTPException(status_code=400, detail=f"Your bid must be at least {d['currency']} {floor:,.2f}")
    await db.mkt_bids.insert_one({"listing_id": d["_id"], "kind": "bid", "amount": body.amount, "bidder": who, "created_at": now_iso()})
    return {"ok": True, "top_bid": body.amount}


@router.post("/listings/{lid}/offer")
async def place_offer(lid: str, body: BidIn, request: Request):
    who = await _bidder(request)
    d = await _live_for(lid, who, "best_offer")
    await db.mkt_bids.update_many({"listing_id": d["_id"], "kind": "offer", "status": "open", "bidder.id": who["id"]}, {"$set": {"status": "replaced"}})
    await db.mkt_bids.insert_one({"listing_id": d["_id"], "kind": "offer", "status": "open", "amount": body.amount,
                                  "note": body.note, "bidder": who, "created_at": now_iso()})
    return {"ok": True}


@router.post("/listings/{lid}/buy")
async def buy_now(lid: str, request: Request):
    who = await _bidder(request)
    d = await _live_for(lid, who, "fixed")
    return _out(await _make_order(d, who, float(d["buy_now_price"]), "fixed"))


@router.get("/my-purchases")
async def my_purchases(request: Request):
    who = await _bidder(request)
    orders = [_out(o) for o in await db.mkt_orders.find({"buyer.id": who["id"]}).sort("created_at", -1).to_list(200)]
    bids = [_out(b) for b in await db.mkt_bids.find({"bidder.id": who["id"]}).sort("created_at", -1).to_list(200)]
    for x in orders + bids:
        x["listing_id"] = str(x["listing_id"])
    return {"orders": orders, "bids": bids, "me": who}


@router.post("/orders/{oid}/pay")
async def pay_order(oid: str, request: Request):
    who = await _bidder(request)
    o = await db.mkt_orders.find_one({"_id": _oid(oid), "buyer.id": who["id"]})
    if not o or o["status"] != "awaiting_payment":
        raise HTTPException(status_code=409, detail="This order is not awaiting payment")
    origin = request.headers.get("origin") or _site()
    link = await _checkout(o["amount"], o["currency"], "marketplace_order", f"/market/purchases?order={oid}", "/market/purchases",
                           origin, {"order_id": oid}, {"order_id": oid, "buyer": who["email"]})
    await db.mkt_orders.update_one({"_id": o["_id"]}, {"$set": {"session_id": link["session_id"]}})
    return link


@router.get("/orders/{oid}/status")
async def order_status(oid: str, request: Request):
    who = await _bidder(request)
    o = await db.mkt_orders.find_one({"_id": _oid(oid), "buyer.id": who["id"]})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.get("session_id") and o["status"] == "awaiting_payment":
        st = await _sync_status(o["session_id"])
        if st.get("payment_status") == "paid":
            await db.mkt_orders.update_one({"_id": o["_id"]}, {"$set": {"status": "paid", "paid_at": now_iso(), "payout_status": "due"}})
    return _out(await db.mkt_orders.find_one({"_id": o["_id"]}))


# ---------- admin ----------
@router.get("/admin/listings")
async def admin_listings(status: str = "pending", admin=Depends(require_role(*STAFF))):
    f = {} if status == "all" else {"status": status}
    return {"items": [_out(d) for d in await db.mkt_listings.find(f).sort("created_at", -1).to_list(500)]}


class DecisionIn(BaseModel):
    action: Literal["approve", "reject"]
    waive_sale_fee: bool = False
    notes: str = Field(default="", max_length=1000)


@router.post("/admin/listings/{lid}/decision")
async def admin_decide(lid: str, body: DecisionIn, admin=Depends(require_role(*STAFF))):
    d = await db.mkt_listings.find_one({"_id": _oid(lid), "status": "pending"})
    if not d:
        raise HTTPException(status_code=409, detail="Only pending listings can be decided")
    upd = {"status": "live" if body.action == "approve" else "rejected", "review_notes": body.notes,
           "sale_fee_waived": body.waive_sale_fee, "decided_by": admin["email"], "decided_at": now_iso()}
    await db.mkt_listings.update_one({"_id": d["_id"]}, {"$set": upd})
    await audit_log("market.listing.decide", admin, "mkt_listing", lid, upd)
    return {"ok": True, **upd}


class SettingsIn(BaseModel):
    fee_type: Literal["percent", "fixed"]
    fee_value: float = Field(ge=0)
    charge: bool = True


@router.get("/admin/settings")
async def get_settings(admin=Depends(require_role(*STAFF))):
    return await _settings()


@router.put("/admin/settings")
async def put_settings(body: SettingsIn, admin=Depends(require_role("super_admin", "admin"))):
    await db.mkt_settings.update_one({"_id": "default"}, {"$set": {**body.model_dump(), "updated_by": admin["email"], "updated_at": now_iso()}}, upsert=True)
    await audit_log("market.settings", admin, "mkt_settings", "default", body.model_dump())
    return await _settings()


@router.get("/admin/orders")
async def admin_orders(admin=Depends(require_role(*STAFF))):
    from routers.consortium_split import _bank
    out = []
    for o in await db.mkt_orders.find({}).sort("created_at", -1).to_list(500):
        v = await db.vendors.find_one({"_id": ObjectId(o["seller_id"])}, {"email": 1}) if ObjectId.is_valid(o["seller_id"]) else None
        x = _out(o)
        x["seller_bank"] = await _bank(o["seller_id"], (v or {}).get("email"))
        out.append(x)
    return {"items": out}


class PayoutIn(BaseModel):
    reference: str = Field(min_length=2, max_length=120)


@router.post("/admin/orders/{oid}/payout")
async def mark_payout(oid: str, body: PayoutIn, admin=Depends(require_role("super_admin", "admin"))):
    r = await db.mkt_orders.update_one({"_id": _oid(oid), "status": "paid", "payout_status": "due"},
                                       {"$set": {"payout_status": "sent", "payout_reference": body.reference,
                                                 "payout_by": admin["email"], "payout_at": now_iso()}})
    if not r.modified_count:
        raise HTTPException(status_code=409, detail="Payout is only possible for paid orders that are due")
    await audit_log("market.payout", admin, "mkt_order", oid, body.model_dump())
    return {"ok": True}


async def ensure_indexes():
    await db.mkt_listings.create_index([("status", 1), ("closes_at", 1)])
    await db.mkt_listings.create_index("seller_id")
    await db.mkt_bids.create_index([("listing_id", 1), ("kind", 1), ("amount", -1)])
    await db.mkt_orders.create_index("seller_id")
    await db.mkt_orders.create_index("buyer.id")
