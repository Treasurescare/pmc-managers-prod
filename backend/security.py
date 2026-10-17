import bcrypt
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, Request, Depends
from bson import ObjectId

import config
from db import db


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_admin_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role, "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def new_magic_token() -> str:
    """URL-safe token used to resume registration drafts via email link."""
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    """Double-submit CSRF token — sent as both cookie (JS-readable) AND header."""
    return secrets.token_urlsafe(24)


async def current_admin(request: Request) -> dict:
    """Auth dependency for admin/reviewer routes."""
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.admin_users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Return the active role from the JWT (multi-role support), and
        # ALL roles the user actually holds — useful for role-switching UIs.
        active_role = payload.get("role") or user.get("role") or "admin"
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name"),
            "role": active_role,
            "roles": user.get("roles") or [user.get("role") or "admin"],
            "hierarchy_level": user.get("hierarchy_level", 1),
            "tenant_id": user.get("tenant_id", config.DEFAULT_TENANT_ID),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def is_preview_request(request) -> bool:
    """True only for the Emergent preview sandbox, which embeds the app in a
    CROSS-SITE iframe — that context genuinely needs SameSite=None + Partitioned
    (CHIPS) cookies. Production (the custom domain) and localhost are FIRST-PARTY,
    same-origin setups where SameSite=None is both unnecessary and actively
    rejected by Safari/ITP, causing the "login 200 then instantly logged out"
    bounce. Those must use a plain SameSite=Lax cookie."""
    if request is None:
        return False
    src = request.headers.get("origin") or request.headers.get("referer") or ""
    return "preview.emergentagent.com" in src


def _samesite_parts(cross_site: bool) -> list:
    # Cross-site (preview iframe) → None+Partitioned. First-party (prod/local) → Lax.
    return ["SameSite=None", "Partitioned"] if cross_site else ["SameSite=Lax"]


def set_csrf_cookie(response, csrf: str, max_age: int, cross_site: bool = True) -> None:
    """JS-readable double-submit CSRF cookie. Attributes depend on context:
    cross-site preview iframe → SameSite=None; Secure; Partitioned; first-party
    production/localhost → SameSite=Lax; Secure. Starlette 0.37's set_cookie
    lacks a `partitioned` kwarg, so we append the raw header."""
    parts = [f"csrf_token={csrf}", f"Max-Age={max_age}", "Path=/", "Secure"]
    parts += _samesite_parts(cross_site)
    if config.COOKIE_DOMAIN:
        parts.append(f"Domain={config.COOKIE_DOMAIN}")
    response.headers.append("set-cookie", "; ".join(parts))


def set_access_cookie(response, name: str, value: str, max_age: int, cross_site: bool = True) -> None:
    """HttpOnly session cookie. First-party production (same-origin behind
    CloudFront) uses SameSite=Lax; Secure — the only combination Safari reliably
    keeps first-party. The cross-site preview iframe keeps SameSite=None; Secure;
    Partitioned. Starlette can't emit `Partitioned`, so we build the header
    manually."""
    parts = [f"{name}={value}", f"Max-Age={max_age}", "Path=/", "HttpOnly", "Secure"]
    parts += _samesite_parts(cross_site)
    if config.COOKIE_DOMAIN:
        parts.append(f"Domain={config.COOKIE_DOMAIN}")
    response.headers.append("set-cookie", "; ".join(parts))


def clear_session_cookie(response, name: str, cross_site: bool = True) -> None:
    """Expire a cookie. The clear header's SameSite/Partitioned attributes must
    match the ones used when the cookie was set, or the browser keeps it."""
    parts = [f"{name}=", "Max-Age=0", "Path=/", "Secure"]
    parts += _samesite_parts(cross_site)
    if config.COOKIE_DOMAIN:
        parts.append(f"Domain={config.COOKIE_DOMAIN}")
    response.headers.append("set-cookie", "; ".join(parts))


async def require_csrf(request: Request) -> None:
    """Double-submit CSRF check. Enforced on state-changing admin endpoints.

    Rejects the request unless the `csrf_token` cookie matches the
    `X-CSRF-Token` header. Because attackers cannot read the cookie from a
    cross-site page (browser same-origin policy on document.cookie), they
    cannot forge the header.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie_val = request.cookies.get("csrf_token")
    header_val = request.headers.get("x-csrf-token") or request.headers.get("X-CSRF-Token")
    if not cookie_val or not header_val or not secrets.compare_digest(cookie_val, header_val):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")


def require_role(*roles: str):
    async def _dep(admin: dict = Depends(current_admin), _csrf: None = Depends(require_csrf)) -> dict:
        if admin.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return admin
    return _dep

