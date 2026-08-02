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

    # EMD collected — aggregate in MongoDB (unbounded find would degrade badly)
    emd_pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    agg = await db.payment_transactions.aggregate(emd_pipeline).to_list(length=1)
    emd_collected = float(agg[0]["total"]) if agg else 0.0

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


@router.post("/ai/audit-copilot/{bid_id}")
async def audit_copilot(bid_id: str,
                        admin=Depends(require_role("admin", "committee_member", "auditor"))):
    """LLM reviews the bid's workflow_history and flags anomalies + issues an OK/REVIEW verdict.
    Falls back to a deterministic rule-based verdict if the Emergent LLM key is unavailable."""
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    history = bid.get("workflow_history") or []
    # Deterministic quick-checks
    verdict = "ok"
    flags = []
    if bid.get("emd_paid_at") and bid.get("status") == "escrow_accepted":
        # Time between EMD paid and escrow accept
        try:
            from datetime import datetime
            t1 = datetime.fromisoformat(bid["emd_paid_at"].replace("Z", ""))
            for h in history:
                if h.get("action") == "accept" and h.get("role") == "escrow_agent":
                    t2 = datetime.fromisoformat(h["at"].replace("Z", ""))
                    delta = (t2 - t1).total_seconds() / 60
                    if delta < 2:
                        flags.append(f"Escrow accepted only {delta:.1f} min after EMD paid — very fast, verify manually")
                    break
        except Exception:
            pass
    # Legal cleared without any KYC evidence?
    if any(h.get("role") == "legal_counsel" and h.get("action") == "accept" for h in history):
        kyc = await db.kyc_cases.find_one({"vendor_ref": bid.get("vendor_ref")})
        if not kyc:
            flags.append("Legal cleared but no KYC case on file for this vendor — needs review")
            verdict = "review"
    if flags:
        verdict = "review"

    # Try LLM narrative
    narrative = ""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        key = os.environ.get("EMERGENT_LLM_KEY", "")
        if key:
            chat = LlmChat(api_key=key, session_id=f"copilot-{bid_id}",
                           system_message=("You are a procurement audit copilot. "
                                            "Read the workflow history of a bid and reply "
                                            "in 2 short lines: (1) OK or REVIEW, "
                                            "(2) one-sentence rationale."))
            chat.with_model("openai", "gpt-4o-mini")
            hist_short = [{"role": h.get("role"), "action": h.get("action"),
                           "to": h.get("to_status"), "at": h.get("at")} for h in history[-10:]]
            msg = (f"Bid {bid.get('bid_ref')} vendor={bid.get('company_name')} "
                   f"price={bid.get('price_amount')} status={bid.get('status')}. "
                   f"History: {hist_short}. Rule flags: {flags}. Verdict?")
            resp = await chat.send_message(UserMessage(text=msg))
            narrative = str(resp)[:400]
    except Exception as e:
        narrative = f"(AI narrative unavailable: {type(e).__name__})"

    return {"verdict": verdict, "flags": flags, "narrative": narrative,
            "history_length": len(history), "generated_at": now_iso()}


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
