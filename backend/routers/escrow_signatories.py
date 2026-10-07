"""Escrow institution signatory auth + enhanced dashboard — v51an.

Signatories registered on an approved escrow institution can claim a
password (via the institution's magic token) and then sign in through the
usual email+password flow. Once signed in they get a transaction grid of
every pending EMD release awaiting their signature on the joint accounts
their institution operates.

Pattern mirrors `routers/vendor_auth.py` — HttpOnly `escrow_sig_token`
cookie + double-submit CSRF (`csrf_token`), JWT with `type=signatory_access`.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from models.base import now_iso
from security import hash_password, new_csrf_token, require_csrf, verify_password

router = APIRouter(prefix="/api/v1/escrow-signatories", tags=["escrow-signatories"])


# ---------- Models -------------------------------------------------------

class SignatoryClaimIn(BaseModel):
    institution_id: str
    email: EmailStr
    password: str = Field(min_length=8)


class SignatoryLoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


# ---------- Helpers ------------------------------------------------------

def _create_token(sig_id: str, email: str) -> str:
    payload = {
        "sub": sig_id, "email": email, "type": "signatory_access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _set_cookies(response: Response, token: str) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    ck = {"httponly": True, "secure": True, "samesite": "lax",
          "max_age": max_age, "path": "/"}
    if config.COOKIE_DOMAIN:
        ck["domain"] = config.COOKIE_DOMAIN
    response.set_cookie("escrow_sig_token", token, **ck)
    csrf = new_csrf_token()
    ck["httponly"] = False
    response.set_cookie("csrf_token", csrf, **ck)
    return csrf


async def current_signatory(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("escrow_sig_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, config.JWT_SECRET,
                              algorithms=[config.JWT_ALGORITHM])
        if payload.get("type") != "signatory_access":
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    sig = await db.escrow_signatories.find_one({"_id": ObjectId(payload["sub"])})
    if not sig:
        raise HTTPException(status_code=401, detail="Signatory not found")
    return {
        "id": str(sig["_id"]),
        "email": sig["email"],
        "name": sig.get("name"),
        "institution_ids": [str(i) for i in (sig.get("institution_ids") or [])],
    }


async def _resolve_signatory_institutions(email: str) -> List[dict]:
    """Return every APPROVED institution that lists this email as a signatory."""
    email = (email or "").lower()
    out: List[dict] = []
    async for inst in db.escrow_institutions.find({"status": "approved"}):
        for s in inst.get("signatories") or []:
            if (s.get("email") or "").lower() == email:
                out.append(inst)
                break
    return out


# ---------- Claim password -----------------------------------------------

@router.post("/claim")
async def claim_password(payload: SignatoryClaimIn, token: str) -> dict:
    """A registered signatory on an approved institution sets a password so
    they can sign in without the magic link going forward. Protected by the
    institution's `magic_token` so only insiders can perform the claim."""
    try:
        inst = await db.escrow_institutions.find_one(
            {"_id": ObjectId(payload.institution_id), "magic_token": token})
    except Exception:
        inst = None
    if not inst:
        raise HTTPException(status_code=404,
            detail="Institution not found or link invalid")
    if inst.get("status") != "approved":
        raise HTTPException(status_code=400,
            detail="This institution has not been approved yet")
    emails = {(s.get("email") or "").lower() for s in inst.get("signatories") or []}
    email = payload.email.lower()
    if email not in emails:
        raise HTTPException(status_code=403,
            detail="This email is not registered as a signatory on this institution")

    existing = await db.escrow_signatories.find_one({"email": email})
    pw_hash = hash_password(payload.password)
    if existing:
        inst_ids = set(str(i) for i in existing.get("institution_ids") or [])
        inst_ids.add(payload.institution_id)
        await db.escrow_signatories.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": pw_hash,
                      "institution_ids": list(inst_ids),
                      "updated_at": now_iso()}})
        sid = str(existing["_id"])
    else:
        name = next((s.get("name") for s in inst.get("signatories") or []
                      if (s.get("email") or "").lower() == email), email)
        r = await db.escrow_signatories.insert_one({
            "email": email, "name": name, "password_hash": pw_hash,
            "institution_ids": [payload.institution_id],
            "is_active": True, "created_at": now_iso(),
        })
        sid = str(r.inserted_id)
    await audit_log("escrow_sig.claim", None, "escrow_signatory", sid,
                    {"email": email, "institution_id": payload.institution_id})
    return {"ok": True, "signatory_id": sid}


# ---------- Login / Logout / Me ------------------------------------------

@router.post("/auth/login")
async def login(payload: SignatoryLoginIn, response: Response) -> Dict[str, Any]:
    sig = await db.escrow_signatories.find_one({"email": payload.email.lower()})
    if not sig or not verify_password(payload.password, sig.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not sig.get("is_active", True):
        raise HTTPException(status_code=403, detail="Signatory account disabled")
    token = _create_token(str(sig["_id"]), sig["email"])
    csrf = _set_cookies(response, token)
    await audit_log("escrow_sig.login", None, "escrow_signatory",
                    str(sig["_id"]), {"email": sig["email"]})
    return {
        "id": str(sig["_id"]), "email": sig["email"], "name": sig.get("name"),
        "institution_ids": [str(i) for i in sig.get("institution_ids") or []],
        "csrf_token": csrf, "token": token,
    }


@router.post("/auth/logout")
async def logout(response: Response, _csrf: None = Depends(require_csrf)):
    response.delete_cookie("escrow_sig_token", path="/", domain=config.COOKIE_DOMAIN)
    response.delete_cookie("csrf_token", path="/", domain=config.COOKIE_DOMAIN)
    return {"ok": True}


@router.get("/auth/me")
async def me(sig=Depends(current_signatory)) -> dict:
    insts = []
    for iid in sig["institution_ids"]:
        try:
            i = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
            if i:
                insts.append({"id": str(i["_id"]),
                              "legal_name": i.get("legal_name"),
                              "status": i.get("status")})
        except Exception:
            continue
    return {**sig, "institutions": insts}


# ---------- Forgot / reset password --------------------------------------

@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordIn) -> dict:
    """Emails the signatory a one-time reset link (1-hour TTL). Always
    returns ok=True to avoid user enumeration — if the email isn't on file
    the function is a no-op."""
    import secrets as _secrets
    sig = await db.escrow_signatories.find_one({"email": payload.email.lower()})
    if sig:
        token = _secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        await db.escrow_sig_password_resets.insert_one({
            "token": token, "email": sig["email"],
            "expires_at": expires, "used_at": None,
            "created_at": now_iso(),
        })
        try:
            from emails import send_email, wrap
            reset_url = f"{config.FRONTEND_URL}/escrow/login?reset=1&token={token}"
            body = wrap("Reset your PMC escrow signatory password",
                f"<p>Hi {sig.get('name') or sig['email']},</p>"
                f"<p>Click the button below to pick a new password. This link "
                f"expires in 1 hour. If you didn't request a reset, ignore "
                f"this email — nothing will change.</p>",
                "Reset password", reset_url)
            await send_email(sig["email"],
                "[PMC] Reset your escrow signatory password", body)
        except Exception as e:
            import logging
            logging.getLogger("escrow_sig").warning("reset email failed: %s", e)
    return {"ok": True}


@router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordIn) -> dict:
    rec = await db.escrow_sig_password_resets.find_one(
        {"token": payload.token, "used_at": None})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or already-used reset link")
    try:
        exp = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
    except Exception:
        exp = datetime.now(timezone.utc) - timedelta(seconds=1)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset link has expired")
    sig = await db.escrow_signatories.find_one({"email": rec["email"]})
    if not sig:
        raise HTTPException(status_code=400, detail="Signatory not found")
    await db.escrow_signatories.update_one(
        {"_id": sig["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password),
                  "updated_at": now_iso()}})
    await db.escrow_sig_password_resets.update_one(
        {"_id": rec["_id"]}, {"$set": {"used_at": now_iso()}})
    await audit_log("escrow_sig.password_reset", None, "escrow_signatory",
                    str(sig["_id"]), {"email": sig["email"]})
    return {"ok": True}


# ---------- Dashboard transactions grid ----------------------------------

@router.get("/dashboard")
async def dashboard_full(sig=Depends(current_signatory)) -> dict:
    """Full dashboard payload — joint account summary + every transaction
    awaiting signature from this signatory's institutions."""
    # Collect signatory emails from all their approved institutions.
    emails: set = set()
    inst_names: Dict[str, str] = {}
    for iid in sig["institution_ids"]:
        try:
            inst = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
        except Exception:
            inst = None
        if not inst:
            continue
        inst_names[str(inst["_id"])] = inst.get("legal_name") or ""
        for s in inst.get("signatories") or []:
            if s.get("email"):
                emails.add((s["email"] or "").lower())
    emails.add(sig["email"].lower())

    # Joint accounts the institution's officers operate.
    accounts: List[dict] = []
    async for a in db.escrow_accounts.find({}):
        officer_email = ((a.get("escrow_officer") or {}).get("email") or "").lower()
        if officer_email and officer_email in emails:
            accounts.append(a)
    account_ids = {str(a["_id"]) for a in accounts}

    # Pending / awaiting-signature transactions on those accounts.
    pending: List[dict] = []
    all_tx: List[dict] = []
    async for t in db.escrow_transactions.find({"escrow_account_id": {"$in": list(account_ids)}}
                                                 ).sort("created_at", -1).limit(200):
        snap = t.get("escrow_account_snapshot") or {}
        signed_me = False
        sigs = t.get("signatures") or {}
        if (sigs.get("escrow_institution") or {}).get("by") == sig["email"]:
            signed_me = True
        row = {
            "id": str(t["_id"]),
            "bid_ref": t.get("bid_ref"),
            "notice_ref": t.get("notice_ref"),
            "vendor_ref": t.get("vendor_ref"),
            "amount": t.get("amount"),
            "currency": t.get("currency"),
            "status": t.get("status"),
            "received_at": t.get("received_at"),
            "created_at": t.get("created_at"),
            "account_name": snap.get("name"),
            "institution": snap.get("institution"),
            "signed_by_pmc": bool((sigs.get("pmc") or {}).get("signed_at")),
            "signed_by_institution": bool((sigs.get("escrow_institution") or {}).get("signed_at")),
            "signed_by_me": signed_me,
            "awaiting_my_signature": (t.get("status") in ("received", "awaiting_signatures")
                                       and not signed_me),
        }
        all_tx.append(row)
        if row["awaiting_my_signature"]:
            pending.append(row)
    return {
        "signatory": {"email": sig["email"], "name": sig.get("name")},
        "institutions": [{"id": iid, "legal_name": inst_names.get(iid)}
                          for iid in sig["institution_ids"]],
        "joint_accounts": [{"id": str(a["_id"]), "name": a.get("name"),
                              "institution": a.get("institution"),
                              "account_no": a.get("account_no"),
                              "currency": a.get("currency")}
                             for a in accounts],
        "pending_signatures_count": len(pending),
        "pending_transactions": pending,
        "transactions": all_tx,
    }
