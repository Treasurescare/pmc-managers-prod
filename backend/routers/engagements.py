"""Wave 38 — Engagement / Quote pipeline.

Every "Request quote" click from the client/supplier purchase surfaces lands
here as an engagement in status=`quote_requested`. Admin quotes an amount,
generates a Stripe Checkout URL (via billing.py), the buyer pays, and the
engagement moves to status=`paid`. Full audit trail on every transition.

State machine:
    quote_requested → quoted → invoiced → paid
                    ↘ cancelled
"""
from datetime import datetime, timezone
from typing import Optional, Literal, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import current_admin
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/engagements", tags=["engagements"])


STATUS_QUOTE     = "quote_requested"
STATUS_QUOTED    = "quoted"
STATUS_INVOICED  = "invoiced"
STATUS_PAID      = "paid"
STATUS_CANCELLED = "cancelled"
STATUSES = [STATUS_QUOTE, STATUS_QUOTED, STATUS_INVOICED, STATUS_PAID, STATUS_CANCELLED]


class QuoteRequestIn(BaseModel):
    product_code: str
    quantity: int = Field(1, ge=1, le=1000)
    buyer_email: Optional[EmailStr] = None
    buyer_company: Optional[str] = None
    buyer_notes: Optional[str] = None
    project_ref: Optional[str] = None    # optional link to notice / project


class QuoteSetIn(BaseModel):
    quoted_amount: float = Field(gt=0)
    quoted_currency: str = "USD"
    admin_notes: Optional[str] = None
    valid_until: Optional[str] = None    # ISO date


class CheckoutIn(BaseModel):
    origin_url: str


def _out(doc: dict) -> dict:
    d = BaseDocument.out(doc)
    return d


async def _resolve_buyer(request: Request, fallback_email: Optional[str]) -> tuple[str, str]:
    """Best-effort — same policy as billing checkout."""
    try:
        u = await current_admin(request)
        if u:
            return u.get("email"), "admin"
    except Exception:
        pass
    try:
        v = await current_vendor(request)
        if v:
            return v.get("email"), "vendor"
    except Exception:
        pass
    return fallback_email or "anonymous@pmcmanagers.com", "anonymous"


@router.post("/quote-request")
async def quote_request(payload: QuoteRequestIn, request: Request):
    """Public — client/supplier hits this from the purchase surface.
    Creates the engagement in `quote_requested` for admin to price."""
    product = await db.products.find_one({"code": payload.product_code, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {payload.product_code}")
    email, role = await _resolve_buyer(request, payload.buyer_email)
    doc = {
        "product_code":     product["code"],
        "product_name":     product["name"],
        "product_side":     product.get("side"),
        "product_currency": product.get("currency"),
        "quantity":         payload.quantity,
        "buyer_email":      email,
        "buyer_role":       role,
        "buyer_company":    payload.buyer_company,
        "buyer_notes":      payload.buyer_notes,
        "project_ref":      payload.project_ref,
        "status":           STATUS_QUOTE,
        "quoted_amount":    None,
        "quoted_currency":  None,
        "checkout_session_id": None,
        "paid_at":          None,
        "history":          [{"at": now_iso(), "by": email,
                              "event": "quote_requested"}],
        "created_at":       now_iso(),
        "updated_at":       now_iso(),
    }
    r = await db.engagements.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log("engagement.quote_request",
                    {"email": email, "role": role},
                    "product", product["code"],
                    {"engagement_id": str(r.inserted_id),
                     "quantity": payload.quantity})
    return _out(doc)


@router.get("")
async def list_engagements(status: Optional[str] = None,
                            admin=Depends(current_admin)):
    q: dict = {}
    if status and status in STATUSES:
        q["status"] = status
    docs = await db.engagements.find(q).sort("created_at", -1).to_list(500)
    return {"items": [_out(d) for d in docs], "count": len(docs)}


@router.get("/{eid}")
async def get_engagement(eid: str, admin=Depends(current_admin)):
    if not ObjectId.is_valid(eid):
        raise HTTPException(status_code=400, detail="Invalid engagement id")
    d = await db.engagements.find_one({"_id": ObjectId(eid)})
    if not d:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return _out(d)


@router.patch("/{eid}/quote")
async def set_quote(eid: str, payload: QuoteSetIn, admin=Depends(current_admin)):
    """Admin sets the quoted amount + currency. Moves engagement to `quoted`."""
    if not ObjectId.is_valid(eid):
        raise HTTPException(status_code=400, detail="Invalid engagement id")
    doc = await db.engagements.find_one({"_id": ObjectId(eid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if doc["status"] not in (STATUS_QUOTE, STATUS_QUOTED):
        raise HTTPException(status_code=409,
            detail=f"Cannot quote an engagement in status={doc['status']}")
    entry = {"at": now_iso(), "by": admin["email"], "event": "quoted",
             "amount": payload.quoted_amount, "currency": payload.quoted_currency,
             "notes": payload.admin_notes, "valid_until": payload.valid_until}
    await db.engagements.update_one(
        {"_id": ObjectId(eid)},
        {"$set": {"status": STATUS_QUOTED,
                    "quoted_amount": float(payload.quoted_amount),
                    "quoted_currency": payload.quoted_currency.upper(),
                    "quote_valid_until": payload.valid_until,
                    "admin_notes": payload.admin_notes,
                    "updated_at": now_iso()},
         "$push": {"history": entry}},
    )
    await audit_log("engagement.quoted", admin, "engagement", eid,
                    {"amount": payload.quoted_amount, "currency": payload.quoted_currency})
    return _out(await db.engagements.find_one({"_id": ObjectId(eid)}))


@router.post("/{eid}/checkout")
async def engagement_checkout(eid: str, payload: CheckoutIn, request: Request,
                                admin=Depends(current_admin)):
    """Admin generates a Stripe checkout URL for the buyer using the quoted amount.
    Marks engagement as `invoiced` once the session is created (still needs payment)."""
    if not ObjectId.is_valid(eid):
        raise HTTPException(status_code=400, detail="Invalid engagement id")
    doc = await db.engagements.find_one({"_id": ObjectId(eid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if doc["status"] != STATUS_QUOTED:
        raise HTTPException(status_code=409,
            detail=f"Engagement must be `quoted` before checkout — current={doc['status']}")
    import os
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    host = str(request.base_url)
    webhook_url = f"{host}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"),
                         webhook_url=webhook_url)
    ck = CheckoutSessionRequest(
        amount=float(doc["quoted_amount"]),
        currency=(doc["quoted_currency"] or "USD").lower(),
        success_url=f"{payload.origin_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{payload.origin_url.rstrip('/')}/billing/cancel",
        metadata={"engagement_id": eid, "product_code": doc["product_code"],
                   "buyer_email": doc.get("buyer_email", ""),
                   "kind": "engagement_invoice"},
    )
    session = await sc.create_checkout_session(ck)
    # Log payment_transactions same way as billing.py
    await db.payment_transactions.insert_one({
        "session_id":   session.session_id,
        "product_code": doc["product_code"],
        "buyer_email":  doc.get("buyer_email"),
        "buyer_role":   doc.get("buyer_role"),
        "amount":       float(doc["quoted_amount"]),
        "currency":     (doc["quoted_currency"] or "USD").lower(),
        "quantity":     doc.get("quantity", 1),
        "cadence":      "engagement_invoice",
        "engagement_id": eid,
        "status":       "initiated",
        "payment_status": "pending",
        "created_at":   datetime.now(timezone.utc),
        "updated_at":   datetime.now(timezone.utc),
    })
    entry = {"at": now_iso(), "by": admin["email"], "event": "invoiced",
             "session_id": session.session_id, "checkout_url": session.url}
    await db.engagements.update_one(
        {"_id": ObjectId(eid)},
        {"$set": {"status": STATUS_INVOICED,
                    "checkout_session_id": session.session_id,
                    "checkout_url": session.url,
                    "updated_at": now_iso()},
         "$push": {"history": entry}},
    )
    await audit_log("engagement.invoiced", admin, "engagement", eid,
                    {"session_id": session.session_id,
                     "amount": doc["quoted_amount"],
                     "currency": doc["quoted_currency"]})
    return {"checkout_url": session.url, "session_id": session.session_id,
             "engagement": _out(await db.engagements.find_one({"_id": ObjectId(eid)}))}


@router.post("/{eid}/cancel")
async def cancel_engagement(eid: str, admin=Depends(current_admin)):
    if not ObjectId.is_valid(eid):
        raise HTTPException(status_code=400, detail="Invalid engagement id")
    doc = await db.engagements.find_one({"_id": ObjectId(eid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if doc["status"] in (STATUS_PAID, STATUS_CANCELLED):
        raise HTTPException(status_code=409,
            detail=f"Cannot cancel an engagement in status={doc['status']}")
    entry = {"at": now_iso(), "by": admin["email"], "event": "cancelled"}
    await db.engagements.update_one(
        {"_id": ObjectId(eid)},
        {"$set": {"status": STATUS_CANCELLED, "updated_at": now_iso()},
         "$push": {"history": entry}},
    )
    await audit_log("engagement.cancelled", admin, "engagement", eid, {})
    return _out(await db.engagements.find_one({"_id": ObjectId(eid)}))
