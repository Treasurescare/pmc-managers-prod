"""Wave 31 — AI Redline Comparison of two bids.

Feeds two bid scopes / technical narratives into the LLM and asks it
to surface clause-level differences (obligations, pricing, timeline, risks).
Runs as an ADVISORY layer — no state change to either bid, only an audit-log
entry. Human evaluators still make the final call, keeping the audit chain
attributable to authorised individuals.
"""
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/bids", tags=["bids-ai"])


class RedlineIn(BaseModel):
    bid_ref_a: Optional[str] = None
    bid_ref_b: Optional[str] = None
    scope_a: Optional[str] = None
    scope_b: Optional[str] = None
    focus: str = Field(default="scope",
                        description="scope | pricing | timeline | risk | all")


async def _fetch_bid_scope(ref: str) -> str:
    """Best-effort: pull the scope of a bid from the notice and the bid record.
    Bids don't always carry their own scope text, so we assemble from
    company_name + price + technical_notes + linked notice description."""
    b = await db.bids.find_one({"bid_ref": ref})
    if not b:
        try:
            b = await db.bids.find_one({"_id": ObjectId(ref)})
        except Exception:
            b = None
    if not b:
        raise HTTPException(status_code=404, detail=f"Bid {ref} not found")
    notice_ref = b.get("notice_ref")
    n = await db.notices.find_one({"notice_ref": notice_ref}) if notice_ref else None
    parts = [
        f"Bid ref: {b.get('bid_ref')}",
        f"Vendor: {b.get('company_name') or b.get('vendor_ref')}",
        f"Price: {b.get('price_amount')} {b.get('price_currency')}",
        f"Delivery: {b.get('delivery_days') or '?'} days",
        f"Technical notes: {b.get('technical_notes') or '—'}",
        f"Scope of underlying notice: {(n or {}).get('description', '—')}",
    ]
    return "\n".join(parts)


@router.post("/compare-ai")
async def compare_bids_ai(payload: RedlineIn,
                           admin=Depends(require_role("admin", "reviewer", "committee_member"))):
    """Return a clause-level AI redline between two bids.
    Provide either (bid_ref_a, bid_ref_b) or (scope_a, scope_b)."""
    key = os.environ.get("LLM_API_KEY", "") or os.environ.get("LEGACY_LLM_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="AI copilot not configured")
    if payload.bid_ref_a and payload.bid_ref_b:
        scope_a = await _fetch_bid_scope(payload.bid_ref_a)
        scope_b = await _fetch_bid_scope(payload.bid_ref_b)
    elif payload.scope_a and payload.scope_b:
        scope_a, scope_b = payload.scope_a, payload.scope_b
    else:
        raise HTTPException(status_code=400,
                             detail="Provide (bid_ref_a & bid_ref_b) OR (scope_a & scope_b)")
    try:
        from pmc_lib.llm.chat import LlmChat, UserMessage
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM SDK unavailable: {type(e).__name__}")

    focus = payload.focus or "scope"
    chat = LlmChat(
        api_key=key,
        session_id=f"bid-compare-{payload.bid_ref_a or 'a'}-{payload.bid_ref_b or 'b'}",
        system_message=(
            "You are a procurement evaluation copilot operating in ADVISORY mode. "
            "Compare two bid submissions clause by clause and surface concrete "
            "differences. Focus on: obligations, deliverables, pricing basis, "
            "payment terms, timeline, warranties, penalties, exclusions and risks. "
            "Return ONE compact JSON object with keys "
            "`summary` (2-3 sentence overview), "
            "`clauses` (array of {topic, bid_a, bid_b, delta, severity: low|medium|high}), "
            "`recommended_questions` (array of 3-5 short clarification questions the "
            "committee should send to both bidders), and "
            "`advisory_notice` (a one-line reminder that this is guidance only). "
            "Do NOT rank the bids or recommend a winner — final signature stays with "
            "authorised procurement personnel."
        ),
    )
    chat.with_model("openai", "gpt-4o-mini")
    prompt = f"Focus area: {focus}\n\nBID A:\n{scope_a}\n\nBID B:\n{scope_b}"
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__}")
    text = str(resp)
    # Try to parse JSON; if the model wrapped it in fences, strip them.
    import json
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {"summary": text[:1200], "clauses": [], "recommended_questions": [],
                   "advisory_notice": "AI output was not structured JSON; showing raw text."}
    parsed.setdefault("advisory_notice",
                       "This comparison is AI-assisted and advisory. Final decisions remain "
                       "with authorised procurement personnel and are fully audited.")
    await audit_log("bid.ai_compare", admin, "bid",
                     f"{payload.bid_ref_a}~{payload.bid_ref_b}",
                     {"focus": focus, "clause_count": len(parsed.get("clauses") or [])})
    return parsed
