"""Wave 35 — Billing / Checkout via Stripe (Flow B, `sk_test_managed`).

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
from security import current_admin, require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

log = logging.getLogger("billing")
router = APIRouter(tags=["billing"])


# ---- Managed Stripe (Flow B) ------------------------------------

def _stripe_checkout():
    from pmc_lib.payments.stripe.checkout import StripeCheckout
    return StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_managed"),
                          webhook_url="")  # webhook URL is set per-request below


_QUOTE_ONLY_MODELS = {
    "percentage":    "Percentage-of-value products cannot be checked out directly — please request a quote.",
    "cost_recovery": "Cost-recovery items require a quote before checkout.",
}
_FLAT_MODELS         = {"fixed", "monthly", "annual", "package"}
_PER_QUANTITY_MODELS = {"per_delegate", "per_user_monthly"}


def _price_from_product(product: dict, quantity: int) -> tuple[float, str, str]:
    """Compute (amount, currency, cadence) from a catalog row.
    Returns amount as float, currency lower-cased, cadence for metadata.

    Refactored (Wave 35 code-review): flat table lookup with an explicit
    initial `amt` so control flow can never leave the function with an
    uninitialised value.
    """
    pm = product.get("pricing_model", "fixed")
    curr = (product.get("currency") or "USD").lower()
    amt = 0.0
    if pm in _QUOTE_ONLY_MODELS:
        raise HTTPException(status_code=400, detail=_QUOTE_ONLY_MODELS[pm])
    if pm in _FLAT_MODELS:
        amt = float(product.get("amount") or 0)
    elif pm == "range":
        amt = float(product.get("min_amount") or 0)
    elif pm in _PER_QUANTITY_MODELS:
        amt = float(product.get("amount") or 0) * max(1, int(quantity))
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
    # Anonymous checkout only — surfaces the buyer in the session metadata.
    buyer_email: Optional[str] = None


@router.post("/api/v1/billing/checkout")
async def create_checkout(req: CheckoutRequest, request: Request):
    """Create a Stripe Checkout session for one catalog product. Accepts:
    * admin session (staff subscribing on behalf of a client), OR
    * vendor session (supplier subscribing to a supplier-side product), OR
    * anonymous with a `buyer_email` — recorded in metadata only.
    Pricing is always server-authoritative (from the catalog row)."""
    # Resolve buyer identity — best-effort, never blocks anonymous checkout
    buyer_email = None
    buyer_role = "anonymous"
    try:
        u = await current_admin(request)
        if u:
            buyer_email = u.get("email"); buyer_role = "admin"
    except Exception:
        try:
            v = await current_vendor(request)
            if v:
                buyer_email = v.get("email"); buyer_role = "vendor"
        except Exception:
            pass
    if not buyer_email:
        buyer_email = req.buyer_email or "anonymous@pmcmanagers.com"
    product = await db.products.find_one({"code": req.product_code, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {req.product_code}")
    amount, currency, cadence = _price_from_product(product, req.quantity)
    if req.currency_override:
        if req.currency_override.upper() in {"USD", "GBP", "EUR", "KZT"}:
            currency = req.currency_override.lower()

    # Build Stripe checkout (Flow B, pmc_lib)
    from pmc_lib.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_managed"),
                         webhook_url=webhook_url)
    ck_req = CheckoutSessionRequest(
        amount=float(amount),
        currency=currency,
        success_url=f"{req.origin_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.origin_url.rstrip('/')}/billing/cancel",
        tax_mode=os.environ.get("STRIPE_TAX_MODE", "full"),
        product_name=product["name"],
        product_tax_code=product.get("stripe_tax_code") or "txcd_10000000",
        metadata={
            "product_code": product["code"],
            "product_name": product["name"],
            "quantity": str(req.quantity),
            "buyer_email": buyer_email,
            "buyer_role": buyer_role,
            "cadence": cadence,
        },
    )
    session = await sc.create_checkout_session(ck_req)

    # Insert payment_transactions BEFORE returning the URL
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "product_code": product["code"],
        "buyer_email": buyer_email,
        "buyer_role": buyer_role,
        "amount": float(amount),
        "currency": currency,
        "quantity": req.quantity,
        "cadence": cadence,
        "status": "initiated",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    await audit_log("billing.checkout_init",
                    {"email": buyer_email, "role": buyer_role},
                    "product", product["code"],
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
            from pmc_lib.payments.stripe.checkout import StripeCheckout
            host_url = str(request.base_url)
            webhook_url = f"{host_url}api/webhook/stripe"
            sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_managed"),
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
    """Flow-B webhook — exact path required by pmc_lib.

    v52cj — SEC-001: webhook signature verification is REQUIRED. Returns
    503 if STRIPE_WEBHOOK_SECRET is not configured so no event is trusted.
    """
    from config import STRIPE_WEBHOOK_SECRET
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="webhook not configured")
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        from pmc_lib.payments.stripe.checkout import StripeCheckout
        host_url = str(request.base_url)
        webhook_url = f"{host_url}api/webhook/stripe"
        sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_managed"),
                             webhook_url=webhook_url,
                             webhook_secret=STRIPE_WEBHOOK_SECRET)
        event = await sc.handle_webhook(body, sig)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid webhook: {e}")
    if event.session_id:
        # Idempotent: only advance if not already paid
        res = await db.payment_transactions.update_one(
            {"session_id": event.session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed" if event.payment_status == "paid" else event.payment_status,
                      "payment_status": event.payment_status,
                      "updated_at": datetime.now(timezone.utc)}},
        )
        if res.modified_count and event.payment_status == "paid":
            tx = await db.payment_transactions.find_one({"session_id": event.session_id})
            if (tx or {}).get("purpose") == "tender_builder_sub":
                from routers.vendor_tenders import activate_subscription
                await activate_subscription(tx.get("vendor_id"))
            elif (tx or {}).get("purpose") == "tender_fee":
                from routers.vendor_tenders import apply_tender_fee_payment
                await apply_tender_fee_payment(event.session_id)
            elif (tx or {}).get("purpose") == "tender_credit":
                from routers.vendor_tenders import apply_credit_payment
                await apply_credit_payment(event.session_id)
            elif (tx or {}).get("purpose") == "category_fee":
                from routers.vendor_categories import apply_category_payment
                await apply_category_payment(event.session_id)
            elif (tx or {}).get("purpose") in ("doc_fee", "hosting_fee", "data_intel"):
                from routers.payments_extra import apply_extra_payment
                await apply_extra_payment(event.session_id)
    # v52ck — record every signature-verified event for the webhook-health
    # indicator on the admin Billing page.
    await db.webhook_events.insert_one({
        "provider": "stripe",
        "session_id": event.session_id,
        "payment_status": event.payment_status,
        "received_at": now_iso(),
    })
    return {"status": "ok"}


# ---- Admin: transaction list --------------------------------------------

# v52ck — SEC-001 follow-up: admin-visible webhook health so a missing or
# rotated STRIPE_WEBHOOK_SECRET is obvious from the Billing page instead of
# silently 503-ing Stripe retries for weeks.
@router.get("/api/v1/billing/webhook-health")
async def webhook_health(admin=Depends(require_role("admin", "accounting", "reviewer", "auditor"))):
    import config as _config
    last = await db.webhook_events.find_one({"provider": "stripe"}, sort=[("received_at", -1)])
    cutoff = datetime.now(timezone.utc).timestamp() - 24 * 3600
    events_24h = 0
    async for e in db.webhook_events.find({"provider": "stripe"}).sort("received_at", -1).limit(500):
        try:
            ts = datetime.fromisoformat(str(e.get("received_at", "")).replace("Z", "+00:00")).timestamp()
            if ts >= cutoff:
                events_24h += 1
        except Exception:
            continue
    key = os.environ.get("STRIPE_API_KEY", "")
    mode = ("live" if key.startswith(("sk_live_", "rk_live_")) else
            "sandbox (Emergent test key)" if "sk_test_emergent" in key else
            "test" if key.startswith(("sk_test_", "rk_test_")) else "not set")
    return {
        "stripe_mode": mode,
        "secret_configured": bool(_config.STRIPE_WEBHOOK_SECRET),
        "last_event_at": (last or {}).get("received_at"),
        "last_session_id": (last or {}).get("session_id"),
        "last_payment_status": (last or {}).get("payment_status"),
        "events_24h": events_24h,
    }


@router.get("/api/v1/billing/transactions")
async def list_transactions(admin=Depends(require_role("admin", "accounting", "reviewer", "auditor")), limit: int = 50):
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


# v52p — Admin "Resync pending payments". Bulk-poll Stripe for every
# payment_transactions row still stuck in pending/initiated, mark the ones
# Stripe reports as paid, and advance the bid to emd_paid via the same
# idempotent `_mark_paid` helper the webhook uses. Safe to re-run; only
# touches rows the webhook never processed.
@router.post("/api/v1/billing/resync-pending")
async def resync_pending_payments(admin=Depends(require_role("admin", "accounting", "reviewer", "auditor")), limit: int = 200) -> dict:
    import os as _os
    from pmc_lib.payments.stripe.checkout import StripeCheckout as _SC
    from routers.payments import _mark_paid

    api_key = _os.environ.get("STRIPE_API_KEY", "sk_test_managed")
    checkout = _SC(api_key=api_key, webhook_url="")

    q = {
        "payment_status": {"$nin": ["paid", "refunded"]},
        "session_id": {"$exists": True, "$ne": None},
    }
    docs = await db.payment_transactions.find(q).sort("created_at", -1).limit(limit).to_list(limit)

    reconciled = 0
    still_pending = 0
    failed: list[dict] = []
    for d in docs:
        sid = d.get("session_id")
        if not sid:
            continue
        try:
            s = await checkout.get_checkout_status(sid)
            paid = (getattr(s, "payment_status", "") == "paid") or (getattr(s, "status", "") == "complete")
            if paid:
                await _mark_paid(sid, getattr(s, "payment_status", None) or "paid")
                reconciled += 1
            else:
                still_pending += 1
        except Exception as e:
            failed.append({"session_id": sid, "error": str(e)[:120]})
            log.warning("resync %s failed: %s", sid, e)

    await audit_log("billing.resync_pending", admin, "billing", "resync",
                    {"scanned": len(docs), "reconciled": reconciled,
                     "still_pending": still_pending, "failed": len(failed)})
    return {
        "scanned": len(docs),
        "reconciled": reconciled,
        "still_pending": still_pending,
        "failed": failed,
    }


# ---- Fee master → Stripe checkout (v46b) ---------------------------------
# Turns any EMD / registration / subscription / premium / transaction /
# data-intel fee master into a Stripe Checkout session. Amount is computed
# from the matching slab (see tender_pro.compute_emd) — the client is never
# trusted for pricing.

class FeeCheckoutRequest(BaseModel):
    fee_master_id: str
    tender_value: float = Field(0, ge=0)
    origin_url: str
    buyer_email: Optional[str] = None
    label: Optional[str] = None            # override display label
    context_ref: Optional[str] = None      # tender_ref / notice_ref for audit


@router.post("/api/v1/billing/fee-checkout")
async def create_fee_checkout(req: FeeCheckoutRequest, request: Request):
    """Public — vendors and buyers can pay a configured fee. Admin can also
    pay-on-behalf. Amount is server-authoritative from the fee master."""
    # Look up buyer
    buyer_email = None
    buyer_role = "anonymous"
    try:
        u = await current_admin(request)
        if u:
            buyer_email = u.get("email"); buyer_role = "admin"
    except Exception:
        try:
            v = await current_vendor(request)
            if v:
                buyer_email = v.get("email"); buyer_role = "vendor"
        except Exception:
            pass
    if not buyer_email:
        buyer_email = req.buyer_email or "anonymous@pmcmanagers.com"

    if buyer_role == "admin":
        if not (req.buyer_email or "").strip() or "@" not in req.buyer_email:
            raise HTTPException(status_code=422, detail="Payer email (buyer or vendor) is required — the payment link is emailed to them.")
    try:
        m = await db.emd_masters.find_one({"_id": ObjectId(req.fee_master_id)})
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid fee_master_id")
    if not m:
        raise HTTPException(status_code=404, detail="Fee master not found")
    if not m.get("is_active", True):
        raise HTTPException(status_code=400, detail="This fee master is inactive")

    # Compute amount from slabs (mirrors tender_pro.compute_emd)
    v = req.tender_value
    amt = None
    slab_used = None
    for slab in (m.get("slabs") or []):
        lo = slab.get("tender_value_min") or 0
        hi = slab.get("tender_value_max")
        if v >= lo and (hi is None or v < hi):
            if slab["fee_type"] == "fixed":
                amt = float(slab.get("fixed_amount") or 0)
            else:
                amt = round(v * float(slab.get("percentage") or 0) / 100.0, 2)
            slab_used = slab
            break
    if amt is None:
        raise HTTPException(status_code=422,
            detail=f"No slab matches tender value {v} for master '{m.get('name')}'. Configure a slab that covers this range.")
    if amt <= 0:
        raise HTTPException(status_code=400,
            detail=f"Computed fee is 0 — check that slab has a positive amount or percentage.")

    currency = (m.get("currency") or "USD").lower()
    label = req.label or f"{m.get('name')} · {m.get('kind')}"

    from pmc_lib.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ.get("STRIPE_API_KEY", "sk_test_managed"),
                         webhook_url=webhook_url)
    ck_req = CheckoutSessionRequest(
        amount=float(amt),
        currency=currency,
        success_url=f"{req.origin_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.origin_url.rstrip('/')}/billing/cancel",
        tax_mode=os.environ.get("STRIPE_TAX_MODE", "full"),
        product_name=label,
        product_tax_code="txcd_10000000",
        metadata={
            "fee_master_id": str(m["_id"]),
            "fee_master_name": m.get("name") or "",
            "fee_kind": m.get("kind") or "",
            "tender_value": str(v),
            "context_ref": req.context_ref or "",
            "buyer_email": buyer_email,
            "buyer_role": buyer_role,
        },
    )
    session = await sc.create_checkout_session(ck_req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "product_code": f"FEE:{m.get('kind')}",
        "fee_master_id": str(m["_id"]),
        "fee_kind": m.get("kind"),
        "tender_value": v,
        "buyer_email": buyer_email,
        "buyer_role": buyer_role,
        "amount": float(amt),
        "currency": currency,
        "context_ref": req.context_ref,
        "status": "initiated",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    await audit_log("billing.fee_checkout_init",
                    {"email": buyer_email, "role": buyer_role},
                    "fee_master", str(m["_id"]),
                    {"amount": amt, "currency": currency, "tender_value": v,
                     "context_ref": req.context_ref, "session_id": session.session_id})
    payer = (req.buyer_email or "").strip() if buyer_role == "admin" else None
    email_sent = False
    if payer:
        from emails import send_email, wrap
        ft = await db.fee_types.find_one({"code": m.get("kind")}) or {}
        subject = f"Payment request — {ft.get('name') or m.get('kind')}"
        html = wrap(subject,
            f"<p>PMC Managers has requested a payment of <b>{currency.upper()} {amt:,.2f}</b> for "
            f"<b>{m.get('name')}</b>{' (ref ' + req.context_ref + ')' if req.context_ref else ''}.</p>"
            f"<p>Pay securely with the button below. The link is valid for 24 hours.</p>",
            f"Pay {currency.upper()} {amt:,.2f}", session.url)
        email_sent = await send_email(payer, f"[PMC] {subject}", html)
        await db.payment_transactions.update_one({"session_id": session.session_id},
                                                 {"$set": {"payer_email": payer, "link_emailed": email_sent}})
    return {"checkout_url": session.url, "session_id": session.session_id,
             "amount": amt, "currency": currency, "emailed_to": payer, "email_sent": email_sent,
             "fee_kind": m.get("kind"), "slab": slab_used}


# ---- Refund a fee-checkout (v46c) ----------------------------------------

class FeeRefundRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/api/v1/billing/refund/{session_id}")
async def refund_fee_checkout(session_id: str, payload: FeeRefundRequest,
                                admin=Depends(require_role("admin", "accounting", "reviewer", "auditor"))):
    """Admin refunds a paid Stripe fee-checkout. Uses stripe.Refund.create
    against the PaymentIntent for the session."""
    record = await db.payment_transactions.find_one({"session_id": session_id})
    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if record.get("payment_status") == "refunded":
        return {"ok": True, "already": True, "status": "refunded"}
    if record.get("payment_status") != "paid":
        raise HTTPException(status_code=400,
            detail=f"Cannot refund a {record.get('payment_status')} transaction — only paid transactions can be refunded")

    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_managed")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        pi = session.get("payment_intent") if isinstance(session, dict) else session.payment_intent
        if not pi:
            raise HTTPException(status_code=400,
                detail="Stripe session has no PaymentIntent — refund not possible")
        refund = stripe.Refund.create(payment_intent=pi,
                                       metadata={"reason": payload.reason or ""})
        refund_id = refund.get("id") if isinstance(refund, dict) else refund.id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502,
            detail=f"Stripe refund failed: {type(e).__name__}: {e}")

    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": "refunded",
                  "status": "refunded",
                  "refund_id": refund_id,
                  "refund_reason": payload.reason,
                  "refunded_by": admin.get("email"),
                  "refunded_at": now_iso(),
                  "updated_at": datetime.now(timezone.utc)}})
    await audit_log("billing.refund", admin, "session", session_id,
                    {"reason": payload.reason, "refund_id": refund_id,
                     "amount": record.get("amount"), "currency": record.get("currency")})
    return {"ok": True, "session_id": session_id, "refund_id": refund_id,
             "status": "refunded"}

