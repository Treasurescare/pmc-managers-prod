"""Helpers extracted from routers/analytics.py::audit_copilot.

Kept side-effect free (or minimal I/O) so the router can compose them cheaply.
"""
import os
from datetime import datetime
from typing import List, Optional

from db import db


def _escrow_speed_flag(bid: dict) -> Optional[str]:
    """Return a warning if EMD → escrow-accept happened suspiciously fast."""
    if not (bid.get("emd_paid_at") and bid.get("status") == "escrow_accepted"):
        return None
    history = bid.get("workflow_history") or []
    try:
        t1 = datetime.fromisoformat(bid["emd_paid_at"].replace("Z", ""))
    except (ValueError, TypeError):
        return None
    escrow_step = next(
        (h for h in history
         if h.get("action") == "accept" and h.get("role") == "escrow_agent"),
        None,
    )
    if not escrow_step:
        return None
    try:
        t2 = datetime.fromisoformat(escrow_step["at"].replace("Z", ""))
    except (ValueError, TypeError):
        return None
    delta_min = (t2 - t1).total_seconds() / 60
    if delta_min < 2:
        return f"Escrow accepted only {delta_min:.1f} min after EMD paid — very fast, verify manually"
    return None


async def deterministic_flags(bid: dict) -> tuple[List[str], str]:
    """Run rule-based checks on the bid and return (flags, verdict)."""
    flags: List[str] = []
    verdict = "ok"
    history = bid.get("workflow_history") or []

    speed_flag = _escrow_speed_flag(bid)
    if speed_flag:
        flags.append(speed_flag)

    legal_ok = any(h.get("role") == "legal_counsel" and h.get("action") == "accept" for h in history)
    if legal_ok:
        kyc = await db.kyc_cases.find_one({"vendor_ref": bid.get("vendor_ref")})
        if not kyc:
            flags.append("Legal cleared but no KYC case on file for this vendor — needs review")
    if flags:
        verdict = "review"
    return flags, verdict


async def llm_narrative(bid: dict, flags: List[str], session_prefix: str) -> str:
    """Best-effort short narrative via PMC LLM key.
    Silently returns a placeholder if the key or the SDK is unavailable."""
    key = os.environ.get("LLM_API_KEY", "") or os.environ.get("LEGACY_LLM_KEY", "")
    if not key:
        return ""
    try:
        from pmc_lib.llm.chat import LlmChat, UserMessage
    except Exception as e:
        return f"(AI narrative unavailable: {type(e).__name__})"
    try:
        history = bid.get("workflow_history") or []
        chat = LlmChat(
            api_key=key,
            session_id=f"{session_prefix}-{bid.get('_id')}",
            system_message=(
                "You are a procurement audit copilot. "
                "Read the workflow history of a bid and reply in 2 short lines: "
                "(1) OK or REVIEW, (2) one-sentence rationale."
            ),
        )
        chat.with_model("openai", "gpt-4o-mini")
        hist_short = [
            {"role": h.get("role"), "action": h.get("action"),
             "to": h.get("to_status"), "at": h.get("at")}
            for h in history[-10:]
        ]
        msg = (
            f"Bid {bid.get('bid_ref')} vendor={bid.get('company_name')} "
            f"price={bid.get('price_amount')} status={bid.get('status')}. "
            f"History: {hist_short}. Rule flags: {flags}. Verdict?"
        )
        resp = await chat.send_message(UserMessage(text=msg))
        return str(resp)[:400]
    except Exception as e:
        return f"(AI narrative unavailable: {type(e).__name__})"


async def anomaly_llm_narrative(bid: dict, peer_prices: List[float], avg: float,
                                 deviation_pct: float, flags: List[str]) -> str:
    """Short LLM narrative for the bid-anomaly endpoint."""
    key = os.environ.get("LLM_API_KEY", "") or os.environ.get("LEGACY_LLM_KEY", "")
    if not key:
        return ""
    try:
        from pmc_lib.llm.chat import LlmChat, UserMessage
    except Exception as e:
        return f"(AI narrative unavailable: {type(e).__name__})"
    try:
        chat = LlmChat(
            api_key=key,
            session_id=f"anomaly-{bid.get('_id')}",
            system_message=(
                "You are a procurement audit assistant. Reply with 2-3 concise sentences."
            ),
        )
        chat.with_model("openai", "gpt-4o-mini")
        msg = (
            f"Bid price {bid.get('price_amount')}. Peer prices: {peer_prices}. "
            f"Average: {avg:.2f}. Deviation: {deviation_pct:.2f}%. "
            f"Flags detected: {flags}. Assess anomaly risk plainly."
        )
        resp = await chat.send_message(UserMessage(text=msg))
        return str(resp)[:500]
    except Exception as e:
        return f"(AI narrative unavailable: {type(e).__name__})"


def anomaly_flags(price: float, peer_prices: List[float], deviation_pct: float) -> List[str]:
    """Deterministic anomaly checks vs. peer bid prices."""
    flags: List[str] = []
    if not peer_prices:
        return flags
    lo, hi = min(peer_prices), max(peer_prices)
    if price < lo * 0.75:
        flags.append("Bid is >25% below the lowest peer — investigate for below-cost pricing")
    if price > hi * 1.3:
        flags.append("Bid is >30% above the highest peer — check for scoping mismatch")
    if abs(deviation_pct) < 0.5 and len(peer_prices) > 2:
        flags.append("Bid nearly identical to peer average — possible collusion signal")
    return flags
