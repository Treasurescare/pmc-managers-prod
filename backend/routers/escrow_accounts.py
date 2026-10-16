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
from security import hash_password, new_csrf_token, require_csrf, verify_password, set_csrf_cookie

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
    set_csrf_cookie(response, csrf, max_age)
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
    # v53m — be specific about which part failed so the user can self-serve:
    #   * no account at all → tell them to register / ask admin for an invite
    #   * account exists but password wrong → "wrong password"
    # Password-wrong still uses 401, no-account uses 404 so the UI can show
    # a dedicated hint without leaking account enumeration everywhere else.
    if not acc:
        # Check if ANY institution exists for this email so we can hint the
        # user that admin invited them but no account was ever created yet.
        inst = await db.escrow_institutions.find_one({
            "primary_contact_email": {
                "$regex": f"^{payload.email.lower().strip()}$", "$options": "i"}},
            {"status": 1, "magic_token": 1})
        if inst:
            raise HTTPException(status_code=404, detail={
                "error": "no_account_only_institution",
                "message": "This email was invited by an admin but you haven't "
                           "finished registration yet. Open the invite link in "
                           "your mailbox, or ask the admin to resend it.",
            })
        raise HTTPException(status_code=404, detail={
            "error": "no_account",
            "message": "No escrow account found with this email. Register at "
                       "/escrow/register, or ask the admin to invite you.",
        })
    if not verify_password(payload.password, acc.get("password_hash", "")):
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
    email = payload.email.lower().strip()
    acc = await db.escrow_accounts.find_one({"email": email})
    if not acc:
        # v52i — legacy recovery. Institutions registered under the old
        # magic-link flow have no account row, so forgot-password used to
        # silently no-op and those owners could never sign in. Provision a
        # verified account on the fly, linked to the institution on file —
        # the reset link then doubles as the account-claim link. It is only
        # emailed to the address already registered for the institution, so
        # mailbox possession is the proof of ownership.
        inst = await db.escrow_institutions.find_one(
            {"primary_contact_email": email}, sort=[("created_at", -1)])
        if inst:
            doc = {
                "email": email,
                "legal_name": inst.get("legal_name") or email,
                "primary_contact_phone": inst.get("primary_contact_phone") or "",
                "password_hash": hash_password(secrets.token_urlsafe(24)),
                "status": "verified",
                "token_generation": 0,
                "institution_id": str(inst["_id"]),
                "legacy_claim": True,
                "created_at": now_iso(),
            }
            r = await db.escrow_accounts.insert_one(doc)
            acc = {**doc, "_id": r.inserted_id}
            await db.escrow_institutions.update_one(
                {"_id": inst["_id"]},
                {"$set": {"account_id": str(r.inserted_id)}})
            await audit_log("escrow_account.legacy_claim", None,
                            "escrow_account", str(r.inserted_id),
                            {"email": email})
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
                   # Resetting via the emailed link proves mailbox ownership,
                   # so the account counts as verified from here on.
                   "status": "verified",
                   "password_changed_at": now_iso()},
         "$inc": {"token_generation": 1},
         "$unset": {"reset_token": "", "reset_token_expires_at": ""}})
    await audit_log("escrow_account.password_reset", None, "escrow_account",
                    str(acc["_id"]), {"email": acc["email"]})
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

@router.get("/me/dashboard")
async def dashboard(acc=Depends(current_account)) -> Dict[str, Any]:
    """v52e — real pending signatures + transactions for the owning account.
    Scans escrow_transactions for rows whose escrow_account_snapshot points
    at an escrow_accounts row operated by one of this institution's named
    signatories, OR whose institution_id matches directly."""
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    iid = full.get("institution_id")
    inst: Dict[str, Any] = {}
    signatory_emails: List[str] = []
    if iid:
        d = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
        if d:
            inst = {"id": str(d["_id"]),
                    "legal_name": d.get("legal_name"),
                    "status": d.get("status")}
            signatory_emails = [
                (s.get("email") or "").lower()
                for s in (d.get("signatories") or []) if s.get("email")
            ]
    # Joint accounts: any escrow_accounts row where the escrow_officer email
    # matches one of our signatories. Legacy data uses escrow_account_id on
    # the transaction; new flow also tags account_id on the institution.
    joint_accounts: List[Dict[str, Any]] = []
    joint_account_ids: List[str] = []
    if signatory_emails:
        async for a in db.escrow_accounts.find({}):
            officer_email = ((a.get("escrow_officer") or {}).get("email") or "").lower()
            if officer_email and officer_email in signatory_emails:
                joint_account_ids.append(str(a["_id"]))
                joint_accounts.append({
                    "id": str(a["_id"]),
                    "name": a.get("name"),
                    "account_no": a.get("account_no"),
                    "currency": a.get("currency"),
                    "balance": a.get("balance"),
                })
    pending: List[Dict[str, Any]] = []
    transactions: List[Dict[str, Any]] = []
    if joint_account_ids:
        async for t in db.escrow_transactions.find(
                {"escrow_account_id": {"$in": joint_account_ids}}
            ).sort("created_at", -1).limit(200):
            sigs = t.get("signatures") or {}
            row = {
                "id": str(t["_id"]),
                "bid_ref": t.get("bid_ref"),
                "notice_ref": t.get("notice_ref"),
                "vendor_ref": t.get("vendor_ref"),
                "amount": t.get("amount"),
                "currency": t.get("currency"),
                "status": t.get("status"),
                "created_at": t.get("created_at"),
                "signed_by_pmc": bool((sigs.get("pmc") or {}).get("signed_at")),
                "signed_by_institution": bool((sigs.get("escrow_institution") or {}).get("signed_at")),
            }
            transactions.append(row)
            if t.get("status") in ("received", "awaiting_signatures") \
                    and not row["signed_by_institution"]:
                pending.append(row)
    unread = await db.escrow_notifications.count_documents(
        {"account_id": acc["id"], "read_at": None})
    return {
        "account": _public(full),
        "institution": inst,
        "joint_accounts": joint_accounts,
        "joint_accounts_count": len(joint_accounts),
        "pending_signatures": pending,
        "pending_signatures_count": len(pending),
        "transactions": transactions,
        "transactions_count": len(transactions),
        "unread_notifications": unread,
    }


# ---------- v54a: Transaction detail + payment entries + DocuSign signing ----------
#
# The institution-portal views one of their joint-account transactions, lists
# payment entries, creates new ones (receipts / releases / refunds / fees)
# with a proof upload, signs them, and opens the DocuSign signing session
# for the transaction. All endpoints scoped to the current account via
# escrow_officer.email matching institution.signatories[].email.

async def _account_signatory_emails(acc_full: dict) -> List[str]:
    """Emails of users who can act for this institution: the account's own
    email plus every signatory on the owned institution."""
    emails = [acc_full.get("email", "").lower()]
    iid = acc_full.get("institution_id")
    if iid:
        d = await db.escrow_institutions.find_one({"_id": ObjectId(iid)})
        if d:
            for s in d.get("signatories") or []:
                e = (s.get("email") or "").lower()
                if e: emails.append(e)
    return list({e for e in emails if e})


async def _assert_tx_owned_by_account(tx: dict, acc: Dict[str, Any]) -> None:
    """Allow the current account to touch this tx only if the escrow
    officer on the account snapshot is one of the account's signatories."""
    full = await db.escrow_accounts.find_one({"_id": ObjectId(acc["id"])})
    emails = await _account_signatory_emails(full)
    snap = tx.get("escrow_account_snapshot") or {}
    esc_email = ((snap.get("escrow_officer") or {}).get("email") or "").lower()
    if esc_email and esc_email in emails:
        return
    # Fallback: account_id on the escrow_accounts row stored on this institution
    acc_doc = await db.escrow_accounts.find_one(
        {"_id": ObjectId(tx.get("escrow_account_id") or "0" * 24)}
    ) if tx.get("escrow_account_id") else None
    officer_email = ""
    if acc_doc:
        officer_email = ((acc_doc.get("escrow_officer") or {}).get("email") or "").lower()
    if officer_email and officer_email in emails:
        return
    raise HTTPException(
        403,
        "This transaction is not on an escrow account operated by your institution.",
    )


class _PaymentEntryInstIn(BaseModel):
    direction: str  # "in" | "out"
    kind: str  # "emd_in" | "release_out" | "refund_out" | "fee_out"
    amount: float
    currency: str
    dated_on: Optional[str] = None
    bank_reference: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    notes: Optional[str] = None
    proof_data_url: Optional[str] = None
    proof_filename: Optional[str] = None


class _SignIn(BaseModel):
    action: str = "approve"  # approve | reject
    comment: Optional[str] = None


@router.get("/me/transactions/{tid}")
async def get_my_transaction(tid: str, acc=Depends(current_account)) -> Dict[str, Any]:
    if not ObjectId.is_valid(tid):
        raise HTTPException(400, "Invalid transaction id")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    await _assert_tx_owned_by_account(tx, acc)
    # Payment entries
    entries: List[Dict[str, Any]] = []
    async for pe in db.escrow_payment_entries.find(
        {"transaction_id": tid}
    ).sort("created_at", -1):
        entries.append({**{k: v for k, v in pe.items() if k != "_id"},
                        "id": str(pe["_id"])})
    # DocuSign envelope detail
    envelope = None
    env_id = tx.get("docusign_envelope_id")
    if env_id:
        row = await db.docusign_envelopes.find_one({"envelope_id": env_id})
        if row:
            envelope = {
                "envelope_id": env_id,
                "status": row.get("status"),
                "signers": row.get("signers") or [],
                "created_at": row.get("created_at"),
            }
    out = {k: v for k, v in tx.items() if k != "_id"}
    out["id"] = str(tx["_id"])
    out["payment_entries"] = entries
    out["docusign_envelope"] = envelope
    return out


@router.post("/me/transactions/{tid}/payment-entries",
              dependencies=[Depends(require_csrf)])
async def create_my_payment_entry(tid: str, payload: _PaymentEntryInstIn,
                                    acc=Depends(current_account)) -> Dict[str, Any]:
    if payload.direction not in ("in", "out"):
        raise HTTPException(400, "direction must be in or out")
    if payload.kind not in ("emd_in", "release_out", "refund_out", "fee_out"):
        raise HTTPException(400, "kind not allowed")
    if payload.amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    if not ObjectId.is_valid(tid):
        raise HTTPException(400, "Invalid transaction id")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    await _assert_tx_owned_by_account(tx, acc)
    doc = {
        "transaction_id": tid,
        "escrow_account_id": tx.get("escrow_account_id"),
        "escrow_account_snapshot": tx.get("escrow_account_snapshot"),
        "bid_ref": tx.get("bid_ref"),
        "notice_ref": tx.get("notice_ref"),
        "direction": payload.direction,
        "kind": payload.kind,
        "amount": payload.amount,
        "currency": payload.currency.upper(),
        "dated_on": payload.dated_on or now_iso(),
        "bank_reference": payload.bank_reference,
        "counterparty_name": payload.counterparty_name,
        "counterparty_account": payload.counterparty_account,
        "notes": payload.notes,
        "proof": {
            "data_url": payload.proof_data_url,
            "filename": payload.proof_filename,
        } if payload.proof_data_url else None,
        "signatures": {},
        "status": "pending_signatures",
        "audit_trail": [{
            "at": now_iso(), "by": acc.get("email"),
            "event": "created", "source": "institution",
        }],
        "docusign_envelope_id": None,
        "created_at": now_iso(),
        "created_by": acc.get("email"),
        "created_by_role": "institution",
    }
    r = await db.escrow_payment_entries.insert_one(doc)
    doc["_id"] = r.inserted_id
    await audit_log(
        "escrow.payment_entry_create", None, "escrow_payment_entry",
        str(r.inserted_id),
        {"tx_id": tid, "kind": payload.kind, "amount": payload.amount,
         "by_institution": acc.get("email")},
    )
    return {**{k: v for k, v in doc.items() if k != "_id"}, "id": str(r.inserted_id)}


@router.post("/me/payment-entries/{peid}/sign",
              dependencies=[Depends(require_csrf)])
async def sign_my_payment_entry(peid: str, payload: _SignIn,
                                  acc=Depends(current_account)) -> Dict[str, Any]:
    if not ObjectId.is_valid(peid):
        raise HTTPException(400, "Invalid payment entry id")
    pe = await db.escrow_payment_entries.find_one({"_id": ObjectId(peid)})
    if not pe:
        raise HTTPException(404, "Payment entry not found")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(pe["transaction_id"])})
    if not tx:
        raise HTTPException(404, "Linked transaction missing")
    await _assert_tx_owned_by_account(tx, acc)
    if pe.get("status") in ("fully_signed", "rejected", "void"):
        raise HTTPException(409, f"Already {pe.get('status')}")
    if payload.action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve or reject")
    sigs = pe.get("signatures") or {}
    sigs["escrow_institution"] = {
        "email": acc.get("email"),
        "action": payload.action,
        "comment": payload.comment,
        "signed_at": now_iso(),
        "via": "institution_portal",
    }
    trail = pe.get("audit_trail") or []
    trail.append({"at": now_iso(), "by": acc.get("email"),
                   "event": "signed_escrow_institution",
                   "action": payload.action, "comment": payload.comment,
                   "via": "institution_portal"})
    # Compute final status
    pmc_sig = (sigs.get("pmc") or {})
    new_status = pe.get("status") or "pending_signatures"
    if payload.action == "reject" or pmc_sig.get("action") == "reject":
        new_status = "rejected"
    elif pmc_sig.get("action") == "approve" and sigs["escrow_institution"]["action"] == "approve":
        new_status = "fully_signed"
    await db.escrow_payment_entries.update_one(
        {"_id": ObjectId(peid)},
        {"$set": {"signatures": sigs, "audit_trail": trail,
                   "status": new_status, "updated_at": now_iso()}},
    )
    await audit_log("escrow.payment_entry_sign", None, "escrow_payment_entry",
                    peid, {"side": "escrow_institution", "action": payload.action,
                            "by_institution": acc.get("email")})
    pe = await db.escrow_payment_entries.find_one({"_id": ObjectId(peid)})
    return {**{k: v for k, v in pe.items() if k != "_id"}, "id": str(pe["_id"])}


@router.get("/me/transactions/{tid}/docusign-url")
async def my_transaction_docusign_url(tid: str,
                                        acc=Depends(current_account)) -> Dict[str, Any]:
    """Return a one-time hosted-signing URL for the escrow institution
    officer on this transaction's DocuSign envelope. If the envelope was
    issued in email-mode (default), DocuSign already emailed them the link
    the moment the envelope was sent; this endpoint reissues a fresh console
    view so they can sign from inside the PMC portal too."""
    if not ObjectId.is_valid(tid):
        raise HTTPException(400, "Invalid transaction id")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    await _assert_tx_owned_by_account(tx, acc)
    env_id = tx.get("docusign_envelope_id")
    if not env_id:
        raise HTTPException(
            404,
            "PMC admin has not sent a DocuSign envelope for this transaction yet. "
            "They can issue one from the admin console.",
        )
    try:
        import docusign_esign as ds
        from routers.docusign import _client, DS_ACCOUNT_ID
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        view = envelopes.create_console_view(DS_ACCOUNT_ID,
            console_view_request=ds.ConsoleViewRequest(
                envelope_id=env_id,
                return_url=f"{config.FRONTEND_URL}/escrow/me"))
        return {"url": view.url, "envelope_id": env_id, "mode": "console"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Could not create signing URL: {e}")


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
