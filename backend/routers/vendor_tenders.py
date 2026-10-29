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
    scope_rules, vendor_scope_snapshot,
)
from routers._fees import (tender_builder_fees, upfront_quote, credit_required,
                           paid_credit, issue_receipt)
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


# ----------------------- vendor scope rules -----------------------

@router.get("/scope")
async def my_scope(vendor=Depends(current_vendor)):
    return await vendor_scope_snapshot(vendor["id"])


@router.get("/scope-rules")
async def get_scope_rules(admin=Depends(require_role("admin", "reviewer"))):
    return await scope_rules()


class ScopeRulesIn(BaseModel):
    restrict_to_approved_categories: bool = True
    max_pending_tenders: int = Field(ge=0, le=100)
    max_pending_category_requests: int = Field(ge=0, le=100)


@router.put("/scope-rules")
async def set_scope_rules(payload: ScopeRulesIn, admin=Depends(require_role("admin", "reviewer"))):
    body = payload.model_dump()
    await db.platform_config.update_one({"key": "vendor_scope_rules"},
        {"$set": {"key": "vendor_scope_rules", **body, "updated_at": now_iso(),
                  "updated_by": admin["email"]}}, upsert=True)
    await audit_log("vendor_scope.rules", admin, "platform_config", "vendor_scope_rules", body)
    return body


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
    if not rec or rec.get("vendor_id") != vendor["id"]:
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


async def activate_subscription(vendor_id: Optional[str]):
    await _activate_subscription(vendor_id)


# ----------------------- per-tender fees (Fee Type master → Stripe) -----------------------

async def _own_template(tid: str, vendor: dict) -> dict:
    from bson import ObjectId
    try:
        doc = await db.tender_templates.find_one({"_id": ObjectId(tid)})
    except Exception:
        doc = None
    if not doc or doc.get("owner_vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Template not found")
    return doc


@router.get("/fees/{tid}")
async def tender_fees(tid: str, vendor=Depends(current_vendor)):
    doc = await _own_template(tid, vendor)
    vdoc = await _vendor_doc(vendor)
    return {"fees": await tender_builder_fees(vendor_country(vdoc), doc)}


class FeeCheckoutIn(BaseModel):
    fee_code: str
    origin_url: str


@router.post("/fees/{tid}/checkout")
async def tender_fee_checkout(tid: str, payload: FeeCheckoutIn, vendor=Depends(current_vendor)):
    doc = await _own_template(tid, vendor)
    vdoc = await _vendor_doc(vendor)
    fee = next((f for f in await tender_builder_fees(vendor_country(vdoc), doc)
                if f["code"] == payload.fee_code), None)
    if not fee:
        raise HTTPException(status_code=404, detail="This fee does not apply to this tender")
    if fee["needs_value"]:
        raise HTTPException(status_code=422, detail="Enter the tender value and save before paying this fee")
    if fee["paid"]:
        raise HTTPException(status_code=409, detail="Already paid")
    amount = float(fee["outstanding"])
    from pmc_lib.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
    origin = payload.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=amount, currency=fee["currency"].lower(),
        success_url=f"{origin}/vendor/tender-builder?fee_session={{CHECKOUT_SESSION_ID}}&tid={tid}",
        cancel_url=f"{origin}/vendor/tender-builder?fee_cancel=1",
        metadata={"purpose": "tender_fee", "vendor_id": vendor["id"], "template_id": tid,
                  "fee_code": fee["code"]},
    )
    session = await checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "purpose": "tender_fee", "vendor_id": vendor["id"],
        "template_id": tid, "fee_code": fee["code"], "rule_id": fee["rule_id"],
        "amount": amount, "currency": fee["currency"].lower(),
        "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id}


async def apply_tender_fee_payment(session_id: str) -> None:
    """Credit a paid tender-fee session onto its template exactly once."""
    from bson import ObjectId
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "purpose": "tender_fee", "credited": {"$ne": True}},
        {"$set": {"credited": True}})
    if not tx:
        return
    await db.tender_templates.update_one({"_id": ObjectId(tx["template_id"])},
        {"$inc": {f"fees_paid.{tx['fee_code']}.amount": float(tx["amount"])},
         "$set": {f"fees_paid.{tx['fee_code']}.currency": tx["currency"],
                  f"fees_paid.{tx['fee_code']}.last_session": session_id,
                  f"fees_paid.{tx['fee_code']}.paid_at": now_iso()}})
    await audit_log("tender_fee.paid", {"id": tx["vendor_id"], "role": "vendor"}, "tender_template",
                    tx["template_id"], {"fee": tx["fee_code"], "amount": tx["amount"]})
    t = await db.tender_templates.find_one({"_id": ObjectId(tx["template_id"])}, {"name": 1, "header": 1}) or {}
    ft = await db.fee_types.find_one({"code": tx["fee_code"]}) or {}
    await issue_receipt(tx["vendor_id"], "tender_fee",
                        [{"code": tx["fee_code"], "name": ft.get("name") or tx["fee_code"], "amount": tx["amount"]}],
                        tx["currency"], session_id,
                        {"template_id": tx["template_id"],
                         "tender_name": (t.get("header") or {}).get("work_title") or t.get("name"),
                         "category": (t.get("header") or {}).get("product_category")})


# ----------------------- start-of-tender gate (upfront fees before any building) -----------------------

class StartQuoteIn(BaseModel):
    category: str = Field(min_length=1)
    tender_value: Optional[float] = Field(default=None, ge=0)


class StartCheckoutIn(StartQuoteIn):
    origin_url: str


@router.get("/start/check")
async def start_check(vendor=Depends(current_vendor)):
    vdoc = await _vendor_doc(vendor)
    required = await credit_required(vendor_country(vdoc))
    cr = await paid_credit(vendor["id"]) if required else None
    return {"required": required,
            "credit": {"id": str(cr["_id"]), "category": cr["category"],
                       "tender_value": cr.get("tender_value")} if cr else None}


async def _quote(vendor: dict, payload: StartQuoteIn) -> dict:
    vdoc = await _vendor_doc(vendor)
    snap = await vendor_scope_snapshot(vendor["id"])
    if snap["rules"]["restrict_to_approved_categories"] and \
            payload.category.strip().lower() not in {c.strip().lower() for c in snap["approved_categories"]}:
        raise HTTPException(status_code=403, detail=f"You are not approved for '{payload.category}'.")
    fees = await upfront_quote(vendor_country(vdoc), payload.category.strip(), payload.tender_value)
    if any(f["needs_value"] for f in fees):
        raise HTTPException(status_code=422, detail="Enter the estimated tender value to calculate the fee.")
    currencies = {f["currency"] for f in fees}
    if len(currencies) > 1:
        raise HTTPException(status_code=422, detail="Fee rules for this category use different currencies — ask PMC to align them.")
    total = round(sum(f["amount"] for f in fees), 2)
    return {"fees": fees, "total": total, "currency": currencies.pop() if currencies else None}


@router.post("/start/quote")
async def start_quote(payload: StartQuoteIn, vendor=Depends(current_vendor)):
    return await _quote(vendor, payload)


@router.post("/start/checkout")
async def start_checkout(payload: StartCheckoutIn, vendor=Depends(current_vendor)):
    q = await _quote(vendor, payload)
    credit = {"vendor_id": vendor["id"], "category": payload.category.strip(),
              "tender_value": payload.tender_value,
              "fees": {f["code"]: {"amount": f["amount"], "currency": f["currency"].lower()} for f in q["fees"]},
              "lines": [{"code": f["code"], "name": f["name"], "amount": f["amount"]} for f in q["fees"]],
              "total": q["total"], "currency": (q["currency"] or "usd").lower(),
              "status": "pending", "created_at": now_iso()}
    if q["total"] <= 0:
        credit["status"] = "paid"
        r = await db.tender_credits.insert_one(credit)
        return {"free": True, "credit_id": str(r.inserted_id)}
    r = await db.tender_credits.insert_one(credit)
    from pmc_lib.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
    origin = payload.origin_url.rstrip("/")
    session = await checkout.create_checkout_session(CheckoutSessionRequest(
        amount=q["total"], currency=credit["currency"],
        success_url=f"{origin}/vendor/tender-builder?credit_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/vendor/tender-builder?fee_cancel=1",
        metadata={"purpose": "tender_credit", "vendor_id": vendor["id"], "credit_id": str(r.inserted_id)}))
    await db.tender_credits.update_one({"_id": r.inserted_id}, {"$set": {"session_id": session.session_id}})
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "purpose": "tender_credit", "vendor_id": vendor["id"],
        "credit_id": str(r.inserted_id), "amount": q["total"], "currency": credit["currency"],
        "status": "initiated", "payment_status": "pending",
        "created_at": now_iso(), "updated_at": now_iso()})
    return {"checkout_url": session.url, "session_id": session.session_id}


async def apply_credit_payment(session_id: str) -> None:
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "purpose": "tender_credit", "credited": {"$ne": True}},
        {"$set": {"credited": True}})
    if not tx:
        return
    from bson import ObjectId
    cr = await db.tender_credits.find_one_and_update(
        {"_id": ObjectId(tx["credit_id"]), "status": "pending"},
        {"$set": {"status": "paid", "paid_at": now_iso()}})
    if cr:
        await issue_receipt(tx["vendor_id"], "tender_start", cr.get("lines") or [], cr["currency"],
                            session_id, {"credit_id": tx["credit_id"], "category": cr["category"]})


@router.get("/start/checkout/status/{session_id}")
async def start_status(session_id: str, vendor=Depends(current_vendor)):
    rec = await db.payment_transactions.find_one({"session_id": session_id, "purpose": "tender_credit"})
    if not rec or rec.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if rec.get("payment_status") != "paid":
        try:
            from pmc_lib.payments.stripe.checkout import StripeCheckout
            checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
            s = await checkout.get_checkout_status(session_id)
            if s.payment_status == "paid":
                await db.payment_transactions.update_one({"session_id": session_id},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
        except Exception:
            pass
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if rec.get("payment_status") == "paid":
        await apply_credit_payment(session_id)
    return {"session_id": session_id, "payment_status": rec["payment_status"], "credit_id": rec.get("credit_id")}


@router.get("/receipts")
async def my_receipts(vendor=Depends(current_vendor)):
    cur = db.fee_receipts.find({"vendor_id": vendor["id"]}).sort("paid_at", -1).limit(200)
    return {"items": [_out(r) async for r in cur]}


@router.get("/fees/checkout/status/{session_id}")
async def tender_fee_status(session_id: str, vendor=Depends(current_vendor)):
    rec = await db.payment_transactions.find_one({"session_id": session_id, "purpose": "tender_fee"})
    if not rec or rec.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if rec.get("payment_status") != "paid":
        try:
            from pmc_lib.payments.stripe.checkout import StripeCheckout
            checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
            s = await checkout.get_checkout_status(session_id)
            if s.payment_status == "paid":
                await db.payment_transactions.update_one({"session_id": session_id},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
        except Exception:
            pass
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if rec.get("payment_status") == "paid":
        await apply_tender_fee_payment(session_id)
    return {"session_id": session_id, "status": rec["status"], "payment_status": rec["payment_status"],
            "template_id": rec.get("template_id"), "fee_code": rec.get("fee_code")}


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
