"""Sign in with Google (Emergent-managed) for existing vendor and staff accounts only."""
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

import config
from audit import audit_log
from db import db
from security import create_admin_token

router = APIRouter(prefix="/api/v1/auth/google", tags=["google-auth"])
SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
STAFF_ROLES = ["reviewer", "escrow_agent", "certifier", "legal_counsel", "accounting", "committee_member",
               "auditor", "support", "management", "partner", "agent"]


class ExchangeIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=512)
    portal: Literal["supplier", "staff", "admin"]


async def _google_email(session_id: str) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(SESSION_DATA_URL, headers={"X-Session-ID": session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified. Please try again.")
    email = (r.json().get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google did not share an email address.")
    return email


@router.post("/exchange")
async def exchange(body: ExchangeIn, response: Response, request: Request):
    email = await _google_email(body.session_id)
    no_account = HTTPException(status_code=404, detail=f"No PMC account uses {email}. Register first, or sign in with your email and password.")
    if body.portal == "supplier":
        from routers.vendor_auth import _create_vendor_token, _set_cookies
        v = await db.vendors.find_one({"email": email})
        if not v:
            raise no_account
        if not v.get("is_active", True):
            raise HTTPException(status_code=403, detail="Vendor account disabled")
        csrf = _set_cookies(response, _create_vendor_token(str(v["_id"]), v["email"], int(v.get("token_generation") or 0)))
        response.delete_cookie("access_token", path="/", domain=config.COOKIE_DOMAIN)
        await audit_log("vendor.login", None, "vendor", str(v["_id"]), {"email": email, "method": "google"})
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
    if body.portal == "admin":
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
                    {"active_role": active, "method": "google"})
    return {"portal": body.portal, "active_role": active, "next": "/admin" if active == "admin" else "/staff",
            "csrf_token": csrf}
