"""Bid workflow router — Wave 1.

Vendors submit bids on published notices; each bid moves through the sequential
approval pipeline: emd_paid → escrow_accepted → admin_flagged → certifier_cleared
→ legal_cleared → accounting_cleared → committee_review → awarded/rejected.
"""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

import config
from db import db, next_sequence
from models.bid import BidCreateIn, BidUpdateIn, BidDecisionIn
from models.emd_payment import EMDConfig
from models.base import BaseDocument, now_iso
from security import require_role
from routers.vendor_auth import current_vendor
from audit import audit_log

router = APIRouter(prefix="/api/v1/bids", tags=["bids"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- Vendor endpoints ----------

@router.post("")
async def create_bid(payload: BidCreateIn, vendor=Depends(current_vendor)) -> dict:
    """Vendor creates a bid draft against a published notice."""
    notice = await db.notices.find_one({"notice_ref": payload.notice_ref, "is_published": True})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found or not published")
    # Deadline check
    deadline = notice.get("submission_deadline")
    if deadline and deadline < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Submission deadline has passed")

    # Prevent duplicate active bid per vendor+notice
    dup = await db.bids.find_one({
        "notice_ref": payload.notice_ref,
        "vendor_id": vendor["id"],
        "status": {"$nin": ["withdrawn", "rejected"]},
    })
    if dup:
        raise HTTPException(status_code=409, detail="You already have an active bid on this notice")

    # Compute EMD due
    emd_cfg = EMDConfig(**(notice.get("emd_config") or {}))
    emd_due = emd_cfg.compute(notice.get("budget_amount") or 0.0)

    seq = await next_sequence("bid_seq")
    year = datetime.now(timezone.utc).year
    bid_ref = f"PMC-BID-{year}-{seq:05d}"

    doc = {
        "bid_ref": bid_ref,
        "notice_ref": payload.notice_ref,
        "vendor_id": vendor["id"],
        "vendor_email": vendor["email"],
        "vendor_ref": vendor.get("vendor_ref"),
        "company_name": vendor.get("company_name"),
        "price_amount": payload.price_amount,
        "price_currency": payload.price_currency,
        "technical_notes": payload.technical_notes,
        "commercial_notes": payload.commercial_notes,
        "documents": [d.model_dump() for d in payload.documents],
        "emd_due_amount": emd_due,
        "emd_currency": emd_cfg.currency,
        "emd_paid_amount": 0.0,
        "status": "emd_pending" if emd_due > 0 else "submitted",
        "tenant_id": config.DEFAULT_TENANT_ID,
        "workflow_history": [],
        "created_at": now_iso(),
        "submitted_at": now_iso(),
    }
    res = await db.bids.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("bid.submit", None, "bid", bid_ref,
                    {"vendor": vendor["email"], "notice": payload.notice_ref, "price": payload.price_amount})
    return _out(doc)


@router.get("/mine")
async def list_my_bids(vendor=Depends(current_vendor)) -> List[dict]:
    """List a vendor's own bids."""
    cursor = db.bids.find({"vendor_id": vendor["id"]}).sort("created_at", -1).limit(200)
    return [_out(b) async for b in cursor]


@router.get("/{bid_id}")
async def get_bid(bid_id: str, vendor=Depends(current_vendor)) -> dict:
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b or b.get("vendor_id") != vendor["id"]:
        raise HTTPException(status_code=404, detail="Bid not found")
    return _out(b)


@router.post("/{bid_id}/withdraw")
async def withdraw_bid(bid_id: str, vendor=Depends(current_vendor)) -> dict:
    b = await db.bids.find_one({"_id": ObjectId(bid_id), "vendor_id": vendor["id"]})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    if b.get("status") in ("awarded", "closed", "withdrawn"):
        raise HTTPException(status_code=400, detail="Cannot withdraw at this stage")
    await db.bids.update_one({"_id": ObjectId(bid_id)},
                             {"$set": {"status": "withdrawn", "withdrawn_at": now_iso()}})
    await audit_log("bid.withdraw", None, "bid", b.get("bid_ref"), {})
    return {"ok": True}


# ---------- Staff endpoints (multi-role) ----------

@router.get("")
async def list_all_bids(
    notice_ref: Optional[str] = None,
    status: Optional[str] = None,
    admin=Depends(require_role("admin", "reviewer", "escrow_agent", "certifier",
                               "legal_counsel", "accounting", "committee_member", "auditor")),
) -> List[dict]:
    q: dict = {}
    if notice_ref:
        q["notice_ref"] = notice_ref
    if status:
        q["status"] = status
    return [_out(b) async for b in db.bids.find(q).sort("created_at", -1).limit(300)]


_ROLE_TO_TARGET_STATUS = {
    "escrow_agent":   ("emd_paid",            "escrow_accepted"),
    "admin":          ("escrow_accepted",     "admin_flagged"),
    "certifier":      ("admin_flagged",       "certifier_cleared"),
    "legal_counsel":  ("certifier_cleared",   "legal_cleared"),
    "accounting":     ("legal_cleared",       "accounting_cleared"),
    "committee":      ("accounting_cleared",  "awarded"),  # or "rejected"
}


@router.post("/{bid_id}/decision")
async def decide_bid(bid_id: str, payload: BidDecisionIn,
                     admin=Depends(require_role("admin", "reviewer", "escrow_agent", "certifier",
                                                "legal_counsel", "accounting", "committee_member"))):
    """Sequential approval step. The active role in the JWT must match `payload.role`."""
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    if admin.get("role") != payload.role and not (payload.role == "committee" and admin.get("role") == "committee_member"):
        raise HTTPException(status_code=403, detail=f"Active role {admin.get('role')} cannot act as {payload.role}")

    prev_status = b.get("status")
    expected, next_status = _ROLE_TO_TARGET_STATUS.get(payload.role, (None, None))

    if payload.action == "reject":
        next_status = "rejected"
    elif payload.action == "flag":
        next_status = "admin_flagged"
    elif payload.action == "award":
        if payload.role != "committee":
            raise HTTPException(status_code=403, detail="Only committee can award")
        next_status = "awarded"

    if not next_status:
        raise HTTPException(status_code=400, detail="Invalid action for role")
    if payload.action == "accept" and expected and prev_status != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Bid must be in status '{expected}' before {payload.role} can accept (current: {prev_status})",
        )

    entry = {
        "role": payload.role, "action": payload.action, "from_status": prev_status,
        "to_status": next_status, "notes": payload.notes, "by": admin.get("email"),
        "at": now_iso(),
    }
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"status": next_status, "updated_at": now_iso()},
         "$push": {"workflow_history": entry}},
    )
    await audit_log(f"bid.{payload.role}.{payload.action}", admin, "bid", b.get("bid_ref"), entry)
    return {"ok": True, "status": next_status}


@router.post("/{bid_id}/assign-certifier")
async def assign_certifier(bid_id: str, certifier_id: str,
                           admin=Depends(require_role("admin"))) -> dict:
    """Admin assigns a specific staff member (with certifier role) as responsible
    for the tender/bid verification incl. site inspection."""
    cert = await db.admin_users.find_one({"_id": ObjectId(certifier_id)})
    if not cert:
        raise HTTPException(status_code=404, detail="Certifier not found")
    roles = cert.get("roles") or [cert.get("role")]
    if "certifier" not in roles:
        raise HTTPException(status_code=400, detail="Assigned staff does not hold certifier role")
    b = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not b:
        raise HTTPException(status_code=404, detail="Bid not found")
    await db.bids.update_one(
        {"_id": ObjectId(bid_id)},
        {"$set": {"assigned_certifier_id": certifier_id,
                  "assigned_certifier_email": cert.get("email"),
                  "assigned_at": now_iso()}},
    )
    await audit_log("bid.assign_certifier", admin, "bid", b.get("bid_ref"),
                    {"certifier_id": certifier_id, "certifier_email": cert.get("email")})
    return {"ok": True}
