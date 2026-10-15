"""v52g — Escrow institution profile change requests.

Institution owners can propose field-level edits at any stage (draft or
after approval). Changes stay pending until a PMC admin approves them.

Scope decided with user (15 Oct 2026):
- All five sections editable (core, signatories, banking, documents).
- Changes allowed at every stage, including drafts.
- Unlimited field-level requests per institution.
- Admin review happens inside the existing Admin → Escrow Institutions
  detail panel.

A change-request row records WHICH logical path on the institution the
owner wants to update AND the proposed value. On approval we `$set` that
dot-path onto `escrow_institutions`. Sections "signatories", "banking"
and "documents" replace the whole collection to keep diffing simple.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from audit import audit_log
from db import db
from models.base import now_iso
from security import require_csrf, require_role

router = APIRouter(prefix="/api/v1/escrow-accounts/me/change-requests",
                   tags=["escrow-profile-changes"])

admin_router = APIRouter(prefix="/api/v1/escrow-institutions",
                         tags=["escrow-profile-changes-admin"])


SECTION_CHOICES = {"core", "signatories", "banking", "documents"}

# Only these paths may be written when a change-request is approved. Keeps
# a bad actor from targeting status / account_id / magic_token / etc.
ALLOWED_CORE_FIELDS = {
    "legal_name", "trading_name", "country", "registered_address",
    "address_line1", "address_line2", "city", "state_code", "state_name",
    "postal_code", "reg_number", "tax_id", "gst_or_vat", "regulator",
    "licence_number", "licence_expiry", "website",
    "primary_contact_email", "primary_contact_phone",
    "mobile_phone", "office_phone", "phone_country_code",
    "primary_contact_name", "institution_type",
}


class ChangeRequestIn(BaseModel):
    section: str
    field_path: str = Field(min_length=1, max_length=120)
    current_value: Any = None
    proposed_value: Any = None
    reason: Optional[str] = Field(default=None, max_length=600)

    @field_validator("section")
    @classmethod
    def _section_ok(cls, v: str) -> str:
        if v not in SECTION_CHOICES:
            raise ValueError(f"section must be one of {sorted(SECTION_CHOICES)}")
        return v

    @field_validator("field_path")
    @classmethod
    def _path_ok(cls, v: str) -> str:
        v = (v or "").strip()
        if any(ch in v for ch in ("$", "{", "}", "\x00")):
            raise ValueError("invalid field_path")
        return v


class DecisionIn(BaseModel):
    reviewer_notes: Optional[str] = Field(default=None, max_length=600)


def _row_out(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(d["_id"]),
        "institution_id": d.get("institution_id"),
        "account_id": d.get("account_id"),
        "section": d.get("section"),
        "field_path": d.get("field_path"),
        "current_value": d.get("current_value"),
        "proposed_value": d.get("proposed_value"),
        "reason": d.get("reason"),
        "status": d.get("status", "pending"),
        "reviewer_notes": d.get("reviewer_notes"),
        "reviewed_by": d.get("reviewed_by"),
        "reviewed_at": d.get("reviewed_at"),
        "created_at": d.get("created_at"),
    }


def _validate_target(section: str, field_path: str) -> str:
    """Return the mongo `$set` key or raise 422."""
    if section == "core":
        if field_path not in ALLOWED_CORE_FIELDS:
            raise HTTPException(status_code=422,
                detail=f"'{field_path}' is not editable via change requests.")
        return field_path
    if section == "signatories":
        if field_path != "signatories":
            raise HTTPException(status_code=422,
                detail="Signatories edits must target field_path='signatories'.")
        return "signatories"
    if section == "banking":
        if field_path != "banking":
            raise HTTPException(status_code=422,
                detail="Banking edits must target field_path='banking'.")
        return "banking"
    if section == "documents":
        # Allow whole-dict replacement OR single-slot ("documents.<slot>")
        if field_path == "documents":
            return "documents"
        if field_path.startswith("documents.") and "." not in field_path[10:]:
            return field_path
        raise HTTPException(status_code=422,
            detail="Documents edits must target 'documents' or 'documents.<slot>'.")
    raise HTTPException(status_code=422, detail="Unknown section")


async def _restore_live_if_clear(iid: str) -> None:
    """v52k — an approved institution is paused (`changes_requested`) while
    any change request is pending. Once the queue is empty (approved,
    rejected or cancelled), flip it back to its previous live status."""
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not inst or inst.get("status") != "changes_requested":
        return
    pending = await db.escrow_change_requests.count_documents(
        {"institution_id": iid, "status": "pending"})
    if pending:
        return
    await db.escrow_institutions.update_one(
        {"_id": ObjectId(iid)},
        {"$set": {"status": inst.get("previous_status") or "approved",
                   "updated_at": now_iso()},
         "$unset": {"previous_status": "", "changes_requested_at": ""}})


# ---------- Owner (escrow_account cookie) --------------------------------

@router.post("", dependencies=[Depends(require_csrf)])
async def create_change_request(payload: ChangeRequestIn, request: Request):
    from routers.escrow_accounts import current_account
    acc = await current_account(request)
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    iid = full.get("institution_id")
    if not iid:
        raise HTTPException(status_code=404,
            detail="You don't have an institution record yet.")
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    _validate_target(payload.section, payload.field_path)
    row = {
        "institution_id": iid,
        "account_id": acc["id"],
        "section": payload.section,
        "field_path": payload.field_path.strip(),
        "current_value": payload.current_value,
        "proposed_value": payload.proposed_value,
        "reason": (payload.reason or None),
        "status": "pending",
        "created_at": now_iso(),
    }
    r = await db.escrow_change_requests.insert_one(row)
    row["_id"] = r.inserted_id
    await audit_log("escrow_profile.request_create", None, "escrow_change_request",
                    str(r.inserted_id),
                    {"iid": iid, "field_path": payload.field_path})
    # v52k — a live (approved) institution with pending changes must NOT
    # stay live until PMC clears the queue. Pause it immediately.
    if inst.get("status") == "approved":
        await db.escrow_institutions.update_one(
            {"_id": ObjectId(iid)},
            {"$set": {"status": "changes_requested",
                       "previous_status": "approved",
                       "changes_requested_at": now_iso()}})
        await audit_log("escrow_institution.changes_requested", None,
                        "escrow_institution", iid, {"by_account": acc["id"]})
    return _row_out(row)


@router.get("")
async def list_my_change_requests(request: Request):
    from routers.escrow_accounts import current_account
    acc = await current_account(request)
    out: List[Dict[str, Any]] = []
    async for d in db.escrow_change_requests.find(
            {"account_id": acc["id"]}).sort("created_at", -1):
        out.append(_row_out(d))
    return {"items": out, "total": len(out)}


@router.delete("/{cid}", dependencies=[Depends(require_csrf)])
async def cancel_my_change_request(cid: str, request: Request):
    from routers.escrow_accounts import current_account
    acc = await current_account(request)
    row = await db.escrow_change_requests.find_one({"_id": ObjectId(cid),
                                                      "account_id": acc["id"]})
    if not row:
        raise HTTPException(status_code=404, detail="Change request not found")
    if row.get("status") != "pending":
        raise HTTPException(status_code=400,
            detail=f"Cannot cancel — already {row.get('status')}")
    await db.escrow_change_requests.update_one(
        {"_id": row["_id"]},
        {"$set": {"status": "cancelled", "reviewed_at": now_iso()}})
    await audit_log("escrow_profile.request_cancel", None,
                    "escrow_change_request", cid, {})
    await _restore_live_if_clear(row["institution_id"])
    return {"ok": True}


# ---------- Admin ---------------------------------------------------------

@admin_router.get("/{iid}/change-requests")
async def admin_list_change_requests(iid: str,
                                       admin=Depends(require_role("admin", "reviewer"))):
    out: List[Dict[str, Any]] = []
    async for d in db.escrow_change_requests.find(
            {"institution_id": iid}).sort("created_at", -1):
        out.append(_row_out(d))
    return {"items": out, "total": len(out)}


@admin_router.post("/change-requests/{cid}/approve")
async def admin_approve(cid: str, payload: DecisionIn,
                         admin=Depends(require_role("admin"))):
    row = await db.escrow_change_requests.find_one({"_id": ObjectId(cid)})
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if row.get("status") != "pending":
        raise HTTPException(status_code=400,
            detail=f"Already {row.get('status')}")
    set_key = _validate_target(row["section"], row["field_path"])
    iid = row["institution_id"]
    inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    # Apply.
    await db.escrow_institutions.update_one(
        {"_id": ObjectId(iid)},
        {"$set": {set_key: row.get("proposed_value"),
                   "updated_at": now_iso()}})
    await db.escrow_change_requests.update_one(
        {"_id": row["_id"]},
        {"$set": {"status": "approved",
                   "reviewer_notes": payload.reviewer_notes,
                   "reviewed_by": admin.get("email"),
                   "reviewed_at": now_iso()}})
    await audit_log("escrow_profile.request_approve", admin,
                    "escrow_change_request", cid,
                    {"iid": iid, "field_path": row["field_path"]})
    await _restore_live_if_clear(iid)
    # Notify the owner so the bell + email light up.
    if row.get("account_id"):
        try:
            from routers.escrow_accounts import notify_account
            await notify_account(row["account_id"], "profile_change_approved",
                "Profile change approved",
                f"PMC approved your change to '{row['field_path']}'. The updated value is now live on your institution record.",
                "/escrow/me")
        except Exception:
            pass
    return {"ok": True}


@admin_router.post("/change-requests/{cid}/reject")
async def admin_reject(cid: str, payload: DecisionIn,
                        admin=Depends(require_role("admin"))):
    row = await db.escrow_change_requests.find_one({"_id": ObjectId(cid)})
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if row.get("status") != "pending":
        raise HTTPException(status_code=400,
            detail=f"Already {row.get('status')}")
    if not (payload.reviewer_notes or "").strip():
        raise HTTPException(status_code=422,
            detail="Reviewer notes are required when rejecting.")
    await db.escrow_change_requests.update_one(
        {"_id": row["_id"]},
        {"$set": {"status": "rejected",
                   "reviewer_notes": payload.reviewer_notes,
                   "reviewed_by": admin.get("email"),
                   "reviewed_at": now_iso()}})
    await audit_log("escrow_profile.request_reject", admin,
                    "escrow_change_request", cid,
                    {"iid": row["institution_id"],
                     "field_path": row["field_path"]})
    await _restore_live_if_clear(row["institution_id"])
    if row.get("account_id"):
        try:
            from routers.escrow_accounts import notify_account
            await notify_account(row["account_id"], "profile_change_rejected",
                "Profile change not approved",
                f"PMC did not approve your change to '{row['field_path']}'. Reviewer notes: {payload.reviewer_notes}",
                "/escrow/me")
        except Exception:
            pass
    return {"ok": True}
