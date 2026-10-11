"""Stripe EMD Payments router (Flow B — pmc_lib lib).

Vendor pays the EMD due on a bid via Stripe Checkout. On webhook success the
bid transitions from `emd_pending` to `emd_paid`, unlocking the sequential
Escrow → Admin → Certifier → Legal → Accounting → Committee pipeline.
"""
import os
import logging
import config
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


# v49l — Vendor EMD statement PDF.
# Reads every payment_transactions row + escrow ledger entries for the
# current vendor and renders an A4 statement via WeasyPrint. Streamed
# with Content-Disposition: attachment so the browser saves it as
# "PMC-EMD-Statement-<vendor_ref>-<date>.pdf".
@router.get("/payments/emd/statement.pdf")
async def emd_statement_pdf(vendor=Depends(current_vendor)):
    from fastapi.responses import Response
    from weasyprint import HTML

    vendor_id = vendor["id"]
    vendor_ref = vendor.get("vendor_ref") or "—"
    company = vendor.get("company_name") or vendor.get("email") or vendor_ref

    # Collect vendor's bids so we can label rows with the notice ref
    vbids = {}
    async for b in db.bids.find({"vendor_id": vendor_id}):
        vbids[str(b["_id"])] = b

    rows = []
    total_paid = 0.0
    total_refunded = 0.0
    async for tx in db.payment_transactions.find({"vendor_id": vendor_id, "purpose": "emd"}).sort("created_at", -1):
        bid = vbids.get(str(tx.get("bid_id") or ""), {}) or {}
        amt = float(tx.get("amount") or 0.0)
        status = (tx.get("status") or "").lower()
        rows.append({
            "date":   (tx.get("paid_at") or tx.get("created_at") or "")[:19].replace("T", " "),
            "bid":    bid.get("bid_ref") or "—",
            "notice": bid.get("notice_ref") or "—",
            "cur":    tx.get("currency") or "USD",
            "amount": f"{amt:,.2f}",
            "status": status or "pending",
            "ref":    tx.get("provider_ref") or tx.get("session_id") or "—",
        })
        if status == "paid":     total_paid += amt
        if status == "refunded": total_refunded += amt

    from datetime import datetime, timezone
    generated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    tbody = "".join(
        f"<tr><td>{r['date']}</td><td>{r['bid']}</td><td>{r['notice']}</td>"
        f"<td class='r'>{r['cur']} {r['amount']}</td>"
        f"<td class='pill p-{r['status']}'>{r['status'].upper()}</td>"
        f"<td class='mono'>{r['ref']}</td></tr>"
        for r in rows
    ) or "<tr><td colspan='6' class='empty'>No EMD payments recorded for this account yet.</td></tr>"

    html = f"""<!doctype html><html><head><meta charset='utf-8'><style>
      @page {{ size: A4; margin: 22mm 18mm; }}
      body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color:#14261F; font-size:11px; }}
      h1 {{ font-family: 'Times New Roman', serif; font-size:22px; margin:0 0 4px; color:#0F3B2E; }}
      .brand {{ font-size:10px; letter-spacing:2px; text-transform:uppercase; color:#C9A24B; }}
      .meta {{ display:flex; justify-content:space-between; margin:14px 0 22px; font-size:11px; }}
      .meta b {{ display:block; margin-bottom:2px; color:#5B6B63; font-weight:600; font-size:9px; text-transform:uppercase; letter-spacing:1px; }}
      .kpi {{ display:flex; gap:12px; margin:0 0 18px; }}
      .kpi .b {{ flex:1; padding:12px; border:1px solid rgba(15,59,46,.15); border-radius:6px; }}
      .kpi .b .l {{ font-size:9px; text-transform:uppercase; letter-spacing:1px; color:#5B6B63; }}
      .kpi .b .v {{ font-size:16px; font-weight:600; margin-top:4px; color:#0F3B2E; }}
      table {{ width:100%; border-collapse:collapse; }}
      th, td {{ padding:8px 10px; text-align:left; border-bottom:1px solid rgba(15,59,46,.1); }}
      th {{ font-size:9px; letter-spacing:1px; text-transform:uppercase; color:#5B6B63; }}
      td.r {{ text-align:right; }}
      td.mono {{ font-family:'Courier New',monospace; font-size:10px; color:#5B6B63; }}
      td.empty {{ text-align:center; padding:24px; color:#7B8B83; font-style:italic; }}
      .pill {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:9px; letter-spacing:1px; font-weight:600; }}
      .p-paid {{ background:#DEEEE1; color:#0F3B2E; }}
      .p-refunded {{ background:#F3E7CE; color:#8B6A1E; }}
      .p-pending {{ background:#EFE9DA; color:#5B6B63; }}
      .foot {{ position:fixed; bottom:-14mm; left:0; right:0; font-size:9px; color:#7B8B83; text-align:center; }}
    </style></head><body>
      <div class="brand">PMC Managers · Global Tender Board</div>
      <h1>EMD Statement</h1>
      <div class="meta">
        <div><b>Vendor</b>{company}<br/>{vendor_ref}</div>
        <div><b>Generated</b>{generated}</div>
      </div>
      <div class="kpi">
        <div class="b"><div class="l">Total EMD paid</div><div class="v">{total_paid:,.2f}</div></div>
        <div class="b"><div class="l">Refunded</div><div class="v">{total_refunded:,.2f}</div></div>
        <div class="b"><div class="l">Rows</div><div class="v">{len(rows)}</div></div>
      </div>
      <table>
        <thead><tr>
          <th>Date</th><th>Bid</th><th>Notice</th><th style='text-align:right'>Amount</th>
          <th>Status</th><th>Reference</th>
        </tr></thead>
        <tbody>{tbody}</tbody>
      </table>
      <div class="foot">Chained to the audit ledger · every entry is time-stamped and cannot be altered</div>
    </body></html>"""

    pdf = HTML(string=html).write_pdf()
    fname = f"PMC-EMD-Statement-{vendor_ref}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    await audit_log("vendor.emd_statement_pdf", None, "vendor", vendor_id, {"rows": len(rows)})
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


def _stripe():
    """Lazy-import to keep dev startup resilient if key is missing."""
    from pmc_lib.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
    api_key = os.environ.get("STRIPE_API_KEY", "sk_test_managed")
    return StripeCheckout, CheckoutSessionRequest, api_key


# v52bu — Per-bid EMD receipt PDF. Vendors can download a single-page
# receipt for any paid EMD transaction straight from the deposits row.
# Secured by vendor ownership (bid.vendor_id must match current vendor).
@router.get("/payments/emd/bid/{bid_id}/receipt.pdf")
async def emd_receipt_pdf(bid_id: str, vendor=Depends(current_vendor)):
    from fastapi.responses import Response
    from weasyprint import HTML
    bid = await db.bids.find_one({"_id": ObjectId(bid_id), "vendor_id": vendor["id"]})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    tx = await db.payment_transactions.find_one(
        {"bid_id": bid_id, "vendor_id": vendor["id"], "purpose": "emd",
         "payment_status": "paid"},
        sort=[("paid_at", -1), ("updated_at", -1)],
    )
    if not tx:
        raise HTTPException(status_code=404,
            detail="No paid EMD transaction found for this bid")
    paid_at = (tx.get("paid_at") or tx.get("updated_at") or "")[:19].replace("T", " ")
    amount = float(tx.get("amount") or 0.0)
    currency = (tx.get("currency") or "USD").upper()
    ref = tx.get("provider_ref") or tx.get("session_id") or "—"
    vendor_ref = vendor.get("vendor_ref") or "—"
    company = vendor.get("company_name") or vendor.get("email") or vendor_ref
    bid_ref = bid.get("bid_ref") or "—"
    notice_ref = bid.get("notice_ref") or "—"
    generated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    html = f"""<!doctype html><html><head><meta charset='utf-8'><style>
      @page {{ size: A4; margin: 24mm 20mm; }}
      body {{ font-family:'Helvetica Neue',Arial,sans-serif;color:#14261F;font-size:12px; }}
      h1 {{ font-family:'Times New Roman',serif;font-size:26px;margin:0 0 2px;color:#0F3B2E; }}
      .brand {{ font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#C9A24B; }}
      .amt {{ font-size:32px;font-weight:600;color:#0F3B2E;margin:14px 0 20px; }}
      .pill {{ display:inline-block;padding:3px 10px;border-radius:12px;font-size:10px;
             letter-spacing:1px;font-weight:600;background:#DEEEE1;color:#0F3B2E;margin-left:10px;vertical-align:middle; }}
      table {{ width:100%;border-collapse:collapse;margin-top:12px; }}
      td {{ padding:10px 0;border-bottom:1px solid rgba(15,59,46,.1); }}
      td.l {{ color:#5B6B63;font-size:10px;text-transform:uppercase;letter-spacing:1px;width:38%; }}
      td.r {{ color:#14261F;font-weight:500; }}
      td.mono {{ font-family:'Courier New',monospace;font-size:11px; }}
      .foot {{ margin-top:28px;font-size:10px;color:#7B8B83;line-height:1.5; }}
    </style></head><body>
      <div class='brand'>PMC Managers · Global Tender Board</div>
      <h1>EMD Payment Receipt</h1>
      <div style='font-size:11px;color:#5B6B63'>Receipt generated {generated}</div>
      <div class='amt'>{currency} {amount:,.2f}<span class='pill'>PAID</span></div>
      <table>
        <tr><td class='l'>Vendor</td><td class='r'>{company}<br><span style='color:#5B6B63;font-size:11px'>{vendor_ref}</span></td></tr>
        <tr><td class='l'>Bid reference</td><td class='r mono'>{bid_ref}</td></tr>
        <tr><td class='l'>Notice reference</td><td class='r mono'>{notice_ref}</td></tr>
        <tr><td class='l'>Payment date</td><td class='r'>{paid_at}</td></tr>
        <tr><td class='l'>Payment reference</td><td class='r mono'>{ref}</td></tr>
        <tr><td class='l'>Method</td><td class='r'>Stripe Checkout (card/bank)</td></tr>
      </table>
      <div class='foot'>This receipt confirms the Earnest Money Deposit held in escrow against the bid above.
      The deposit is refunded to your verified account if the bid is not awarded, or converted to a
      security deposit upon contract signature. Every entry is chained to the PMC audit ledger.</div>
    </body></html>"""
    pdf = HTML(string=html).write_pdf()
    fname = f"PMC-EMD-Receipt-{bid_ref}.pdf"
    await audit_log("vendor.emd_receipt_pdf", None, "bid", bid_ref, {"amount": amount, "currency": currency})
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


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
        tax_mode=os.environ.get("STRIPE_TAX_MODE", "full"),
        product_name=f"EMD — bid {bid.get('bid_ref') or payload.bid_id}",
        product_tax_code="txcd_10000000",  # digital services (SMP-eligible)
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
        # v51am — auto-mint an escrow ledger transaction so admins never
        # have to manually double-enter the EMD receipt against the joint
        # account. Idempotent (keyed on session_id). Failure is logged but
        # non-fatal — admins can still record manually from Escrow panel.
        try:
            from routers.escrow import auto_init_from_emd_payment
            await auto_init_from_emd_payment(bid_id, tx)
        except Exception as e:
            log.warning(f"escrow auto-init failed for bid {bid_id}: {e}")
        # Notify Escrow that a new EMD-paid bid is ready
        try:
            from notify import notify_bid_transition, vendor_confirm
            b = await db.bids.find_one({"_id": ObjectId(bid_id)})
            await notify_bid_transition(b, "emd_paid")
            # v47c — payment confirmation email to the bidder (fires exactly
            # once thanks to the idempotent find_one_and_update guard above).
            if b:
                await vendor_confirm(
                    b.get("vendor_email"),
                    f"EMD payment received — {b.get('bid_ref')}",
                    f"<p>Dear {b.get('company_name') or 'Vendor'},</p>"
                    f"<p>We confirm receipt of your EMD payment of "
                    f"<strong>{(tx.get('currency') or 'USD').upper()} {float(tx.get('amount') or 0):,.2f}</strong> "
                    f"for bid <strong>{b.get('bid_ref')}</strong> on tender "
                    f"<code>{b.get('notice_ref')}</code>.</p>"
                    f"<p>Payment reference: <code>{session_id}</code><br/>"
                    f"Your bid is now in the evaluation pipeline — no further action is needed.</p>",
                    "View my bids", f"{config.FRONTEND_URL}/vendor")
        except Exception as e:
            log.warning(f"post-payment notifications failed for {session_id}: {e}")


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
    stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_managed")
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
    # v47c — refund confirmation email to the bidder
    try:
        from notify import vendor_confirm
        await vendor_confirm(
            bid.get("vendor_email"),
            f"EMD refunded — {bid.get('bid_ref')}",
            f"<p>Dear {bid.get('company_name') or 'Vendor'},</p>"
            f"<p>The EMD of <strong>{bid.get('emd_currency')} {float(bid.get('emd_paid_amount') or 0):,.2f}</strong> "
            f"for bid <strong>{bid.get('bid_ref')}</strong> on tender "
            f"<code>{bid.get('notice_ref')}</code> has been refunded to your original payment method."
            + (f"<br/>Reason: <em>{payload.reason}</em>" if payload.reason else "")
            + "</p><p>Refunds typically reflect within 5–10 business days depending on your bank.</p>")
    except Exception as e:
        log.warning(f"refund confirmation email failed: {e}")
    return {"ok": True}
