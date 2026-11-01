"""Tender process tracker: criteria -> bids -> opening -> proof review -> price -> L1 -> award."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from db import db
from security import current_admin

router = APIRouter(prefix="/api/v1/tender-tracker", tags=["tender-tracker"])
LABELS = [("criteria", "Criteria"), ("bids", "Bids"), ("opening", "Opening"), ("proof", "Proof review"),
          ("price", "Price"), ("l1", "L1"), ("award", "Award")]


def _past(iso) -> bool:
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return False
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)) <= datetime.now(timezone.utc)


async def _track(n: dict) -> dict:
    ref = n["notice_ref"]
    crit = n.get("tender_criteria") or []
    bids = [b async for b in db.bids.find({"notice_ref": ref, "status": {"$nin": ["withdrawn", "draft"]}},
                                          {"status": 1, "technical_cleared_at": 1, "qualification": 1})]
    pending = sum(1 for b in bids if b.get("technical_cleared_at")
                  and any(v.get("status") == "pending" for v in ((b.get("qualification") or {}).get("proof_reviews") or {}).values()))
    l1 = await db.comparison_runs.find_one({"notice_ref": ref}, {"_id": 1})
    awarded = any(b.get("status") == "awarded" for b in bids)
    done = {
        "criteria": bool(crit),
        "bids": bool(n.get("is_published")) and _past(n.get("submission_deadline")) and bool(bids),
        "opening": bool(n.get("technical_opened_at")),
        "proof": bool(n.get("technical_opened_at")) and not pending,
        "price": bool(n.get("commercial_opened_at")),
        "l1": bool(l1),
        "award": awarded,
    }
    detail = {
        "criteria": f"{len(crit)} criteria" if crit else "No criteria yet",
        "bids": f"{len(bids)} bid(s)" + ("" if _past(n.get("submission_deadline")) else " \u00b7 open"),
        "opening": "Technical envelopes opened" if done["opening"] else "Awaiting committee signatures",
        "proof": f"{pending} bid(s) awaiting decisions" if pending else ("All proofs decided" if done["opening"] else "After opening"),
        "price": "Prices opened" if done["price"] else "After proof review",
        "l1": "Ranking ready" if done["l1"] else "Runs after price opening",
        "award": "Awarded" if awarded else "Not awarded yet",
    }
    stages, current = [], None
    last = max((i for i, (k, _) in enumerate(LABELS) if done[k]), default=-1)
    for i, (k, label) in enumerate(LABELS):
        st = "done" if done[k] else ("skipped" if i < last else ("current" if current is None else "todo"))
        if st == "current":
            current = k
        stages.append({"key": k, "label": label, "state": st, "detail": detail[k]})
    return {"stages": stages, "current": current, "done": sum(done.values())}


@router.get("/live")
async def live(_=Depends(current_admin)):
    rows = []
    async for n in db.notices.find({"is_published": True, "deleted_at": None}, {"notice_ref": 1, "title": 1, "tender_criteria": 1, "is_published": 1, "submission_deadline": 1,
                                                                             "technical_opened_at": 1, "commercial_opened_at": 1}).sort("submission_deadline", 1):
        if len(rows) >= 40:
            break
        t = await _track(n)
        if t["current"]:
            rows.append({"notice_ref": n["notice_ref"], "title": n.get("title"), "deadline": n.get("submission_deadline"), **t})
    return {"tenders": rows}


@router.get("")
async def tracker(refs: str = Query(..., max_length=4000), _=Depends(current_admin)):
    out = {}
    wanted = [r for r in refs.split(",") if r][:60]
    async for n in db.notices.find({"notice_ref": {"$in": wanted}}, {"notice_ref": 1, "tender_criteria": 1, "is_published": 1, "submission_deadline": 1,
                                                                    "technical_opened_at": 1, "commercial_opened_at": 1}):
        out[n["notice_ref"]] = await _track(n)
    return out
