"""Extra payment flows: tender document download fee, tender hosting fee, data intel
service requests, refund alerts, category upsell notices and the 3-day category
payment reminder cron."""
import hmac
import os
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import config
from audit import audit_log
from db import db
from models.base import BaseDocument, now_iso
from notify import vendor_confirm
from routers._fees import compute_amount, find_rule, issue_receipt
from routers.vendor_auth import current_vendor
from security import current_admin, require_role

router = APIRouter(tags=["payments-extra"])


def _out(d):
    return BaseDocument.out(d)


def _oid(x: str) -> str:
    if not ObjectId.is_valid(x):
        raise HTTPException(status_code=404, detail="Not found")
    return x


def _site() -> str:
    return (config.FRONTEND_URL or "").rstrip("/")


async def _checkout(amount: float, currency: str, purpose: str, success_path: str,
                    cancel_path: str, origin: str, meta: dict, record: dict) -> dict:
    from pmc_lib.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="")
    origin = origin.rstrip("/")
    s = await sc.create_checkout_session(CheckoutSessionRequest(
        amount=float(amount), currency=currency.lower(),
        success_url=f"{origin}{success_path}{'&' if '?' in success_path else '?'}session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}{cancel_path}", metadata={"purpose": purpose, **meta}))
    await db.payment_transactions.insert_one({
        "session_id": s.session_id, "purpose": purpose, "amount": float(amount),
        "currency": currency.lower(), "status": "initiated", "payment_status": "pending",
        **record, "created_at": now_iso(), "updated_at": now_iso()})
    return {"checkout_url": s.url, "session_id": s.session_id}


async def _sync_status(session_id: str) -> dict:
    rec = await db.payment_transactions.find_one({"session_id": session_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if rec.get("payment_status") != "paid":
        try:
            from pmc_lib.payments.stripe.checkout import StripeCheckout
            st = await StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="").get_checkout_status(session_id)
            if st.payment_status == "paid":
                await db.payment_transactions.update_one({"session_id": session_id},
                    {"$set": {"status": "completed", "payment_status": "paid", "updated_at": now_iso()}})
        except Exception:
            pass
        rec = await db.payment_transactions.find_one({"session_id": session_id})
    if rec.get("payment_status") == "paid":
        await apply_extra_payment(session_id)
    return rec


async def apply_extra_payment(session_id: str) -> None:
    tx = await db.payment_transactions.find_one_and_update(
        {"session_id": session_id, "payment_status": "paid", "credited": {"$ne": True}},
        {"$set": {"credited": True}})
    if not tx:
        return
    p = tx["purpose"]
    lines = [{"code": p, "name": tx.get("label") or p, "amount": tx["amount"]}]
    if p == "doc_fee":
        await db.doc_purchases.update_one({"vendor_id": tx["vendor_id"], "notice_ref": tx["notice_ref"]},
            {"$set": {"paid": True, "paid_at": now_iso(), "session_id": session_id,
                      "amount": tx["amount"], "currency": tx["currency"]}}, upsert=True)
        await issue_receipt(tx["vendor_id"], "doc_fee", lines, tx["currency"], session_id,
                            {"notice_ref": tx["notice_ref"], "tender_name": tx.get("notice_title")})
    elif p == "hosting_fee":
        await db.notices.update_one({"notice_ref": tx["notice_ref"]},
            {"$set": {"hosting_fee.status": "paid", "hosting_fee.paid_at": now_iso(),
                      "is_published": True, "published_at": now_iso()}})
        await audit_log("notice.hosting_fee_paid", {"email": tx.get("payer_email"), "role": "payer"},
                        "notice", tx["notice_ref"], {"amount": tx["amount"]})
        await vendor_confirm(tx.get("payer_email"), f"Receipt \u2014 hosting fee {tx['notice_ref']}",
            f"<p>We received {tx['currency'].upper()} {tx['amount']:,.2f} for hosting tender "
            f"<b>{tx['notice_ref']}</b>. It is now published on PMC Managers.</p>"
            f"<p style='color:#666;font-size:12px'>Payment reference: {session_id}</p>", None, None)
    elif p == "data_intel":
        r = await db.data_intel_requests.find_one_and_update({"_id": ObjectId(tx["request_id"]), "status": "quoted"},
            {"$set": {"status": "paid", "paid_at": now_iso()}})
        if r:
            await issue_receipt(r["vendor_id"], "data_intel", lines, tx["currency"], session_id,
                                {"category": r.get("category"), "tender_name": r.get("subject")})
        else:
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"needs_refund": True}})


@router.get("/api/v1/pay/status/{session_id}")
async def public_pay_status(session_id: str):
    rec = await _sync_status(session_id)
    return {"session_id": session_id, "payment_status": rec["payment_status"],
            "purpose": rec.get("purpose"), "amount": rec.get("amount"), "currency": rec.get("currency")}


# ----------------------- vendor messages (inbox) -----------------------

async def post_vendor_message(vendor_ref: Optional[str], kind: str, subject: str, body: str,
                              link: Optional[str] = None) -> None:
    if vendor_ref:
        await db.messages.insert_one({"to_vendor_ref": vendor_ref, "from": "PMC Managers", "kind": kind,
            "subject": subject, "body": body, "link": link, "created_at": now_iso(), "read": False})


@router.get("/api/v1/vendor/messages")
async def my_messages(vendor=Depends(current_vendor)):
    q = {"to_vendor_ref": vendor.get("vendor_ref")}
    items = [_out(m) async for m in db.messages.find(q).sort("created_at", -1).limit(300)]
    return {"items": items, "unread": sum(1 for m in items if not m.get("read"))}


@router.get("/api/v1/vendor/messages/unread-count")
async def my_unread_count(vendor=Depends(current_vendor)):
    n = await db.messages.count_documents({"to_vendor_ref": vendor.get("vendor_ref"), "read": {"$ne": True}})
    return {"unread": n}


@router.post("/api/v1/vendor/messages/read-all")
async def mark_all_read(vendor=Depends(current_vendor)):
    await db.messages.update_many({"to_vendor_ref": vendor.get("vendor_ref"), "read": {"$ne": True}},
                                  {"$set": {"read": True, "read_at": now_iso()}})
    return {"ok": True}


@router.post("/api/v1/vendor/messages/{mid}/read")
async def mark_message_read(mid: str, vendor=Depends(current_vendor)):
    r = await db.messages.update_one({"_id": ObjectId(_oid(mid)), "to_vendor_ref": vendor.get("vendor_ref")},
                                     {"$set": {"read": True, "read_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ----------------------- category upsell notice -----------------------

async def notify_category_upsell(vdoc: dict, notice: dict) -> None:
    """In-app + email + message when a vendor opens/bids a tender outside their categories."""
    if not vdoc.get("email"):
        return
    cat, ref = notice.get("category"), notice.get("notice_ref")
    key = {"vendor_id": str(vdoc["_id"]), "notice_ref": ref}
    if await db.category_upsell_log.find_one(key):
        return
    await db.category_upsell_log.insert_one({**key, "category": cat, "at": now_iso()})
    link = f"{_site()}/vendor/categories?add={cat}"
    body = (f"<p>You showed interest in tender <b>{notice.get('title') or ref}</b> ({ref}).</p>"
            f"<p>It is in the category <b>{cat}</b>, which is not one of your registered categories. "
            "Registration is free for one category; every additional category needs a payment.</p>"
            "<p>Add the category from <b>My categories</b>, pay the fee, and you can bid once PMC approves it.</p>")
    await db.notifications.insert_one({"user_email": vdoc["email"], "user_ref": vdoc.get("vendor_ref"),
        "role": "vendor", "subject": f"Add '{cat}' to bid on {ref}", "body": body,
        "related_type": "notice", "related_id": ref, "read": False, "created_at": now_iso()})
    await db.messages.insert_one({"to_vendor_ref": vdoc.get("vendor_ref"), "from": "PMC Managers",
        "kind": "category", "subject": f"Category needed for {ref}", "body": body, "link": link,
        "created_at": now_iso(), "read": False})
    await vendor_confirm(vdoc["email"], f"Add the category '{cat}' to bid on {ref}", body,
                         "Add this category", link)


@router.post("/api/v1/notices/{notice_ref}/category-interest")
async def category_interest(notice_ref: str, vendor=Depends(current_vendor)):
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])}) or {}
    cat = (n.get("category") or "").strip()
    mine = {str(c).strip().lower() for c in (v.get("business_categories") or [])}
    registered = not cat or cat.lower() in mine
    pending = await db.vendor_category_requests.find_one(
        {"vendor_ref": v.get("vendor_ref"), "category_name": cat, "status": {"$in": ["pending", "payment_pending"]}})
    if not registered and not pending:
        await notify_category_upsell(v, n)
    return {"category": cat, "registered": registered, "pending_request": _out(pending) if pending else None}


# ----------------------- tender document download fee -----------------------

async def _doc_fee(notice: dict) -> Optional[dict]:
    rule = await find_rule("tender_document_download", notice.get("delivery_country"), notice.get("category"))
    amt = compute_amount(rule, notice.get("budget_amount")) if rule else None
    if not amt:
        return None
    return {"amount": float(amt), "currency": (rule.get("currency") or "USD").upper(), "rule": rule.get("name")}


async def assert_doc_fee_paid(request: Request, notice: dict) -> None:
    fee = await _doc_fee(notice)
    if not fee:
        return
    try:
        if await current_admin(request):
            return
    except Exception:
        pass
    try:
        v = await current_vendor(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Log in as a registered supplier to download tender documents.")
    if not await db.doc_purchases.find_one({"vendor_id": v["id"], "notice_ref": notice["notice_ref"], "paid": True}):
        raise HTTPException(status_code=402, detail={"code": "doc_fee_required", **fee,
            "message": f"A document download fee of {fee['currency']} {fee['amount']:,.2f} applies to this tender. Pay once to download any number of times."})


@router.get("/api/v1/notices/{notice_ref}/doc-fee")
async def doc_fee_quote(notice_ref: str, vendor=Depends(current_vendor)):
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    fee = await _doc_fee(n)
    paid = bool(await db.doc_purchases.find_one({"vendor_id": vendor["id"], "notice_ref": notice_ref, "paid": True}))
    return {"required": bool(fee), "paid": paid, **(fee or {})}


class OriginIn(BaseModel):
    origin_url: str


@router.post("/api/v1/notices/{notice_ref}/doc-fee/checkout")
async def doc_fee_checkout(notice_ref: str, payload: OriginIn, vendor=Depends(current_vendor)):
    n = await db.notices.find_one({"notice_ref": notice_ref, "is_published": True})
    fee = await _doc_fee(n) if n else None
    if not fee:
        raise HTTPException(status_code=404, detail="No document fee applies")
    if await db.doc_purchases.find_one({"vendor_id": vendor["id"], "notice_ref": notice_ref, "paid": True}):
        raise HTTPException(status_code=409, detail="Already paid")
    return await _checkout(fee["amount"], fee["currency"], "doc_fee",
        f"/notices/{notice_ref}?doc_paid=1", f"/notices/{notice_ref}", payload.origin_url,
        {"notice_ref": notice_ref, "vendor_id": vendor["id"]},
        {"vendor_id": vendor["id"], "notice_ref": notice_ref, "notice_title": n.get("title"),
         "label": "Tender document download"})


@router.get("/api/v1/notices/doc-fee/status/{session_id}")
async def doc_fee_status(session_id: str, vendor=Depends(current_vendor)):
    rec = await db.payment_transactions.find_one({"session_id": session_id, "purpose": "doc_fee"})
    if not rec or rec.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Transaction not found")
    rec = await _sync_status(session_id)
    return {"payment_status": rec["payment_status"], "notice_ref": rec.get("notice_ref")}


# ----------------------- tender hosting fee (admin-created notices) -----------------------

class HostingIn(BaseModel):
    payer_email: str = Field(min_length=5, pattern=r".+@.+\..+")


@router.get("/api/v1/notices/{notice_ref}/hosting-fee")
async def hosting_fee_quote(notice_ref: str, admin=Depends(require_role("admin"))):
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    rule = await find_rule("tender_hosting", n.get("delivery_country"), n.get("category"))
    amt = compute_amount(rule, n.get("budget_amount")) if rule else None
    return {"required": bool(amt), "amount": amt, "currency": (rule or {}).get("currency"),
            "rule": (rule or {}).get("name"), "hosting_fee": n.get("hosting_fee")}


@router.post("/api/v1/notices/{notice_ref}/hosting-fee/request")
async def hosting_fee_request(notice_ref: str, payload: HostingIn, admin=Depends(require_role("admin"))):
    q = await hosting_fee_quote(notice_ref, admin)
    if not q["required"]:
        raise HTTPException(status_code=404, detail="No hosting fee rule applies to this notice (country/category/value).")
    n = await db.notices.find_one({"notice_ref": notice_ref})
    if n.get("is_published"):
        raise HTTPException(status_code=409, detail="Notice is already published")
    chk = await _checkout(q["amount"], q["currency"], "hosting_fee", "/pay/complete", "/pay/complete?cancel=1",
        _site(), {"notice_ref": notice_ref}, {"notice_ref": notice_ref, "payer_email": payload.payer_email,
                                              "label": "Tender hosting fee"})
    await db.notices.update_one({"notice_ref": notice_ref}, {"$set": {"hosting_fee": {
        "status": "unpaid", "amount": q["amount"], "currency": q["currency"], "payer_email": payload.payer_email,
        "session_id": chk["session_id"], "requested_at": now_iso(), "requested_by": admin["email"]}}})
    amt = f"{q['currency']} {q['amount']:,.2f}"
    await vendor_confirm(payload.payer_email, f"Hosting fee for your tender {notice_ref}",
        f"<p>Your tender <b>{n.get('title') or notice_ref}</b> is ready to be hosted on PMC Managers.</p>"
        f"<p><b>Hosting fee:</b> {amt}. It goes live as soon as this is paid. The link is valid for 24 hours.</p>",
        f"Pay {amt}", chk["checkout_url"])
    await audit_log("notice.hosting_fee_request", admin, "notice", notice_ref, {"amount": q["amount"]})
    return {"ok": True, "checkout_url": chk["checkout_url"], "amount": q["amount"], "currency": q["currency"]}


# ----------------------- data intel service requests -----------------------

class IntelIn(BaseModel):
    kind: Literal["market_insights", "vendor_report"]
    category: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, max_length=3)
    subject: str = Field(min_length=3, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=2000)


@router.post("/api/v1/data-intel/requests")
async def intel_request(payload: IntelIn, vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])}) or {}
    doc = {**payload.model_dump(), "vendor_id": vendor["id"], "vendor_ref": v.get("vendor_ref"),
           "vendor_email": v.get("email"), "company_name": v.get("company_name"),
           "status": "requested", "created_at": now_iso()}
    r = await db.data_intel_requests.insert_one(doc)
    from notify import notify_role
    await notify_role("admin", f"Data intel request \u2014 {payload.subject}",
                      f"<p>{v.get('company_name')} requested <b>{payload.kind.replace('_', ' ')}</b>: {payload.subject}</p>",
                      "data_intel", str(r.inserted_id))
    return _out({**doc, "_id": r.inserted_id})


@router.get("/api/v1/data-intel/requests/mine")
async def intel_mine(vendor=Depends(current_vendor)):
    return {"items": [_out(d) async for d in db.data_intel_requests.find({"vendor_id": vendor["id"]}).sort("created_at", -1)]}


@router.post("/api/v1/data-intel/requests/{rid}/checkout")
async def intel_checkout(rid: str, payload: OriginIn, vendor=Depends(current_vendor)):
    r = await db.data_intel_requests.find_one({"_id": ObjectId(_oid(rid)), "vendor_id": vendor["id"]})
    if not r or r["status"] != "quoted":
        raise HTTPException(status_code=409, detail="This request has no open quote")
    return await _checkout(r["amount"], r["currency"], "data_intel", "/vendor/data-intel?paid=1", "/vendor/data-intel",
        payload.origin_url, {"request_id": rid}, {"request_id": rid, "vendor_id": vendor["id"], "label": "Data intel"})


@router.get("/api/v1/data-intel/admin")
async def intel_admin_list(admin=Depends(require_role("admin"))):
    items = []
    async for d in db.data_intel_requests.find({}).sort("created_at", -1).limit(300):
        rule = await find_rule("data_intel", d.get("country"), d.get("category"))
        items.append({**_out(d), "suggested_amount": compute_amount(rule, None) if rule else None,
                      "suggested_currency": (rule or {}).get("currency")})
    return {"items": items}


class QuoteIn(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


@router.post("/api/v1/data-intel/admin/{rid}/quote")
async def intel_quote(rid: str, payload: QuoteIn, admin=Depends(require_role("admin"))):
    r = await db.data_intel_requests.find_one({"_id": ObjectId(_oid(rid))})
    if not r or r["status"] not in ("requested", "quoted"):
        raise HTTPException(status_code=409, detail="Request can't be quoted now")
    await db.data_intel_requests.update_one({"_id": r["_id"]}, {"$set": {"status": "quoted",
        "amount": payload.amount, "currency": payload.currency.upper(), "quoted_at": now_iso()}})
    chk = await _checkout(payload.amount, payload.currency, "data_intel", "/vendor/data-intel?paid=1",
        "/vendor/data-intel", _site(), {"request_id": rid},
        {"request_id": rid, "vendor_id": r["vendor_id"], "label": "Data intel"})
    amt = f"{payload.currency.upper()} {payload.amount:,.2f}"
    await vendor_confirm(r.get("vendor_email"), f"Quote for your data intel request \u2014 {r['subject']}",
        f"<p>Your request <b>{r['subject']}</b> has been quoted at <b>{amt}</b>.</p>"
        "<p>Pay with the button below (valid 24 hours) or from Data intel in the supplier portal.</p>",
        f"Pay {amt}", chk["checkout_url"])
    await post_vendor_message(r.get("vendor_ref"), "payment", f"Quote for data intel — {r['subject']}",
        f"<p>Your request <b>{r['subject']}</b> has been quoted at <b>{amt}</b>. Pay from Data intel.</p>",
        "/vendor/data-intel")
    await audit_log("data_intel.quote", admin, "data_intel", rid, payload.model_dump())
    return {"ok": True}


class DeliverIn(BaseModel):
    summary: str = Field(min_length=3, max_length=5000)
    link_url: Optional[str] = Field(default=None, max_length=500)


@router.post("/api/v1/data-intel/admin/{rid}/deliver")
async def intel_deliver(rid: str, payload: DeliverIn, admin=Depends(require_role("admin"))):
    r = await db.data_intel_requests.find_one_and_update({"_id": ObjectId(_oid(rid)), "status": "paid"},
        {"$set": {"status": "delivered", "delivery": payload.model_dump(), "delivered_at": now_iso()}})
    if not r:
        raise HTTPException(status_code=409, detail="Only paid requests can be delivered")
    await vendor_confirm(r.get("vendor_email"), f"Your data intel is ready \u2014 {r['subject']}",
        "<p>Your report is ready. Open Data intel in the supplier portal to view it.</p>",
        "View report", f"{_site()}/vendor/data-intel")
    await post_vendor_message(r.get("vendor_ref"), "service", f"Your data intel is ready — {r['subject']}",
        "<p>Your report is ready to view.</p>", "/vendor/data-intel")
    return {"ok": True}


class DeclineIn(BaseModel):
    notes: str = Field(min_length=3, max_length=400)


@router.post("/api/v1/data-intel/admin/{rid}/decline")
async def intel_decline(rid: str, payload: DeclineIn, admin=Depends(require_role("admin"))):
    r = await db.data_intel_requests.find_one_and_update(
        {"_id": ObjectId(_oid(rid)), "status": {"$in": ["requested", "quoted"]}},
        {"$set": {"status": "declined", "decision_notes": payload.notes}})
    if not r:
        raise HTTPException(status_code=409, detail="Request can't be declined now")
    return {"ok": True}


# ----------------------- refund alerts -----------------------

@router.get("/api/v1/billing/refund-alerts")
async def refund_alerts(admin=Depends(require_role("admin"))):
    cur = db.payment_transactions.find({"needs_refund": True}).sort("updated_at", -1).limit(200)
    return {"items": [{k: d.get(k) for k in ("session_id", "purpose", "amount", "currency", "vendor_ref",
                       "vendor_id", "payer_email", "refund_status", "refund_error", "updated_at")} async for d in cur]}


@router.post("/api/v1/billing/refund-alerts/{session_id}/refund")
async def refund_payment(session_id: str, admin=Depends(require_role("admin"))):
    tx = await db.payment_transactions.find_one({"session_id": session_id, "needs_refund": True})
    if not tx:
        raise HTTPException(status_code=404, detail="No refund pending for this payment")
    if tx.get("refund_status") == "refunded":
        raise HTTPException(status_code=409, detail="Already refunded")
    import stripe
    stripe.api_key = os.environ["STRIPE_API_KEY"]
    try:
        s = stripe.checkout.Session.retrieve(session_id)
        ref = stripe.Refund.create(payment_intent=s.payment_intent)
    except Exception as e:
        msg = getattr(e, "user_message", None) or str(e)[:300]
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"refund_error": msg}})
        raise HTTPException(status_code=424, detail=f"Stripe refund failed: {msg}")
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {
        "refund_status": "refunded", "refund_id": ref.id, "needs_refund": False,
        "refunded_at": now_iso(), "refunded_by": admin["email"], "payment_status": "refunded"}})
    await audit_log("billing.refund", admin, "payment", session_id, {"amount": tx.get("amount")})
    return {"ok": True, "refund_id": ref.id}


# ----------------------- cron: category payment reminders -----------------------

async def _send_category_reminders():
    from datetime import datetime, timedelta, timezone
    from routers.vendor_categories import _category_checkout, FREE_CATEGORY_MSG
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    q = {"status": "payment_pending", "payment_status": "unpaid",
         "$or": [{"last_reminder_at": {"$lt": cutoff}},
                 {"last_reminder_at": {"$exists": False}, "sent_back_at": {"$lt": cutoff}}]}
    async for req in db.vendor_category_requests.find(q).limit(200):
        chk = await _category_checkout(req, _site())
        amt = f"{req['fee_currency']} {float(req['fee_amount']):,.2f}"
        await vendor_confirm(req.get("vendor_email"), f"Reminder: payment pending \u2014 {req['category_name']}",
            f"<p>Your additional category <b>{req['category_name']}</b> is still waiting for payment.</p>"
            f"<p>{FREE_CATEGORY_MSG}</p><p><b>Amount due:</b> {amt}. This fresh link is valid for 24 hours.</p>",
            f"Pay {amt}", chk["checkout_url"])
        await post_vendor_message(req.get("vendor_ref"), "payment", f"Reminder: payment pending — {req['category_name']}",
            f"<p>Your additional category <b>{req['category_name']}</b> is still waiting for payment ({amt}).</p>"
            f"<p>{FREE_CATEGORY_MSG}</p>", "/vendor/categories")
        await db.vendor_category_requests.update_one({"_id": req["_id"]},
            {"$set": {"last_reminder_at": now_iso()}, "$inc": {"reminders_sent": 1}})


@router.post("/api/v1/cron/category-payment-reminders")
async def cron_category_reminders(request: Request, bg: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    if not secret or not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    run_id = request.headers.get("X-Webhook-Id") or ""
    if run_id:
        if await db.cron_runs.find_one({"run_id": run_id}):
            return {"ok": True, "duplicate": True}
        await db.cron_runs.insert_one({"run_id": run_id, "job": "category-payment-reminders", "at": now_iso()})
    bg.add_task(_send_category_reminders)
    return {"ok": True}
