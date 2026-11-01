"""Onboarding agents: admin invite → agent sets password → escrow-style KYC wizard → agreement → admin review."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator

import config
from audit import audit_log
from db import db
from emails import send_email, wrap
from models.base import now_iso
from security import csrf_for_session, hash_password, require_csrf, require_role, set_csrf_cookie, verify_password

router = APIRouter(tags=["agents"])
ADMIN = Depends(require_role("admin"))
CSRF = [Depends(require_csrf)]
COOKIE = "agent_token"
EDITABLE = {"draft", "needs_clarification"}
AGREEMENT_VERSION = "2026-10-v1"
CONSENT_KEYS = ["supplier_consent", "data_privacy", "confidentiality", "indemnity", "anti_bribery", "accuracy"]
AGREEMENT = [
    ("Role", "You introduce and help suppliers register on PMC Managers. You act for yourself as an independent agent, not as PMC's employee, partner or legal representative."),
    ("Supplier consent", "Before entering any detail or uploading any document for a supplier, you will obtain that supplier's informed written consent. The supplier must also approve the PMC consent request sent to them before their registration is submitted."),
    ("Data privacy", "You will collect, use and store supplier information only to complete their PMC registration, keep it secure, never sell or share it, and delete your own copies when no longer needed, in line with applicable data-protection law."),
    ("Confidentiality (NDA)", "Everything you learn about PMC, its suppliers, buyers, tenders and pricing is confidential. You will not disclose or use it for any other purpose, during or after your engagement."),
    ("Responsibility and indemnity", "You are solely responsible for your own acts and omissions. You will indemnify PMC Managers against any loss, claim or penalty caused by your negligence, misconduct, misrepresentation or breach of these terms. PMC is not liable for your conduct. Information and documents supplied by a supplier remain that supplier's responsibility."),
    ("Anti-bribery and conduct", "You will not offer, pay or accept any bribe or improper benefit, will not promise any tender outcome, and will not misrepresent PMC's services."),
    ("Commission", "Any commission is set by PMC admin in writing and paid by PMC from its own account. No commission is due for registrations that are rejected, withdrawn or found to be improper."),
    ("Termination", "PMC may suspend or end your access at any time if these terms are breached. The confidentiality, data-privacy and indemnity clauses survive termination."),
]
PROFILE_FIELDS = {"entity_type", "legal_name", "trading_name", "country", "registered_address", "address_line1", "address_line2",
                  "city", "state_code", "state_name", "postal_code", "reg_number", "tax_id", "gst_or_vat", "regulator",
                  "licence_number", "licence_expiry", "website", "primary_contact_email", "primary_contact_phone",
                  "phone_country_code", "mobile_phone", "office_phone", "banking", "documents", "id_number", "date_of_birth"}


def _site() -> str:
    return config.FRONTEND_URL.rstrip("/")


def _client_ip(request: Request) -> str:
    """Rightmost X-Forwarded-For hop is the one appended by our ingress (not client-controlled)."""
    xff = [p.strip() for p in (request.headers.get("x-forwarded-for") or "").split(",") if p.strip()]
    return xff[-1] if xff else (request.client.host if request.client else "")


def _public(a: dict) -> dict:
    a = dict(a)
    a["id"] = str(a.pop("_id"))
    for k in ("password_hash", "invite_token", "token_generation"):
        a.pop(k, None)
    return a


def _jwt(a: dict) -> str:
    return jwt.encode({"sub": str(a["_id"]), "email": a["email"], "type": "agent_access", "gen": int(a.get("token_generation") or 0),
                       "exp": datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN)},
                      config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _set_cookies(response: Response, a: dict) -> str:
    max_age = config.ACCESS_TOKEN_TTL_MIN * 60
    ck = {"httponly": True, "secure": True, "samesite": "lax", "max_age": max_age, "path": "/"}
    if config.COOKIE_DOMAIN:
        ck["domain"] = config.COOKIE_DOMAIN
    response.set_cookie(COOKIE, _jwt(a), **ck)
    for other in ("access_token", "vendor_token", "escrow_account_token", "escrow_sig_token"):
        response.delete_cookie(other, path="/", domain=config.COOKIE_DOMAIN)
    csrf = csrf_for_session(f"agent:{a['_id']}")
    set_csrf_cookie(response, csrf, max_age)
    return csrf


async def current_agent(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        p = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if p.get("type") != "agent_access":
        raise HTTPException(status_code=401, detail="Invalid token")
    a = await db.agents.find_one({"_id": ObjectId(p["sub"])})
    if not a or int(p.get("gen") or 0) < int(a.get("token_generation") or 0) or a.get("status") in ("invited", "suspended"):
        raise HTTPException(status_code=401, detail="Session revoked")
    return a


# ---------- admin ----------

class InviteIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)


class DecisionIn(BaseModel):
    action: Literal["approve", "reject", "clarify", "suspend", "request_payment"]
    note: str = Field("", max_length=2000)
    waive_fee: bool = False


def _oid(aid: str) -> ObjectId:
    if not ObjectId.is_valid(aid):
        raise HTTPException(status_code=404, detail="Agent not found")
    return ObjectId(aid)


async def _send_invite(a: dict) -> bool:
    link = f"{_site()}/partner/join/{a['invite_token']}"
    body = (f"<p>Hello {a['name']},</p><p>Please confirm your email to join PMC Managers as a partner. Use the button below to create your "
            f"password and complete your partner profile, banking details, identity documents and the partner agreement.</p>"
            f"<p>This link expires in 7 days. If you did not request this, ignore this email.</p>")
    return await send_email(a["email"], "[PMC] Confirm your email to become a PMC partner", wrap("Join PMC as a partner", body, "Confirm email & continue", link))


async def _send_reminder(a: dict) -> bool:
    body = (f"<p>Hello {a.get('legal_name') or a['name']},</p><p>Your PMC partner account is set up but your profile is not finished yet. "
            f"Sign in with this email and the password you created to add your details, banking, identity documents and sign the partner agreement, "
            f"then submit it for review.</p><p>Forgotten your password? Use <b>Forgot password</b> on the sign-in page.</p>")
    return await send_email(a["email"], "[PMC] Please complete your PMC partner profile", wrap("Finish your partner profile", body, "Sign in", f"{_site()}/login"))


async def _nudge(a: dict, admin: dict) -> dict:
    """Re-send whatever the partner needs next: a fresh invite link, or a finish-your-profile reminder."""
    from emails import last_error
    if a["status"] == "invited":
        upd = {"invite_token": secrets.token_urlsafe(32), "invite_expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()}
        await db.agents.update_one({"_id": a["_id"]}, {"$set": upd})
        sent, kind = await _send_invite({**a, **upd}), "invitation"
    elif a["status"] in EDITABLE:
        sent, kind = await _send_reminder(a), "reminder"
    else:
        raise HTTPException(status_code=409, detail=f"This partner is already {a['status'].replace('_', ' ')} — nothing to resend")
    await audit_log(f"agent.{kind}_resent", admin, "agent", str(a["_id"]), {"email": a["email"]})
    return {"email_sent": sent, "kind": kind, "email_error": "" if sent else last_error(a["email"])}


@router.post("/api/v1/admin/agents/invite", dependencies=CSRF)
async def invite_agent(body: InviteIn, admin=ADMIN):
    email = body.email.lower().strip()
    existing = await db.agents.find_one({"email": email, "status": {"$ne": "rejected"}})
    if existing:
        if existing["status"] == "invited" or existing["status"] in EDITABLE:
            return {**_public(existing), **(await _nudge(existing, admin)), "existing": True}
        raise HTTPException(status_code=409, detail=f"{email} is already a partner (status: {existing['status'].replace('_', ' ')}). Open their card below.")
    a = {"email": email, "name": body.name.strip(), "status": "invited", "invite_token": secrets.token_urlsafe(32),
         "invite_expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(), "invited_by": admin.get("email"),
         "created_at": now_iso(), "banking": [], "documents": {}, "history": []}
    a["_id"] = (await db.agents.insert_one(a)).inserted_id
    sent = await _send_invite(a)
    await audit_log("agent.invited", admin, "agent", str(a["_id"]), {"email": email})
    from emails import last_error
    return {**_public(a), "email_sent": sent, "email_error": "" if sent else last_error(email)}


@router.post("/api/v1/admin/agents/{aid}/resend", dependencies=CSRF)
async def resend_invite(aid: str, admin=ADMIN):
    a = await db.agents.find_one({"_id": _oid(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await _nudge(a, admin)


ADMIN_EDITABLE = {"name", "legal_name", "trading_name", "entity_type", "primary_contact_phone", "country", "city",
                  "address_line1", "address_line2", "postal_code", "reg_number", "tax_id", "website"}


@router.patch("/api/v1/admin/agents/{aid}/profile", dependencies=CSRF)
async def admin_edit_agent(aid: str, body: Dict[str, Any], admin=ADMIN):
    a = await db.agents.find_one({"_id": _oid(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    if a["status"] == "rejected":
        raise HTTPException(status_code=409, detail="A rejected partner can't be edited")
    raw = dict(body)
    data = {k: (str(v).strip()[:500] if v is not None else None) for k, v in raw.items()
            if (k in ADMIN_EDITABLE or k in PROFILE_FIELDS) and k not in ("banking", "documents", "primary_contact_email")}
    if raw.get("banking") is not None:
        data["banking"] = [{k: (str(v).strip()[:200] if v is not None else None) for k, v in b.items()}
                           for b in raw["banking"] if isinstance(b, dict)][:5]
    if raw.get("documents") is not None:
        data["documents"] = {k: v for k, v in raw["documents"].items() if isinstance(v, dict) and str(v.get("key", "")).startswith("agent-docs/")}
        keys = [v["key"] for v in data["documents"].values()]
        await db.uploads.update_many({"key": {"$in": keys}, "owner_agent_id": None}, {"$set": {"owner_agent_id": str(a["_id"])}})
    if data.get("entity_type") not in (None, "individual", "company"):
        raise HTTPException(status_code=422, detail="Type must be individual or company")
    if data.get("country"):
        data["country"] = data["country"].upper()
    if not data:
        raise HTTPException(status_code=422, detail="Nothing to update")
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {**data, "updated_at": now_iso()},
                                                  "$push": {"history": {"action": "admin_edit", "fields": sorted(data), "by": admin.get("email"), "at": now_iso()}}})
    await audit_log("agent.admin_edit", admin, "agent", aid, {"fields": sorted(data)})
    return _public(await db.agents.find_one({"_id": a["_id"]}))


@router.get("/api/v1/admin/agents")
async def list_agents(admin=ADMIN):
    rows = await db.agents.find({}, {"password_hash": 0, "invite_token": 0}).sort("created_at", -1).to_list(500)
    return {"items": [_public(r) for r in rows]}


@router.get("/api/v1/admin/agents/{aid}")
async def get_agent(aid: str, admin=ADMIN):
    a = await db.agents.find_one({"_id": _oid(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _public(a)


@router.post("/api/v1/admin/agents/{aid}/decision", dependencies=CSRF)
async def decide_agent(aid: str, body: DecisionIn, admin=ADMIN):
    a = await db.agents.find_one({"_id": _oid(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    allowed = {"approve": {"submitted", "payment_pending"}, "reject": {"submitted", "needs_clarification", "payment_pending"}, "clarify": {"submitted"},
               "suspend": {"approved"}, "request_payment": {"submitted", "payment_pending"}}[body.action]
    if a["status"] not in allowed:
        raise HTTPException(status_code=409, detail=f"Cannot {body.action} a partner whose status is {a['status']}")
    if body.action == "approve" and not body.waive_fee:
        raise HTTPException(status_code=409, detail="Tick 'Waive registration fee' to approve now, or send a payment request")
    if body.action == "request_payment":
        return await _request_payment(a, admin)
    if body.action in ("reject", "clarify") and not body.note.strip():
        raise HTTPException(status_code=422, detail="Add a note explaining what the agent must fix or why")
    new = {"approve": "approved", "reject": "rejected", "clarify": "needs_clarification", "suspend": "suspended"}[body.action]
    entry = {"action": body.action, "note": body.note.strip(), "by": admin.get("email"), "at": now_iso(),
             **({"fee_waived": True} if body.action == "approve" else {})}
    extra = {"fee_waived": True, **(await _code_for(a))} if new == "approved" else {}
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"status": new, "reviewed_at": now_iso(), **extra}, "$push": {"history": entry},
                                                  **({"$inc": {"token_generation": 1}} if new == "suspended" else {})})
    await audit_log(f"agent.{body.action}", admin, "agent", aid, {"note": body.note.strip()})
    msg = {"approved": "Your PMC partner profile has been approved. You can now sign in to your partner portal.",
           "rejected": "Your PMC partner application was not approved.",
           "needs_clarification": "PMC needs a few changes to your partner profile. Please sign in and update it.",
           "suspended": "Your PMC partner access has been suspended."}[new]
    note = f"<p><b>Note from PMC:</b> {body.note.strip()}</p>" if body.note.strip() else ""
    await send_email(a["email"], f"[PMC] Partner application: {new.replace('_', ' ')}",
                     wrap("Partner application update", f"<p>{msg}</p>{note}", "Open partner portal", f"{_site()}/partner/login"))
    return {"status": new}


async def _code_for(a: dict) -> dict:
    from db import next_sequence
    return {} if a.get("partner_code") else {"partner_code": f"PT-{await next_sequence('partner_code'):04d}"}


async def _request_payment(a: dict, admin: dict) -> dict:
    from routers._fees import compute_amount, find_rule
    from routers.payments_extra import _checkout
    rule = await find_rule("partner_registration", a.get("country"))
    amount = compute_amount(rule, None) if rule else None
    if not rule or not amount:
        raise HTTPException(status_code=422, detail=f"No active 'Partner registration' fee rule covers {a.get('country') or 'this country'} — add one in Fee Rules, or waive the fee")
    cur = (rule.get("currency") or "USD").upper()
    chk = await _checkout(amount, cur, "partner_fee", "/partner/me?paid=1", "/partner/me", _site(),
                          {"agent_id": str(a["_id"])}, {"agent_id": str(a["_id"]), "payer_email": a["email"], "rule_id": str(rule["_id"])})
    pay = {"amount": float(amount), "currency": cur, "checkout_url": chk["checkout_url"], "session_id": chk["session_id"],
           "rule_id": str(rule["_id"]), "requested_at": now_iso(), "requested_by": admin.get("email"), "status": "pending"}
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"status": "payment_pending", "payment": pay},
        "$push": {"history": {"action": "request_payment", "note": f"{cur} {amount:,.2f}", "by": admin.get("email"), "at": now_iso()}}})
    await audit_log("agent.payment_requested", admin, "agent", str(a["_id"]), {"amount": amount, "currency": cur})
    sent = await send_email(a["email"], "[PMC] Partner registration fee",
        wrap("Your partner registration fee", f"<p>Your partner profile has been reviewed. Please pay the partner registration fee of "
             f"<b>{cur} {amount:,.2f}</b> to activate your account. You can also pay from your partner portal.</p>", "Pay securely", chk["checkout_url"]))
    return {"status": "payment_pending", "payment": pay, "email_sent": sent}


async def apply_partner_payment(session_id: str) -> None:
    a = await db.agents.find_one({"payment.session_id": session_id})
    if not a or (a.get("payment") or {}).get("status") == "paid":
        return
    pay = a["payment"]
    upd = {"status": "approved", "payment.status": "paid", "payment.paid_at": now_iso(), "reviewed_at": now_iso(), **(await _code_for(a))}
    await db.agents.update_one({"_id": a["_id"], "payment.status": {"$ne": "paid"}}, {"$set": upd})
    await audit_log("agent.payment_received", None, "agent", str(a["_id"]), {"session_id": session_id})
    att = None
    try:
        import asyncio
        import base64
        from routers.site_settings import render_receipt_pdf
        rec = {"receipt_no": f"PMC-PR-{session_id[-8:].upper()}", "purpose": "partner_registration", "currency": pay["currency"],
               "lines": [{"name": "Partner registration fee", "amount": pay["amount"]}], "total": pay["amount"],
               "session_id": session_id, "paid_at": now_iso()}
        pdf = await asyncio.to_thread(render_receipt_pdf, rec, {"company_name": a.get("legal_name") or a["name"],
                                                                "vendor_ref": upd.get("partner_code") or a.get("partner_code"), "email": a["email"]})
        att = [{"filename": f"{rec['receipt_no']}.pdf", "content_b64": base64.b64encode(pdf).decode(), "content_type": "application/pdf"}]
    except Exception:
        import logging
        logging.getLogger(__name__).exception("partner receipt pdf failed for %s", session_id)
    await send_email(a["email"], "[PMC] Payment received — your partner account is active",
                     wrap("Welcome, PMC partner", f"<p>We received your partner registration fee. Your partner code is "
                          f"<b>{upd.get('partner_code') or a.get('partner_code')}</b>. Your receipt is attached.</p>",
                          "Open partner portal", f"{_site()}/partner/me"), attachments=att)


@router.post("/api/v1/agents/me/payment/refresh", dependencies=CSRF)
async def refresh_payment(request: Request):
    a = await current_agent(request)
    pay = a.get("payment") or {}
    if a["status"] == "payment_pending" and pay.get("session_id"):
        import os
        from pmc_lib.payments.stripe.checkout import StripeCheckout
        try:
            st = await StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url="").get_checkout_status(pay["session_id"])
            if st.payment_status == "paid":
                await db.payment_transactions.update_one({"session_id": pay["session_id"]},
                    {"$set": {"payment_status": "paid", "status": "completed", "updated_at": now_iso()}})
                await apply_partner_payment(pay["session_id"])
        except Exception:
            pass
    return _public(await db.agents.find_one({"_id": a["_id"]}))


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    country: Optional[str] = Field(default=None, min_length=2, max_length=3)


@router.post("/api/v1/agents/register")
async def self_register(body: RegisterIn, request: Request):
    ip = _client_ip(request)
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if await db.agent_login_attempts.count_documents({"identifier": f"reg:{ip}", "at": {"$gte": since}}) >= 5:
        raise HTTPException(status_code=429, detail="Too many sign-ups from this network. Try again later.")
    await db.agent_login_attempts.insert_one({"identifier": f"reg:{ip}", "at": now_iso()})
    email = body.email.lower().strip()
    country = (body.country or "").upper().strip() or None
    a = await db.agents.find_one({"email": email, "status": {"$ne": "rejected"}})
    if a and a["status"] == "invited":
        upd = {"country": a.get("country") or country, "invite_token": secrets.token_urlsafe(32), "invite_expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()}
        await db.agents.update_one({"_id": a["_id"]}, {"$set": upd})
        await _send_invite({**a, **upd})
    elif not a:
        a = {"email": email, "name": body.name.strip(), "country": country, "status": "invited", "invite_token": secrets.token_urlsafe(32), "source": "self",
             "invite_expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(), "created_at": now_iso(),
             "banking": [], "documents": {}, "history": []}
        a["_id"] = (await db.agents.insert_one(a)).inserted_id
        await _send_invite(a)
    return {"ok": True, "message": "If this email can be used, we've sent a confirmation link to it."}


# ---------- agent self-service ----------

class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AgreementIn(BaseModel):
    signer_name: str = Field(min_length=3, max_length=120)
    consents: Dict[str, bool]

    @field_validator("signer_name")
    @classmethod
    def _s(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Type your full name")
        return v.strip()


class ProfileIn(BaseModel):
    model_config = {"extra": "allow"}
    entity_type: Optional[Literal["individual", "company"]] = None
    banking: Optional[List[dict]] = None
    documents: Optional[dict] = None


@router.get("/api/v1/agents/agreement")
async def agreement_text():
    return {"version": AGREEMENT_VERSION, "sections": [{"title": t, "text": x} for t, x in AGREEMENT], "consent_keys": CONSENT_KEYS}


async def _by_invite(token: str) -> dict:
    a = await db.agents.find_one({"invite_token": token, "status": "invited"})
    if not a or a.get("invite_expires_at", "") < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=404, detail="This invitation link is invalid or has expired. Ask PMC to resend it.")
    return a


@router.get("/api/v1/agents/join/{token}")
async def join_info(token: str):
    a = await _by_invite(token)
    return {"email": a["email"], "name": a["name"]}


@router.post("/api/v1/agents/join/{token}")
async def join(token: str, body: PasswordIn, response: Response):
    a = await _by_invite(token)
    upd = {"password_hash": hash_password(body.password), "status": "draft", "joined_at": now_iso(), "invite_token": None,
           "primary_contact_email": a["email"], "legal_name": a.get("legal_name") or a["name"]}
    await db.agents.update_one({"_id": a["_id"]}, {"$set": upd})
    a.update(upd)
    await audit_log("agent.joined", None, "agent", str(a["_id"]), {"email": a["email"]})
    return {**_public(a), "csrf_token": _set_cookies(response, a)}


@router.post("/api/v1/agents/auth/login")
async def agent_login(body: LoginIn, response: Response, request: Request):
    email = body.email.lower().strip()
    ident = f"email:{email}"
    since = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    if await db.agent_login_attempts.count_documents({"identifier": ident, "at": {"$gte": since}}) >= 5:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    a = await db.agents.find_one({"email": email, "status": {"$nin": ["invited", "rejected"]}})
    if not a or not verify_password(body.password, a.get("password_hash") or ""):
        await db.agent_login_attempts.insert_one({"identifier": ident, "at": now_iso()})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if a["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Your agent access is suspended. Contact PMC.")
    await db.agent_login_attempts.delete_many({"identifier": ident})
    return {**_public(a), "csrf_token": _set_cookies(response, a)}


@router.post("/api/v1/agents/auth/logout")
async def agent_logout(response: Response):
    for name in (COOKIE, "csrf_token"):
        response.delete_cookie(name, path="/", domain=config.COOKIE_DOMAIN)
    return {"ok": True}


@router.get("/api/v1/agents/me")
async def agent_me(request: Request):
    a = await current_agent(request)
    return {**_public(a), "csrf_token": csrf_for_session(f"agent:{a['_id']}")}


@router.patch("/api/v1/agents/me/profile", dependencies=CSRF)
async def agent_profile(body: ProfileIn, request: Request):
    a = await current_agent(request)
    if a["status"] not in EDITABLE:
        raise HTTPException(status_code=409, detail="Your profile is locked while PMC reviews it")
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in PROFILE_FIELDS}
    if "primary_contact_email" in data and str(data["primary_contact_email"]).lower().strip() != a["email"]:
        raise HTTPException(status_code=422, detail="Your sign-in email cannot be changed here")
    if data.get("banking") is not None:
        data["banking"] = [b for b in data["banking"] if isinstance(b, dict)][:5]
    if data.get("documents") is not None:
        data["documents"] = {k: v for k, v in data["documents"].items() if isinstance(v, dict) and str(v.get("key", "")).startswith("agent-docs/")}
    data["updated_at"] = now_iso()
    await db.agents.update_one({"_id": a["_id"]}, {"$set": data})
    return _public(await db.agents.find_one({"_id": a["_id"]}))


@router.post("/api/v1/agents/me/agreement", dependencies=CSRF)
async def sign_agreement(body: AgreementIn, request: Request):
    a = await current_agent(request)
    if a["status"] not in EDITABLE:
        raise HTTPException(status_code=409, detail="Your profile is locked while PMC reviews it")
    if not all(body.consents.get(k) for k in CONSENT_KEYS):
        raise HTTPException(status_code=422, detail="Please tick every statement to sign the agreement")
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (request.client.host if request.client else None)
    sig = {"version": AGREEMENT_VERSION, "signer_name": body.signer_name, "consents": {k: True for k in CONSENT_KEYS},
           "signed_at": now_iso(), "ip": ip, "user_agent": (request.headers.get("user-agent") or "")[:200]}
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"agreement": sig}})
    await audit_log("agent.agreement_signed", {"id": str(a["_id"]), "email": a["email"]}, "agent", str(a["_id"]),
                    {"version": AGREEMENT_VERSION, "signer_name": body.signer_name})
    return {"agreement": sig}


def required_docs(entity_type: str) -> list:
    base = ["id_proof", "address_proof", "bank_proof"]
    return base + (["incorporation_certificate", "tax_registration", "authority_letter"] if entity_type == "company" else [])


@router.post("/api/v1/agents/me/submit", dependencies=CSRF)
async def agent_submit(request: Request):
    a = await current_agent(request)
    if a["status"] not in EDITABLE:
        raise HTTPException(status_code=409, detail="Already submitted")
    et = a.get("entity_type") or "individual"
    missing = [label for k, label in (("legal_name", "name"), ("country", "country"), ("address_line1", "address"), ("city", "city"),
                                      ("primary_contact_phone", "phone")) if not a.get(k)]
    if et == "company" and not a.get("reg_number"):
        missing.append("company registration number")
    if not any((b.get("account_name") and (b.get("account_number") or b.get("iban"))) for b in a.get("banking") or []):
        missing.append("bank account (name and number/IBAN)")
    docs = a.get("documents") or {}
    missing += [f"document: {d.replace('_', ' ')}" for d in required_docs(et) if not (docs.get(d) or {}).get("key")]
    if not (a.get("agreement") or {}).get("version") == AGREEMENT_VERSION:
        missing.append("signed agent agreement")
    if missing:
        raise HTTPException(status_code=422, detail="Still missing: " + ", ".join(missing))
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"status": "submitted", "submitted_at": now_iso()}})
    await audit_log("agent.submitted", {"id": str(a["_id"]), "email": a["email"]}, "agent", str(a["_id"]), {})
    async for adm in db.admin_users.find({"role": "admin", "status": {"$ne": "disabled"}}, {"email": 1}).limit(5):
        await send_email(adm["email"], "[PMC] Onboarding agent submitted for review",
                         wrap("Partner ready for review", f"<p>{a.get('legal_name') or a['name']} ({a['email']}) submitted their partner profile.</p>"
                              "<p>The button opens the admin console — sign in as Administrator if asked, and you'll go straight to Partners.</p>",
                              "Review partners", f"{_site()}/admin/e/partners"))
    return {"status": "submitted"}


async def ensure_indexes() -> None:
    await db.agents.create_index("email")
    await db.agents.create_index("invite_token", sparse=True)
    await db.agent_login_attempts.create_index("identifier")
