"""Sandbox gateways — PayPal & Kaspi in-app demo checkout.

Stripe stays the production-grade gateway. These two provide a fully in-app
demo flow so a vendor (or the sales team during a walkthrough) can experience
the alternate rails end-to-end without live credentials. Every response is
explicitly marked `mode: "sandbox"` and the front-end labels it as such.

Real PayPal + Kaspi live-mode integrations are on the P2 backlog and will
replace these endpoints without changing the vendor-facing contract.
"""
import secrets
from typing import Literal, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId

from db import db
from models.base import now_iso
from routers.vendor_auth import current_vendor
from routers.payments import _mark_paid  # reuse the pipeline advance helper
from audit import audit_log

router = APIRouter(prefix="/api/v1/payments/sandbox", tags=["payments-sandbox"])


GatewayName = Literal["paypal", "kaspi"]


class SandboxCheckoutIn(BaseModel):
    bid_id: str
    gateway: GatewayName
    origin_url: str


class SandboxConfirmIn(BaseModel):
    session_id: str


@router.post("/checkout")
async def create_sandbox_checkout(payload: SandboxCheckoutIn,
                                   vendor=Depends(current_vendor)) -> dict:
    """Create a sandbox session for PayPal or Kaspi. Response tells the FE
    which in-app URL to redirect to (a demo confirm page)."""
    bid = await db.bids.find_one({"_id": ObjectId(payload.bid_id), "vendor_id": vendor["id"]})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.get("status") not in ("emd_pending", "submitted"):
        raise HTTPException(status_code=400, detail=f"EMD not payable at status {bid.get('status')}")
    amount = float(bid.get("emd_due_amount") or 0.0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="No EMD due")

    session_id = f"sbx_{payload.gateway}_{secrets.token_urlsafe(12)}"
    checkout_url = (f"{payload.origin_url}/vendor/payment/sandbox"
                    f"?session_id={session_id}&method={payload.gateway}")
    await db.payment_transactions.insert_one({
        "session_id": session_id,
        "bid_id": payload.bid_id, "vendor_id": vendor["id"],
        "notice_ref": bid.get("notice_ref"),
        "amount": amount, "currency": bid.get("emd_currency", "USD"),
        "purpose": "emd", "gateway": payload.gateway, "mode": "sandbox",
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await audit_log(f"payment.sandbox.{payload.gateway}.init", None, "bid",
                    bid.get("bid_ref"), {"session_id": session_id, "amount": amount})
    return {"checkout_url": checkout_url, "session_id": session_id,
            "amount": amount, "currency": bid.get("emd_currency", "USD"),
            "gateway": payload.gateway, "mode": "sandbox"}


@router.get("/session/{session_id}")
async def get_sandbox_session(session_id: str, vendor=Depends(current_vendor)) -> dict:
    """Retrieve the sandbox session details for the vendor-visible confirm page."""
    tx = await db.payment_transactions.find_one({
        "session_id": session_id, "vendor_id": vendor["id"], "mode": "sandbox",
    })
    if not tx:
        raise HTTPException(status_code=404, detail="Session not found")
    bid = await db.bids.find_one({"_id": ObjectId(tx["bid_id"])})
    return {
        "session_id": session_id, "gateway": tx.get("gateway"),
        "amount": tx.get("amount"), "currency": tx.get("currency"),
        "bid_ref": (bid or {}).get("bid_ref"),
        "notice_ref": tx.get("notice_ref"),
        "payment_status": tx.get("payment_status"),
    }


@router.post("/confirm")
async def confirm_sandbox(payload: SandboxConfirmIn,
                          vendor=Depends(current_vendor)) -> dict:
    """Vendor clicks 'Confirm Payment' on the sandbox page — we mark the bid
    as EMD-paid (reusing the same pipeline advance as Stripe) and fire the
    Escrow notification."""
    tx = await db.payment_transactions.find_one({
        "session_id": payload.session_id, "vendor_id": vendor["id"], "mode": "sandbox",
    })
    if not tx:
        raise HTTPException(status_code=404, detail="Session not found")
    if tx.get("payment_status") == "paid":
        return {"ok": True, "already_paid": True}
    await _mark_paid(payload.session_id, "paid")
    await audit_log(f"payment.sandbox.{tx.get('gateway')}.confirm", None,
                    "bid", tx.get("bid_id"),
                    {"session_id": payload.session_id, "amount": tx.get("amount")})
    return {"ok": True, "gateway": tx.get("gateway"), "amount": tx.get("amount"),
            "bid_id": tx.get("bid_id")}
