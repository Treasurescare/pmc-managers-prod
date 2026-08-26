"""Wave 9 — Permissions Matrix.

Grid of allowed actions on Notices (Tender/RFP/RFQ), keyed by staff role.
- Rows: staff roles (admin, escrow_agent, certifier, legal_counsel, accounting,
        committee_member, reviewer, auditor, support)
- Cols: view, create, modify, delete, publish
- Optional per-document-type filter (`*` = all).

Enforcement: `check_notice_permission(admin, action, document_type)` — call
before mutating a notice.
"""
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


PermAction = Literal["view", "create", "modify", "delete", "publish"]
DocType = Literal["tender", "rfp", "rfq", "*"]


class PermissionRow(BaseModel):
    role: str
    document_type: DocType = "*"
    view: bool = False
    create: bool = False
    modify: bool = False
    delete: bool = False
    publish: bool = False


class PermissionMatrixIn(BaseModel):
    rows: List[PermissionRow]


DEFAULT_MATRIX: List[dict] = [
    {"role": "admin",             "document_type": "*", "view": True, "create": True, "modify": True, "delete": True, "publish": True},
    # Reviewers are typically sub-admin operational staff — allowed to draft &
    # modify notices, but publishing is reserved for the master admin so the
    # final board is gated by one authoritative approver.
    {"role": "reviewer",          "document_type": "*", "view": True, "create": True, "modify": True, "delete": False, "publish": False},
    {"role": "auditor",           "document_type": "*", "view": True, "create": False, "modify": False, "delete": False, "publish": False},
    {"role": "committee_member",  "document_type": "*", "view": True, "create": False, "modify": False, "delete": False, "publish": False},
    {"role": "escrow_agent",      "document_type": "*", "view": True, "create": False, "modify": False, "delete": False, "publish": False},
    {"role": "certifier",         "document_type": "*", "view": True, "create": False, "modify": False, "delete": False, "publish": False},
    {"role": "legal_counsel",     "document_type": "*", "view": True, "create": False, "modify": True, "delete": False, "publish": False},
    {"role": "accounting",        "document_type": "*", "view": True, "create": False, "modify": False, "delete": False, "publish": False},
    {"role": "support",           "document_type": "*", "view": True, "create": False, "modify": False, "delete": False, "publish": False},
]


async def _get_matrix() -> List[dict]:
    doc = await db.permission_matrix.find_one({"scope": "notices"})
    if not doc:
        return DEFAULT_MATRIX
    return doc.get("rows") or DEFAULT_MATRIX


@router.get("")
async def get_matrix(admin=Depends(require_role("admin", "auditor", "reviewer"))):
    return {"scope": "notices", "rows": await _get_matrix()}


@router.put("")
async def put_matrix(payload: PermissionMatrixIn, admin=Depends(require_role("admin"))):
    await db.permission_matrix.update_one(
        {"scope": "notices"},
        {"$set": {"scope": "notices",
                  "rows": [r.model_dump() for r in payload.rows],
                  "updated_at": now_iso(), "updated_by": admin["id"]}},
        upsert=True,
    )
    await audit_log("permissions.update", admin, "permission_matrix", "notices",
                    {"rows": len(payload.rows)})
    return {"ok": True}


@router.post("/reset")
async def reset_matrix(admin=Depends(require_role("admin"))):
    await db.permission_matrix.delete_one({"scope": "notices"})
    await audit_log("permissions.reset", admin, "permission_matrix", "notices", {})
    return {"ok": True, "rows": DEFAULT_MATRIX}


async def check_notice_permission(admin: dict, action: PermAction,
                                   document_type: str = "*") -> bool:
    """Returns True if the admin's active role permits `action` on this doc type.
    Falls back to the default matrix if no custom one has been saved."""
    if admin.get("role") == "admin":
        return True  # master admin is always allowed
    rows = await _get_matrix()
    role = admin.get("role")
    for r in rows:
        if r.get("role") != role:
            continue
        if r.get("document_type") not in (document_type, "*"):
            continue
        return bool(r.get(action, False))
    return False


async def require_notice_permission(admin: dict, action: PermAction,
                                    document_type: str = "*") -> None:
    if not await check_notice_permission(admin, action, document_type):
        raise HTTPException(status_code=403,
                            detail=f"Role '{admin.get('role')}' lacks '{action}' on '{document_type}' — see Permissions Matrix.")
