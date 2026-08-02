"""Helper — compute the active matrix step for a given bid.

Returns the label + role expected next in the pipeline, purely a read-side
computation (does not mutate state). Used by the Bidding Ops table so
staff always see whose court a bid is in.
"""
from typing import Optional, Dict, Any
from bson import ObjectId
from db import db


_DEFAULT_PIPELINE = [
    ("escrow_agent", "Escrow accept EMD"),
    ("admin", "Admin flag to Certifier"),
    ("certifier", "Certifier site inspection"),
    ("legal_counsel", "Legal KYC clearance"),
    ("accounting", "Accounting sign-off"),
    ("committee_member", "Committee award"),
]

_STATUS_TO_ROLE_INDEX = {
    "emd_pending": -1, "submitted": -1,
    "emd_paid": 0, "escrow_accepted": 1,
    "admin_flagged": 2, "certifier_cleared": 3,
    "legal_cleared": 4, "accounting_cleared": 5,
    "awarded": 6, "rejected": 99, "withdrawn": 99,
    "closed": 99,
}


async def active_step(bid: Dict[str, Any]) -> Dict[str, Any]:
    """Return {'role_code': ..., 'label': ..., 'step_number': N} for the NEXT
    action expected on this bid, given its current status and (optionally)
    the notice's approval matrix."""
    status = bid.get("status")
    idx = _STATUS_TO_ROLE_INDEX.get(status, -1)

    if status in ("awarded", "rejected", "withdrawn", "closed"):
        return {"role_code": None, "label": f"Closed ({status})", "step_number": None}
    if status in ("emd_pending", "submitted"):
        return {"role_code": "vendor", "label": "Awaiting vendor EMD payment", "step_number": 0}

    # Try matrix from linked notice
    notice = await db.notices.find_one({"notice_ref": bid.get("notice_ref")})
    matrix_id = (notice or {}).get("approval_matrix_id")
    steps = _DEFAULT_PIPELINE
    if matrix_id:
        try:
            m = await db.approval_matrices.find_one({"_id": ObjectId(matrix_id)})
        except Exception:
            m = None
        if m and m.get("steps"):
            steps = [(s["role_code"], s["action_label"])
                     for s in sorted(m["steps"], key=lambda x: x.get("order", 0))]

    if 0 <= idx < len(steps):
        role, label = steps[idx]
        return {"role_code": role, "label": label, "step_number": idx + 1,
                "total_steps": len(steps)}
    return {"role_code": None, "label": "Unknown", "step_number": None}
