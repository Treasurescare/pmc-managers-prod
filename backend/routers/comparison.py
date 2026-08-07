"""Wave 41 — L1 Auto-Comparison Engine.

Rule-based lowest-price shortlisting for a notice. Filters withdrawn/rejected
bids, requires technical clearance, and flags compliance issues (missing docs,
price outside min/max range if configured). Returns an L1/L2/L3 ranked list.

Endpoints:
  POST /api/v1/comparison/l1/{notice_ref}       (admin) run + return ranking
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.base import BaseDocument
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/comparison", tags=["comparison"])


def _compliance_flags(bid: dict, notice: dict) -> List[str]:
    flags = []
    if not bid.get("technical_cleared_at"):
        flags.append("technical_not_cleared")
    if not bid.get("price_amount") or bid["price_amount"] <= 0:
        flags.append("missing_price")
    if not (bid.get("documents") or []):
        flags.append("no_documents")
    else:
        kinds = {d.get("kind") for d in bid["documents"]}
        if "technical" not in kinds:
            flags.append("no_technical_docs")
        if "commercial" not in kinds:
            flags.append("no_commercial_docs")
    # Budget guardrail — if notice has a budget, flag bids > 150% or < 40%.
    budget = notice.get("budget_amount")
    if budget:
        p = bid.get("price_amount") or 0
        if p > budget * 1.5:
            flags.append("above_budget_150pct")
        if 0 < p < budget * 0.4:
            flags.append("suspiciously_low")
    return flags


def _rank_row(b: dict, notice: dict, rank: int) -> dict:
    flags = _compliance_flags(b, notice)
    return {
        "rank": rank,
        "bid_id": str(b["_id"]),
        "bid_ref": b.get("bid_ref"),
        "vendor_id": b.get("vendor_id"),
        "company_name": b.get("company_name") or b.get("vendor_email"),
        "price_amount": b.get("price_amount"),
        "price_currency": b.get("price_currency"),
        "status": b.get("status"),
        "technical_cleared": bool(b.get("technical_cleared_at")),
        "compliance_flags": flags,
        "compliant": len(flags) == 0,
    }


@router.post("/l1/{notice_ref}")
async def run_l1_comparison(notice_ref: str,
                             admin=Depends(require_role("admin", "committee_member"))):
    notice = await db.notices.find_one({"notice_ref": notice_ref})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    # Only bids that are alive in the pipeline. Withdrawn/rejected are excluded.
    live_statuses = {"submitted", "technical_cleared", "commercial_open",
                      "under_evaluation", "awarded"}
    all_bids = []
    async for b in db.bids.find({"notice_ref": notice_ref}):
        all_bids.append(b)

    eligible = [b for b in all_bids
                if (b.get("status") in live_statuses)
                and bool(b.get("technical_cleared_at"))
                and (b.get("price_amount") or 0) > 0]

    eligible.sort(key=lambda x: x.get("price_amount") or 0)

    ranked = [_rank_row(b, notice, i + 1) for i, b in enumerate(eligible)]
    ineligible = [{
        "bid_id": str(b["_id"]),
        "bid_ref": b.get("bid_ref"),
        "company_name": b.get("company_name") or b.get("vendor_email"),
        "status": b.get("status"),
        "reason": (
            "withdrawn/rejected" if b.get("status") not in live_statuses
            else "no_technical_clear" if not b.get("technical_cleared_at")
            else "no_price"
        ),
    } for b in all_bids if b not in eligible]

    l1_winner = None
    for r in ranked:
        if r["compliant"]:
            l1_winner = r
            break

    result = {
        "notice_ref": notice_ref,
        "notice_title": notice.get("title"),
        "budget_amount": notice.get("budget_amount"),
        "budget_currency": notice.get("budget_currency"),
        "total_bids": len(all_bids),
        "eligible_count": len(eligible),
        "ineligible_count": len(ineligible),
        "ranked": ranked,
        "ineligible": ineligible,
        "l1_winner": l1_winner,
        "l2": next((r for r in ranked if r["compliant"] and r != l1_winner), None),
        "l3": None,
    }
    # Simple L3 pick — second compliant that's not L2.
    compliant = [r for r in ranked if r["compliant"]]
    if len(compliant) > 2:
        result["l3"] = compliant[2]

    await audit_log("comparison.l1", admin, "notice", notice_ref,
                    {"total": len(all_bids), "eligible": len(eligible),
                     "l1": l1_winner["bid_ref"] if l1_winner else None})
    # Persist the last run for later reference.
    await db.comparison_runs.insert_one({
        "notice_ref": notice_ref,
        "run_at": notice.get("_run_at") or __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "run_by": admin.get("email"),
        "result": result,
    })
    return result
