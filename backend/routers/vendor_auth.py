"""Vendor auth — separate collection from staff, cookie-based session."""
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Response, Depends, Request
from bson import ObjectId
import jwt

from db import db
from models.vendor_user import VendorLoginIn, VendorPasswordChangeIn
from security import verify_password, hash_password, new_csrf_token
from audit import audit_log
from models.base import now_iso
import config

router = APIRouter(prefix="/api/v1/vendor", tags=["vendor-auth"])


def _create_vendor_token(vendor_id: str, email: str) -> str:
    payload = {
        "sub": vendor_id, "email": email, "type": "vendor_access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _set_cookies(response: Response, token: str) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    ck = {"httponly": True, "secure": True, "samesite": "lax",
          "max_age": max_age, "path": "/"}
    if config.COOKIE_DOMAIN:
        ck["domain"] = config.COOKIE_DOMAIN
    response.set_cookie("vendor_token", token, **ck)
    csrf = new_csrf_token()
    ck["httponly"] = False
    response.set_cookie("csrf_token", csrf, **ck)
    return csrf


async def current_vendor(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("vendor_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "vendor_access":
            raise HTTPException(status_code=401, detail="Invalid token")
        v = await db.vendors.find_one({"_id": ObjectId(payload["sub"])})
        if not v:
            raise HTTPException(status_code=401, detail="Vendor not found")
        return {
            "id": str(v["_id"]),
            "email": v["email"],
            "vendor_ref": v.get("vendor_ref"),
            "company_name": v.get("company_name"),
            "must_change_password": v.get("must_change_password", False),
            "avatar_data_url": v.get("avatar_data_url"),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/auth/login")
async def vendor_login(payload: VendorLoginIn, response: Response, request: Request) -> Dict[str, Any]:
    v = await db.vendors.find_one({"email": payload.email.lower()})
    if not v or not verify_password(payload.password, v.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not v.get("is_active", True):
        raise HTTPException(status_code=403, detail="Vendor account disabled")
    token = _create_vendor_token(str(v["_id"]), v["email"])
    csrf = _set_cookies(response, token)
    await audit_log("vendor.login", None, "vendor", str(v["_id"]), {"email": v["email"]})
    # v47d — security sign-in alert email on every successful login
    try:
        from notify import login_alert
        await login_alert(v["email"], v.get("company_name"), "Vendor Portal",
                          ip=request.client.host if request.client else None,
                          user_agent=request.headers.get("user-agent"),
                          user_ref=v.get("vendor_ref"))
    except Exception:
        pass
    return {
        "id": str(v["_id"]),
        "email": v["email"],
        "vendor_ref": v.get("vendor_ref"),
        "company_name": v.get("company_name"),
        "must_change_password": v.get("must_change_password", False),
        "csrf_token": csrf,
        "avatar_data_url": v.get("avatar_data_url"),
    }


@router.post("/auth/logout")
async def vendor_logout(response: Response) -> Dict[str, bool]:
    # Bug #82 fix — nuke ALL three cookie realms so a vendor logging out
    # can immediately log in as staff/admin without dual-identity collisions.
    response.delete_cookie("vendor_token", path="/", domain=config.COOKIE_DOMAIN)
    response.delete_cookie("access_token", path="/", domain=config.COOKIE_DOMAIN)
    response.delete_cookie("csrf_token", path="/", domain=config.COOKIE_DOMAIN)
    return {"ok": True}


@router.get("/auth/me")
async def vendor_me(vendor=Depends(current_vendor), response: Response = None) -> Dict[str, Any]:
    # Bug #29 — force no-store so a fresh avatar upload is visible on the next
    # tab/page load (CloudFront was serving a stale /auth/me briefly).
    if response is not None:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return vendor


@router.post("/gdpr-forget")
async def vendor_self_forget(payload: dict, vendor=Depends(current_vendor)):
    """Vendor self-service GDPR forget — requires current password to confirm."""
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if not v or not verify_password(payload.get("password", ""), v.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Password does not match")
    anon = {
        "email": f"anonymised+{vendor['id']}@example.invalid",
        "company_name": "[REDACTED]", "profile": {},
        "is_active": False,
        "gdpr_forgotten_at": now_iso(),
        "gdpr_forgotten_by": "self",
    }
    await db.vendors.update_one({"_id": ObjectId(vendor["id"])}, {"$set": anon})
    if v.get("email"):
        await db.registrations.update_many(
            {"email": v["email"]},
            {"$set": {**anon, "gdpr_forgotten_by": "self"}},
        )
    await audit_log("gdpr.self_forget", None, "vendor", vendor["id"],
                    {"original_email": v.get("email")})
    return {"ok": True}


@router.post("/auth/change-password")
async def change_password(payload: VendorPasswordChangeIn, vendor=Depends(current_vendor)):
    v = await db.vendors.find_one({"_id": ObjectId(vendor["id"])})
    if not v or not verify_password(payload.current_password, v.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password incorrect")
    await db.vendors.update_one(
        {"_id": ObjectId(vendor["id"])},
        {"$set": {"password_hash": hash_password(payload.new_password),
                  "must_change_password": False,
                  "password_changed_at": datetime.now(timezone.utc).isoformat()}},
    )
    await audit_log("vendor.password_change", None, "vendor", vendor["id"], {})
    # v47c — security confirmation email on password change
    try:
        from notify import vendor_confirm
        import config as _cfg
        await vendor_confirm(
            v.get("email"),
            "Your vendor password was changed",
            f"<p>Dear {v.get('company_name') or 'Vendor'},</p>"
            f"<p>The password for your vendor account (<code>{v.get('email')}</code>) "
            f"was changed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.</p>"
            f"<p>If you did not make this change, contact PMC support immediately.</p>",
            "Open vendor portal", f"{_cfg.FRONTEND_URL}/vendor")
    except Exception:
        pass
    return {"ok": True}
