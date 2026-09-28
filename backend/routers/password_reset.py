"""PMC v50 — Real 'Forgot password?' reset flow (vendor + admin/staff).

Endpoints (all under /api/v1/auth/password-reset):
- POST /request  {email, portal}      — always returns ok (no user enumeration).
                                        Emails a signed reset link if the
                                        account exists in the picked realm.
- POST /verify   {token}              — returns {ok, email, portal} if the
                                        token signature is valid, otherwise 400.
- POST /confirm  {token, new_password}— writes password_hash on the correct
                                        collection and clears must_change_password.

Tokens are short-lived (30 min) JWTs signed with JWT_SECRET, scoped by
`type=pwd_reset`. We store the token's issued-at (jti) on the user document
so a successful reset invalidates the link. Prevents replay after use.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
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

RESET_TTL_MIN = 30


class RequestIn(BaseModel):
    email: EmailStr
    portal: str = Field("vendor", pattern="^(vendor|admin|staff)$")


class VerifyIn(BaseModel):
    token: str


class ConfirmIn(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=200)


def _collection_for(portal: str):
    # admin + staff share admin_users in this codebase
    if portal == "vendor":
        return db.vendors
    return db.admin_users


async def _find_user(portal: str, email: str) -> Optional[dict]:
    col = _collection_for(portal)
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
        await send_e_email("account.password_reset", email, ctx)
    except Exception:
        # Do not break the response if email service hiccups; user will retry.
        pass

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
         "$unset": {"pwd_reset_jti": "", "pwd_reset_requested_at": ""}},
    )
    await audit_log("auth.reset_completed", None, "auth", data.get("email"),
                    {"portal": portal})

    # Confirmation email — reuse the v50 password-changed template.
    try:
        await send_e_email(
            "account.password_changed",
            data.get("email"),
            {
                "email": data.get("email"),
                "changed_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
                "help_url": f"{config.FRONTEND_URL.rstrip('/')}/help",
            },
        )
    except Exception:
        pass
    return {"ok": True}
