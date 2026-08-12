from typing import Dict, Any
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, Depends

from db import db
from models import AdminLoginIn, AdminPasswordChangeIn
from security import verify_password, hash_password, create_admin_token, current_admin, new_csrf_token, require_csrf
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin-auth"])


def _set_session_cookies(response: Response, access_token: str) -> str:
    """Set both httpOnly access_token cookie AND JS-readable csrf_token cookie.
    Returns the csrf_token so the caller can echo it in the JSON body too."""
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    response.set_cookie("access_token", access_token, httponly=True, secure=True,
                        samesite="lax", max_age=max_age, path="/")
    csrf = new_csrf_token()
    # csrf_token cookie is INTENTIONALLY not httpOnly — client JS reads it and
    # echoes as X-CSRF-Token header (double-submit-cookie pattern).
    response.set_cookie("csrf_token", csrf, httponly=False, secure=True,
                        samesite="lax", max_age=max_age, path="/")
    return csrf


@router.post("/login")
async def admin_login(payload: AdminLoginIn, response: Response) -> Dict[str, Any]:
    user = await db.admin_users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_admin_token(str(user["_id"]), user["email"], user.get("role", "admin"))
    csrf = _set_session_cookies(response, token)
    await audit_log("admin.login", {"id": str(user["_id"]), "email": user["email"]},
                    "admin_user", str(user["_id"]), {})
    return {"id": str(user["_id"]), "email": user["email"], "name": user.get("name"),
            "role": user.get("role", "admin"), "token": token, "csrf_token": csrf}


@router.post("/logout")
async def admin_logout(response: Response) -> Dict[str, bool]:
    # Logout does not require CSRF — it's idempotent and only clears cookies.
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"ok": True}


@router.get("/me")
async def admin_me(admin: Dict[str, Any] = Depends(current_admin)) -> Dict[str, Any]:
    # GET is CSRF-safe by convention.
    return admin


@router.post("/change-password", dependencies=[Depends(require_csrf)])
async def admin_change_password(
    payload: AdminPasswordChangeIn,
    admin: Dict[str, Any] = Depends(current_admin),
) -> Dict[str, bool]:
    """Self-service password rotation for the currently signed-in admin.

    Requires the current password + a new password ≥ 10 chars."""
    user = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    if not user or not verify_password(payload.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")
    await db.admin_users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    await audit_log("admin.password_change", admin, "admin_user", admin["id"], {})
    return {"ok": True}
