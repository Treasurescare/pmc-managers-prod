"""Vendor Tender Preparation module (R8).

An APPROVED, KYC-verified vendor who holds an active tender-builder subscription
may prepare a tender using the same fields as the staff tender builder. Nothing
a vendor prepares goes live automatically: it must pass MANDATORY PMC review by
an officer holding the `reviewer` role (and only that role). On approval the
tender publishes as a normal notice that other vendors bid on; the preparing
vendor is blocked from bidding on it (conflict of interest) and is disclosed as
the author on the tender and the audit ledger.

Subscription price/period come from backend config (collection platform_config,
key "tender_builder_subscription") so the amount and go-live can be set later
without a code change. Stripe reuses the existing Flow-B pattern.
"""
import os
import secrets
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from routers._tender_access import (
    sub_config as _ta_sub_config, vendor_entitlement, vendor_country,
)
from audit import audit_log

router = APIRouter(prefix="/api/v1/vendor-tenders", tags=["vendor-tenders"])

CORE_FIELDS = {
    "title", "description", "document_type", "category", "delivery_country",
    "submission_deadline", "pre_bid_meeting_date", "budget_currency",
    "budget_amount", "required_licenses", "primary_document", "attachments",
    "contact_email", "contact_name", "sector_code", "contract_type_code",
}


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ----------------------- subscription config -----------------------

async def _sub_config() -> dict:
    cfg = await db.platform_config.find_one({"key": "tender_builder_subscription"})
    if not cfg:
        return {"key": "tender_builder_subscription", "enabled": False,
                "amount": 0.0, "currency": "usd", "period_days": 365}
    cfg.pop("_id", None)
    return cfg


async def _vendor_doc(vendor: dict) -> dict:
    from bson import ObjectId
    return await db.vendors.find_one({"_id": ObjectId(vendor["id"])}) or {}


def _sub_active(vdoc: dict) -> bool:
    sub = vdoc.get("tender_builder_sub") or {}
    if not sub.get("active"):
        return False
    exp = sub.get("expires_at")
    return bool(exp) and exp > now_iso()


async def _require_build_access(vendor: dict) -> dict:
    """Vendor must be KYC-verified and entitled (free when the Fee Master has no
    price for their country, otherwise an active subscription is required)."""
    if (vendor.get("kyc_status") or "verified") != "verified":
        raise HTTPException(status_code=403,
            detail="Your account must be approved and KYC-verified before preparing tenders.")
    vdoc = await _vendor_doc(vendor)
    ent = await vendor_entitlement(vdoc)
    if not ent["entitled"]:
        raise HTTPException(status_code=402,
            detail="A tender-builder subscription is required. Please subscribe to continue.")
    return vdoc


@router.get("/subscription")
async def my_subscription(vendor=Depends(current_vendor)):
    vdoc = await _vendor_doc(vendor)
    ent = await vendor_entitlement(vdoc)
    return {
        "required": ent["sub_required"],
        "free": ent["free"],
        "price": ent["price"],
        "active": ent["sub_active"],
        "expires_at": ent["sub_expires_at"],
        "entitled": ent["entitled"],
        "read_only": ent["read_only"],
        "country": ent["country"],
    }


@router.get("/subscription/config")
async def get_sub_config(admin=Depends(require_role("admin", "reviewer"))):
    return await _sub_config()


class SubConfigIn(BaseModel):
    enabled: bool
    amount: float = Field(ge=0)
    currency: str = "usd"
    period_days: int = Field(gt=0, default=365)


@router.post("/subscription/config")
async def set_sub_config(payload: SubConfigIn, admin=Depends(require_role("admin"))):
    doc = {"key": "tender_builder_subscription", **payload.model_dump()}
    await db.platform_config.update_one({"key": "tender_builder_subscription"},
                                        {"$set": doc}, upsert=True)
    await audit_log("tender_sub.config", admin, "platform_config",
                    "tender_builder_subscription", payload.model_dump())
    return {"ok": True, **doc}


# ----------------------- Stripe subscription checkout (Flow B reuse) -----------------------

class SubCheckoutIn(BaseModel):
    origin_url: str


@router.post("/subscription/checkout")
async def subscribe_checkout(payload: SubCheckoutIn, vendor=Depends(current_vendor)):
    vdoc = await _vendor_doc(vendor)
    cfg = await _ta_sub_config(vendor_country(vdoc))
    amount = float(cfg.get("amount") or 0)
    if not cfg.get("enabled") or amount <= 0:
        raise HTTPException(status_code=400, detail="No paid subscription is active for your country right now.")
    currency = (cfg.get("currency") or "usd").lower()
    from pmc_lib.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    api_key = os.environ["STRIPE_API_KEY"]
    checkout = StripeCheckout(api_key=api_key, webhook_url="")
    origin = payload.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=amount, currency=currency,
        success_url=f"{origin}/vendor/tender-builder?sub_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/vendor/tender-builder?sub_cancel=1",
        metadata={"purpose": "tender_builder_sub", "vendor_id": vendor["id"]},
    )
    session = await checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "purpose": "tender_builder_sub",
        "vendor_id": vendor["id"], "amount": amount, "currency": currency,
        "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id}


@router.get("/subscription/checkout/status/{session_id}")
async def subscribe_status(session_id: str, vendor=Depends(current_vendor)):
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if rec.get("payment_status") != "paid":
        try:
            from pmc_lib.payments.stripe.checkout import StripeCheckout
            checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
            s = await checkout.get_checkout_status(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
                await _activate_subscription(rec.get("vendor_id"))
                rec = await db.payment_transactions.find_one({"session_id": session_id})
        except Exception:
            pass
    return {"session_id": session_id, "status": rec["status"], "payment_status": rec["payment_status"]}


async def _activate_subscription(vendor_id: Optional[str]):
    if not vendor_id:
        return
    from bson import ObjectId
    v = await db.vendors.find_one({"_id": ObjectId(vendor_id)})
    cfg = await _ta_sub_config(vendor_country(v or {}))
    days = int(cfg.get("period_days") or 365)
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    await db.vendors.update_one({"_id": ObjectId(vendor_id)},
        {"$set": {"tender_builder_sub": {"active": True, "expires_at": expires,
                                         "activated_at": now_iso()}}})


# ----------------------- vendor tender drafting -----------------------

class VendorTenderIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str = Field(min_length=3)
    description: str = Field(min_length=10)
    category: str
    submission_deadline: str
    document_type: str = "tender"
    delivery_country: str = "KZ"
    budget_currency: str = "USD"
    budget_amount: Optional[float] = Field(default=None, ge=0)


def _clean(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k in CORE_FIELDS}


@router.post("")
async def create_vendor_tender(payload: VendorTenderIn, vendor=Depends(current_vendor)):
    await _require_build_access(vendor)
    vdoc = await _vendor_doc(vendor)
    ref = "VT-" + secrets.token_hex(4).upper()
    doc = {
        **_clean(payload.model_dump()),
        "notice_ref": ref,
        "origin": "vendor",
        "review_status": "draft",
        "is_published": False,
        "prepared_by_vendor_ref": vdoc.get("vendor_ref"),
        "prepared_by_vendor_id": vendor["id"],
        "author_name": vdoc.get("company_name") or vendor.get("email"),
        "created_at": now_iso(),
    }
    await db.notices.insert_one(doc)
    await audit_log("vendor_tender.create", vendor, "notice", ref,
                    {"title": doc["title"], "author": doc["author_name"]})
    return {"ok": True, "notice_ref": ref, "review_status": "draft"}


async def _owned_draft(ref: str, vendor: dict) -> dict:
    n = await db.notices.find_one({"notice_ref": ref, "origin": "vendor"})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    if n.get("prepared_by_vendor_id") != vendor["id"]:
        raise HTTPException(status_code=403, detail="This is not your tender.")
    return n


@router.put("/{ref}")
async def update_vendor_tender(ref: str, payload: VendorTenderIn, vendor=Depends(current_vendor)):
    n = await _owned_draft(ref, vendor)
    if n.get("review_status") not in ("draft", "changes_requested"):
        raise HTTPException(status_code=409,
            detail=f"This tender is '{n.get('review_status')}' and can't be edited now.")
    await db.notices.update_one({"notice_ref": ref},
        {"$set": {**_clean(payload.model_dump()), "updated_at": now_iso()}})
    await audit_log("vendor_tender.update", vendor, "notice", ref, {})
    return {"ok": True, "notice_ref": ref}


@router.post("/{ref}/submit")
async def submit_vendor_tender(ref: str, vendor=Depends(current_vendor)):
    n = await _owned_draft(ref, vendor)
    if n.get("review_status") not in ("draft", "changes_requested"):
        raise HTTPException(status_code=409, detail=f"Already {n.get('review_status')}.")
    await db.notices.update_one({"notice_ref": ref},
        {"$set": {"review_status": "submitted", "submitted_at": now_iso()}})
    await audit_log("vendor_tender.submit", vendor, "notice", ref, {})
    return {"ok": True, "review_status": "submitted"}


@router.get("/mine")
async def my_vendor_tenders(vendor=Depends(current_vendor)):
    cur = db.notices.find({"origin": "vendor", "prepared_by_vendor_id": vendor["id"]}).sort("created_at", -1)
    return {"items": [_out(d) async for d in cur]}


# ----------------------- reviewer (PMC) review queue — reviewer role ONLY -----------------------

class ReviewDecisionIn(BaseModel):
    note: Optional[str] = None


@router.get("/review/queue")
async def review_queue(status: Optional[str] = "submitted",
                       officer=Depends(require_role("reviewer"))):
    q = {"origin": "vendor"}
    if status:
        q["review_status"] = status
    cur = db.notices.find(q).sort("submitted_at", -1)
    return {"items": [_out(d) async for d in cur]}


@router.post("/{ref}/approve")
async def approve_vendor_tender(ref: str, payload: ReviewDecisionIn,
                                officer=Depends(require_role("reviewer"))):
    n = await db.notices.find_one({"notice_ref": ref, "origin": "vendor"})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    if n.get("review_status") != "submitted":
        raise HTTPException(status_code=409, detail=f"Tender is '{n.get('review_status')}', not awaiting review.")
    await db.notices.update_one({"notice_ref": ref},
        {"$set": {"review_status": "approved", "is_published": True,
                  "published_at": now_iso(), "reviewed_by": officer["email"],
                  "reviewed_at": now_iso(), "review_note": payload.note}})
    await audit_log("vendor_tender.approve", officer, "notice", ref,
                    {"author": n.get("author_name"), "published": True})
    return {"ok": True, "review_status": "approved", "is_published": True}


@router.post("/{ref}/request-changes")
async def request_changes(ref: str, payload: ReviewDecisionIn,
                          officer=Depends(require_role("reviewer"))):
    n = await db.notices.find_one({"notice_ref": ref, "origin": "vendor"})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    await db.notices.update_one({"notice_ref": ref},
        {"$set": {"review_status": "changes_requested", "reviewed_by": officer["email"],
                  "reviewed_at": now_iso(), "review_note": payload.note}})
    await audit_log("vendor_tender.changes", officer, "notice", ref, {"note": payload.note})
    return {"ok": True, "review_status": "changes_requested"}


@router.post("/{ref}/reject")
async def reject_vendor_tender(ref: str, payload: ReviewDecisionIn,
                               officer=Depends(require_role("reviewer"))):
    n = await db.notices.find_one({"notice_ref": ref, "origin": "vendor"})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    await db.notices.update_one({"notice_ref": ref},
        {"$set": {"review_status": "rejected", "is_published": False,
                  "reviewed_by": officer["email"], "reviewed_at": now_iso(),
                  "review_note": payload.note}})
    await audit_log("vendor_tender.reject", officer, "notice", ref, {"note": payload.note})
    return {"ok": True, "review_status": "rejected"}
