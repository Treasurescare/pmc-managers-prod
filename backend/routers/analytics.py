"""Wave 5 — BI Dashboards + AI (bid anomaly & vendor scoring via PMC LLM key)."""
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.base import now_iso
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
    Falls back to a deterministic rule-based verdict if the PMC LLM key is unavailable."""
    from routers.analytics_helpers import deterministic_flags, llm_narrative
    bid = await db.bids.find_one({"_id": ObjectId(bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    flags, verdict = await deterministic_flags(bid)
    narrative = await llm_narrative(bid, flags, session_prefix="copilot")
    return {"verdict": verdict, "flags": flags, "narrative": narrative,
            "history_length": len(bid.get("workflow_history") or []),
            "generated_at": now_iso()}


@router.post("/ai/bid-anomaly/{bid_id}")
async def bid_anomaly_check(bid_id: str,
                             admin=Depends(require_role("admin", "committee_member"))):
    """Uses the PMC LLM key to flag anomalies in a bid vs. peer bids.
    Returns a natural-language flag list + a numeric anomaly score (0-100)."""
    from routers.analytics_helpers import anomaly_flags, anomaly_llm_narrative
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
    price = float(bid.get("price_amount") or 0)
    deviation_pct = ((price - avg) / avg) * 100 if avg else 0.0

    flags = anomaly_flags(price, peer_prices, deviation_pct)
    narrative = await anomaly_llm_narrative(bid, peer_prices, avg, deviation_pct, flags)

    score = min(100.0, abs(deviation_pct) + 10 * len(flags))
    result = {"score": round(score, 1), "flags": flags,
              "deviation_pct": round(deviation_pct, 2),
              "peer_avg": round(avg, 2), "narrative": narrative,
              "computed_at": now_iso()}
    await db.ai_anomalies.update_one(
        {"bid_id": bid_id}, {"$set": {"bid_id": bid_id, **result}}, upsert=True,
    )
    return result
