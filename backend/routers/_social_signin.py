"""Shared 'sign in an existing account by verified email' used by Google and LinkedIn sign-in."""
from typing import Optional

from fastapi import HTTPException, Request, Response

import config
from audit import audit_log
from db import db
from security import create_admin_token

STAFF_ROLES = ["reviewer", "escrow_agent", "certifier", "legal_counsel", "accounting", "committee_member",
               "auditor", "support", "management", "partner", "agent"]


async def sign_in_existing(email: str, portal: str, response: Response, request: Request, method: str) -> dict:
    no_account = HTTPException(status_code=404, detail=f"No PMC account uses {email}. Register first, or sign in with your email and password.")
    if portal == "supplier":
        from routers.vendor_auth import _create_vendor_token, _set_cookies
        v = await db.vendors.find_one({"email": email})
        if not v:
            raise no_account
        if not v.get("is_active", True):
            raise HTTPException(status_code=403, detail="Vendor account disabled")
        csrf = _set_cookies(response, _create_vendor_token(str(v["_id"]), v["email"], int(v.get("token_generation") or 0)))
        response.delete_cookie("access_token", path="/", domain=config.COOKIE_DOMAIN)
        await audit_log("vendor.login", None, "vendor", str(v["_id"]), {"email": email, "method": method})
        return {"portal": "supplier", "next": "/vendor/change-password" if v.get("must_change_password") else "/vendor",
                "csrf_token": csrf}
    from routers.staff_auth import _set_session_cookies
    u = await db.admin_users.find_one({"email": email})
    if not u:
        raise no_account
    if not u.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    if u.get("mfa_enabled"):
        raise HTTPException(status_code=403, detail="This account uses two-factor sign-in. Please sign in with your password and code.")
    roles = u.get("roles") or [u.get("role") or "admin"]
    if portal == "admin":
        if "admin" not in roles:
            raise HTTPException(status_code=403, detail="This account is not an administrator.")
        active: Optional[str] = "admin"
    else:
        active = next((r for r in STAFF_ROLES if r in roles), None)
        if not active:
            raise HTTPException(status_code=403, detail="This account has no staff role. Use the Administrator option.")
        if config.REQUIRE_HIGH_RISK_MFA and active in {"escrow_agent", "legal_counsel", "accounting"}:
            raise HTTPException(status_code=403, detail="This role requires two-factor sign-in. Please use your password and code.")
    csrf = _set_session_cookies(response, create_admin_token(str(u["_id"]), u["email"], active), request)
    response.delete_cookie("vendor_token", path="/", domain=config.COOKIE_DOMAIN)
    await audit_log("staff.login", {"id": str(u["_id"]), "email": email}, "admin_user", str(u["_id"]),
                    {"active_role": active, "method": method})
    return {"portal": portal, "active_role": active, "next": "/admin" if active == "admin" else "/staff", "csrf_token": csrf}
