"""PMC v50 — Real 'Forgot password?' reset flow (vendor + admin/staff).

Endpoints (all under /api/v1/auth/password-reset):
- POST /request  {email, portal}      — always returns ok (no user enumeration).
                                        Emails a signed reset link if the
                                        account exists in the picked realm.
                                        Rate-limited per-email + per-IP.
- POST /verify   {token}              — returns {ok, email, portal} if the
                                        token signature is valid, otherwise 400.
- POST /confirm  {token, new_password}— writes password_hash on the correct
                                        collection and clears must_change_password.

Tokens are short-lived (30 min) JWTs signed with JWT_SECRET, scoped by
`type=pwd_reset`. We store the token's issued-at (jti) on the user document
so a successful reset invalidates the link. Prevents replay after use.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Optional
from uuid import uuid4

import jwt
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from emails_option_e import send_e_email
from security import hash_password

router = APIRouter(prefix="/api/v1/auth/password-reset", tags=["auth-password-reset"])

log = logging.getLogger(__name__)

RESET_TTL_MIN = 30

# ── Rate limiting ────────────────────────────────────────────────────────
# Single-pod in-memory throttle. Fine for the current EB single-instance
# deployment; if we scale to multiple pods, swap for Redis-backed limits.
# Applied BEFORE we look up the account so a 429 never leaks whether an
# email exists (attackers see 429 whether or not the account is real).
_EMAIL_COOLDOWN_SEC = 60         # one reset per email per minute
_IP_WINDOW_SEC = 300             # 5-minute sliding window per IP
_IP_MAX_IN_WINDOW = 10           # at most 10 reset requests per IP per 5 min

_email_last: Dict[str, float] = {}
_ip_hits: Dict[str, Deque[float]] = {}


def _rate_check(email: str, ip: str) -> Optional[str]:
    now = time.time()
    # Per-email cooldown
    last = _email_last.get(email)
    if last is not None and (now - last) < _EMAIL_COOLDOWN_SEC:
        wait = int(_EMAIL_COOLDOWN_SEC - (now - last))
        return f"Please wait {wait}s before requesting another reset for this email."
    # Per-IP sliding window
    hits = _ip_hits.setdefault(ip, deque())
    while hits and (now - hits[0]) > _IP_WINDOW_SEC:
        hits.popleft()
    if len(hits) >= _IP_MAX_IN_WINDOW:
        return "Too many reset requests from this network. Try again in a few minutes."
    hits.append(now)
    _email_last[email] = now
    # Trim the email table if it grows unbounded.
    if len(_email_last) > 10000:
        cutoff = now - _EMAIL_COOLDOWN_SEC
        for k in [k for k, v in _email_last.items() if v < cutoff]:
            _email_last.pop(k, None)
    return None


class RequestIn(BaseModel):
    email: EmailStr
    portal: str = Field("vendor", pattern="^(vendor|admin|staff|partner)$")


class VerifyIn(BaseModel):
    token: str


class ConfirmIn(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=200)


def _collection_for(portal: str):
    # admin + staff share admin_users in this codebase
    if portal == "vendor":
        return db.vendors
    if portal == "partner":
        return db.agents
    return db.admin_users


async def _find_user(portal: str, email: str) -> Optional[dict]:
    col = _collection_for(portal)
    if portal == "partner":
        return await col.find_one({"email": email.lower(), "status": {"$nin": ["invited", "rejected", "suspended"]}})
    return await col.find_one({"email": email.lower()})


def _mint_reset_token(user_id: str, email: str, portal: str, jti: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "portal": portal,
        "jti": jti,
        "type": "pwd_reset",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=RESET_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _decode_reset_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset link has expired. Request a new one.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="This reset link is invalid.")
    if payload.get("type") != "pwd_reset":
        raise HTTPException(status_code=400, detail="This reset link is invalid.")
    return payload


@router.post("/request")
async def request_reset(payload: RequestIn, request: Request):
    email = payload.email.lower()
    portal = payload.portal
    ip = request.client.host if request.client else "unknown"

    # Rate-limit BEFORE the account lookup so 429 never leaks existence.
    err = _rate_check(email, ip)
    if err:
        await audit_log("auth.reset_rate_limited", None, "auth", email,
                        {"portal": portal, "ip": ip})
        raise HTTPException(status_code=429, detail=err)

    user = await _find_user(portal, email)
    # Always return the same shape (do not leak account existence).
    if not user:
        await audit_log("auth.reset_requested_unknown", None, "auth", email,
                        {"portal": portal})
        return {"ok": True}

    jti = uuid4().hex
    await _collection_for(portal).update_one(
        {"_id": user["_id"]},
        {"$set": {"pwd_reset_jti": jti,
                  "pwd_reset_requested_at": datetime.now(timezone.utc).isoformat()}},
    )
    token = _mint_reset_token(str(user["_id"]), email, portal, jti)
    reset_url = f"{config.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"

    ip = request.client.host if request.client else "—"
    user_agent = request.headers.get("user-agent", "—")
    device = user_agent[:64]
    ctx = {
        "email": email,
        "reset_url": reset_url,
        "requested_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        "device": device,
        "location": ip,
        "expires_at": f"{RESET_TTL_MIN} minutes",
    }
    try:
        result = await send_e_email("account.password_reset", email, ctx)
        if not result.get("ok"):
            log.error("password-reset email NOT delivered to %s (portal=%s): %s",
                      email, portal, result.get("error"))
            await audit_log("auth.reset_email_failed", None, "auth", email,
                            {"portal": portal, "error": result.get("error")})
    except Exception as exc:
        # Do not break the response if email service hiccups; user will retry.
        log.exception("password-reset email dispatch raised for %s (portal=%s): %s",
                      email, portal, exc)
        await audit_log("auth.reset_email_failed", None, "auth", email,
                        {"portal": portal, "error": str(exc)})

    await audit_log("auth.reset_requested", None, "auth", email,
                    {"portal": portal, "jti": jti})
    return {"ok": True}


@router.post("/verify")
async def verify_token(payload: VerifyIn):
    data = _decode_reset_token(payload.token)
    portal = data.get("portal", "vendor")
    user = await _collection_for(portal).find_one({"_id": ObjectId(data["sub"])})
    if not user or user.get("pwd_reset_jti") != data.get("jti"):
        raise HTTPException(status_code=400, detail="This reset link is no longer valid.")
    return {"ok": True, "email": data.get("email"), "portal": portal}


@router.post("/confirm")
async def confirm_reset(payload: ConfirmIn):
    data = _decode_reset_token(payload.token)
    portal = data.get("portal", "vendor")
    col = _collection_for(portal)
    user = await col.find_one({"_id": ObjectId(data["sub"])})
    if not user or user.get("pwd_reset_jti") != data.get("jti"):
        raise HTTPException(status_code=400, detail="This reset link is no longer valid.")

    await col.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password),
                  "must_change_password": False,
                  "password_changed_at": datetime.now(timezone.utc).isoformat()},
         **({"$inc": {"token_generation": 1}} if portal == "partner" else {}),
         "$unset": {"pwd_reset_jti": "", "pwd_reset_requested_at": ""}},
    )
    await audit_log("auth.reset_completed", None, "auth", data.get("email"),
                    {"portal": portal})

    # Confirmation email — reuse the v50 password-changed template.
    try:
        result = await send_e_email(
            "account.password_changed",
            data.get("email"),
            {
                "email": data.get("email"),
                "changed_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
                "help_url": f"{config.FRONTEND_URL.rstrip('/')}/help",
            },
        )
        if not result.get("ok"):
            log.error("password-changed confirmation NOT delivered to %s: %s",
                      data.get("email"), result.get("error"))
    except Exception as exc:
        log.exception("password-changed confirmation raised for %s: %s",
                      data.get("email"), exc)
    return {"ok": True}
