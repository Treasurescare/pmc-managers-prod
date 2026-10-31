"""Partner-led supplier onboarding (invite → supplier consent → partner fills → supplier submits) + commission wallet."""
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

import config
from audit import audit_log
from db import db
from emails import send_email, wrap
from models.base import now_iso
from routers.agents import current_agent
from security import new_magic_token, require_csrf, require_role

router = APIRouter(tags=["partner-suppliers"])
ADMIN = Depends(require_role("admin"))
CSRF = [Depends(require_csrf)]
CLAIM_DAYS = 30
ACTIVE = ["draft", "submitted", "under_review", "needs_clarification"]
PARTNER_BLOCKED_PREFIXES = ("decl_", "signature_")
CONSENT_VERSION = "2026-11-v1"
CONSENT = [
    ("partner_help", "I allow this PMC partner to enter my company details and upload my documents on my behalf, only to complete my PMC supplier registration."),
    ("my_review", "I will review everything the partner enters. Nothing is submitted to PMC until I submit it myself."),
    ("data_privacy", "I consent to PMC and the partner processing my company and personal data for my registration, in line with PMC's privacy policy."),
    ("confidentiality", "The partner must keep my information confidential and use it for no other purpose."),
    ("my_responsibility", "The information and documents in my registration are my responsibility. PMC and the partner are not liable for information I provide or approve."),
    ("can_revoke", "I can remove the partner's access at any time before I submit."),
]


def _site() -> str:
    return config.FRONTEND_URL.rstrip("/")


def _ago(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _oid(x: str) -> ObjectId:
    if not ObjectId.is_valid(x):
        raise HTTPException(status_code=404, detail="Not found")
    return ObjectId(x)


async def _approved_partner(request: Request) -> dict:
    a = await current_agent(request)
    if a.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Only approved partners can onboard suppliers")
    return a


def _supplier_row(r: dict) -> dict:
    return {"id": str(r["_id"]), "company_name": r.get("company_name"), "email": r.get("email"), "mobile": r.get("contact_mobile"),
            "status": r.get("status"), "partner_access": r.get("partner_access"), "partner_stage": r.get("partner_stage"),
            "invited_at": r.get("partner_invited_at"), "consent_at": (r.get("partner_consent") or {}).get("at"),
            "vendor_ref": r.get("vendor_ref"), "claim_expires_at": r.get("partner_claim_expires_at"),
            "edits": len(r.get("partner_edits") or [])}


# ---------- token resolution used by registrations.py ----------

async def resolve_reg_token(token: str, request: Request, extra: Optional[dict] = None) -> tuple:
    """Return (registration, editor) where editor is 'supplier' (magic token) or 'partner' (partner edit token + partner cookie)."""
    q = dict(extra or {})
    reg = await db.registrations.find_one({**q, "magic_token": token})
    if reg:
        return reg, "supplier"
    reg = await db.registrations.find_one({**q, "partner_edit_token": token, "partner_access": "granted"})
    if not reg:
        return None, None
    try:
        a = await current_agent(request)
    except HTTPException:
        return None, None
    if str(a["_id"]) != reg.get("partner_id") or a.get("status") != "approved":
        return None, None
    return reg, "partner"


def strip_partner_fields(updates: dict) -> dict:
    return {k: v for k, v in updates.items() if not k.startswith(PARTNER_BLOCKED_PREFIXES)}


async def record_partner_edit(reg: dict, fields: list) -> None:
    entry = {"at": now_iso(), "fields": sorted(fields)[:80], "partner_code": reg.get("partner_code")}
    await db.registrations.update_one({"_id": reg["_id"]}, {"$push": {"partner_edits": {"$each": [entry], "$slice": -200}},
                                                              "$addToSet": {"partner_fields": {"$each": entry["fields"]}}})
    await audit_log("registration.partner_update", {"id": reg.get("partner_id"), "email": reg.get("partner_code")},
                    "registration", str(reg["_id"]), {"fields": entry["fields"]})


def partner_view(reg: dict) -> dict:
    if not reg.get("partner_id"):
        return {}
    return {"partner": {"name": reg.get("partner_name"), "code": reg.get("partner_code"), "access": reg.get("partner_access"),
                        "stage": reg.get("partner_stage"), "fields": reg.get("partner_fields") or [],
                        "last_edit_at": ((reg.get("partner_edits") or [{}])[-1]).get("at")}}


# ---------- partner: invite & manage suppliers ----------

class SupplierInviteIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    mobile: str = Field(min_length=6, max_length=25)


async def _send_supplier_invite(reg: dict) -> bool:
    link = f"{_site()}/supplier-invite/{reg['partner_consent_token']}"
    body = (f"<p>Hello,</p><p><b>{reg['partner_name']}</b> (PMC partner code <b>{reg['partner_code']}</b>) has offered to help "
            f"<b>{reg['company_name']}</b> register as a supplier on PMC Managers.</p>"
            f"<p>Please confirm this email address and decide whether you allow this partner to fill in your registration. "
            f"Nothing is sent to PMC until you review and submit it yourself. If you don't know this partner, ignore this email.</p>"
            f"<p>This link expires in 7 days.</p>")
    return await send_email(reg["email"], f"[PMC] {reg['partner_name']} invited {reg['company_name']} to register on PMC",
                            wrap("Supplier registration invitation", body, "Review & give consent", link))


async def _dup_check(email: str, company: str, partner_id: str) -> None:
    if await db.vendors.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="This email already belongs to a registered PMC supplier")
    if await db.vendors.find_one({"company_name": {"$regex": f"^{re.escape(company)}$", "$options": "i"}}):
        raise HTTPException(status_code=409, detail="A supplier with this company name is already registered on PMC")
    reg = await db.registrations.find_one({"email": email, "status": {"$in": ACTIVE}})
    if not reg:
        return
    if reg.get("partner_id") == partner_id:
        raise HTTPException(status_code=409, detail="You have already invited this supplier — use Resend in your list")
    if reg.get("partner_id") and reg.get("partner_access") not in ("declined", "revoked") and reg.get("partner_claim_expires_at", "") > now_iso():
        raise HTTPException(status_code=409, detail="Another partner is already working with this supplier. Contact PMC if you think this is wrong.")
    raise HTTPException(status_code=409, detail="This supplier has already started a PMC registration. Contact PMC to be linked to it.")


@router.post("/api/v1/agents/me/suppliers", dependencies=CSRF)
async def invite_supplier(body: SupplierInviteIn, request: Request):
    a = await _approved_partner(request)
    email, company = body.email.lower().strip(), body.company_name.strip()
    await _dup_check(email, company, str(a["_id"]))
    reg = {"email": email, "company_name": company, "contact_email": email, "contact_mobile": body.mobile.strip(),
           "status": "draft", "tenant_id": config.DEFAULT_TENANT_ID, "magic_token": new_magic_token(), "created_at": now_iso(),
           "data_processing_consent": False, "marketing_consent": False, "consent_at": None,
           "partner_id": str(a["_id"]), "partner_code": a.get("partner_code"), "partner_name": a.get("legal_name") or a["name"],
           "partner_access": "awaiting_consent", "partner_stage": "invited", "partner_invited_at": now_iso(),
           "partner_consent_token": secrets.token_urlsafe(32), "partner_consent_expires_at": _ago(7),
           "partner_claim_expires_at": _ago(CLAIM_DAYS), "partner_edits": [], "partner_fields": []}
    reg["_id"] = (await db.registrations.insert_one(reg)).inserted_id
    sent = await _send_supplier_invite(reg)
    await audit_log("partner.supplier_invited", {"id": str(a["_id"]), "email": a["email"]}, "registration", str(reg["_id"]),
                    {"email": email, "company_name": company, "partner_code": a.get("partner_code")})
    return {**_supplier_row(reg), "email_sent": sent}


@router.get("/api/v1/agents/me/suppliers")
async def my_suppliers(request: Request):
    a = await _approved_partner(request)
    rows = await db.registrations.find({"partner_id": str(a["_id"])}).sort("partner_invited_at", -1).to_list(500)
    return {"items": [_supplier_row(r) for r in rows]}


async def _my_reg(rid: str, a: dict) -> dict:
    reg = await db.registrations.find_one({"_id": _oid(rid), "partner_id": str(a["_id"])})
    if not reg:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return reg


@router.post("/api/v1/agents/me/suppliers/{rid}/resend", dependencies=CSRF)
async def resend_supplier_invite(rid: str, request: Request):
    reg = await _my_reg(rid, await _approved_partner(request))
    if reg.get("partner_access") != "awaiting_consent":
        raise HTTPException(status_code=409, detail="The supplier has already responded to this invitation")
    upd = {"partner_consent_token": secrets.token_urlsafe(32), "partner_consent_expires_at": _ago(7)}
    await db.registrations.update_one({"_id": reg["_id"]}, {"$set": upd})
    return {"email_sent": await _send_supplier_invite({**reg, **upd})}


@router.post("/api/v1/agents/me/suppliers/{rid}/edit-link", dependencies=CSRF)
async def partner_edit_link(rid: str, request: Request):
    reg = await _my_reg(rid, await _approved_partner(request))
    if reg.get("partner_access") != "granted":
        raise HTTPException(status_code=403, detail="The supplier has not given (or has removed) consent for you to fill their form")
    if reg.get("status") not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=409, detail="This registration has been submitted and is locked")
    tok = reg.get("partner_edit_token") or secrets.token_urlsafe(32)
    await db.registrations.update_one({"_id": reg["_id"]}, {"$set": {"partner_edit_token": tok, "partner_stage": reg.get("partner_stage") if reg.get("partner_stage") == "ready_for_review" else "filling"}})
    return {"path": f"/register/resume?token={tok}&from=partner"}


@router.post("/api/v1/agents/me/suppliers/{rid}/send-for-review", dependencies=CSRF)
async def send_for_review(rid: str, request: Request):
    a = await _approved_partner(request)
    reg = await _my_reg(rid, a)
    if reg.get("partner_access") != "granted" or reg.get("status") not in ("draft", "needs_clarification"):
        raise HTTPException(status_code=409, detail="This registration can't be sent for review right now")
    await db.registrations.update_one({"_id": reg["_id"]}, {"$set": {"partner_stage": "ready_for_review", "partner_review_sent_at": now_iso()}})
    link = f"{_site()}/register/resume?token={reg['magic_token']}"
    sent = await send_email(reg["email"], f"[PMC] Your registration is ready for your review — {reg['company_name']}",
        wrap("Please review and submit your registration",
             f"<p>{reg['partner_name']} (partner {reg['partner_code']}) has finished filling your PMC supplier registration.</p>"
             f"<p>Please check every section — fields the partner filled are marked — then tick the declarations, sign and submit. "
             f"You can also remove the partner's access from the same page.</p>", "Review my registration", link))
    await audit_log("partner.sent_for_review", {"id": str(a["_id"]), "email": a["email"]}, "registration", rid, {})
    return {"email_sent": sent, "partner_stage": "ready_for_review"}


# ---------- supplier: consent / decline / revoke ----------

class ConsentIn(BaseModel):
    decision: Literal["accept", "decline"]
    signer_name: str = Field("", max_length=120)
    consents: Dict[str, bool] = {}


async def _by_consent_token(token: str) -> dict:
    reg = await db.registrations.find_one({"partner_consent_token": token})
    if not reg or reg.get("partner_consent_expires_at", "") < now_iso():
        raise HTTPException(status_code=404, detail="This invitation link is invalid or has expired. Ask the partner to resend it.")
    return reg


@router.get("/api/v1/supplier-invites/{token}")
async def invite_info(token: str):
    reg = await _by_consent_token(token)
    return {"company_name": reg["company_name"], "email": reg["email"], "partner_name": reg["partner_name"], "partner_code": reg["partner_code"],
            "partner_access": reg["partner_access"], "version": CONSENT_VERSION,
            "consents": [{"key": k, "text": t} for k, t in CONSENT]}


@router.post("/api/v1/supplier-invites/{token}")
async def invite_decide(token: str, body: ConsentIn, request: Request):
    reg = await _by_consent_token(token)
    if reg.get("partner_access") != "awaiting_consent":
        raise HTTPException(status_code=409, detail="You have already responded to this invitation")
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or None
    if body.decision == "decline":
        await db.registrations.update_one({"_id": reg["_id"]}, {"$set": {"partner_access": "declined", "partner_stage": "declined",
                                                                          "status": "withdrawn", "partner_consent_token": None}})
        await audit_log("supplier.partner_declined", None, "registration", str(reg["_id"]), {"ip": ip})
        await _notify_partner(reg, "declined your invitation")
        return {"partner_access": "declined"}
    if len(body.signer_name.strip()) < 3 or not all(body.consents.get(k) for k, _ in CONSENT):
        raise HTTPException(status_code=422, detail="Type your full name and tick every statement to give consent")
    consent = {"version": CONSENT_VERSION, "signer_name": body.signer_name.strip(), "consents": {k: True for k, _ in CONSENT},
               "at": now_iso(), "ip": ip, "user_agent": (request.headers.get("user-agent") or "")[:200]}
    await db.registrations.update_one({"_id": reg["_id"]}, {"$set": {
        "partner_access": "granted", "partner_stage": "consented", "partner_consent": consent, "email_verified_at": now_iso(),
        "data_processing_consent": True, "consent_at": now_iso(), "partner_consent_token": None}})
    await audit_log("supplier.partner_consent", None, "registration", str(reg["_id"]),
                    {"signer_name": consent["signer_name"], "version": CONSENT_VERSION, "ip": ip})
    await _notify_partner(reg, "gave consent — you can now fill their registration")
    return {"partner_access": "granted", "resume_path": f"/register/resume?token={reg['magic_token']}"}


async def _notify_partner(reg: dict, what: str) -> None:
    a = await db.agents.find_one({"_id": ObjectId(reg["partner_id"])}, {"email": 1})
    if a:
        await send_email(a["email"], f"[PMC] {reg['company_name']} {what.split(' —')[0]}",
                         wrap("Supplier update", f"<p>{reg['company_name']} ({reg['email']}) {what}.</p>", "Open partner portal", f"{_site()}/partner/me"))


@router.post("/api/v1/registrations/{rid}/partner-access/revoke")
async def revoke_partner(rid: str, token: str):
    reg = await db.registrations.find_one({"_id": _oid(rid), "magic_token": token})
    if not reg or not reg.get("partner_id"):
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.get("partner_access") == "revoked":
        return {"partner_access": "revoked"}
    await db.registrations.update_one({"_id": reg["_id"]}, {"$set": {"partner_access": "revoked", "partner_stage": "revoked",
                                                                      "partner_revoked_at": now_iso(), "partner_edit_token": None}})
    await audit_log("supplier.partner_revoked", None, "registration", rid, {"partner_code": reg.get("partner_code")})
    await _notify_partner(reg, "removed your access to their registration")
    return {"partner_access": "revoked"}


# ---------- commission settings + wallet ----------

class CommissionRule(BaseModel):
    currency: str = Field("USD", min_length=3, max_length=3)
    onboarding_amount: float = Field(0, ge=0)
    deal_type: Literal["fixed", "percent"] = "percent"
    deal_value: float = Field(0, ge=0)


async def _rule_for(a: dict) -> dict:
    if a.get("commission"):
        return {**a["commission"], "source": "partner"}
    s = await db.partner_commission_settings.find_one({"key": "default"}, {"_id": 0, "key": 0}) or CommissionRule().model_dump()
    return {**s, "source": "default"}


@router.get("/api/v1/admin/partner-commission/settings")
async def get_commission_settings(admin=ADMIN):
    s = await db.partner_commission_settings.find_one({"key": "default"}, {"_id": 0, "key": 0})
    return s or CommissionRule().model_dump()


@router.put("/api/v1/admin/partner-commission/settings", dependencies=CSRF)
async def put_commission_settings(body: CommissionRule, admin=ADMIN):
    data = {**body.model_dump(), "currency": body.currency.upper(), "updated_at": now_iso(), "updated_by": admin.get("email")}
    await db.partner_commission_settings.update_one({"key": "default"}, {"$set": data}, upsert=True)
    await audit_log("partner.commission_settings", admin, "settings", "partner_commission", body.model_dump())
    return data


class PartnerRuleIn(BaseModel):
    rule: Optional[CommissionRule] = None


@router.put("/api/v1/admin/agents/{aid}/commission", dependencies=CSRF)
async def put_partner_rule(aid: str, body: PartnerRuleIn, admin=ADMIN):
    rule = {**body.rule.model_dump(), "currency": body.rule.currency.upper()} if body.rule else None
    await db.agents.update_one({"_id": _oid(aid)}, {"$set": {"commission": rule}})
    await audit_log("partner.commission_override", admin, "agent", aid, {"rule": rule})
    return {"commission": rule}


def _entry(e: dict) -> dict:
    e = dict(e)
    e["id"] = str(e.pop("_id"))
    return e


def _totals(rows: list) -> dict:
    t: dict = {}
    for r in rows:
        if r["status"] in ("due", "paid"):
            c = t.setdefault(r["currency"], {"due": 0.0, "paid": 0.0})
            c[r["status"]] = round(c[r["status"]] + float(r["amount"]), 2)
    return t


async def on_supplier_approved(reg: dict, vendor_ref: Optional[str]) -> None:
    """Accrue the onboarding commission once a partner-assisted registration is approved."""
    if not reg.get("partner_id") or reg.get("partner_access") != "granted":
        return
    a = await db.agents.find_one({"_id": ObjectId(reg["partner_id"])})
    if not a:
        return
    rule = await _rule_for(a)
    amount = float(rule.get("onboarding_amount") or 0)
    if amount <= 0 or await db.partner_commissions.find_one({"registration_id": str(reg["_id"]), "kind": "onboarding"}):
        return
    await db.partner_commissions.insert_one({"partner_id": reg["partner_id"], "partner_code": a.get("partner_code"), "kind": "onboarding",
        "registration_id": str(reg["_id"]), "vendor_ref": vendor_ref, "company_name": reg.get("company_name"), "amount": round(amount, 2),
        "currency": rule.get("currency") or "USD", "basis": "Supplier approved", "status": "due", "created_at": now_iso()})
    await audit_log("partner.commission_accrued", None, "agent", reg["partner_id"], {"kind": "onboarding", "amount": amount, "vendor_ref": vendor_ref})


class DealIn(BaseModel):
    vendor_ref: str = Field(min_length=2, max_length=40)
    deal_ref: str = Field(min_length=2, max_length=120)
    business_amount: float = Field(0, ge=0)
    note: str = Field("", max_length=500)


@router.post("/api/v1/admin/agents/{aid}/commissions", dependencies=CSRF)
async def add_deal_commission(aid: str, body: DealIn, admin=ADMIN):
    a = await db.agents.find_one({"_id": _oid(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Partner not found")
    reg = await db.registrations.find_one({"partner_id": aid, "vendor_ref": body.vendor_ref.strip(), "status": "approved"})
    if not reg:
        raise HTTPException(status_code=422, detail="That supplier reference is not an approved supplier onboarded by this partner")
    rule = await _rule_for(a)
    val = float(rule.get("deal_value") or 0)
    amount = val if rule.get("deal_type") == "fixed" else body.business_amount * val / 100
    if amount <= 0:
        raise HTTPException(status_code=422, detail="The deal commission works out to zero — set the deal commission rule, or enter the business amount")
    doc = {"partner_id": aid, "partner_code": a.get("partner_code"), "kind": "deal", "registration_id": str(reg["_id"]),
           "vendor_ref": reg["vendor_ref"], "company_name": reg.get("company_name"), "deal_ref": body.deal_ref.strip(),
           "business_amount": body.business_amount, "amount": round(amount, 2), "currency": rule.get("currency") or "USD",
           "basis": f"{val:g}% of {body.business_amount:,.2f}" if rule.get("deal_type") == "percent" else "Fixed deal fee",
           "note": body.note.strip(), "status": "due", "created_at": now_iso(), "created_by": admin.get("email")}
    doc["_id"] = (await db.partner_commissions.insert_one(doc)).inserted_id
    await audit_log("partner.commission_accrued", admin, "agent", aid, {"kind": "deal", "amount": doc["amount"], "deal_ref": doc["deal_ref"]})
    return _entry(doc)


class SettleIn(BaseModel):
    action: Literal["paid", "void"]
    reference: str = Field(min_length=2, max_length=200)
    paid_on: str = Field("", max_length=10)


@router.post("/api/v1/admin/partner-commissions/{cid}", dependencies=CSRF)
async def settle_commission(cid: str, body: SettleIn, admin=ADMIN):
    e = await db.partner_commissions.find_one({"_id": _oid(cid)})
    if not e:
        raise HTTPException(status_code=404, detail="Commission not found")
    if e["status"] != "due":
        raise HTTPException(status_code=409, detail=f"This commission is already {e['status']}")
    upd = {"status": body.action, "settled_at": now_iso(), "settled_by": admin.get("email"), "reference": body.reference.strip(),
           **({"paid_on": body.paid_on or now_iso()[:10]} if body.action == "paid" else {})}
    await db.partner_commissions.update_one({"_id": e["_id"], "status": "due"}, {"$set": upd})
    await audit_log(f"partner.commission_{body.action}", admin, "agent", e["partner_id"], {"commission_id": cid, "reference": upd["reference"]})
    if body.action == "paid":
        a = await db.agents.find_one({"_id": ObjectId(e["partner_id"])}, {"email": 1})
        if a:
            await send_email(a["email"], "[PMC] Commission paid", wrap("Commission paid",
                f"<p>PMC has paid your commission of <b>{e['currency']} {e['amount']:,.2f}</b> ({e['kind']} — {e.get('company_name') or ''}). "
                f"Reference: {upd['reference']}.</p>", "Open my wallet", f"{_site()}/partner/me"))
    return _entry({**e, **upd})


@router.get("/api/v1/admin/agents/{aid}/wallet")
async def admin_wallet(aid: str, admin=ADMIN):
    a = await db.agents.find_one({"_id": _oid(aid)})
    if not a:
        raise HTTPException(status_code=404, detail="Partner not found")
    rows = await db.partner_commissions.find({"partner_id": aid}).sort("created_at", -1).to_list(1000)
    sups = await db.registrations.find({"partner_id": aid}).sort("partner_invited_at", -1).to_list(500)
    return {"items": [_entry(r) for r in rows], "totals": _totals(rows), "rule": await _rule_for(a),
            "override": a.get("commission"), "suppliers": [_supplier_row(r) for r in sups]}


@router.get("/api/v1/agents/me/wallet")
async def my_wallet(request: Request):
    a = await _approved_partner(request)
    rows = await db.partner_commissions.find({"partner_id": str(a["_id"])}, {"settled_by": 0, "created_by": 0}).sort("created_at", -1).to_list(1000)
    rule = await _rule_for(a)
    rule.pop("updated_by", None)
    return {"items": [_entry(r) for r in rows], "totals": _totals(rows), "rule": rule,
            "payout_requested_at": a.get("payout_requested_at")}


@router.post("/api/v1/agents/me/wallet/request-payout", dependencies=CSRF)
async def request_payout(request: Request):
    a = await _approved_partner(request)
    rows = await db.partner_commissions.find({"partner_id": str(a["_id"]), "status": "due"}).to_list(1000)
    if not rows:
        raise HTTPException(status_code=409, detail="You have no commission due right now")
    await db.agents.update_one({"_id": a["_id"]}, {"$set": {"payout_requested_at": now_iso()}})
    summary = ", ".join(f"{c} {v['due']:,.2f}" for c, v in _totals(rows).items())
    async for adm in db.admin_users.find({"role": "admin", "status": {"$ne": "disabled"}}, {"email": 1}).limit(5):
        await send_email(adm["email"], f"[PMC] Payout requested by partner {a.get('partner_code')}",
                         wrap("Partner payout request", f"<p>{a.get('legal_name') or a['name']} ({a.get('partner_code')}) asked to be paid {summary}.</p>",
                              "Open partners", f"{_site()}/admin/e/partners"))
    await audit_log("partner.payout_requested", {"id": str(a["_id"]), "email": a["email"]}, "agent", str(a["_id"]), {"due": summary})
    return {"payout_requested_at": now_iso(), "due": summary}


async def ensure_indexes() -> None:
    await db.registrations.create_index("partner_id", sparse=True)
    await db.registrations.create_index("partner_consent_token", sparse=True)
    await db.registrations.create_index("partner_edit_token", sparse=True)
    await db.partner_commissions.create_index([("partner_id", 1), ("created_at", -1)])
