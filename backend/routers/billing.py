"""Wave 35 — Billing / Checkout via Stripe (Flow B, `sk_test_emergent`).

Sits on top of the Product Catalog:
  * `POST /api/v1/billing/checkout` — creates a Stripe Checkout session for a
    single catalog product (one-off or subscription depending on `pricing_model`).
  * `GET  /api/v1/billing/status/{session_id}` — polled by frontend.
  * `POST /api/webhook/stripe` — Stripe → us. Idempotent on `payment_status`.

Amounts and currency come from the catalog row — never trusted from the client.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timezone

from db import db
from models.base import BaseDocument, now_iso
from security import current_admin
from audit import audit_log

log = logging.getLogger("billing")
router = APIRouter(tags=["billing"])


# ---- Emergent-managed Stripe (Flow B) ------------------------------------

def _stripe_checkout():
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    return StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"),
                          webhook_url="")  # webhook URL is set per-request below


def _price_from_product(product: dict, quantity: int) -> tuple[float, str, str]:
    """Compute (amount, currency, cadence) from a catalog row.
    Returns amount as float, currency lower-cased, cadence for metadata."""
    pm = product.get("pricing_model", "fixed")
    curr = (product.get("currency") or "USD").lower()
    if pm == "fixed":
        amt = float(product.get("amount") or 0)
    elif pm == "range":
        amt = float(product.get("min_amount") or 0)
    elif pm == "monthly":
        amt = float(product.get("amount") or 0)
    elif pm == "annual":
        amt = float(product.get("amount") or 0)
    elif pm == "per_delegate":
        amt = float(product.get("amount") or 0) * max(1, int(quantity))
    elif pm == "per_user_monthly":
        amt = float(product.get("amount") or 0) * max(1, int(quantity))
    elif pm == "percentage":
        raise HTTPException(status_code=400,
            detail="Percentage-of-value products cannot be checked out directly — please request a quote.")
    elif pm == "cost_recovery":
        raise HTTPException(status_code=400,
            detail="Cost-recovery items require a quote before checkout.")
    elif pm == "package":
        amt = float(product.get("amount") or 0)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported pricing_model: {pm}")
    if amt <= 0:
        raise HTTPException(status_code=400,
            detail="Product has no priced amount set. Ask an admin to configure it.")
    return amt, curr, pm


class CheckoutRequest(BaseModel):
    product_code: str
    quantity: int = Field(1, ge=1, le=1000)
    origin_url: str
    # Optional currency override — only accepted if it matches product OR is one
    # of the platform-supported currencies. Amount stays server-authoritative.
    currency_override: Optional[str] = None


@router.post("/api/v1/billing/checkout")
async def create_checkout(req: CheckoutRequest, request: Request,
                            admin=Depends(current_admin)):
    product = await db.products.find_one({"code": req.product_code, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {req.product_code}")
    amount, currency, cadence = _price_from_product(product, req.quantity)
    if req.currency_override:
        # Whitelist we support at the payment layer
        if req.currency_override.upper() in {"USD", "GBP", "EUR", "KZT"}:
            currency = req.currency_override.lower()

    # Build Stripe checkout (Flow B, emergentintegrations)
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"),
                         webhook_url=webhook_url)
    ck_req = CheckoutSessionRequest(
        amount=float(amount),
        currency=currency,
        success_url=f"{req.origin_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.origin_url.rstrip('/')}/billing/cancel",
        metadata={
            "product_code": product["code"],
            "product_name": product["name"],
            "quantity": str(req.quantity),
            "buyer_email": admin.get("email", ""),
            "cadence": cadence,
        },
    )
    session = await sc.create_checkout_session(ck_req)

    # Insert payment_transactions BEFORE returning the URL
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "product_code": product["code"],
        "buyer_email": admin.get("email"),
        "amount": float(amount),
        "currency": currency,
        "quantity": req.quantity,
        "cadence": cadence,
        "status": "initiated",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    await audit_log("billing.checkout_init", admin, "product", product["code"],
                    {"amount": amount, "currency": currency, "session_id": session.session_id})
    return {"checkout_url": session.url, "session_id": session.session_id,
             "amount": amount, "currency": currency}


@router.get("/api/v1/billing/status/{session_id}")
async def get_status(session_id: str, request: Request):
    """Public — unauthenticated. Frontend polls this. Returns only the flags."""
    record = await db.payment_transactions.find_one({"session_id": session_id})
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Ask Stripe directly if we're still pending — webhook may be delayed.
    if record.get("payment_status") != "paid":
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout
            host_url = str(request.base_url)
            webhook_url = f"{host_url}api/webhook/stripe"
            sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"),
                                 webhook_url=webhook_url)
            status = await sc.get_checkout_status(session_id)
            if status.payment_status == "paid":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed",
                              "payment_status": "paid",
                              "updated_at": datetime.now(timezone.utc)}},
                )
                record = await db.payment_transactions.find_one({"session_id": session_id})
        except Exception as e:
            log.warning(f"stripe status polling failed: {e}")
    return {"session_id": record["session_id"],
             "status": record["status"],
             "payment_status": record["payment_status"],
             "amount": record.get("amount"),
             "currency": record.get("currency"),
             "product_code": record.get("product_code")}


@router.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Flow-B webhook — exact path required by emergentintegrations."""
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        host_url = str(request.base_url)
        webhook_url = f"{host_url}api/webhook/stripe"
        sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_emergent"),
                             webhook_url=webhook_url)
        event = await sc.handle_webhook(body, sig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid webhook: {e}")
    if event.session_id:
        # Idempotent: only advance if not already paid
        await db.payment_transactions.update_one(
            {"session_id": event.session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed" if event.payment_status == "paid" else event.payment_status,
                      "payment_status": event.payment_status,
                      "updated_at": datetime.now(timezone.utc)}},
        )
    return {"status": "ok"}


# ---- Admin: transaction list --------------------------------------------

@router.get("/api/v1/billing/transactions")
async def list_transactions(admin=Depends(current_admin), limit: int = 50):
    docs = await db.payment_transactions.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        for k in ("created_at", "updated_at"):
            v = d.get(k)
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        out.append(d)
    return {"items": out, "count": len(out)}
