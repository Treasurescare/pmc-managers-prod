"""Escrow Account auth — v52d (14 Feb 2026).

Account-first replacement for the old magic-link draft flow. The primary
contact of a prospective escrow institution signs up with
{email, legal_name, phone, password}, verifies their email via a one-click
link, then signs in to a persistent account that owns the institution draft
plus every status change / notification over the lifetime of the record.

Pattern mirrors routers/vendor_auth.py (HttpOnly `escrow_account_token`
cookie + double-submit CSRF). Reuses hash_password / verify_password /
new_csrf_token from security.py; email send through emails.send_email.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import secrets

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator

import config
from audit import audit_log
from db import db
from emails import send_email, _wrap
from models.base import now_iso
from security import hash_password, new_csrf_token, require_csrf, verify_password

router = APIRouter(prefix="/api/v1/escrow-accounts", tags=["escrow-accounts"])

VERIFY_TTL_HOURS = 24
RESET_TTL_HOURS = 2


# ---------- Pydantic models ---------------------------------------------

class RegisterIn(BaseModel):
    email: EmailStr
    legal_name: str = Field(min_length=2, max_length=200)
    primary_contact_phone: str = Field(min_length=5, max_length=40)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ProfileIn(BaseModel):
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    primary_contact_phone: Optional[str] = Field(default=None, min_length=5, max_length=40)
    avatar_data_url: Optional[str] = None


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ---------- Helpers ------------------------------------------------------

def _token() -> str:
    return secrets.token_urlsafe(32)


def _create_jwt(acc_id: str, email: str, gen: int = 0) -> str:
    payload = {
        "sub": acc_id, "email": email, "type": "escrow_account_access",
        "gen": gen,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _set_cookies(response: Response, token: str) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    ck = {"httponly": True, "secure": True, "samesite": "lax",
          "max_age": max_age, "path": "/"}
    if config.COOKIE_DOMAIN:
        ck["domain"] = config.COOKIE_DOMAIN
    response.set_cookie("escrow_account_token", token, **ck)
    csrf = new_csrf_token()
    ck["httponly"] = False
    response.set_cookie("csrf_token", csrf, **ck)
    return csrf


async def current_account(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("escrow_account_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.JWT_SECRET,
                              algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "escrow_account_access":
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    acc = await db.escrow_accounts.find_one({"_id": ObjectId(payload["sub"])})
    if not acc:
        raise HTTPException(status_code=401, detail="Account not found")
    if int(payload.get("gen") or 0) < int(acc.get("token_generation") or 0):
        raise HTTPException(status_code=401, detail="Session revoked")
    return _public(acc)


def _public(acc: dict) -> Dict[str, Any]:
    return {
        "id": str(acc["_id"]),
        "email": acc["email"],
        "legal_name": acc.get("legal_name"),
        "primary_contact_phone": acc.get("primary_contact_phone"),
        "status": acc.get("status", "unverified"),
        "institution_id": acc.get("institution_id"),
        "avatar_data_url": acc.get("avatar_data_url"),
        "created_at": acc.get("created_at"),
    }


async def _send_verify_email(email: str, legal_name: str, token: str) -> None:
    verify_url = f"{config.FRONTEND_URL}/escrow/verify/{token}"
    html = _wrap(
        "Verify your escrow institution email",
        f"<p>Dear {legal_name or 'applicant'},</p>"
        f"<p>You just started an escrow institution registration on "
        f"PMC Managers. Click the button below to confirm this email "
        f"address — the link is valid for {VERIFY_TTL_HOURS} hours. "
        f"After verification you can sign in and complete the five "
        f"registration sections at your own pace; your progress is "
        f"saved to your account.</p>",
        "Verify email & continue", verify_url,
    )
    try:
        await send_email(email, "Verify your PMC escrow account", html)
    except Exception:
        pass


async def _send_reset_email(email: str, token: str) -> None:
    url = f"{config.FRONTEND_URL}/escrow/login?reset=1&token={token}"
    html = _wrap(
        "Reset your escrow account password",
        f"<p>We received a request to reset the password for your PMC "
        f"escrow account ({email}). This link is valid for "
        f"{RESET_TTL_HOURS} hours. If you did not request this, ignore "
        f"this email.</p>",
        "Reset password", url,
    )
    try:
        await send_email(email, "Reset your PMC escrow password", html)
    except Exception:
        pass


# ---------- Register / verify -------------------------------------------

@router.post("/register")
async def register(payload: RegisterIn, response: Response) -> Dict[str, Any]:
    """Public — creates an UNVERIFIED account and emails a verify link.
    Enforces one-account-per-email at the account layer. Institutions
    collection is only touched after the user verifies and signs in."""
    email = payload.email.lower().strip()
    existing = await db.escrow_accounts.find_one({"email": email})
    if existing:
        # Already verified -> clean 409 the UI can route to login.
        # Still unverified -> re-send verify link, keep the row.
        if existing.get("status") == "verified":
            raise HTTPException(status_code=409,
                detail={
                    "error": "account_exists",
                    "message": f"An escrow account for {email} already exists. "
                               f"Please sign in."})
        new_tok = _token()
        await db.escrow_accounts.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "legal_name": payload.legal_name.strip(),
                "primary_contact_phone": payload.primary_contact_phone.strip(),
                "password_hash": hash_password(payload.password),
                "verify_token": new_tok,
                "verify_token_expires_at":
                    (datetime.now(timezone.utc) + timedelta(hours=VERIFY_TTL_HOURS)).isoformat(),
                "updated_at": now_iso(),
            }},
        )
        await _send_verify_email(email, payload.legal_name, new_tok)
        return {"id": str(existing["_id"]), "status": "unverified",
                "message": "Verify email re-sent."}
    # Also guard against legacy magic-link institutions sharing this email —
    # the user said "force everyone to the new flow", so we accept the
    # registration but will NOT auto-attach their old draft here; the
    # verify step attaches an institution record keyed on the account.
    doc = {
        "email": email,
        "legal_name": payload.legal_name.strip(),
        "primary_contact_phone": payload.primary_contact_phone.strip(),
        "password_hash": hash_password(payload.password),
        "status": "unverified",
        "verify_token": _token(),
        "verify_token_expires_at":
            (datetime.now(timezone.utc) + timedelta(hours=VERIFY_TTL_HOURS)).isoformat(),
        "token_generation": 0,
        "institution_id": None,
        "created_at": now_iso(),
    }
    r = await db.escrow_accounts.insert_one(doc)
    await _send_verify_email(email, payload.legal_name, doc["verify_token"])
    await audit_log("escrow_account.register", None, "escrow_account",
                     str(r.inserted_id), {"email": email})
    return {"id": str(r.inserted_id), "status": "unverified",
            "message": "Verify email sent."}


@router.get("/verify/{token}")
async def verify_email(token: str) -> Dict[str, Any]:
    """Public — one-click email verification. Also creates (or links) a
    draft escrow_institutions row keyed to this account so the wizard can
    PATCH it immediately after sign-in."""
    acc = await db.escrow_accounts.find_one({"verify_token": token})
    if not acc:
        raise HTTPException(status_code=404,
            detail="Verification link is invalid or has already been used.")
    exp = acc.get("verify_token_expires_at")
    if exp and datetime.fromisoformat(exp) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410,
            detail="Verification link expired. Please request a new one.")
    # Ensure a draft institution exists so the wizard has a stable id.
    inst_id = acc.get("institution_id")
    if not inst_id:
        inst_doc = {
            "legal_name": acc.get("legal_name"),
            "primary_contact_email": acc["email"],
            "primary_contact_phone": acc.get("primary_contact_phone"),
            "status": "draft",
            "account_id": str(acc["_id"]),
            "signatories": [],
            "bank_accounts": [],
            "created_at": now_iso(),
        }
        r = await db.escrow_institutions.insert_one(inst_doc)
        inst_id = str(r.inserted_id)
    await db.escrow_accounts.update_one(
        {"_id": acc["_id"]},
        {"$set": {"status": "verified",
                   "institution_id": inst_id,
                   "verified_at": now_iso()},
         "$unset": {"verify_token": "", "verify_token_expires_at": ""}})
    await audit_log("escrow_account.verify", None, "escrow_account",
                     str(acc["_id"]), {"email": acc["email"]})
    return {"ok": True, "email": acc["email"], "institution_id": inst_id}


@router.post("/auth/resend-verify")
async def resend_verify(payload: ForgotIn) -> Dict[str, bool]:
    acc = await db.escrow_accounts.find_one({"email": payload.email.lower().strip()})
    if not acc or acc.get("status") == "verified":
        # Silent 200 — don't leak account existence.
        return {"ok": True}
    tok = _token()
    await db.escrow_accounts.update_one(
        {"_id": acc["_id"]},
        {"$set": {"verify_token": tok,
                   "verify_token_expires_at":
                       (datetime.now(timezone.utc) + timedelta(hours=VERIFY_TTL_HOURS)).isoformat()}})
    await _send_verify_email(acc["email"], acc.get("legal_name"), tok)
    return {"ok": True}


# ---------- Login / logout / me -----------------------------------------

@router.post("/auth/login")
async def login(payload: LoginIn, response: Response, request: Request) -> Dict[str, Any]:
    acc = await db.escrow_accounts.find_one({"email": payload.email.lower().strip()})
    if not acc or not verify_password(payload.password, acc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if acc.get("status") != "verified":
        raise HTTPException(status_code=403,
            detail={"error": "unverified",
                     "message": "Please verify your email before signing in. "
                                "Check your inbox for the link we sent you."})
    gen = int(acc.get("token_generation") or 0)
    token = _create_jwt(str(acc["_id"]), acc["email"], gen)
    csrf = _set_cookies(response, token)
    # Kill competing session cookies so account/vendor/admin never mix.
    response.delete_cookie("access_token", path="/", domain=config.COOKIE_DOMAIN)
    response.delete_cookie("vendor_token", path="/", domain=config.COOKIE_DOMAIN)
    response.delete_cookie("escrow_sig_token", path="/", domain=config.COOKIE_DOMAIN)
    await audit_log("escrow_account.login", None, "escrow_account",
                     str(acc["_id"]), {"email": acc["email"]})
    return {**_public(acc), "csrf_token": csrf}


@router.post("/auth/logout")
async def logout(response: Response) -> Dict[str, bool]:
    for name in ("escrow_account_token", "csrf_token"):
        response.delete_cookie(name, path="/", domain=config.COOKIE_DOMAIN)
    return {"ok": True}


@router.get("/auth/me")
async def me(acc=Depends(current_account), response: Response = None) -> Dict[str, Any]:
    if response is not None:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    data = _public(full)
    # Attach institution snapshot so the UI can route to wizard vs dashboard
    # without a second round-trip.
    if full.get("institution_id"):
        inst = await db.escrow_institutions.find_one(
            {"_id": ObjectId(full["institution_id"])})
        if inst:
            data["institution"] = {
                "id": str(inst["_id"]),
                "legal_name": inst.get("legal_name"),
                "status": inst.get("status"),
            }
    data["unread_notifications"] = await db.escrow_notifications.count_documents(
        {"account_id": acc["id"], "read_at": None})
    return data


@router.patch("/me/profile", dependencies=[Depends(require_csrf)])
async def update_profile(payload: ProfileIn, acc=Depends(current_account)):
    patch = payload.model_dump(exclude_unset=True)
    if "legal_name" in patch:
        patch["legal_name"] = patch["legal_name"].strip()
    if "primary_contact_phone" in patch:
        patch["primary_contact_phone"] = patch["primary_contact_phone"].strip()
    if not patch:
        return _public(await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])}))
    patch["updated_at"] = now_iso()
    await db.escrow_accounts.update_one(
        {"_id": ObjectId(acc["id"])}, {"$set": patch})
    # Mirror legal_name / phone onto the owned institution so the dashboard
    # and the admin console stay in sync (what the user sees as "profile").
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    if full.get("institution_id") and ("legal_name" in patch or "primary_contact_phone" in patch):
        inst_patch = {k: v for k, v in patch.items()
                       if k in ("legal_name", "primary_contact_phone")}
        if inst_patch:
            await db.escrow_institutions.update_one(
                {"_id": ObjectId(full["institution_id"])},
                {"$set": inst_patch})
    await audit_log("escrow_account.profile_update", None, "escrow_account",
                     acc["id"], list(patch.keys()))
    return _public(full)


@router.post("/auth/change-password", dependencies=[Depends(require_csrf)])
async def change_password(payload: ChangePasswordIn, response: Response,
                           acc=Depends(current_account)) -> Dict[str, Any]:
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    if not verify_password(payload.current_password, full.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password incorrect")
    await db.escrow_accounts.update_one(
        {"_id": full["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password),
                   "password_changed_at": now_iso()},
         "$inc": {"token_generation": 1}})
    new_gen = int(full.get("token_generation") or 0) + 1
    token = _create_jwt(acc["id"], acc["email"], new_gen)
    csrf = _set_cookies(response, token)
    await audit_log("escrow_account.password_change", None, "escrow_account",
                     acc["id"], {})
    return {"ok": True, "csrf_token": csrf}


# ---------- Forgot / reset ----------------------------------------------

@router.post("/auth/forgot")
async def forgot_password(payload: ForgotIn) -> Dict[str, bool]:
    acc = await db.escrow_accounts.find_one({"email": payload.email.lower().strip()})
    if acc:
        tok = _token()
        await db.escrow_accounts.update_one(
            {"_id": acc["_id"]},
            {"$set": {"reset_token": tok,
                       "reset_token_expires_at":
                           (datetime.now(timezone.utc) + timedelta(hours=RESET_TTL_HOURS)).isoformat()}})
        await _send_reset_email(acc["email"], tok)
    return {"ok": True}


@router.post("/auth/reset")
async def reset_password(payload: ResetIn) -> Dict[str, bool]:
    acc = await db.escrow_accounts.find_one({"reset_token": payload.token})
    if not acc:
        raise HTTPException(status_code=404, detail="Reset link invalid or already used")
    exp = acc.get("reset_token_expires_at")
    if exp and datetime.fromisoformat(exp) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Reset link expired")
    await db.escrow_accounts.update_one(
        {"_id": acc["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password),
                   "password_changed_at": now_iso()},
         "$inc": {"token_generation": 1},
         "$unset": {"reset_token": "", "reset_token_expires_at": ""}})
    return {"ok": True}


# ---------- Notifications ------------------------------------------------

@router.get("/me/notifications")
async def list_notifications(acc=Depends(current_account),
                              limit: int = 50) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cur = db.escrow_notifications.find({"account_id": acc["id"]}) \
                                  .sort("created_at", -1).limit(limit)
    async for n in cur:
        out.append({
            "id": str(n["_id"]),
            "kind": n.get("kind"),
            "title": n.get("title"),
            "body": n.get("body"),
            "link": n.get("link"),
            "read": bool(n.get("read_at")),
            "created_at": n.get("created_at"),
        })
    return out


@router.post("/me/notifications/{nid}/read",
              dependencies=[Depends(require_csrf)])
async def mark_read(nid: str, acc=Depends(current_account)) -> Dict[str, bool]:
    await db.escrow_notifications.update_one(
        {"_id": ObjectId(nid), "account_id": acc["id"]},
        {"$set": {"read_at": now_iso()}})
    return {"ok": True}


@router.post("/me/notifications/mark-all-read",
              dependencies=[Depends(require_csrf)])
async def mark_all_read(acc=Depends(current_account)) -> Dict[str, int]:
    r = await db.escrow_notifications.update_many(
        {"account_id": acc["id"], "read_at": None},
        {"$set": {"read_at": now_iso()}})
    return {"updated": r.modified_count}


# ---------- Helper for other routers (status change hook) ---------------

async def notify_account(account_id: str, kind: str, title: str,
                          body: str, link: Optional[str] = None,
                          send_email_too: bool = True) -> None:
    """Called from escrow_institutions when admin changes institution
    status. Writes an in-app notification AND fires an email."""
    doc = {"account_id": account_id, "kind": kind,
            "title": title, "body": body, "link": link,
            "read_at": None, "created_at": now_iso()}
    await db.escrow_notifications.insert_one(doc)
    if send_email_too:
        acc = await db.escrow_accounts.find_one({"_id": ObjectId(account_id)})
        if acc and acc.get("email"):
            url = f"{config.FRONTEND_URL}{link or '/escrow/me'}"
            html = _wrap(title, f"<p>{body}</p>", "Open your dashboard", url)
            try:
                await send_email(acc["email"],
                                   f"PMC Escrow · {title}", html)
            except Exception:
                pass
