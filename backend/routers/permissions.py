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
    # Bucket B — Tab-level RBAC extension. If empty/None, the role's tab
    # visibility falls back to the DEFAULT_TABS derived from role name. If a
    # non-empty list is provided, ONLY those tab keys are visible to the role.
    tabs: Optional[List[str]] = None


# Default tab visibility per role — used when no explicit `tabs` set on the row.
DEFAULT_TABS: dict = {
    "admin":            ["*"],  # all tabs
    "reviewer":         ["notices", "registrations", "bids", "escrow", "meetings", "reports"],
    "auditor":          ["notices", "audit", "reports", "vendor_intel"],
    "committee_member": ["bids", "evaluations"],
    "escrow_agent":     ["escrow", "meetings"],
    "certifier":        ["bids", "evaluations"],
    "legal_counsel":    ["notices", "bids", "evaluations", "docusign"],
    "accounting":       ["escrow", "awards", "products", "reports"],
    "support":          ["help", "vendors", "notices"],
}


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


@router.get("/tabs/{role}")
async def get_tabs_for_role(role: str,
                             admin=Depends(require_role("admin", "auditor", "reviewer"))):
    """Bucket B — tab-level RBAC.
    Returns the list of tab keys visible to a given role. If no explicit
    override is stored, falls back to DEFAULT_TABS."""
    rows = await _get_matrix()
    for r in rows:
        if r.get("role") == role and r.get("tabs"):
            return {"role": role, "tabs": r["tabs"], "source": "matrix_override"}
    return {"role": role, "tabs": DEFAULT_TABS.get(role, ["notices"]),
            "source": "default_tabs"}


@router.post("/reset")
async def reset_matrix(admin=Depends(require_role("admin"))):
    await db.permission_matrix.delete_one({"scope": "notices"})
    await audit_log("permissions.reset", admin, "permission_matrix", "notices", {})
    return {"ok": True, "rows": DEFAULT_MATRIX}


@router.get("/effective/{role}")
async def effective_permissions(role: str,
                                  admin=Depends(require_role("admin", "auditor", "reviewer"))):
    """Wave G2 — consolidated access-control for a role.

    Merges the two previously-independent access-control systems into a single
    payload:
      * `actions` — from the Permissions Matrix (view/create/modify/delete/publish)
      * `tabs`    — matrix override OR DEFAULT_TABS fallback
      * `level`   — hierarchy Level (0=master, 1=reviewer/deputy, 2=operator, 3=viewer)

    Frontend uses this single call to gate everything: menu visibility,
    button disabled-state and API permission hints.
    """
    rows = await _get_matrix()
    actions = {"view": False, "create": False, "modify": False, "delete": False, "publish": False}
    matched_row = None
    for r in rows:
        if r.get("role") != role:
            continue
        matched_row = r
        for a in actions:
            if r.get(a):
                actions[a] = True
        break
    # Tab visibility.
    tabs = (matched_row or {}).get("tabs") or DEFAULT_TABS.get(role, ["notices"])
    # Hierarchy level mapping — deliberately kept explicit so the source of
    # truth for G3 is legible to every reviewer.
    LEVEL_BY_ROLE = {
        "admin": 0,             # master administrator
        "reviewer": 1,          # deputy / sub-admin
        "legal_counsel": 1,
        "certifier": 2,         # operational specialist
        "escrow_agent": 2,
        "accounting": 2,
        "committee_member": 2,
        "support": 3,           # read-mostly
        "auditor": 3,           # read-only
    }
    level = LEVEL_BY_ROLE.get(role, 3)
    return {
        "role": role,
        "level": level,
        "level_label": {0: "master", 1: "deputy", 2: "operator", 3: "viewer"}[level],
        "tabs": tabs,
        "actions": actions,
        "source": "matrix_override" if matched_row and matched_row.get("tabs") else "default_tabs",
        "generated_at": now_iso(),
    }


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
