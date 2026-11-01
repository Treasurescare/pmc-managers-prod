"""Consortium award-payment split: when escrow releases money on a consortium bid, it is divided by the agreed shares."""
import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/escrow", tags=["escrow-consortium"])
logger = logging.getLogger(__name__)
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


async def _bank(vendor_id, email) -> dict:
    keys = ("bank_name", "bank_branch", "bank_account_number", "bank_swift", "bank_address")
    v = await db.vendors.find_one({"_id": ObjectId(vendor_id)}) if vendor_id and ObjectId.is_valid(vendor_id) else None
    src = v if v and v.get("bank_account_number") else await db.registrations.find_one(
        {"email": (email or "").lower(), "bank_account_number": {"$nin": [None, ""]}}, sort=[("created_at", -1)])
    return {k: (src or {}).get(k) for k in keys} if src else {}


async def apply_split(tid: str, action: str, admin: dict) -> None:
    """Called right after a release. Records the split and tells each member their amount."""
    tx, bid = await _tx_bid(tid)
    if not bid or not bid.get("consortium") or action not in ("release_to_contractor", "release_to_vendor") or tx.get("consortium_split"):
        return
    split = compute_split(tx, bid, action)
    split.update(at=now_iso(), by=admin.get("email"))
    for i, x in enumerate(split["lines"]):
        x.update(instruction_ref=f"{tx.get('bid_ref')}-P{i + 1}", bank=await _bank(x.get("vendor_id"), x.get("email")),
                 signatures={}, status="awaiting_signatures")
    await db.escrow_transactions.update_one({"_id": tx["_id"]}, {"$set": {"consortium_split": split},
                                                                 "$push": {"audit_trail": {"at": now_iso(), "by": admin.get("email"), "event": "consortium_split"}}})
    await audit_log("escrow.consortium_split", admin, "escrow_tx", tid, {"lines": len(split["lines"]), "total": split["total"]})
    from emails import send_email, wrap
    for x in split["lines"]:
        if not x.get("email"):
            continue
        try:
            await send_email(x["email"], f"[PMC] Your consortium share · {tx.get('bid_ref')}",
                             wrap("Consortium payment share", f"<p>Escrow released <b>{tx.get('currency')} {split['total']:,.2f}</b> for bid "
                                  f"<b>{tx.get('bid_ref')}</b> ({split['consortium']}).</p><p>Your share: <b>{x['share_pct']:g}% = {x['currency']} {x['amount']:,.2f}</b><br/>"
                                  f"{x['route']}.</p><p>{split['basis']}.</p>"))
        except Exception:
            logger.exception("consortium split email failed")


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
    proof_key: str = Field(min_length=3, max_length=300)


class LineSignIn(BaseModel):
    comment: Optional[str] = Field(default=None, max_length=500)


async def _line(tid: str, idx: int):
    tx, _ = await _tx_bid(tid)
    split = tx.get("consortium_split")
    if not split or idx < 0 or idx >= len(split["lines"]):
        raise HTTPException(status_code=404, detail="Split line not found")
    return tx, split, split["lines"][idx]


async def _sign(tid: str, idx: int, email: str, comment: Optional[str], via: str) -> dict:
    tx, split, line = await _line(tid, idx)
    if line.get("status") not in ("awaiting_signatures", "pending_payout"):
        raise HTTPException(status_code=409, detail=f"This payment is already {line.get('status', '').replace('_', ' ')}")
    snap = tx.get("escrow_account_snapshot") or {}
    pmc_email = ((snap.get("pmc_officer") or {}).get("email") or "").lower()
    esc_email = ((snap.get("escrow_officer") or {}).get("email") or "").lower()
    me = (email or "").lower()
    if pmc_email and pmc_email == esc_email:
        raise HTTPException(status_code=409, detail="Both officers on this escrow account have the same email — fix the account before signing payments.")
    side = "pmc" if me and me == pmc_email else "escrow_institution" if me and me == esc_email else None
    if not side:
        raise HTTPException(status_code=403, detail="Only the two officers named on this escrow account can sign payments")
    if not (line.get("bank") or {}).get("bank_account_number"):
        line["bank"] = await _bank(line.get("vendor_id"), line.get("email"))
        if not line["bank"].get("bank_account_number"):
            raise HTTPException(status_code=409, detail=f"{line.get('company')} has no bank account on file. Ask them to add it to their supplier profile.")
    p = f"consortium_split.lines.{idx}"
    sig = {"email": me, "at": now_iso(), "comment": comment, "via": via,
           "amount": line["amount"], "account": line["bank"]["bank_account_number"]}
    r = await db.escrow_transactions.update_one(
        {"_id": tx["_id"], f"{p}.status": {"$in": ["awaiting_signatures", "pending_payout"]}},
        {"$set": {f"{p}.signatures.{side}": sig, f"{p}.bank": line["bank"], f"{p}.status": "awaiting_signatures"},
         "$push": {"audit_trail": {"at": now_iso(), "by": me, "event": f"split_{line['instruction_ref']}_signed_by_{side}"}}})
    if not r.matched_count:
        raise HTTPException(status_code=409, detail="This payment changed while you were signing — reload and check it")
    await db.escrow_transactions.update_one(
        {"_id": tx["_id"], f"{p}.signatures.pmc": {"$exists": True}, f"{p}.signatures.escrow_institution": {"$exists": True},
         f"{p}.status": "awaiting_signatures"}, {"$set": {f"{p}.status": "approved"}})
    await audit_log(f"escrow.consortium_split_sign_{side}", {"email": me, "role": via}, "escrow_tx", tid,
                    {"line": line["instruction_ref"], "amount": line["amount"]})
    return {"recorded": True, **(await db.escrow_transactions.find_one({"_id": tx["_id"]}))["consortium_split"]}


@router.post("/transactions/{tid}/consortium-split/{idx}/sign")
async def sign_line(tid: str, idx: int, body: LineSignIn, user=Depends(require_role("admin", "accounting", "escrow_agent"))):
    return await _sign(tid, idx, user.get("email"), body.comment, "staff")


async def _magic(token: str) -> dict:
    t = await db.escrow_magic_tokens.find_one({"token": token, "revoked": False})
    if not t:
        raise HTTPException(status_code=404, detail="Invalid or revoked magic token")
    return t


@router.get("/magic/{token}/consortium-splits")
async def magic_splits(token: str):
    t = await _magic(token)
    out = []
    async for x in db.escrow_transactions.find({"escrow_account_id": t["account_id"], "consortium_split": {"$exists": True}}).sort("released_at", -1).limit(100):
        out.append({"tid": str(x["_id"]), "bid_ref": x.get("bid_ref"), "notice_ref": x.get("notice_ref"), **x["consortium_split"]})
    return {"items": out, "officer_email": t["officer_email"]}


@router.post("/magic/{token}/consortium-split/{tid}/{idx}/sign")
async def magic_sign_line(token: str, tid: str, idx: int, body: LineSignIn):
    t = await _magic(token)
    tx, _ = await _tx_bid(tid)
    if tx.get("escrow_account_id") != t["account_id"]:
        raise HTTPException(status_code=403, detail="This payment is not on your escrow account")
    return await _sign(tid, idx, t["officer_email"], body.comment, "magic_link")


@router.post("/transactions/{tid}/consortium-split/{idx}/paid")
async def mark_paid(tid: str, idx: int, body: PaidIn, admin=Depends(require_role("admin", "accounting"))):
    tx, split, line = await _line(tid, idx)
    if line["status"] == "paid":
        raise HTTPException(status_code=409, detail="Already marked paid")
    if line["status"] != "approved":
        raise HTTPException(status_code=409, detail="Both escrow officers must sign this payment instruction before it can be marked paid")
    if not await db.uploads.find_one({"key": body.proof_key}):
        raise HTTPException(status_code=422, detail="Attach the bank payment slip first")
    acct = (line.get("bank") or {}).get("bank_account_number")
    if any(s.get("account") != acct for s in (line.get("signatures") or {}).values()):
        raise HTTPException(status_code=409, detail="The bank account changed after the officers signed — both must sign again")
    p = f"consortium_split.lines.{idx}"
    r = await db.escrow_transactions.update_one(
        {"_id": tx["_id"], f"{p}.status": "approved"},
        {"$set": {f"{p}.status": "paid", f"{p}.paid_ref": body.reference.strip(), f"{p}.paid_at": now_iso(),
                  f"{p}.paid_by": admin.get("email"), f"{p}.proof_key": body.proof_key}})
    if not r.matched_count:
        raise HTTPException(status_code=409, detail="Already marked paid")
    await audit_log("escrow.consortium_split_paid", admin, "escrow_tx", tid, {"member": line.get("company"), "amount": line["amount"], "ref": body.reference.strip()})
    return {"recorded": True, **(await db.escrow_transactions.find_one({"_id": tx["_id"]}))["consortium_split"]}


@router.get("/consortium-splits")
async def list_splits(_=Depends(VIEW)):
    out = []
    async for t in db.escrow_transactions.find({"consortium_split": {"$exists": True}}).sort("released_at", -1).limit(200):
        out.append({"tid": str(t["_id"]), "bid_ref": t.get("bid_ref"), "notice_ref": t.get("notice_ref"), **t["consortium_split"]})
    return {"items": out}
