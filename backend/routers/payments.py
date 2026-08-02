"""Stripe EMD Payments router (Flow B — emergentintegrations lib).

Vendor pays the EMD due on a bid via Stripe Checkout. On webhook success the
bid transitions from `emd_pending` to `emd_paid`, unlocking the sequential
Escrow → Admin → Certifier → Legal → Accounting → Committee pipeline.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from bson import ObjectId

from db import db
from models.emd_payment import EMDCheckoutIn, EMDRefundIn
from models.base import now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1", tags=["payments"])
log = logging.getLogger("payments")


def _stripe():
    """Lazy-import to keep dev startup resilient if key is missing."""
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    api_key = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
    return StripeCheckout, CheckoutSessionRequest, api_key


@router.post("/payments/emd/checkout")
async def create_emd_checkout(payload: EMDCheckoutIn, request: Request,
                              vendor=Depends(current_vendor)) -> dict:
    bid = await db.bids.find_one({"_id": ObjectId(payload.bid_id), "vendor_id": vendor["id"]})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.get("status") not in ("emd_pending", "submitted"):
        raise HTTPException(status_code=400, detail=f"EMD not payable at status {bid.get('status')}")
    amount = float(bid.get("emd_due_amount") or 0.0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="No EMD due on this bid")

    StripeCheckout, CheckoutSessionRequest, api_key = _stripe()
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    success_url = f"{payload.origin_url}/vendor/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{payload.origin_url}/vendor/payment/cancel?bid_id={payload.bid_id}"
    currency = (bid.get("emd_currency") or "USD").lower()

    req = CheckoutSessionRequest(
        amount=amount,
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"bid_id": payload.bid_id, "vendor_id": vendor["id"],
                  "notice_ref": bid.get("notice_ref", ""), "purpose": "emd"},
    )
    session = await checkout.create_checkout_session(req)

    # Persist transaction BEFORE redirect
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "bid_id": payload.bid_id,
        "vendor_id": vendor["id"],
        "notice_ref": bid.get("notice_ref"),
        "amount": amount, "currency": currency.upper(),
        "purpose": "emd",
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id, "amount": amount, "currency": currency.upper()}


@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str) -> dict:
    """Unauthenticated status probe (Stripe redirect target polls this)."""
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Webhook-fallback poll: ask Stripe directly if still pending
    if rec.get("payment_status") != "paid":
        try:
            StripeCheckout, _CS, api_key = _stripe()
            checkout = StripeCheckout(api_key=api_key, webhook_url="")
            s = await checkout.get_checkout_status(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await _mark_paid(session_id, s.payment_status or "paid")
                rec = await db.payment_transactions.find_one({"session_id": session_id})
        except Exception as e:
            log.warning(f"Status poll fallback failed: {e}")
    return {"session_id": rec["session_id"], "status": rec["status"],
            "payment_status": rec["payment_status"], "amount": rec.get("amount"),
            "currency": rec.get("currency"), "bid_id": rec.get("bid_id")}


async def _mark_paid(session_id: str, payment_status: str = "paid") -> None:
    """Idempotent — advances the bid to `emd_paid` only on first success."""
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
        {"$set": {"status": "completed", "payment_status": payment_status,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
    )
    if not tx:
        return  # already applied
    bid_id = tx.get("bid_id")
    if bid_id:
        await db.bids.update_one(
            {"_id": ObjectId(bid_id), "status": {"$in": ["emd_pending", "submitted"]}},
            {"$set": {"status": "emd_paid",
                      "emd_paid_amount": tx.get("amount"),
                      "emd_paid_at": now_iso()},
             "$push": {"workflow_history": {
                 "role": "system", "action": "emd_paid",
                 "from_status": "emd_pending", "to_status": "emd_paid",
                 "notes": f"Stripe session {session_id}", "by": "stripe.webhook",
                 "at": now_iso(),
             }}},
        )
        await audit_log("bid.emd_paid", None, "bid", bid_id,
                        {"session_id": session_id, "amount": tx.get("amount")})


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Flow B webhook path — MUST be /api/webhook/stripe per playbook."""
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    StripeCheckout, _CS, api_key = _stripe()
    checkout = StripeCheckout(api_key=api_key, webhook_url="")
    try:
        resp = await checkout.handle_webhook(body, sig)
    except Exception as e:
        log.warning(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    if resp and resp.payment_status == "paid":
        await _mark_paid(resp.session_id, resp.payment_status)
    return {"ok": True}


@router.post("/payments/emd/refund")
async def refund_emd(payload: EMDRefundIn,
                     admin=Depends(require_role("admin", "accounting"))) -> dict:
    """Admin/Accounting can refund the EMD when a bid is not awarded."""
    bid = await db.bids.find_one({"_id": ObjectId(payload.bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if not bid.get("emd_paid_at"):
        raise HTTPException(status_code=400, detail="EMD was not paid")
    tx = await db.payment_transactions.find_one({"bid_id": payload.bid_id, "purpose": "emd",
                                                 "payment_status": "paid"})
    if not tx:
        raise HTTPException(status_code=404, detail="Paid transaction not found")

    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
    pi = tx.get("stripe_payment_intent_id") or tx.get("session_id")
    try:
        stripe.Refund.create(payment_intent=pi) if pi and pi.startswith("pi_") else None
    except Exception as e:
        log.warning(f"Refund API call failed: {e}")

    await db.payment_transactions.update_one(
        {"session_id": tx["session_id"]},
        {"$set": {"status": "refunded", "payment_status": "refunded",
                  "refund_reason": payload.reason, "updated_at": now_iso()}},
    )
    await db.bids.update_one(
        {"_id": ObjectId(payload.bid_id)},
        {"$set": {"emd_refunded_at": now_iso(), "emd_refund_reason": payload.reason}},
    )
    await audit_log("bid.emd_refund", admin, "bid", bid.get("bid_ref"), {"reason": payload.reason})
    return {"ok": True}
