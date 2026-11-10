import bcrypt
import jwt
import secrets
import hmac
import hashlib
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


def csrf_for_session(sub: str) -> str:
    """v56b2 — session-bound CSRF token: HMAC(JWT_SECRET, 'csrf:'+sub). Lets the
    server validate the X-CSRF-Token header WITHOUT depending on the csrf cookie
    surviving the CDN, while remaining unforgeable from a cross-site context."""
    return hmac.new(config.JWT_SECRET.encode(), f"csrf:{sub}".encode(),
                    hashlib.sha256).hexdigest()


def _session_sub(request) -> Optional[str]:
    """Resolve the authenticated subject (user id) from the access_token
    cookie or Bearer header, for the session-bound CSRF fallback."""
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        return _agent_sub(request)
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except Exception:
        return None


def _vendor_sub(request) -> Optional[str]:
    vt = request.cookies.get("vendor_token")
    if not vt:
        return None
    try:
        p = jwt.decode(vt, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return f"vendor:{p['sub']}" if p.get("type") == "vendor_access" else None
    except Exception:
        return None


def _agent_sub(request) -> Optional[str]:
    at = request.cookies.get("agent_token")
    if not at:
        return None
    try:
        p = jwt.decode(at, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return f"agent:{p['sub']}" if p.get("type") == "agent_access" else None
    except Exception:
        return None


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
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account disabled")
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
    """Double-submit CSRF check with a session-bound HMAC fallback.

    v56b2 — production behind CloudFront can fail to deliver the JS-readable
    `csrf_token` cookie to the origin, which broke the classic cookie==header
    check even though the session was valid. We now accept EITHER:
      1. classic double-submit: `csrf_token` cookie == `X-CSRF-Token` header, OR
      2. session-bound token: header == HMAC(JWT_SECRET, "csrf:"+session_sub),
         which needs no cookie at all yet stays unforgeable cross-site (an
         attacker can neither read the session nor compute the HMAC, and cannot
         set a custom header on a cross-site request).
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    header_val = request.headers.get("x-csrf-token") or request.headers.get("X-CSRF-Token")
    if not header_val:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    cookie_val = request.cookies.get("csrf_token")
    if cookie_val and secrets.compare_digest(cookie_val, header_val):
        return
    sub = _session_sub(request)
    if sub and secrets.compare_digest(header_val, csrf_for_session(sub)):
        return
    asub = _agent_sub(request)
    if asub and secrets.compare_digest(header_val, csrf_for_session(asub)):
        return
    vsub = _vendor_sub(request)
    if vsub and secrets.compare_digest(header_val, csrf_for_session(vsub)):
        return
    raise HTTPException(status_code=403, detail="CSRF token missing or invalid")


def require_role(*roles: str):
    async def _dep(admin: dict = Depends(current_admin), _csrf: None = Depends(require_csrf)) -> dict:
        if admin.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return admin
    return _dep

