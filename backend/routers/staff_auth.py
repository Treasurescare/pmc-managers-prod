"""Staff auth — unified login for admins + all specialised roles.

Staff records hold a LIST of roles; on login the user picks an active role.
Same cookie/CSRF mechanics as admin_auth. Backwards-compatible with the
legacy `admin_users` collection: existing admins are auto-migrated on login.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response, Depends
from bson import ObjectId

from db import db
from models.staff_user import StaffLoginIn, StaffCreateIn, StaffUpdateIn, ALL_STAFF_ROLES
from security import (
    verify_password, hash_password, create_admin_token, current_admin,
    new_csrf_token, require_role, require_csrf,
)
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/staff", tags=["staff-auth"])


def _set_session_cookies(response: Response, access_token: str) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    response.set_cookie("access_token", access_token, httponly=True, secure=True,
                        samesite="lax", max_age=max_age, path="/")
    csrf = new_csrf_token()
    response.set_cookie("csrf_token", csrf, httponly=False, secure=True,
                        samesite="lax", max_age=max_age, path="/")
    return csrf


def _out(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d.pop("password_hash", None)
    return d


@router.post("/auth/login")
async def staff_login(payload: StaffLoginIn, response: Response) -> Dict[str, Any]:
    user = await db.admin_users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Backfill multi-role list on legacy single-role docs
    roles: List[str] = user.get("roles") or [user.get("role") or "admin"]
    if payload.active_role not in roles:
        raise HTTPException(status_code=403, detail=f"You do not hold the {payload.active_role} role")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    # Wave 7 — MFA gate. If the user has MFA enabled we require an OTP.
    if user.get("mfa_enabled"):
        if not payload.otp_code:
            return {"mfa_required": True, "email": user["email"]}
        import pyotp
        if not pyotp.TOTP(user.get("mfa_secret") or "").verify(payload.otp_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid OTP")

    token = create_admin_token(str(user["_id"]), user["email"], payload.active_role)
    csrf = _set_session_cookies(response, token)
    await audit_log("staff.login", {"id": str(user["_id"]), "email": user["email"]},
                    "admin_user", str(user["_id"]), {"active_role": payload.active_role})
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name"),
        "roles": roles,
        "active_role": payload.active_role,
        "hierarchy_level": user.get("hierarchy_level", 1),
        "csrf_token": csrf,
    }


@router.post("/auth/logout")
async def staff_logout(response: Response) -> Dict[str, bool]:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def staff_me(admin: Dict[str, Any] = Depends(current_admin)) -> Dict[str, Any]:
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    d = _out(doc)
    d["active_role"] = admin.get("role")
    return d


@router.get("/roles")
async def list_role_choices() -> Dict[str, Any]:
    return {"roles": ALL_STAFF_ROLES}


# ---------- Staff master (admin-only CRUD) ----------

@router.get("")
async def list_staff(admin=Depends(require_role("admin"))) -> List[dict]:
    return [_out(d) async for d in db.admin_users.find({"tenant_id": admin["tenant_id"]}).sort("email", 1)]


@router.post("")
async def create_staff(payload: StaffCreateIn, admin=Depends(require_role("admin"))) -> dict:
    if await db.admin_users.find_one({"email": payload.email.lower()}):
        raise HTTPException(status_code=409, detail="Email already exists")
    from datetime import datetime, timezone
    doc = {
        "email": payload.email.lower(),
        "name": payload.name,
        "password_hash": hash_password(payload.password),
        "roles": payload.roles,
        "role": payload.roles[0],  # legacy compat
        "hierarchy_level": payload.hierarchy_level,
        "company_id": payload.company_id,
        "reports_to": payload.reports_to,
        "tenant_id": admin["tenant_id"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin["id"],
    }
    res = await db.admin_users.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("staff.create", admin, "admin_user", str(res.inserted_id),
                    {"email": doc["email"], "roles": doc["roles"]})
    return _out(doc)


@router.patch("/{staff_id}")
async def update_staff(staff_id: str, payload: StaffUpdateIn,
                       admin=Depends(require_role("admin"))) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    if "roles" in updates and updates["roles"]:
        updates["role"] = updates["roles"][0]
    r = await db.admin_users.update_one({"_id": ObjectId(staff_id)}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    fresh = await db.admin_users.find_one({"_id": ObjectId(staff_id)})
    await audit_log("staff.update", admin, "admin_user", staff_id, updates)
    return _out(fresh)
