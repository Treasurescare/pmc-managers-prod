from typing import Dict, Any
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, Depends, Request

from db import db
from models import AdminLoginIn, AdminPasswordChangeIn
from security import verify_password, hash_password, create_admin_token, current_admin, new_csrf_token, csrf_for_session, require_csrf, set_csrf_cookie, set_access_cookie, clear_session_cookie, is_preview_request
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin-auth"])


def _set_session_cookies(response: Response, access_token: str, request: Request = None) -> str:
    """Set both httpOnly access_token cookie AND JS-readable csrf_token cookie.
    Returns the csrf_token so the caller can echo it in the JSON body too."""
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    cross_site = is_preview_request(request)
    set_access_cookie(response, "access_token", access_token, max_age, cross_site)
    csrf = _csrf_from_token(access_token)
    # csrf_token cookie is INTENTIONALLY not httpOnly — client JS reads it and
    # echoes as X-CSRF-Token header (double-submit-cookie pattern).
    set_csrf_cookie(response, csrf, max_age, cross_site)
    return csrf


def _csrf_from_token(access_token: str) -> str:
    """v56b2 — derive the session-bound CSRF token so validation never depends
    on the cookie surviving the CDN. Falls back to a random token if decode
    fails (keeps classic cookie==header behaviour)."""
    try:
        import jwt as _jwt
        sub = _jwt.decode(access_token, config.JWT_SECRET,
                          algorithms=[config.JWT_ALGORITHM]).get("sub")
        return csrf_for_session(sub) if sub else new_csrf_token()
    except Exception:
        return new_csrf_token()


@router.post("/login")
async def admin_login(payload: AdminLoginIn, response: Response, request: Request) -> Dict[str, Any]:
    user = await db.admin_users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_admin_token(str(user["_id"]), user["email"], user.get("role", "admin"))
    csrf = _set_session_cookies(response, token, request)
    # v52bx — bug #34: a stale vendor_token on the same browser was leaking
    # vendor permissions into the admin session (and vice versa). On every
    # admin login we now kill the OTHER role cookies so switching accounts
    # on the same browser can never mix contexts.
    response.delete_cookie("vendor_token", path="/", domain=config.COOKIE_DOMAIN)
    await audit_log("admin.login", {"id": str(user["_id"]), "email": user["email"]},
                    "admin_user", str(user["_id"]), {})
    # v47d — security sign-in alert email on every successful login
    try:
        from notify import login_alert
        await login_alert(user["email"], user.get("name"), "Admin Console",
                          ip=request.client.host if request.client else None,
                          user_agent=request.headers.get("user-agent"),
                          user_id=str(user["_id"]))
    except Exception:
        pass
    return {"id": str(user["_id"]), "email": user["email"], "name": user.get("name"),
            "role": user.get("role", "admin"), "token": token, "csrf_token": csrf,
            "avatar_data_url": user.get("avatar_data_url")}


@router.post("/logout")
async def admin_logout(response: Response, request: Request) -> Dict[str, bool]:
    # Logout does not require CSRF — it's idempotent and only clears cookies.
    # Bug #82 fix — nuke ALL three cookie realms so switching roles never
    # leaves a stale vendor_token / access_token behind (which caused the
    # "Your session is still active" ErrorBoundary crash on the next login).
    cross_site = is_preview_request(request)
    response.delete_cookie("access_token", path="/", domain=config.COOKIE_DOMAIN)
    clear_session_cookie(response, "access_token", cross_site)
    clear_session_cookie(response, "vendor_token", cross_site)
    clear_session_cookie(response, "csrf_token", cross_site)
    return {"ok": True}


@router.get("/me")
async def admin_me(admin: Dict[str, Any] = Depends(current_admin), response: Response = None) -> Dict[str, Any]:
    # GET is CSRF-safe by convention. Enrich with avatar for the profile widget.
    user = await db.admin_users.find_one({"_id": ObjectId(admin["id"])},
                                          {"avatar_data_url": 1})
    # Bug #29 — force no-store so a fresh avatar upload is visible on the next
    # tab/page load. CloudFront was serving a stale /me for up to 60s, which
    # made the newly-picked profile photo disappear until the cache expired.
    if response is not None:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return {**admin, "avatar_data_url": (user or {}).get("avatar_data_url")}


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
