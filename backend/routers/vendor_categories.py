"""Vendor Category Interest flow (v50l).

Suppliers add categories they're interested in bidding on; the admin
reviews and approves/rejects each request. Approved categories land
in the vendor's `business_categories` list so tender matching picks
them up on the next bid search.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log
from routers._tender_access import scope_rules
import os

FREE_CATEGORY_MSG = ("Registration is free for one category. Every additional category needs a "
                     "payment before PMC can approve it.")
OPEN = ["pending", "payment_pending"]


async def _category_fee(v: dict, category_name: str) -> dict:
    """Fee for one more category: first category free; extra ones priced by the
    'registration' Fee rule for the vendor's country (category-specific wins)."""
    from routers._tender_access import vendor_country
    from routers._fees import compute_amount
    from routers.pricing import vendor_waived
    if vendor_waived(v, "registration"):
        return {"amount": 0.0, "currency": None, "required": False, "reason": "waived"}
    approved = list((v or {}).get("business_categories") or [])
    open_paid = await db.vendor_category_requests.count_documents(
        {"vendor_ref": v.get("vendor_ref"), "status": {"$in": OPEN}})
    if not approved and not open_paid:
        return {"amount": 0.0, "currency": None, "required": False, "reason": "first_free"}
    country = vendor_country(v)
    from routers._fees import find_rule
    best = await find_rule("registration", country, category_name)
    amount = compute_amount(best, None) if best else None
    if not amount:
        return {"amount": 0.0, "currency": None, "required": False, "reason": "no_price"}
    return {"amount": float(amount), "currency": (best.get("currency") or "USD").upper(),
            "required": True, "rule_id": str(best["_id"])}

router = APIRouter(tags=["vendor-categories"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


class CategoryRequestIn(BaseModel):
    category_code: str = Field(min_length=1, max_length=60)
    category_name: str = Field(min_length=1, max_length=200)
    rationale: Optional[str] = Field(default=None, max_length=600)
    # v56s — optional Sector → Contract-type taxonomy context for the request.
    sector_code: Optional[str] = Field(default=None, max_length=60)
    sector_name: Optional[str] = Field(default=None, max_length=200)
    contract_type_code: Optional[str] = Field(default=None, max_length=60)
    contract_type_name: Optional[str] = Field(default=None, max_length=200)


# ---------- Vendor side ----------
@router.get("/api/v1/vendor/categories/mine")
async def my_categories(vendor=Depends(current_vendor)):
    """Approved categories + any pending requests, for the signed-in vendor."""
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    approved = list((v or {}).get("business_categories") or [])
    pending = [_out(r) async for r in db.vendor_category_requests.find(
        {"vendor_ref": vendor["vendor_ref"], "status": {"$in": OPEN}}
    ).sort("requested_at", -1)]
    recent = [_out(r) async for r in db.vendor_category_requests.find(
        {"vendor_ref": vendor["vendor_ref"], "status": {"$in": ["approved", "rejected"]}}
    ).sort("decided_at", -1).limit(10)]
    return {"approved": approved, "pending": pending, "recent": recent}


@router.post("/api/v1/vendor/categories/request")
async def request_category(payload: CategoryRequestIn, vendor=Depends(current_vendor)):
    """Vendor requests a new category. Dedupes by (vendor_ref, category_code)
    across pending/approved so the same category can't be queued twice."""
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if payload.category_name in ((v or {}).get("business_categories") or []):
        raise HTTPException(status_code=409, detail="Category already in your approved list")
    dup = await db.vendor_category_requests.find_one({
        "vendor_ref": vendor["vendor_ref"],
        "category_code": payload.category_code,
        "status": {"$in": OPEN},
    })
    if dup:
        raise HTTPException(status_code=409, detail="A pending request for this category already exists")
    cap = int((await scope_rules())["max_pending_category_requests"] or 0)
    if cap:
        n = await db.vendor_category_requests.count_documents(
            {"vendor_ref": vendor["vendor_ref"], "status": {"$in": OPEN}})
        if n >= cap:
            raise HTTPException(status_code=429,
                detail=f"You already have {n} category request(s) pending (limit {cap}). Wait for a decision first.")
    # Verify the category exists in the master.
    master = await db.categories.find_one({"code": payload.category_code, "is_active": True})
    if not master:
        raise HTTPException(status_code=400, detail="Unknown or inactive category")
    fee = await _category_fee(v or {}, payload.category_name)
    doc = {
        "fee_amount": fee["amount"], "fee_currency": fee["currency"],
        "payment_status": "unpaid" if fee["required"] else "not_required",
        "vendor_ref": vendor["vendor_ref"],
        "vendor_email": vendor["email"],
        "vendor_company": v.get("company_name") if v else None,
        "category_code": payload.category_code,
        "category_name": payload.category_name,
        "rationale": payload.rationale,
        "sector_code": payload.sector_code,
        "sector_name": payload.sector_name,
        "contract_type_code": payload.contract_type_code,
        "contract_type_name": payload.contract_type_name,
        "status": "pending",
        "requested_at": now_iso(),
    }
    res = await db.vendor_category_requests.insert_one(doc)
    doc["_id"] = res.inserted_id
    if fee["required"]:
        from routers.payments_extra import post_vendor_message
        await post_vendor_message(vendor["vendor_ref"], "payment", f"Payment needed — {payload.category_name}",
            f"<p>{FREE_CATEGORY_MSG}</p><p>The fee for <b>{payload.category_name}</b> is "
            f"<b>{fee['currency']} {fee['amount']:,.2f}</b>. Pay it from My categories so PMC can approve it.</p>",
            "/vendor/categories")
    return {**_out(doc), "fee_message": FREE_CATEGORY_MSG if fee["required"] else None}


@router.get("/api/v1/vendor/categories/fee-quote")
async def category_fee_quote(category_name: str, vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    return {**(await _category_fee(v or {}, category_name)), "message": FREE_CATEGORY_MSG}


async def _category_checkout(req: dict, origin: str) -> dict:
    from pmc_lib.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
    session = await checkout.create_checkout_session(CheckoutSessionRequest(
        amount=float(req["fee_amount"]), currency=req["fee_currency"].lower(),
        success_url=f"{origin.rstrip('/')}/vendor/categories?cat_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin.rstrip('/')}/vendor/categories",
        metadata={"purpose": "category_fee", "request_id": str(req["_id"]), "vendor_ref": req["vendor_ref"]}))
    v = await db.vendors.find_one({"vendor_ref": req["vendor_ref"]}, {"_id": 1})
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "purpose": "category_fee", "request_id": str(req["_id"]),
        "vendor_id": str(v["_id"]) if v else None, "vendor_ref": req["vendor_ref"],
        **{k: v[k] for k in ("partner_code", "partner_id") if v and v.get(k)},
        "amount": float(req["fee_amount"]), "currency": req["fee_currency"].lower(),
        "status": "initiated", "payment_status": "pending", "created_at": now_iso(), "updated_at": now_iso()})
    return {"checkout_url": session.url, "session_id": session.session_id}


class CatCheckoutIn(BaseModel):
    origin_url: str


@router.post("/api/v1/vendor/categories/requests/{request_id}/checkout")
async def category_checkout(request_id: str, payload: CatCheckoutIn, vendor=Depends(current_vendor)):
    req = await db.vendor_category_requests.find_one({"_id": ObjectId(request_id), "vendor_ref": vendor["vendor_ref"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.get("payment_status") != "unpaid" or req["status"] not in OPEN:
        raise HTTPException(status_code=409, detail="No payment is due for this request")
    return await _category_checkout(req, payload.origin_url)


async def apply_category_payment(session_id: str) -> None:
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "purpose": "category_fee", "credited": {"$ne": True}},
        {"$set": {"credited": True}})
    if not tx:
        return
    req = await db.vendor_category_requests.find_one_and_update(
        {"_id": ObjectId(tx["request_id"]), "payment_status": "unpaid", "status": {"$in": OPEN}},
        {"$set": {"payment_status": "paid", "paid_at": now_iso(), "payment_session": session_id,
                  "status": "pending"}})
    if not req:
        await db.payment_transactions.update_one({"session_id": session_id},
            {"$set": {"duplicate": True, "needs_refund": True, "updated_at": now_iso()}})
        await audit_log("vendor.category_duplicate_payment", {"id": tx.get("vendor_id"), "role": "vendor"},
                        "vendor", tx.get("vendor_ref"), {"session_id": session_id, "amount": tx["amount"]})
        return
    if req and tx.get("vendor_id"):
        from routers._fees import issue_receipt
        await issue_receipt(tx["vendor_id"], "category_fee",
                            [{"code": "registration", "name": "Additional category", "amount": tx["amount"]}],
                            tx["currency"], session_id, {"category": req.get("category_name"),
                                                          "request_id": tx["request_id"]})


@router.get("/api/v1/vendor/categories/checkout/status/{session_id}")
async def category_checkout_status(session_id: str, vendor=Depends(current_vendor)):
    rec = await db.payment_transactions.find_one({"session_id": session_id, "purpose": "category_fee"})
    if not rec or rec.get("vendor_ref") != vendor["vendor_ref"]:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if rec.get("payment_status") != "paid":
        try:
            from pmc_lib.payments.stripe.checkout import StripeCheckout
            s = await StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="").get_checkout_status(session_id)
            if s.payment_status == "paid":
                await db.payment_transactions.update_one({"session_id": session_id},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
        except Exception:
            pass
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if rec.get("payment_status") == "paid":
        await apply_category_payment(session_id)
    return {"payment_status": rec["payment_status"]}


# ---------- Admin side ----------
@router.get("/api/v1/vendors/category-requests")
async def list_category_requests(status: str = "pending",
                                   admin=Depends(require_role("admin", "reviewer"))):
    cursor = db.vendor_category_requests.find({"status": status})\
        .sort("requested_at", -1).limit(500)
    return [_out(r) async for r in cursor]


class DecisionIn(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=400)


@router.post("/api/v1/vendors/category-requests/{request_id}/approve")
async def approve_category_request(request_id: str, payload: DecisionIn,
                                      admin=Depends(require_role("admin", "reviewer"))):
    req = await db.vendor_category_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Already {req['status']}")
    if req.get("payment_status") == "unpaid":
        raise HTTPException(status_code=409,
            detail="Payment pending for this additional category — use 'Payment pending — send back' instead of approving.")
    now = now_iso()
    from routers.payments_extra import post_vendor_message
    await post_vendor_message(req["vendor_ref"], "category", f"Category approved — {req['category_name']}",
        f"<p>PMC approved <b>{req['category_name']}</b>. You can now bid on tenders in this category.</p>",
        "/vendor/categories")
    await db.vendors.update_one(
        {"vendor_ref": req["vendor_ref"]},
        [{"$set": {"business_categories": {"$setUnion": [
            {"$ifNull": ["$business_categories", []]}, [req["category_name"]]]}}}],
    )
    await db.vendor_category_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "approved", "decided_at": now,
                   "decided_by": admin["email"], "decision_notes": payload.notes}},
    )
    await audit_log("vendor.category_approve", admin, "vendor", req["vendor_ref"],
                     {"category": req["category_name"], "code": req["category_code"]})
    return {"ok": True}


class SendBackIn(BaseModel):
    origin_url: str
    notes: Optional[str] = Field(default=None, max_length=400)


@router.post("/api/v1/vendors/category-requests/{request_id}/payment-pending")
async def send_back_payment_pending(request_id: str, payload: SendBackIn,
                                    admin=Depends(require_role("admin", "reviewer"))):
    req = await db.vendor_category_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] not in OPEN or req.get("payment_status") != "unpaid":
        raise HTTPException(status_code=409, detail="No unpaid fee on this request")
    chk = await _category_checkout(req, payload.origin_url)
    await db.vendor_category_requests.update_one({"_id": req["_id"]},
        {"$set": {"status": "payment_pending", "sent_back_at": now_iso(), "sent_back_by": admin["email"],
                  "decision_notes": payload.notes}})
    from notify import vendor_confirm
    from html import escape as _esc
    notes = _esc(payload.notes) if payload.notes else None
    amt = f"{req['fee_currency']} {float(req['fee_amount']):,.2f}"
    body = (f"<p>Your request to add the category <b>{req['category_name']}</b> has been reviewed, "
            f"but the payment is still pending.</p><p>{FREE_CATEGORY_MSG}</p>"
            f"<p><b>Amount due:</b> {amt}</p>"
            f"{'<p><b>Note from PMC:</b> ' + notes + '</p>' if notes else ''}"
            f"<p>Pay securely here (link valid 24 hours): <a href='{chk['checkout_url']}'>Pay {amt}</a></p>"
            f"<p>After 24 hours, pay from <a href='{payload.origin_url.rstrip('/')}/vendor/categories'>My categories</a> in the supplier portal.</p>")
    await vendor_confirm(req.get("vendor_email"), f"Payment pending — {req['category_name']}", body,
                         f"Pay {amt}", chk["checkout_url"])
    from routers.payments_extra import post_vendor_message
    await post_vendor_message(req["vendor_ref"], "payment", f"Payment pending — {req['category_name']}",
        f"<p>Your request to add <b>{req['category_name']}</b> was sent back: the payment of <b>{amt}</b> is pending.</p>"
        f"<p>{FREE_CATEGORY_MSG}</p>{'<p><b>Note from PMC:</b> ' + notes + '</p>' if notes else ''}",
        "/vendor/categories")
    await audit_log("vendor.category_payment_pending", admin, "vendor", req["vendor_ref"],
                    {"category": req["category_name"], "amount": req["fee_amount"]})
    return {"ok": True, "status": "payment_pending", "checkout_url": chk["checkout_url"]}


@router.post("/api/v1/vendors/category-requests/{request_id}/reject")
async def reject_category_request(request_id: str, payload: DecisionIn,
                                     admin=Depends(require_role("admin", "reviewer"))):
    req = await db.vendor_category_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] not in OPEN:
        raise HTTPException(status_code=409, detail=f"Already {req['status']}")
    if not (payload.notes or "").strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    await db.vendor_category_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {"status": "rejected", "decided_at": now_iso(),
                   "decided_by": admin["email"], "decision_notes": payload.notes}},
    )
    await audit_log("vendor.category_reject", admin, "vendor", req["vendor_ref"],
                     {"category": req["category_name"], "reason": payload.notes})
    return {"ok": True}
