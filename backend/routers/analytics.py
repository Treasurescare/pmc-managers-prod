"""Wave 5 — BI Dashboards + AI (bid anomaly & vendor scoring via Emergent LLM key)."""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics-ai"])


@router.get("/dashboard")
async def dashboard(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    """Aggregated KPIs for the executive dashboard."""
    total_notices = await db.notices.count_documents({})
    published = await db.notices.count_documents({"is_published": True})
    total_bids = await db.bids.count_documents({})
    awarded = await db.bids.count_documents({"status": "awarded"})
    pending_emd = await db.bids.count_documents({"status": "emd_pending"})
    vendors = await db.vendors.count_documents({})
    active_contracts = await db.contracts.count_documents({"status": "active"})

    # EMD collected (sum of paid transactions)
    emd_collected = 0.0
    async for tx in db.payment_transactions.find({"payment_status": "paid"}):
        emd_collected += float(tx.get("amount") or 0)

    # Pipeline funnel
    funnel = {}
    for status in ["emd_pending", "emd_paid", "escrow_accepted", "admin_flagged",
                   "certifier_cleared", "legal_cleared", "accounting_cleared", "awarded"]:
        funnel[status] = await db.bids.count_documents({"status": status})

    # Top-priced bids for spend visibility
    top_bids = []
    async for b in db.bids.find({}, {"bid_ref": 1, "notice_ref": 1, "company_name": 1,
                                     "price_amount": 1, "status": 1}) \
                          .sort("price_amount", -1).limit(10):
        top_bids.append({"bid_ref": b.get("bid_ref"), "notice_ref": b.get("notice_ref"),
                         "vendor": b.get("company_name"), "price": b.get("price_amount"),
                         "status": b.get("status")})
    return {
        "totals": {"notices": total_notices, "published_notices": published,
                   "bids": total_bids, "awarded": awarded,
                   "pending_emd": pending_emd, "vendors": vendors,
                   "active_contracts": active_contracts,
                   "emd_collected": round(emd_collected, 2)},
        "funnel": funnel, "top_bids": top_bids,
    }


@router.post("/ai/bid-anomaly/{bid_id}")
async def bid_anomaly_check(bid_id: str,
                             admin=Depends(require_role("admin", "committee_member"))):
    """Uses the Emergent LLM key to flag anomalies in a bid vs. peer bids.
    Returns a natural-language flag list + a numeric anomaly score (0-100)."""
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    peers = [b async for b in db.bids.find({
        "notice_ref": bid["notice_ref"], "_id": {"$ne": bid["_id"]},
    }).limit(50)]
    peer_prices = [float(p.get("price_amount") or 0) for p in peers if p.get("price_amount")]
    if not peer_prices:
        return {"score": 0, "flags": [], "notes": "No peer bids yet — cannot compute."}

    avg = sum(peer_prices) / len(peer_prices)
    lo, hi = min(peer_prices), max(peer_prices)
    price = float(bid.get("price_amount") or 0)
    deviation_pct = ((price - avg) / avg) * 100 if avg else 0.0

    flags = []
    if price < lo * 0.75:
        flags.append("Bid is >25% below the lowest peer — investigate for below-cost pricing")
    if price > hi * 1.3:
        flags.append("Bid is >30% above the highest peer — check for scoping mismatch")
    if abs(deviation_pct) < 0.5 and len(peer_prices) > 2:
        flags.append("Bid nearly identical to peer average — possible collusion signal")

    # Try to enrich with LLM narrative
    narrative = ""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        key = os.environ.get("EMERGENT_LLM_KEY", "")
        if key:
            chat = LlmChat(api_key=key, session_id=f"anomaly-{bid_id}",
                           system_message="You are a procurement audit assistant. "
                                          "Reply with 2-3 concise sentences.")
            chat.with_model("openai", "gpt-4o-mini")
            msg = (f"Bid price {price}. Peer prices: {peer_prices}. "
                   f"Average: {avg:.2f}. Deviation: {deviation_pct:.2f}%. "
                   f"Flags detected: {flags}. Assess anomaly risk plainly.")
            resp = await chat.send_message(UserMessage(text=msg))
            narrative = str(resp)[:500]
    except Exception as e:
        narrative = f"(AI narrative unavailable: {type(e).__name__})"

    score = min(100.0, abs(deviation_pct) + 10 * len(flags))
    result = {"score": round(score, 1), "flags": flags,
              "deviation_pct": round(deviation_pct, 2),
              "peer_avg": round(avg, 2), "narrative": narrative,
              "computed_at": now_iso()}
    # Persist for audit
    await db.ai_anomalies.update_one(
        {"bid_id": bid_id}, {"$set": {"bid_id": bid_id, **result}}, upsert=True,
    )
    return result
