"""Helpers extracted from routers/bids.py::decide_bid to reduce complexity.

Kept side-effect free: pure functions that resolve the next status and
validate transitions. All DB writes remain in the router.
"""
from typing import Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException

from db import db


ROLE_TO_TARGET_STATUS = {
    "escrow_agent":   ("emd_paid",            "escrow_accepted"),
    "admin":          ("escrow_accepted",     "admin_flagged"),
    "certifier":      ("admin_flagged",       "certifier_cleared"),
    "legal_counsel":  ("certifier_cleared",   "legal_cleared"),
    "accounting":     ("legal_cleared",       "accounting_cleared"),
    "committee":      ("accounting_cleared",  "awarded"),
}


def check_role_match(admin_role: str, payload_role: str) -> None:
    """Committee members can act as 'committee', otherwise roles must match."""
    if admin_role == payload_role:
        return
    if payload_role == "committee" and admin_role == "committee_member":
        return
    raise HTTPException(
        status_code=403,
        detail=f"Active role {admin_role} cannot act as {payload_role}",
    )


async def resolve_matrix_next_status(bid: dict, payload_role: str) -> Tuple[Optional[str], bool]:
    """If the notice has an approval matrix, return (next_status, matrix_used).
    matrix_used=True means the fallback expected-status check is bypassed."""
    notice = await db.notices.find_one({"notice_ref": bid.get("notice_ref")})
    matrix_id = (notice or {}).get("approval_matrix_id")
    if not matrix_id:
        return None, False
    try:
        matrix = await db.approval_matrices.find_one({"_id": ObjectId(matrix_id)})
    except Exception:
        matrix = None
    steps = sorted((matrix or {}).get("steps", []), key=lambda s: s.get("order", 0))
    for i, s in enumerate(steps):
        if s.get("role_code") != payload_role:
            continue
        if i + 1 < len(steps):
            if payload_role == "escrow_agent":
                return "escrow_accepted", True
            if payload_role == "admin":
                return "admin_flagged", True
            return f"{payload_role}_cleared", True
        # Terminal step
        if payload_role in ("committee", "committee_member"):
            return "awarded", True
        return f"{payload_role}_cleared", True
    return None, False


def resolve_action_next_status(action: str, role: str, current_next: Optional[str]) -> str:
    """For non-accept actions (reject/flag/award) the next_status is fixed."""
    if action == "reject":
        return "rejected"
    if action == "flag":
        return "admin_flagged"
    if action == "award":
        if role != "committee":
            raise HTTPException(status_code=403, detail="Only committee can award")
        return "awarded"
    if not current_next:
        raise HTTPException(status_code=400, detail="Invalid action for role")
    return current_next


def validate_transition(action: str, expected: Optional[str], prev_status: Optional[str],
                         payload_role: str) -> None:
    """Enforce the from→to transition when we're accepting via the fixed pipeline."""
    if action != "accept":
        return
    if not expected:
        return
    if prev_status == expected:
        return
    raise HTTPException(
        status_code=400,
        detail=f"Bid must be in status '{expected}' before {payload_role} can accept (current: {prev_status})",
    )
