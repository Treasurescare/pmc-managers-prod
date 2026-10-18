"""Staff auth — unified login for admins + all specialised roles.

Staff records hold a LIST of roles; on login the user picks an active role.
Same cookie/CSRF mechanics as admin_auth. Backwards-compatible with the
legacy `admin_users` collection: existing admins are auto-migrated on login.
"""
from typing import Dict, Any, List
import re
from fastapi import APIRouter, HTTPException, Response, Depends, Request
from bson import ObjectId
from pydantic import BaseModel
import jwt

from db import db
from models.staff_user import StaffLoginIn, StaffCreateIn, StaffUpdateIn, ALL_STAFF_ROLES, StaffRole
from security import (
    verify_password, hash_password, create_admin_token, current_admin,
    new_csrf_token, csrf_for_session, require_role, require_csrf, set_csrf_cookie,
    set_access_cookie, clear_session_cookie, is_preview_request,
)
from audit import audit_log
import config

router = APIRouter(prefix="/api/v1/staff", tags=["staff-auth"])


def _set_session_cookies(response: Response, access_token: str, request: Request = None) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    cross_site = is_preview_request(request)
    set_access_cookie(response, "access_token", access_token, max_age, cross_site)
    try:
        sub = jwt.decode(access_token, config.JWT_SECRET,
                         algorithms=[config.JWT_ALGORITHM]).get("sub")
        csrf = csrf_for_session(sub) if sub else new_csrf_token()
    except Exception:
        csrf = new_csrf_token()
    set_csrf_cookie(response, csrf, max_age, cross_site)
    return csrf


def _out(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d.pop("password_hash", None)
    roles = d.get("roles") or ([d.get("role")] if d.get("role") else [])
    # v55 — backfill account_type for legacy records: a record that holds an
    # admin-console role is an "admin" account, otherwise it's a "staff" account.
    d["account_type"] = d.get("account_type") or (
        "admin" if (set(roles) & ADMIN_CONSOLE_ROLES) else "staff"
    )
    return d


# v55 — roles that unlock the admin console. "staff" accounts may never hold these.
ADMIN_CONSOLE_ROLES = {"admin", "reviewer"}


def _validate_account_type(account_type: str, roles: List[str]) -> None:
    held_admin = ADMIN_CONSOLE_ROLES & set(roles or [])
    if account_type == "staff" and held_admin:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Staff accounts cannot hold the {', '.join(sorted(held_admin))} "
                "role. Set the account type to Admin, or remove those roles."
            ),
        )
    if account_type == "admin" and not held_admin:
        raise HTTPException(
            status_code=400,
            detail="Admin accounts must include the Admin or Reviewer role.",
        )


@router.get("/auth/csrf")
async def refresh_csrf_token(request: Request, response: Response):
    """v56b — re-issue the CSRF cookie for an already-authenticated session.

    When the browser drops the JS-readable `csrf_token` cookie (Safari ITP,
    cookie partitioning, or a long-idle tab) while the HttpOnly `access_token`
    is still valid, every state-changing request 403s with "CSRF token missing
    or invalid" — the sessionStorage header fallback can't satisfy the server's
    double-submit check because the cookie itself is gone. The axios interceptor
    calls this once to recover, then retries the original request.

    Auth is the existing access_token (any role); the OLD csrf is NOT trusted.
    """
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
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    cross_site = is_preview_request(request)
    csrf = csrf_for_session(payload["sub"]) if payload.get("sub") else new_csrf_token()
    set_csrf_cookie(response, csrf, max_age, cross_site)
    return {"csrf_token": csrf}


@router.post("/auth/login")
async def staff_login(payload: StaffLoginIn, response: Response, request: Request) -> Dict[str, Any]:
    user = await db.admin_users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Backfill multi-role list on legacy single-role docs
    roles: List[str] = user.get("roles") or [user.get("role") or "admin"]
    if payload.active_role not in roles:
        raise HTTPException(status_code=403, detail=f"You do not hold the {payload.active_role} role")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    # Wave 8 — Force MFA on high-risk roles (gated by config flag; OFF for
    # testing, re-enable before beta via REQUIRE_HIGH_RISK_MFA).
    HIGH_RISK_ROLES = {"escrow_agent", "legal_counsel", "accounting"}
    if config.REQUIRE_HIGH_RISK_MFA and payload.active_role in HIGH_RISK_ROLES and not user.get("mfa_enabled"):
        raise HTTPException(
            status_code=403,
            detail=f"MFA is required for {payload.active_role}. Sign in as 'admin' first and enable Two-Factor from the Security · 2FA button, then retry.",
        )

    # Wave 7 — MFA gate. If the user has MFA enabled we require an OTP.
    if user.get("mfa_enabled"):
        if not payload.otp_code:
            return {"mfa_required": True, "email": user["email"]}
        import pyotp
        if not pyotp.TOTP(user.get("mfa_secret") or "").verify(payload.otp_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid OTP")

    token = create_admin_token(str(user["_id"]), user["email"], payload.active_role)
    csrf = _set_session_cookies(response, token, request)
    # v52bx — bug #34: nuke stale vendor cookie on staff login too.
    response.delete_cookie("vendor_token", path="/", domain=config.COOKIE_DOMAIN)
    await audit_log("staff.login", {"id": str(user["_id"]), "email": user["email"]},
                    "admin_user", str(user["_id"]), {"active_role": payload.active_role})
    # v47d — security sign-in alert email on every successful login (post-MFA)
    try:
        from notify import login_alert
        await login_alert(user["email"], user.get("name"),
                          f"Staff Portal · {payload.active_role}",
                          ip=request.client.host if request.client else None,
                          user_agent=request.headers.get("user-agent"),
                          user_id=str(user["_id"]))
    except Exception:
        pass
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name"),
        "roles": roles,
        "active_role": payload.active_role,
        "hierarchy_level": user.get("hierarchy_level", 1),
        "csrf_token": csrf,
    }


@router.post("/auth/logout")
async def staff_logout(response: Response, request: Request) -> Dict[str, bool]:
    # Bug #82 fix — nuke ALL three cookie realms (see admin_auth.logout).
    # Clear attributes must match how they were set (context-aware SameSite) or
    # the browser keeps the cookie, which blocks the next login (v54s/v54u).
    cross_site = is_preview_request(request)
    clear_session_cookie(response, "access_token", cross_site)
    clear_session_cookie(response, "vendor_token", cross_site)
    clear_session_cookie(response, "csrf_token", cross_site)
    return {"ok": True}


@router.get("/auth/me")
async def staff_me(admin: Dict[str, Any] = Depends(current_admin)) -> Dict[str, Any]:
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    d = _out(doc)
    d["active_role"] = admin.get("role")
    return d


@router.get("/roles")
async def list_role_choices() -> Dict[str, Any]:
    return {"roles": ALL_STAFF_ROLES}


class SwitchRoleIn(BaseModel):
    active_role: StaffRole


@router.post("/auth/switch-role")
async def switch_role(payload: SwitchRoleIn, response: Response, request: Request,
                       admin: Dict[str, Any] = Depends(current_admin)):
    """v53p — re-issue the staff session JWT with a new active_role so a
    multi-role employee can switch (e.g. Reviewer → Escrow Agent) without
    logging out. The user MUST already hold the requested role on their
    admin_users record; roles themselves are set only by an admin via
    Masters → Staff, so this cannot elevate privileges.
    """
    doc = await db.admin_users.find_one({"_id": ObjectId(admin["id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Staff not found")
    held = doc.get("roles") or ([doc["role"]] if doc.get("role") else [])
    if payload.active_role not in held:
        raise HTTPException(status_code=403,
            detail=f"You do not hold the {payload.active_role} role.")
    HIGH_RISK_ROLES = {"escrow_agent", "legal_counsel", "accounting"}
    if config.REQUIRE_HIGH_RISK_MFA and payload.active_role in HIGH_RISK_ROLES and not doc.get("mfa_enabled"):
        raise HTTPException(status_code=403,
            detail=f"MFA is required for {payload.active_role}. Enable Two-Factor first.")
    token = create_admin_token(str(doc["_id"]), doc["email"], payload.active_role)
    csrf = _set_session_cookies(response, token, request)
    await audit_log("staff.switch_role", admin, "admin_user", admin["id"],
                     {"from": admin.get("role"), "to": payload.active_role})
    return {"active_role": payload.active_role, "csrf_token": csrf,
             "roles": held, "email": doc["email"], "name": doc.get("name")}


# ---------- Staff master (admin-only CRUD) ----------

@router.get("")
async def list_staff(admin=Depends(require_role("admin"))) -> List[dict]:
    return [_out(d) async for d in db.admin_users.find({"tenant_id": admin["tenant_id"]}).sort("email", 1)]


@router.post("")
async def create_staff(payload: StaffCreateIn, admin=Depends(require_role("admin"))) -> dict:
    if await db.admin_users.find_one({"email": payload.email.lower()}):
        raise HTTPException(status_code=409, detail="Email already exists")
    _validate_account_type(payload.account_type, payload.roles)
    from datetime import datetime, timezone
    doc = {
        "email": payload.email.lower(),
        "name": payload.name,
        "password_hash": hash_password(payload.password),
        "roles": payload.roles,
        "role": payload.roles[0],  # legacy compat
        "account_type": payload.account_type,
        "hierarchy_level": payload.hierarchy_level,
        "company_id": payload.company_id,
        "country_scope": payload.country_scope or [],
        "reports_to": payload.reports_to,
        "designation": payload.designation,
        "is_escrow_signatory": bool(payload.is_escrow_signatory),
        "tenant_id": admin["tenant_id"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin["id"],
    }
    res = await db.admin_users.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("staff.create", admin, "admin_user", str(res.inserted_id),
                    {"email": doc["email"], "roles": doc["roles"]})
    return _out(doc)


@router.patch("/{staff_id}")
async def update_staff(staff_id: str, payload: StaffUpdateIn,
                       admin=Depends(require_role("admin"))) -> dict:
    existing = await db.admin_users.find_one({"_id": ObjectId(staff_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    updates = payload.model_dump(exclude_unset=True)
    if "roles" in updates and updates["roles"]:
        updates["role"] = updates["roles"][0]
    # v55 — validate the resulting (account_type, roles) combination so a staff
    # account can never be given admin/reviewer, and an admin account always
    # keeps one. Persist account_type (backfilling legacy records).
    eff_roles = updates.get("roles") or existing.get("roles") or (
        [existing.get("role")] if existing.get("role") else [])
    eff_type = (updates.get("account_type") or existing.get("account_type")
                or ("admin" if (set(eff_roles) & ADMIN_CONSOLE_ROLES) else "staff"))
    _validate_account_type(eff_type, eff_roles)
    updates["account_type"] = eff_type
    # Password reset: hash before persisting, never store raw
    if updates.get("password"):
        updates["password_hash"] = hash_password(updates.pop("password"))
    else:
        updates.pop("password", None)
    r = await db.admin_users.update_one({"_id": ObjectId(staff_id)}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    fresh = await db.admin_users.find_one({"_id": ObjectId(staff_id)})
    # Redact password_hash before audit log
    audit_updates = {k: v for k, v in updates.items() if k != "password_hash"}
    if "password_hash" in updates:
        audit_updates["password_reset"] = True
    await audit_log("staff.update", admin, "admin_user", staff_id, audit_updates)
    return _out(fresh)


# ---------- v56f: PMC-officer escrow signing surface (staff portal) ----------
# A staff member who is the named PMC officer on a joint escrow account needs
# to see — and sign — the EMD escrow document right inside their staff portal
# (not only via the DocuSign email). These endpoints are scoped strictly to the
# transactions where the logged-in staff email == escrow_account_snapshot
# .pmc_officer.email, so an officer can only ever see their own signing work.

def _escrow_tx_row(t: dict) -> dict:
    sigs = t.get("signatures") or {}
    snap = t.get("escrow_account_snapshot") or {}
    return {
        "id": str(t["_id"]),
        "bid_ref": t.get("bid_ref"),
        "notice_ref": t.get("notice_ref"),
        "vendor_ref": t.get("vendor_ref"),
        "amount": t.get("amount"),
        "currency": t.get("currency"),
        "status": t.get("status"),
        "docusign_status": t.get("docusign_status"),
        "docusign_envelope_id": t.get("docusign_envelope_id"),
        "created_at": t.get("created_at"),
        "institution": snap.get("institution"),
        "account_name": snap.get("name"),
        "pmc_officer": snap.get("pmc_officer") or {},
        "escrow_officer": snap.get("escrow_officer") or {},
        "signed_by_pmc": bool((sigs.get("pmc") or {}).get("signed_at")),
        "signed_by_institution": bool((sigs.get("escrow_institution") or {}).get("signed_at")),
        "has_signed_document": bool((t.get("signed_document") or {}).get("content_b64")),
    }


async def _staff_escrow_tx_or_403(tid: str, email: str) -> dict:
    if not ObjectId.is_valid(tid):
        raise HTTPException(status_code=400, detail="Invalid transaction id")
    tx = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    pmc_email = (((tx.get("escrow_account_snapshot") or {}).get("pmc_officer") or {})
                 .get("email") or "").lower()
    if pmc_email != (email or "").lower():
        raise HTTPException(status_code=403,
            detail="You are not the PMC officer on this escrow transaction.")
    return tx


@router.get("/escrow/signatures")
async def staff_escrow_signatures(admin=Depends(current_admin)) -> Dict[str, Any]:
    email = (admin.get("email") or "").lower()
    pending: List[dict] = []
    transactions: List[dict] = []
    if email:
        cur = db.escrow_transactions.find(
            {"escrow_account_snapshot.pmc_officer.email":
                {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
        ).sort("created_at", -1).limit(200)
        done = {"cancelled", "forfeited", "released_to_vendor", "released_to_contractor"}
        async for t in cur:
            row = _escrow_tx_row(t)
            transactions.append(row)
            if (t.get("docusign_envelope_id") and not row["signed_by_pmc"]
                    and t.get("status") not in done):
                pending.append(row)
    return {"email": email,
            "pending_signatures": pending,
            "pending_signatures_count": len(pending),
            "transactions": transactions,
            "transactions_count": len(transactions)}


@router.get("/escrow/transactions/{tid}")
async def staff_escrow_transaction(tid: str, admin=Depends(current_admin)) -> Dict[str, Any]:
    tx = await _staff_escrow_tx_or_403(tid, admin.get("email"))
    env = None
    env_id = tx.get("docusign_envelope_id")
    if env_id:
        row = await db.docusign_envelopes.find_one({"envelope_id": env_id})
        if row:
            env = {"envelope_id": env_id, "status": row.get("status"),
                   "signers": row.get("signers") or [], "created_at": row.get("created_at")}
    out = _escrow_tx_row(tx)
    out["audit_trail"] = tx.get("audit_trail") or []
    out["signatures"] = tx.get("signatures") or {}
    out["docusign_envelope"] = env
    return out


@router.get("/escrow/transactions/{tid}/docusign-url")
async def staff_escrow_docusign_url(tid: str, admin=Depends(current_admin)) -> Dict[str, Any]:
    tx = await _staff_escrow_tx_or_403(tid, admin.get("email"))
    env_id = tx.get("docusign_envelope_id")
    if not env_id:
        raise HTTPException(status_code=404,
            detail="PMC admin has not issued a DocuSign envelope for this "
                   "transaction yet.")
    try:
        from routers.docusign import create_escrow_recipient_view
        url = await create_escrow_recipient_view(
            env_id, "pmc", f"{config.FRONTEND_URL}/staff?signed=1")
        return {"url": url, "envelope_id": env_id, "mode": "recipient"}
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("escrow").info("staff docusign recipient-view fallback %s: %s", env_id, e)
        return {"url": None, "envelope_id": env_id, "mode": "email_only",
                "message": "In-app signing could not be opened. Ask PMC admin to "
                           "re-issue the DocuSign envelope so you get an embedded "
                           "signing session."}


@router.post("/escrow/transactions/{tid}/docusign/refresh")
async def staff_escrow_refresh(tid: str, admin=Depends(current_admin)) -> Dict[str, Any]:
    tx = await _staff_escrow_tx_or_403(tid, admin.get("email"))
    env_id = tx.get("docusign_envelope_id")
    if not env_id:
        raise HTTPException(status_code=404, detail="No DocuSign envelope on this transaction")
    try:
        import docusign_esign as ds
        from routers.docusign import _client, DS_ACCOUNT_ID, _apply_live_status
        client = _client()
        envelopes = ds.EnvelopesApi(client)
        live = envelopes.get_envelope(DS_ACCOUNT_ID, env_id)
        live_status = (live.status or "").lower()
        await _apply_live_status(env_id, live_status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read DocuSign status: {e}")
    fresh = await db.escrow_transactions.find_one({"_id": ObjectId(tid)})
    return {"ok": True, "status": live_status, **_escrow_tx_row(fresh)}


@router.get("/escrow/transactions/{tid}/signed-document")
async def staff_escrow_signed_document(tid: str, admin=Depends(current_admin)) -> Dict[str, Any]:
    tx = await _staff_escrow_tx_or_403(tid, admin.get("email"))
    doc = tx.get("signed_document") or {}
    if not doc.get("content_b64"):
        raise HTTPException(status_code=404,
            detail="Signed document not available yet. Click Refresh after both "
                   "officers have signed in DocuSign.")
    return {"filename": doc.get("filename"),
            "content_b64": doc.get("content_b64"),
            "content_type": doc.get("content_type") or "application/pdf"}
