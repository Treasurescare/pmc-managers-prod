"""Wave 32 — Joint-controlled Escrow ledger for EMD (Earnest Money Deposit).

Governance model (per user 2026-08-03):
  * Bidders wire EMD into an **escrow account jointly operated** by TWO named
    officers — one from PMC Managers, one from the escrow institution.
  * PMC only *initiates and reconciles* — funds never sit in a PMC-owned
    operational account.
  * On contract award the release requires **both** officers to sign off
    (idempotent per-officer signature). Only after dual sign-off can the
    admin route the money to:
        - `contractor`  — via PMC as the pass-through paymaster to the winning vendor
        - `vendor_refund` — back to the losing bidder
        - `forfeit`     — retained (bid withdrawn, mis-declaration, etc.)
  * Every action is audit-logged and immutably reflected in
    `transaction.audit_trail`.

Wire:
  * POST /api/v1/escrow/accounts                     admin creates a joint account
  * GET  /api/v1/escrow/accounts                     admin lists accounts
  * PATCH /api/v1/escrow/accounts/{aid}              admin updates officers / status
  * POST /api/v1/escrow/transactions/init            admin records an inbound EMD tx
  * GET  /api/v1/escrow/transactions                 admin lists tx (filter by bid_ref, status)
  * POST /api/v1/escrow/transactions/{tid}/sign      one officer signs off on the intended release
  * POST /api/v1/escrow/transactions/{tid}/release   dual-signature release trigger

NOTE: This is the LEDGER + AUTHORISATION layer. Actual bank rails (SWIFT /
Kaspi Pay / Stripe payouts) are wired separately — this module records the
intent and gates the release; the payout gateway watches for state==RELEASED.
"""
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/escrow", tags=["escrow"])


# ---------------- Models ----------------

class EscrowOfficer(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    designation: Optional[str] = None
    # `role` is which side of the joint account this officer represents.
    role: Literal["pmc", "escrow_institution"]


class EscrowAccountIn(BaseModel):
    name: str = Field(min_length=2, description="Display name, e.g. 'PMC-KZ Tender EMD Escrow #1'")
    institution: str = Field(min_length=2, description="Bank / escrow trustee")
    account_no: str = Field(min_length=4)
    iban: Optional[str] = None
    swift: Optional[str] = None
    currency: str = "USD"
    pmc_officer: EscrowOfficer
    escrow_officer: EscrowOfficer
    active: bool = True
    notes: Optional[str] = None


class EscrowAccountPatch(BaseModel):
    name: Optional[str] = None
    institution: Optional[str] = None
    account_no: Optional[str] = None
    iban: Optional[str] = None
    swift: Optional[str] = None
    currency: Optional[str] = None
    pmc_officer: Optional[EscrowOfficer] = None
    escrow_officer: Optional[EscrowOfficer] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


TxStatus = Literal["pending", "received", "awaiting_signatures",
                   "released_to_contractor", "released_to_vendor",
                   "forfeited", "cancelled"]


class TransactionInitIn(BaseModel):
    bid_ref: str
    notice_ref: Optional[str] = None
    vendor_ref: Optional[str] = None
    escrow_account_id: str
    amount: float = Field(gt=0)
    currency: str = "USD"
    reference: Optional[str] = Field(None, description="Bank transaction reference / UTR")
    received_at: Optional[str] = None
    notes: Optional[str] = None


class SignIn(BaseModel):
    intended_action: Literal["release_to_contractor", "release_to_vendor", "forfeit"]
    comment: Optional[str] = None


class ReleaseIn(BaseModel):
    action: Literal["release_to_contractor", "release_to_vendor", "forfeit"]
    beneficiary_account: Optional[str] = None
    memo: Optional[str] = None


# ---------------- Helpers ----------------

def _out_account(d: dict) -> dict:
    return BaseDocument.out(d)


def _out_tx(d: dict) -> dict:
    return BaseDocument.out(d)


def _dual_signed(tx: dict, action: str) -> bool:
    """Return True when both officers have signed off on the same intended
    action after the most recent state-changing event."""
    sigs = tx.get("signatures") or {}
    pmc = sigs.get("pmc") or {}
    esc = sigs.get("escrow_institution") or {}
    return (pmc.get("action") == action and esc.get("action") == action
            and pmc.get("signed_at") and esc.get("signed_at"))


# ---------------- Accounts ----------------

@router.post("/accounts")
async def create_account(payload: EscrowAccountIn,
                          admin=Depends(require_role("admin"))):
    # Bug #14 hardening — reject blank/placeholder officer info
    for label, o in (("PMC officer", payload.pmc_officer), ("Escrow officer", payload.escrow_officer)):
        if not (o.name or "").strip() or len((o.name or "").strip()) < 2:
            raise HTTPException(status_code=400, detail=f"{label}: name is required (min 2 chars)")
        if not (o.email or "").strip():
            raise HTTPException(status_code=400, detail=f"{label}: email is required")
    # Bug G1 (governance) — enforce SEPARATE officers.
    # Same email on both sides makes dual-signature theatre. Refuse.
    if payload.pmc_officer.email.lower() == payload.escrow_officer.email.lower():
        raise HTTPException(status_code=400,
            detail="PMC officer and Escrow officer must be different people (different email addresses). Joint control requires two independent signatories.")
    if payload.pmc_officer.role != "pmc":
        raise HTTPException(status_code=400, detail="pmc_officer.role must equal 'pmc'")
    if payload.escrow_officer.role != "escrow_institution":
        raise HTTPException(status_code=400, detail="escrow_officer.role must equal 'escrow_institution'")
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin.get("email")
    r = await db.escrow_accounts.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log("escrow.account_create", admin, "escrow_account",
                     str(r.inserted_id), {"name": payload.name})
    return _out_account(doc)


@router.get("/accounts")
async def list_accounts(active_only: bool = False,
                          admin=Depends(require_role("admin", "reviewer", "accounting",
                                                      "escrow_agent"))):
    # Bucket B — aging indicator + SLA flag per account.
    # SLA_DAYS = configurable per account via `sla_days` field, defaults to 30.
    from datetime import datetime, timezone
    def _age_days(iso_str: str) -> int:
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).days
        except Exception:
            return 0

    q = {"active": True} if active_only else {}
    cursor = db.escrow_accounts.find(q).sort("created_at", -1)
    items = []
    async for d in cursor:
        row = _out_account(d)
        row["age_days"] = _age_days(d.get("created_at") or "")
        sla_days = d.get("sla_days") or 30
        row["sla_days"] = sla_days
        row["sla_breach"] = row["age_days"] > sla_days
        # 2026-09-19 — surface legacy same-email accounts so the panel can
        # render a red governance banner explaining why sign/release will fail.
        pmc_e = ((d.get("pmc_officer") or {}).get("email") or "").lower()
        esc_e = ((d.get("escrow_officer") or {}).get("email") or "").lower()
        row["governance_ok"] = bool(pmc_e and esc_e and pmc_e != esc_e)
        row["same_email_email"] = pmc_e if pmc_e == esc_e else None
        items.append(row)
    return {"items": items, "total": len(items),
            "governance_summary": {
                "ok": sum(1 for r in items if r["governance_ok"]),
                "broken": sum(1 for r in items if not r["governance_ok"]),
            },
            "sla_summary": {
                "in_sla": sum(1 for r in items if not r["sla_breach"]),
                "breached": sum(1 for r in items if r["sla_breach"]),
            }}


@router.patch("/accounts/{aid}")
async def patch_account(aid: str, payload: EscrowAccountPatch,
                          admin=Depends(require_role("admin"))):
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    # v51aq — carry Bug G1 (governance) through to PATCH too. If either officer
    # block is being updated, resolve the resulting pmc/escrow emails and
    # refuse when they'd collide. Dual-signature is theatre otherwise.
    if "pmc_officer" in changes or "escrow_officer" in changes:
        current = await db.escrow_accounts.find_one({"_id": ObjectId(aid)})
        if not current:
            raise HTTPException(status_code=404, detail="Escrow account not found")
        pmc_new = changes.get("pmc_officer") or current.get("pmc_officer") or {}
        esc_new = changes.get("escrow_officer") or current.get("escrow_officer") or {}
        pmc_email = (pmc_new.get("email") or "").lower()
        esc_email = (esc_new.get("email") or "").lower()
        if pmc_email and esc_email and pmc_email == esc_email:
            raise HTTPException(status_code=400,
                detail="PMC officer and Escrow officer must be different people (different email addresses). Joint control requires two independent signatories.")
    changes["updated_at"] = now_iso()
    r = await db.escrow_accounts.update_one({"_id": ObjectId(aid)}, {"$set": changes})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Escrow account not found")
    await audit_log("escrow.account_update", admin, "escrow_account", aid, changes)
    return _out_account(await db.escrow_accounts.find_one({"_id": ObjectId(aid)}))


# v51aq — Admin cleanup helper. Finds every bid holding more than one open
# escrow transaction (status ∈ pending/received/awaiting_signatures) so the
# UI can nag the admin until the ledger is clean. Returns bid_ref +
# transaction ids. Read-only.
@router.get("/transactions/duplicates")
async def duplicate_scan(admin=Depends(require_role("admin", "accounting"))):
    pipeline = [
        {"$match": {"status": {"$in": ["pending", "received", "awaiting_signatures"]}}},
        {"$group": {"_id": "$bid_ref",
                     "count": {"$sum": 1},
                     "tx_ids": {"$push": "$_id"},
                     "statuses": {"$push": "$status"},
                     "amounts": {"$push": "$amount"},
                     "currencies": {"$push": "$currency"}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1}},
    ]
    out = []
    async for row in db.escrow_transactions.aggregate(pipeline):
        out.append({"bid_ref": row["_id"], "open_count": row["count"],
                    "tx_ids": [str(x) for x in row["tx_ids"]],
                    "statuses": row["statuses"],
                    "amounts": row["amounts"],
                    "currencies": row["currencies"]})
    return {"items": out, "total": len(out)}


# v51aq — CSV export of every CLOSED escrow release for annual compliance
# submissions. Streamed as text/csv.
@router.get("/exports/releases.csv")
async def export_releases_csv(
    year: Optional[int] = None,
    admin=Depends(require_role("admin", "accounting", "reviewer")),
):
    import csv, io
    from fastapi.responses import StreamingResponse
    q: dict = {"status": {"$in": ["released_to_contractor", "released_to_vendor", "forfeited"]}}
    if year:
        q["released_at"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31T23:59:59"}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["bid_ref", "notice_ref", "vendor_ref", "amount", "currency",
                 "escrow_account", "institution", "status", "released_at",
                 "released_to", "pmc_officer_email", "pmc_signed_at", "pmc_action",
                 "escrow_officer_email", "escrow_signed_at", "escrow_action",
                 "reviewer_notes", "created_at"])
    async for t in db.escrow_transactions.find(q).sort("released_at", -1):
        snap = t.get("escrow_account_snapshot") or {}
        sigs = t.get("signatures") or {}
        pmc = sigs.get("pmc") or {}
        esc = sigs.get("escrow_institution") or {}
        notes_parts = []
        for e in (t.get("audit_trail") or []):
            if e.get("comment"):
                notes_parts.append(f"[{(e.get('at') or '')[:16]}] {e.get('comment')}")
        w.writerow([
            t.get("bid_ref"), t.get("notice_ref"), t.get("vendor_ref"),
            t.get("amount"), t.get("currency"),
            snap.get("name"), snap.get("institution"),
            t.get("status"), t.get("released_at"), t.get("released_to"),
            (snap.get("pmc_officer") or {}).get("email"),
            pmc.get("signed_at"), pmc.get("action"),
            (snap.get("escrow_officer") or {}).get("email"),
            esc.get("signed_at"), esc.get("action"),
            " | ".join(notes_parts),
            t.get("created_at"),
        ])
    await audit_log("escrow.export_releases_csv", admin, "escrow", "releases",
                     {"year": year, "status_filter": "closed"})
    buf.seek(0)
    yr = f"-{year}" if year else ""
    return StreamingResponse(iter([buf.getvalue()]),
                              media_type="text/csv",
                              headers={"Content-Disposition":
                                       f'attachment; filename="escrow-releases{yr}.csv"'})


# ---------------- Transactions ----------------

# v51am — invoked by payments._mark_paid to create a ledger row automatically
# the moment a vendor's EMD payment clears Stripe. Idempotent on
# `payment_session_id` so webhook retries don't duplicate rows.
async def auto_init_from_emd_payment(bid_id: str, payment_tx: dict) -> Optional[dict]:
    """Create the receive-side ledger row for an EMD payment that just
    cleared. Picks the notice's `escrow_account_id` if set, otherwise the
    first active escrow account. Admin can still override/sign manually."""
    session_id = payment_tx.get("session_id")
    if not session_id:
        return None
    # Idempotency guard
    existing = await db.escrow_transactions.find_one({"payment_session_id": session_id})
    if existing:
        return _out_tx(existing)
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        return None
    # v51ap — don't double-create if the admin already manually recorded a
    # ledger row for this bid before the webhook fired.
    existing_open = await db.escrow_transactions.find_one({
        "bid_ref": bid.get("bid_ref"),
        "status": {"$nin": ["released_to_contractor", "released_to_vendor",
                             "forfeited", "cancelled"]},
    })
    if existing_open:
        # Backfill the payment_session_id so future retries hit the idempotency
        # guard instead of this slower branch.
        await db.escrow_transactions.update_one(
            {"_id": existing_open["_id"],
             "payment_session_id": {"$exists": False}},
            {"$set": {"payment_session_id": session_id,
                      "auto_source": "stripe_emd_payment",
                      "updated_at": now_iso()}})
        return _out_tx(existing_open)
    # Resolve escrow account: notice-level override first, else newest active.
    acc = None
    notice = await db.notices.find_one({"notice_ref": bid.get("notice_ref")}) or {}
    acc_id = notice.get("escrow_account_id")
    if acc_id:
        try:
            acc = await db.escrow_accounts.find_one({"_id": ObjectId(acc_id), "active": True})
        except Exception:
            acc = None
    if not acc:
        acc = await db.escrow_accounts.find_one({"active": True},
                                                  sort=[("created_at", -1)])
    if not acc:
        import logging
        logging.getLogger("escrow").warning(
            "auto_init_from_emd_payment: no active escrow account; skipping bid %s",
            bid.get("bid_ref"))
        return None
    trail_entry = {"at": now_iso(), "by": "system.auto",
                   "event": "received",
                   "amount": payment_tx.get("amount"),
                   "currency": payment_tx.get("currency") or "USD",
                   "reference": session_id}
    doc = {
        "bid_ref": bid.get("bid_ref"),
        "notice_ref": bid.get("notice_ref"),
        "vendor_ref": bid.get("vendor_ref"),
        "escrow_account_id": str(acc["_id"]),
        "escrow_account_snapshot": {
            "name": acc.get("name"), "institution": acc.get("institution"),
            "account_no": acc.get("account_no"),
            "pmc_officer": acc.get("pmc_officer"),
            "escrow_officer": acc.get("escrow_officer"),
        },
        "amount": payment_tx.get("amount"),
        "currency": payment_tx.get("currency") or "USD",
        "reference": session_id,
        "payment_session_id": session_id,
        "received_at": now_iso(),
        "notes": f"Auto-recorded on Stripe payment success (bid {bid.get('bid_ref')})",
        "status": "received",
        "signatures": {},
        "audit_trail": [trail_entry],
        "released_to": None,
        "released_at": None,
        "created_at": now_iso(),
        "created_by": "system.auto",
        "auto_source": "stripe_emd_payment",
    }
    r = await db.escrow_transactions.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log("escrow.tx_auto_init", None, "escrow_tx", str(r.inserted_id),
                    {"bid_ref": bid.get("bid_ref"), "amount": payment_tx.get("amount"),
                     "session_id": session_id})
    return _out_tx(doc)


@router.post("/transactions/init")
async def init_transaction(payload: TransactionInitIn,
                            admin=Depends(require_role("admin", "accounting"))):
    """Record an inbound EMD wire against an active joint escrow account."""
    acc = await db.escrow_accounts.find_one({"_id": ObjectId(payload.escrow_account_id),
                                              "active": True})
    if not acc:
        raise HTTPException(status_code=404, detail="Active escrow account not found")
    # v51ap — reject duplicate inbound EMD per bid. Each bid can hold ONE
    # open ledger row at a time; once the current row is released or
    # cancelled the admin can record a new one against a different account.
    existing_open = await db.escrow_transactions.find_one({
        "bid_ref": payload.bid_ref,
        "status": {"$nin": ["released_to_contractor", "released_to_vendor",
                             "forfeited", "cancelled"]},
    })
    if existing_open:
        raise HTTPException(status_code=409,
            detail=(f"Bid {payload.bid_ref} already has an open escrow transaction "
                    f"(status: {existing_open.get('status')}). Release or cancel "
                    f"that one before recording another."))
    trail_entry = {"at": now_iso(), "by": admin.get("email"),
                    "event": "received",
                    "amount": payload.amount, "currency": payload.currency,
                    "reference": payload.reference}
    doc = {
        "bid_ref": payload.bid_ref,
        "notice_ref": payload.notice_ref,
        "vendor_ref": payload.vendor_ref,
        "escrow_account_id": payload.escrow_account_id,
        "escrow_account_snapshot": {
            "name": acc.get("name"), "institution": acc.get("institution"),
            "account_no": acc.get("account_no"),
            "pmc_officer": acc.get("pmc_officer"),
            "escrow_officer": acc.get("escrow_officer"),
        },
        "amount": payload.amount,
        "currency": payload.currency,
        "reference": payload.reference,
        "received_at": payload.received_at or now_iso(),
        "notes": payload.notes,
        "status": "received",
        "signatures": {},
        "audit_trail": [trail_entry],
        "released_to": None,
        "released_at": None,
        "created_at": now_iso(),
        "created_by": admin["email"],
    }
    r = await db.escrow_transactions.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log("escrow.tx_init", admin, "escrow_tx", str(r.inserted_id),
                     {"bid_ref": payload.bid_ref, "amount": payload.amount})
    return _out_tx(doc)


@router.get("/transactions")
async def list_transactions(bid_ref: Optional[str] = None,
                              notice_ref: Optional[str] = None,
                              status: Optional[TxStatus] = None,
                              admin=Depends(require_role("admin", "reviewer", "accounting",
                                                          "escrow_agent"))):
    q: dict = {}
    if bid_ref: q["bid_ref"] = bid_ref
    if notice_ref: q["notice_ref"] = notice_ref
    if status: q["status"] = status
    cursor = db.escrow_transactions.find(q).sort("created_at", -1).limit(200)
    items = []
    async for d in cursor:
        row = _out_tx(d)
        # 2026-09-19 — surface the same-email governance flag per-transaction
        # so the panel can render a per-row banner explaining why sign/release
        # will never fire until officers are fixed.
        snap = d.get("escrow_account_snapshot") or {}
        pmc_e = ((snap.get("pmc_officer") or {}).get("email") or "").lower()
        esc_e = ((snap.get("escrow_officer") or {}).get("email") or "").lower()
        row["governance_ok"] = bool(pmc_e and esc_e and pmc_e != esc_e)
        row["same_email_email"] = pmc_e if pmc_e == esc_e else None
        items.append(row)
    return {"items": items, "total": len(items)}


@router.post("/transactions/{tid}/cancel")
async def cancel_transaction(tid: str,
                              admin=Depends(require_role("admin"))):
    """v51ap — admin cancels an open escrow transaction (duplicates or
    mis-entries). Allowed only while status is pending / received /
    awaiting_signatures. Audit-logged."""
    try:
        tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed transaction id")
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.get("status") not in ("pending", "received", "awaiting_signatures"):
        raise HTTPException(status_code=409,
            detail=f"Cannot cancel a transaction in status '{tx.get('status')}'")
    trail_entry = {"at": now_iso(), "by": admin.get("email"),
                    "event": "cancelled",
                    "comment": "Admin-cancelled (e.g. duplicate)"}
    await db.escrow_transactions.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {"status": "cancelled", "updated_at": now_iso()},
         "$push": {"audit_trail": trail_entry}})
    await audit_log("escrow.tx_cancel", admin, "escrow_tx", tid,
                     {"bid_ref": tx.get("bid_ref")})
    return _out_tx(await db.escrow_transactions.find_one({"_id": ObjectId(tid)}))


@router.post("/transactions/{tid}/sign")
async def sign_off(tid: str, payload: SignIn,
                     admin=Depends(require_role("admin", "accounting", "escrow_agent"))):
    """Record one officer's signature toward an intended release action.
    The officer's `role` is inferred from the joint-account snapshot on the
    transaction, so an admin can't accidentally sign as the wrong side."""
    try:
        tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed transaction id")
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx["status"] in ("released_to_contractor", "released_to_vendor", "forfeited", "cancelled"):
        raise HTTPException(status_code=409,
                             detail=f"Transaction already {tx['status']} — cannot re-sign")
    snap = tx.get("escrow_account_snapshot") or {}
    pmc = snap.get("pmc_officer") or {}
    esc = snap.get("escrow_officer") or {}
    pmc_email = (pmc.get("email") or "").lower()
    esc_email = (esc.get("email") or "").lower()
    email = (admin.get("email") or "").lower()
    # Bug (2026-09-19) — legacy joint-escrow accounts created before the
    # "different emails" guard sometimes carry the same email on both sides.
    # In that case the admin clicks Sign, the backend records only the pmc
    # side (if/elif short-circuits), the escrow_institution side stays empty
    # forever, and Release never fires. Detect the misconfiguration and tell
    # the operator exactly how to unblock it instead of silently no-oping.
    if pmc_email and pmc_email == esc_email:
        raise HTTPException(
            status_code=409,
            detail=(
                "This joint escrow account has the SAME email on both officers "
                f"({pmc_email}). Dual-signature is impossible until the two "
                "officers are distinct people. Go to Escrow → Joint Escrow "
                "Accounts, edit this account, and set the Escrow officer to a "
                "different email (or issue a magic-link to the external trustee "
                "via /api/v1/escrow/magic-tokens). Nothing has been signed."
            ),
        )
    if email == pmc_email:
        side = "pmc"
    elif email == esc_email:
        side = "escrow_institution"
    else:
        raise HTTPException(status_code=403,
                             detail="You are not registered as an officer on this escrow account")
    signatures = tx.get("signatures") or {}
    signatures[side] = {
        "email": admin["email"], "action": payload.intended_action,
        "comment": payload.comment, "signed_at": now_iso(),
    }
    trail_entry = {"at": now_iso(), "by": admin["email"],
                    "event": f"signed_by_{side}",
                    "intended_action": payload.intended_action,
                    "comment": payload.comment}
    new_status = "awaiting_signatures" if not _dual_signed({"signatures": signatures},
                                                            payload.intended_action) else tx["status"]
    await db.escrow_transactions.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {"signatures": signatures, "status": new_status,
                    "updated_at": now_iso()},
         "$push": {"audit_trail": trail_entry}},
    )
    await audit_log(f"escrow.sign_{side}", admin, "escrow_tx", tid,
                     {"intended_action": payload.intended_action})
    return _out_tx(await db.escrow_transactions.find_one({"_id": ObjectId(tid)}))


@router.post("/transactions/{tid}/release")
async def release(tid: str, payload: ReleaseIn,
                   admin=Depends(require_role("admin", "accounting"))):
    """Only fires once BOTH officers have signed the same `action`. The admin
    who fires this is recorded as the operator — but they cannot proceed
    without the two independent signatures already stored on the record."""
    try:
        tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed transaction id")
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx["status"] in ("released_to_contractor", "released_to_vendor", "forfeited", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Transaction already {tx['status']}")
    if not _dual_signed(tx, payload.action):
        raise HTTPException(status_code=409,
                             detail="Both officers must sign the same action before release")
    final_status = {"release_to_contractor": "released_to_contractor",
                     "release_to_vendor": "released_to_vendor",
                     "forfeit": "forfeited"}[payload.action]
    trail_entry = {"at": now_iso(), "by": admin["email"], "event": final_status,
                    "beneficiary_account": payload.beneficiary_account,
                    "memo": payload.memo}
    await db.escrow_transactions.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {"status": final_status,
                    "released_to": payload.beneficiary_account,
                    "released_at": now_iso(),
                    "release_memo": payload.memo,
                    "release_operator": admin["email"],
                    "updated_at": now_iso()},
         "$push": {"audit_trail": trail_entry}},
    )
    await audit_log(f"escrow.{final_status}", admin, "escrow_tx", tid,
                     {"amount": tx.get("amount"), "currency": tx.get("currency"),
                      "beneficiary": payload.beneficiary_account})
    return _out_tx(await db.escrow_transactions.find_one({"_id": ObjectId(tid)}))


# ---------------- Magic-link portal for non-PMC escrow officers ----------
#
# The escrow-institution officer is an external party who should NOT need a
# full staff account. They sign via a per-account magic link the admin sends
# them by email. The token maps to their account+email in `escrow_magic_tokens`.

import secrets as _secrets

class MagicIssueIn(BaseModel):
    account_id: str
    officer_email: EmailStr


class MagicSignIn(BaseModel):
    tid: str
    intended_action: Literal["release_to_contractor", "release_to_vendor", "forfeit"]
    comment: Optional[str] = None


@router.post("/magic-tokens")
async def issue_magic_token(payload: MagicIssueIn,
                             admin=Depends(require_role("admin"))):
    """Admin generates a magic-link token for a specific officer of a specific
    joint account. Token is single-account, multi-use (officer can sign as
    many transactions on that account as arrive)."""
    if not ObjectId.is_valid(payload.account_id):
        raise HTTPException(status_code=400, detail="Invalid account id")
    acc = await db.escrow_accounts.find_one({"_id": ObjectId(payload.account_id)})
    if not acc:
        raise HTTPException(status_code=404, detail="Escrow account not found")
    pmc = acc.get("pmc_officer") or {}
    esc = acc.get("escrow_officer") or {}
    email_l = payload.officer_email.lower()
    if email_l not in ((pmc.get("email") or "").lower(),
                       (esc.get("email") or "").lower()):
        raise HTTPException(status_code=400,
            detail="Officer email is not on this joint account")
    token = _secrets.token_urlsafe(28)
    await db.escrow_magic_tokens.insert_one({
        "token": token,
        "account_id": payload.account_id,
        "officer_email": email_l,
        "created_at": now_iso(),
        "created_by": admin["email"],
        "revoked": False,
    })
    await audit_log("escrow.magic_issue", admin, "escrow_account",
                     payload.account_id, {"officer_email": email_l})
    return {"token": token, "portal_url": f"/escrow/officer/{token}"}


@router.get("/magic/{token}")
async def magic_context(token: str):
    """Public — returns the officer's identity + all pending transactions on
    their account. No auth beyond possession of the token."""
    t = await db.escrow_magic_tokens.find_one({"token": token, "revoked": False})
    if not t:
        raise HTTPException(status_code=404, detail="Invalid or revoked magic token")
    acc = await db.escrow_accounts.find_one({"_id": ObjectId(t["account_id"])})
    if not acc:
        raise HTTPException(status_code=404, detail="Escrow account not found")
    officer_email = t["officer_email"]
    officer_side = "pmc" if officer_email == (acc.get("pmc_officer") or {}).get("email", "").lower() \
                   else "escrow_institution"
    txs = await db.escrow_transactions.find(
        {"escrow_account_id": t["account_id"],
         "status": {"$in": ["received", "awaiting_signatures"]}},
    ).sort("created_at", -1).to_list(100)
    return {
        "account": {"name": acc.get("name"), "institution": acc.get("institution"),
                     "currency": acc.get("currency")},
        "officer_email": officer_email,
        "officer_side": officer_side,
        "transactions": [_out_tx(t) for t in txs],
    }


@router.post("/magic/{token}/sign")
async def magic_sign(token: str, payload: MagicSignIn):
    """Officer signs a transaction via magic-link — no staff login needed."""
    t = await db.escrow_magic_tokens.find_one({"token": token, "revoked": False})
    if not t:
        raise HTTPException(status_code=404, detail="Invalid or revoked magic token")
    if not ObjectId.is_valid(payload.tid):
        raise HTTPException(status_code=400, detail="Invalid transaction id")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(payload.tid)})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.get("escrow_account_id") != t["account_id"]:
        raise HTTPException(status_code=403, detail="Transaction is not on this officer's account")
    if tx["status"] in ("released_to_contractor", "released_to_vendor", "forfeited", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Transaction already {tx['status']}")
    acc_snap = tx.get("escrow_account_snapshot") or {}
    officer_email = t["officer_email"]
    if officer_email == (acc_snap.get("pmc_officer") or {}).get("email", "").lower():
        side = "pmc"
    elif officer_email == (acc_snap.get("escrow_officer") or {}).get("email", "").lower():
        side = "escrow_institution"
    else:
        raise HTTPException(status_code=403, detail="Officer not on this transaction snapshot")
    signatures = tx.get("signatures") or {}
    signatures[side] = {
        "email": officer_email, "action": payload.intended_action,
        "comment": payload.comment, "signed_at": now_iso(),
        "via": "magic_link",
    }
    trail_entry = {"at": now_iso(), "by": officer_email,
                    "event": f"signed_by_{side}_magic",
                    "intended_action": payload.intended_action,
                    "comment": payload.comment}
    new_status = "awaiting_signatures" if not _dual_signed({"signatures": signatures},
                                                            payload.intended_action) else tx["status"]
    await db.escrow_transactions.update_one(
        {"_id": ObjectId(payload.tid)},
        {"$set": {"signatures": signatures, "status": new_status,
                    "updated_at": now_iso()},
         "$push": {"audit_trail": trail_entry}},
    )
    await audit_log(f"escrow.sign_{side}",
                    {"email": officer_email, "role": "escrow_officer"},
                    "escrow_tx", payload.tid,
                    {"intended_action": payload.intended_action, "via": "magic_link"})
    return _out_tx(await db.escrow_transactions.find_one({"_id": ObjectId(payload.tid)}))
