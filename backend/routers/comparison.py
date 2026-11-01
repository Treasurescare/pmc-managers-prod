"""Wave 41 — L1 Auto-Comparison Engine.

Rule-based lowest-price shortlisting for a notice. Filters withdrawn/rejected
bids, requires technical clearance, and flags compliance issues (missing docs,
price outside min/max range if configured). Returns an L1/L2/L3 ranked list.

Endpoints:
  POST /api/v1/comparison/l1/{notice_ref}       (admin) run + return ranking
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
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
    # v53g — include the mid-pipeline governance statuses too, otherwise bids
    # that already passed escrow/admin/legal (including v53g zero-EMD bids,
    # which are CREATED at escrow_accepted) silently dropped out of L1.
    live_statuses = {"submitted", "emd_paid", "escrow_accepted",
                      "admin_flagged", "certifier_cleared", "legal_cleared",
                      "accounting_cleared", "technical_cleared",
                      "commercial_open", "under_evaluation", "awarded"}
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
        "award_method": notice.get("award_method") or "l1",
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


@router.get("/l1/{notice_ref}/latest")
async def latest_l1(notice_ref: str, _=Depends(require_role("admin", "committee_member", "reviewer", "auditor"))):
    run = await db.comparison_runs.find_one({"notice_ref": notice_ref}, sort=[("run_at", -1)])
    return {"result": (run or {}).get("result"), "run_at": (run or {}).get("run_at"), "run_by": (run or {}).get("run_by")}


class AwardL1In(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)


@router.post("/l1/{notice_ref}/award")
async def award_l1(notice_ref: str, body: AwardL1In, admin=Depends(require_role("admin", "committee_member"))):
    from models.bid import BidDecisionIn
    from routers.bids import decide_bid
    from routers.proof_ai import _members
    notice = await db.notices.find_one({"notice_ref": notice_ref}, {"award_method": 1, "commercial_opened_at": 1})
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    if admin.get("id") not in await _members(notice_ref):
        raise HTTPException(status_code=403, detail="Only a member of this tender's evaluation committee can award")
    if (notice.get("award_method") or "l1") != "l1":
        raise HTTPException(status_code=409, detail="This tender is awarded on weighted marks — use the Award recommendation report")
    if not notice.get("commercial_opened_at"):
        raise HTTPException(status_code=409, detail="Price envelopes are not open yet")
    if await db.bids.find_one({"notice_ref": notice_ref, "status": "awarded"}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="This tender has already been awarded")
    result = await run_l1_comparison(notice_ref, admin)
    win = result.get("l1_winner")
    if not win:
        raise HTTPException(status_code=409, detail="No compliant L1 bid to award")
    if win["status"] != "accounting_cleared":
        raise HTTPException(status_code=409, detail=f"The L1 bid ({win['bid_ref']}) is at stage '{win['status']}'. Certifier, legal and accounting clearances must be completed before award.")
    note = f"Awarded to L1 (lowest compliant price) from the automatic ranking.{(' ' + body.notes.strip()) if body.notes else ''}"
    await decide_bid(win["bid_id"], BidDecisionIn(action="award", role="committee", notes=note), admin={**admin, "role": "committee_member"})
    await audit_log("comparison.l1_award", admin, "notice", notice_ref, {"bid": win["bid_ref"], "price": win.get("price_amount")})
    return {"awarded": win["bid_ref"], "company_name": win.get("company_name")}