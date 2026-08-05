"""Wave 2 — Evaluation Engine.

Multi-envelope bidding (Technical + Commercial), scoring rubric, evaluator
scores, Conflict-of-Interest (COI) declarations, and Award Recommendation Report.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from db import db
from models.evaluation import (
    EnvelopeLockIn, COIDeclarationIn, ScoringRubricIn, ScoreEntryIn,
)
from models.base import BaseDocument, now_iso
from security import require_role, current_admin
from audit import audit_log

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


# ---------- Envelope lock (public sealed-bid) ----------

@router.post("/lock-envelope")
async def lock_envelope(payload: EnvelopeLockIn, admin=Depends(require_role("admin"))):
    """After the deadline, admin can lock a specific envelope kind so
    scoring can begin (bids can no longer be edited)."""
    key = f"{payload.kind}_locked_at"
    r = await db.notices.update_one(
        {"notice_ref": payload.notice_ref},
        {"$set": {key: now_iso(), f"{payload.kind}_locked_by": admin["id"]}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notice not found")
    await audit_log(f"envelope.lock.{payload.kind}", admin, "notice", payload.notice_ref, {})
    return {"ok": True}


# ---------- Scoring Rubric ----------

@router.post("/rubric")
async def create_rubric(payload: ScoringRubricIn, admin=Depends(require_role("admin"))):
    exist = await db.rubrics.find_one({"notice_ref": payload.notice_ref})
    if exist:
        await db.rubrics.update_one({"_id": exist["_id"]}, {"$set": payload.model_dump()})
        return _out(await db.rubrics.find_one({"_id": exist["_id"]}))
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["created_by"] = admin["id"]
    res = await db.rubrics.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _out(doc)


@router.get("/rubric/{notice_ref}")
async def get_rubric(notice_ref: str, admin=Depends(current_admin)):
    doc = await db.rubrics.find_one({"notice_ref": notice_ref})
    if not doc:
        raise HTTPException(status_code=404, detail="Rubric not defined for this tender")
    return _out(doc)


# ---------- Conflict-of-Interest ----------

@router.post("/coi")
async def declare_coi(payload: COIDeclarationIn, admin=Depends(current_admin)):
    """Evaluator must declare COI BEFORE scoring."""
    doc = payload.model_dump()
    doc.update({"evaluator_id": admin["id"], "evaluator_email": admin["email"],
                "declared_at": now_iso()})
    await db.coi_declarations.update_one(
        {"notice_ref": payload.notice_ref, "evaluator_id": admin["id"]},
        {"$set": doc},
        upsert=True,
    )
    await audit_log("coi.declare", admin, "notice", payload.notice_ref,
                    {"has_conflict": payload.has_conflict})
    return {"ok": True}


@router.get("/coi/{notice_ref}")
async def list_coi(notice_ref: str, admin=Depends(require_role("admin", "auditor"))):
    return [_out(d) async for d in db.coi_declarations.find({"notice_ref": notice_ref})]


# ---------- Score entry ----------

@router.post("/score")
async def submit_score(payload: ScoreEntryIn,
                       admin=Depends(require_role("admin", "committee_member", "reviewer"))):
    # Must have declared COI first (no conflict, or with details)
    bid = await db.bids.find_one({"_id": ObjectId(payload.bid_id)})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    coi = await db.coi_declarations.find_one({
        "notice_ref": bid["notice_ref"], "evaluator_id": admin["id"],
    })
    if not coi:
        raise HTTPException(status_code=400,
                            detail="You must declare Conflict-of-Interest before scoring")
    if coi.get("has_conflict"):
        raise HTTPException(status_code=403,
                            detail="You declared a conflict — cannot score this tender")

    entry = {
        "bid_id": payload.bid_id,
        "notice_ref": bid["notice_ref"],
        "kind": payload.kind,
        "evaluator_id": admin["id"],
        "evaluator_email": admin["email"],
        "scores": payload.scores,
        "remarks": payload.remarks,
        "submitted_at": now_iso(),
    }
    await db.scores.update_one(
        {"bid_id": payload.bid_id, "kind": payload.kind, "evaluator_id": admin["id"]},
        {"$set": entry}, upsert=True,
    )
    await audit_log(f"score.{payload.kind}", admin, "bid", bid.get("bid_ref"), entry)
    return {"ok": True}


@router.get("/scores/{notice_ref}")
async def list_scores(notice_ref: str, admin=Depends(require_role("admin", "committee_member", "auditor"))):
    return [_out(s) async for s in db.scores.find({"notice_ref": notice_ref})]


# ---------- Award Recommendation Report (helpers extracted for clarity) ----------


def _load_rubric_config(rubric: dict) -> dict:
    """Normalise rubric weights + minimum threshold. Never returns invalid values."""
    commercial_weight = float(rubric.get("commercial_weight", 0.4) or 0.4)
    return {
        "tech_criteria":     rubric.get("technical_criteria", []),
        "commercial_weight": commercial_weight,
        "tech_weight":       1.0 - commercial_weight,
        "min_tech":          float(rubric.get("minimum_technical", 60.0) or 60.0),
    }


def _pct_technical(scores: dict, tech_criteria: list) -> float:
    """Weighted average of an evaluator's technical scores, normalised 0-100."""
    if not tech_criteria:
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for c in tech_criteria:
        v = float((scores or {}).get(c["code"], 0) or 0)
        mx = float(c.get("max_score", 100) or 100)
        w = float(c.get("weight", 0) or 0)
        total += (v / mx) * 100.0 * w
        weight_sum += w
    return total / weight_sum if weight_sum else 0.0


def _pct_commercial(scores: dict) -> float:
    v = float((scores or {}).get("commercial", 0) or 0)
    return max(0.0, min(100.0, v))


def _group_scores_by_bid(all_scores: list, tech_criteria: list) -> dict:
    """Return `{bid_id: {"technical": [pct...], "commercial": [pct...]}}`."""
    per_bid: dict = {}
    for s in all_scores:
        bmap = per_bid.setdefault(s["bid_id"], {"technical": [], "commercial": []})
        if s["kind"] == "technical":
            pct = _pct_technical(s.get("scores") or {}, tech_criteria)
        elif s["kind"] == "commercial":
            pct = _pct_commercial(s.get("scores") or {})
        else:
            continue
        bmap[s["kind"]].append(pct)
    return per_bid


def _bid_row(bid: dict, per_bid: dict, cfg: dict) -> dict:
    bid_id = str(bid["_id"])
    m = per_bid.get(bid_id, {"technical": [], "commercial": []})
    tech_avg = (sum(m["technical"]) / len(m["technical"])) if m["technical"] else 0.0
    comm_avg = (sum(m["commercial"]) / len(m["commercial"])) if m["commercial"] else 0.0
    combined = (tech_avg * cfg["tech_weight"]) + (comm_avg * cfg["commercial_weight"])
    return {
        "bid_id":        bid_id,
        "bid_ref":       bid.get("bid_ref"),
        "vendor":        bid.get("company_name") or bid.get("vendor_email"),
        "price":         bid.get("price_amount"),
        "technical_avg": round(tech_avg, 2),
        "commercial_avg": round(comm_avg, 2),
        "combined":      round(combined, 2),
        "qualifies":     tech_avg >= cfg["min_tech"],
        "status":        bid.get("status"),
    }


@router.get("/award-report/{notice_ref}")
async def award_report(notice_ref: str,
                       admin=Depends(require_role("admin", "committee_member", "auditor"))):
    """Aggregate all scores + rubric → weighted combined score per bid → ranking.
    Returns the recommendation report used by the Bid Committee."""
    rubric = await db.rubrics.find_one({"notice_ref": notice_ref}) or {}
    cfg = _load_rubric_config(rubric)
    bids = [b async for b in db.bids.find({"notice_ref": notice_ref})]
    all_scores = [s async for s in db.scores.find({"notice_ref": notice_ref})]
    per_bid = _group_scores_by_bid(all_scores, cfg["tech_criteria"])
    rows = [_bid_row(b, per_bid, cfg) for b in bids]
    rows.sort(key=lambda r: (-r["combined"], r.get("price") or 0))
    return {
        "notice_ref":     notice_ref,
        "rubric":         {"technical_weight": cfg["tech_weight"],
                            "commercial_weight": cfg["commercial_weight"],
                            "minimum_technical": cfg["min_tech"],
                            "criteria": cfg["tech_criteria"]},
        "recommendation": rows[0] if rows and rows[0]["qualifies"] else None,
        "ranking":        rows,
        "generated_at":   now_iso(),
    }
