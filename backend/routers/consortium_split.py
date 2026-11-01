"""Consortium award-payment split: when escrow releases money on a consortium bid, it is divided by the agreed shares."""
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/escrow", tags=["escrow-consortium"])
VIEW = require_role("admin", "accounting", "auditor", "escrow_agent")


def compute_split(tx: dict, bid: dict, action: str) -> dict:
    cons = bid["consortium"]
    amount = round(float(tx.get("amount") or 0), 2)
    people = [{"vendor_id": bid.get("vendor_id"), "company": bid.get("company_name"), "email": bid.get("vendor_email"),
               "share_pct": float(cons.get("lead_share_pct") or 0), "lead": True}]
    people += [{"vendor_id": m["vendor_id"], "company": m.get("company_name"), "email": m.get("email"),
                "share_pct": float(m.get("share_pct") or 0), "lead": False} for m in cons.get("members") or []]
    refund = action == "release_to_vendor"
    if refund and cons.get("deposit_mode") != "each_pays_share":
        people = [dict(people[0], share_pct=100.0)]
        basis = "Deposit paid by the lead — refunded in full to the lead"
    else:
        basis = "Split by the consortium's agreed shares"
    lines = []
    for p in people:
        lines.append({**p, "amount": round(amount * p["share_pct"] / 100, 2)})
    diff = round(amount - sum(x["amount"] for x in lines), 2)
    lines[0]["amount"] = round(lines[0]["amount"] + diff, 2)
    separate = cons.get("escrow_mode") == "separate"
    for x in lines:
        x.update(currency=tx.get("currency"), status="pending_payout",
                 route="Transfer to this member's own escrow account" if separate else "Pay out from the shared escrow to this member")
    return {"consortium_id": cons.get("id"), "consortium": cons.get("name"), "escrow_mode": cons.get("escrow_mode"),
            "action": action, "basis": basis, "total": amount, "lines": lines}


async def _tx_bid(tid: str):
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)}) if ObjectId.is_valid(tid) else None
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    bid = await db.bids.find_one({"bid_ref": tx.get("bid_ref")}) if tx.get("bid_ref") else None
    return tx, bid


async def apply_split(tid: str, action: str, admin: dict) -> None:
    """Called right after a release. Records the split and tells each member their amount."""
    tx, bid = await _tx_bid(tid)
    if not bid or not bid.get("consortium") or action not in ("release_to_contractor", "release_to_vendor") or tx.get("consortium_split"):
        return
    split = compute_split(tx, bid, action)
    split.update(at=now_iso(), by=admin.get("email"))
    await db.escrow_transactions.update_one({"_id": tx["_id"]}, {"$set": {"consortium_split": split},
                                                                 "$push": {"audit_trail": {"at": now_iso(), "by": admin.get("email"), "event": "consortium_split"}}})
    await audit_log("escrow.consortium_split", admin, "escrow_tx", tid, {"lines": len(split["lines"]), "total": split["total"]})
    from emails import send_email, wrap
    for x in split["lines"]:
        if x.get("email"):
            await send_email(x["email"], f"[PMC] Your consortium share · {tx.get('bid_ref')}",
                             wrap("Consortium payment share", f"<p>Escrow released <b>{tx.get('currency')} {split['total']:,.2f}</b> for bid "
                                  f"<b>{tx.get('bid_ref')}</b> ({split['consortium']}).</p><p>Your share: <b>{x['share_pct']:g}% = {x['currency']} {x['amount']:,.2f}</b><br/>"
                                  f"{x['route']}.</p><p>{split['basis']}.</p>"))


@router.get("/transactions/{tid}/consortium-split")
async def get_split(tid: str, _=Depends(VIEW)):
    tx, bid = await _tx_bid(tid)
    if tx.get("consortium_split"):
        return {"recorded": True, **tx["consortium_split"]}
    if not bid or not bid.get("consortium"):
        return {"recorded": False, "applies": False}
    return {"recorded": False, "applies": True, "preview": {a: compute_split(tx, bid, a) for a in ("release_to_contractor", "release_to_vendor")}}


class PaidIn(BaseModel):
    reference: str = Field(min_length=3, max_length=120)


@router.post("/transactions/{tid}/consortium-split/{idx}/paid")
async def mark_paid(tid: str, idx: int, body: PaidIn, admin=Depends(require_role("admin", "accounting"))):
    tx, _ = await _tx_bid(tid)
    split = tx.get("consortium_split")
    if not split or idx < 0 or idx >= len(split["lines"]):
        raise HTTPException(status_code=404, detail="Split line not found")
    line = split["lines"][idx]
    if line["status"] == "paid":
        raise HTTPException(status_code=409, detail="Already marked paid")
    line.update(status="paid", paid_ref=body.reference.strip(), paid_at=now_iso(), paid_by=admin.get("email"))
    await db.escrow_transactions.update_one({"_id": tx["_id"]}, {"$set": {"consortium_split.lines": split["lines"]}})
    await audit_log("escrow.consortium_split_paid", admin, "escrow_tx", tid, {"member": line.get("company"), "amount": line["amount"], "ref": line["paid_ref"]})
    return {"recorded": True, **split}


@router.get("/consortium-splits")
async def list_splits(_=Depends(VIEW)):
    out = []
    async for t in db.escrow_transactions.find({"consortium_split": {"$exists": True}}).sort("released_at", -1).limit(200):
        out.append({"tid": str(t["_id"]), "bid_ref": t.get("bid_ref"), "notice_ref": t.get("notice_ref"), **t["consortium_split"]})
    return {"items": out}
