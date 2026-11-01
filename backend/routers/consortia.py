"""Consortium bidding: a lead supplier forms a team of registered suppliers to bid on one tender together."""
import secrets
from typing import List, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
from audit import audit_log
from db import db
from emails import send_email, wrap
from models.base import now_iso
from routers.vendor_auth import current_vendor
from security import require_role

router = APIRouter(prefix="/api/v1/consortia", tags=["consortia"])

AGREEMENT_VERSION = "2026-11-v1"
STANDARD_AGREEMENT = [
    ("Purpose", "The members join together only to bid for, and if awarded deliver, the tender named on this consortium."),
    ("Lead member", "The lead member submits the bid, speaks for the consortium to the buyer and PMC, and signs on its behalf."),
    ("Responsibility", "All members are jointly and severally responsible to the buyer for the whole contract if it is awarded."),
    ("Shares", "Work and payments are shared in the percentages shown on this consortium. Payments are made only through PMC escrow."),
    ("Exclusivity", "No member may bid for the same tender alone or in another consortium."),
    ("Changes", "Members cannot change after the bid is submitted without the buyer's written consent."),
]
FINAL = {"bid_submitted", "withdrawn"}


async def max_members_default() -> int:
    s = await db.platform_settings.find_one({"_id": "consortium"}) or {}
    return int(s.get("max_members_default") or 5)


async def notice_limit(n: dict) -> int:
    return int(n.get("consortium_max_members") or await max_members_default())


def _out(c: dict) -> dict:
    c = dict(c)
    c["id"] = str(c.pop("_id"))
    ag = dict(c.get("agreement") or {})
    ag["signatures"] = [{k: v for k, v in s.items() if k != "token"} for s in ag.get("signatures") or []]
    c["agreement"] = ag
    return c


async def _kyc_ok(v: dict) -> bool:
    if (v.get("kyc") or {}).get("status") in ("verified", "cleared", "passed") or v.get("kyc_status") in ("verified", "cleared", "passed"):
        return True
    return bool(await db.kyc_cases.find_one({"vendor_id": str(v["_id"]), "status": "passed"}))


def _ready_issues(c: dict, limit: int) -> List[str]:
    out = []
    members = c.get("members") or []
    accepted = [m for m in members if m["status"] == "accepted"]
    if not accepted:
        out.append("Add at least one other member who accepts")
    if any(m["status"] == "invited" for m in members):
        out.append("Some members have not answered their invitation yet")
    if 1 + len(accepted) > limit:
        out.append(f"This tender allows at most {limit} members including the lead")
    total = float(c.get("lead_share_pct") or 0) + sum(float(m.get("share_pct") or 0) for m in accepted)
    if abs(total - 100) > 0.01:
        out.append(f"Shares add up to {total:g}% — they must total 100%")
    ag = c.get("agreement") or {}
    signed = {s["vendor_id"] for s in ag.get("signatures") or []}
    everyone = {c["lead_vendor_id"], *[m["vendor_id"] for m in accepted]}
    if not ag.get("uploaded") and not everyone <= signed:
        out.append("Upload the signed consortium agreement, or have every member sign the standard one")
    if not c.get("escrow_mode") or not c.get("deposit_mode"):
        out.append("Choose how escrow and the bid deposit will work")
    return out


async def view(c: dict, vendor_id: Optional[str] = None) -> dict:
    n = await db.notices.find_one({"notice_ref": c["notice_ref"]}, {"title": 1, "consortium_max_members": 1}) or {}
    limit = await notice_limit(n)
    o = _out(c)
    o.update(notice_title=n.get("title"), max_members=limit, issues=[] if c["status"] in FINAL else _ready_issues(c, limit),
             is_lead=vendor_id == c["lead_vendor_id"], agreement_text=[{"title": t, "text": x} for t, x in STANDARD_AGREEMENT],
             agreement_version=AGREEMENT_VERSION)
    o["ready"] = not o["issues"] and c["status"] not in FINAL
    return o


async def _mine(cid: str, vendor: dict, lead_only: bool = False) -> dict:
    c = await db.consortia.find_one({"_id": ObjectId(cid)}) if ObjectId.is_valid(cid) else None
    ids = {c["lead_vendor_id"], *[m["vendor_id"] for m in c.get("members") or []]} if c else set()
    if not c or vendor["id"] not in ids:
        raise HTTPException(status_code=404, detail="Consortium not found")
    if lead_only and c["lead_vendor_id"] != vendor["id"]:
        raise HTTPException(status_code=403, detail="Only the lead member can do this")
    return c


def _editable(c: dict) -> None:
    if c["status"] in FINAL:
        raise HTTPException(status_code=409, detail="The bid has been submitted — the consortium can no longer change")


async def _reset_signatures(c: dict) -> None:
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"agreement.signatures": [], "updated_at": now_iso()}})


async def busy_on_notice(vendor_id: str, notice_ref: str, except_id=None) -> Optional[dict]:
    q = {"notice_ref": notice_ref, "status": {"$ne": "withdrawn"},
         "$or": [{"lead_vendor_id": vendor_id}, {"members": {"$elemMatch": {"vendor_id": vendor_id, "status": {"$in": ["invited", "accepted"]}}}}]}
    if except_id:
        q["_id"] = {"$ne": except_id}
    return await db.consortia.find_one(q)


# ---------- settings ----------

class SettingsIn(BaseModel):
    max_members_default: int = Field(ge=2, le=20)


@router.get("/settings")
async def get_settings():
    return {"max_members_default": await max_members_default()}


@router.put("/settings")
async def put_settings(body: SettingsIn, admin=Depends(require_role("admin"))):
    await db.platform_settings.update_one({"_id": "consortium"}, {"$set": {"max_members_default": body.max_members_default,
                                                                          "updated_at": now_iso(), "updated_by": admin.get("email")}}, upsert=True)
    await audit_log("consortium.settings", admin, "settings", "consortium", body.model_dump())
    return body.model_dump()


# ---------- supplier ----------

class CreateIn(BaseModel):
    notice_ref: str
    name: str = Field(min_length=3, max_length=150)


class MemberIn(BaseModel):
    email_or_ref: str = Field(min_length=3, max_length=200)
    capability: str = Field(default="", max_length=300)
    share_pct: float = Field(ge=0, le=100)


class TermsIn(BaseModel):
    lead_share_pct: float = Field(ge=0, le=100)
    shares: dict = {}
    escrow_mode: Literal["shared", "separate"]
    deposit_mode: Literal["lead_pays", "each_pays_share"]


class RespondIn(BaseModel):
    accept: bool


class UploadIn(BaseModel):
    key: str
    filename: str = Field(max_length=200)


class SignIn(BaseModel):
    signer_name: str = Field(min_length=3, max_length=120)
    consent: bool


@router.get("/mine")
async def my_consortia(notice_ref: Optional[str] = None, vendor=Depends(current_vendor)):
    q = {"$or": [{"lead_vendor_id": vendor["id"]}, {"members.vendor_id": vendor["id"]}]}
    if notice_ref:
        q["notice_ref"] = notice_ref
    return {"items": [await view(c, vendor["id"]) async for c in db.consortia.find(q).sort("created_at", -1).limit(100)]}


@router.post("")
async def create(body: CreateIn, vendor=Depends(current_vendor)):
    n = await db.notices.find_one({"notice_ref": body.notice_ref, "is_published": True})
    if not n:
        raise HTTPException(status_code=404, detail="Tender not found")
    if not n.get("consortium_allowed"):
        raise HTTPException(status_code=409, detail="This tender does not accept consortium bids")
    if await busy_on_notice(vendor["id"], body.notice_ref):
        raise HTTPException(status_code=409, detail="You are already in a consortium for this tender")
    if await db.bids.find_one({"notice_ref": body.notice_ref, "vendor_id": vendor["id"], "status": {"$nin": ["withdrawn", "rejected"]}}):
        raise HTTPException(status_code=409, detail="You already have a bid of your own on this tender — withdraw it first")
    c = {"notice_ref": body.notice_ref, "name": body.name.strip(), "lead_vendor_id": vendor["id"], "lead_company": vendor.get("company_name"),
         "lead_email": vendor["email"], "lead_vendor_ref": vendor.get("vendor_ref"), "lead_share_pct": 100.0, "members": [],
         "agreement": {"signatures": []}, "status": "forming", "created_at": now_iso()}
    c["_id"] = (await db.consortia.insert_one(c)).inserted_id
    await audit_log("consortium.created", vendor, "consortium", str(c["_id"]), {"notice": body.notice_ref})
    return await view(c, vendor["id"])


@router.post("/{cid}/members")
async def add_member(cid: str, body: MemberIn, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor, lead_only=True)
    _editable(c)
    key = body.email_or_ref.strip()
    v = await db.vendors.find_one({"$or": [{"email": key.lower()}, {"vendor_ref": key.upper()}], "status": "active"})
    if not v:
        raise HTTPException(status_code=404, detail="No registered PMC supplier found with that email or supplier ID. Members must be registered suppliers.")
    vid = str(v["_id"])
    n = await db.notices.find_one({"notice_ref": c["notice_ref"]}) or {}
    if not n.get("kyc_bypass") and not await _kyc_ok(v):
        raise HTTPException(status_code=409, detail="This supplier hasn't completed KYC verification yet, so it can't join a consortium.")
    if vid == c["lead_vendor_id"] or any(m["vendor_id"] == vid and m["status"] != "declined" for m in c["members"]):
        raise HTTPException(status_code=409, detail="This supplier is already in the consortium")
    limit = await notice_limit(n)
    live = [m for m in c["members"] if m["status"] in ("invited", "accepted")]
    if 1 + len(live) >= limit:
        raise HTTPException(status_code=409, detail=f"This tender allows at most {limit} members including the lead")
    if await busy_on_notice(vid, c["notice_ref"], except_id=c["_id"]):
        raise HTTPException(status_code=409, detail="This supplier is already in another consortium for this tender")
    if await db.bids.find_one({"notice_ref": c["notice_ref"], "vendor_id": vid, "status": {"$nin": ["withdrawn", "rejected"]}}):
        raise HTTPException(status_code=409, detail="This supplier has already bid on this tender alone")
    m = {"vendor_id": vid, "company_name": v.get("company_name"), "email": v["email"], "vendor_ref": v.get("vendor_ref"),
         "capability": body.capability.strip(), "share_pct": body.share_pct, "status": "invited", "invited_at": now_iso()}
    c["members"] = [x for x in c["members"] if x["vendor_id"] != vid] + [m]
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"members": c["members"], "agreement.signatures": [], "updated_at": now_iso()}})
    c["agreement"]["signatures"] = []
    await audit_log("consortium.member_invited", vendor, "consortium", cid, {"member": v["email"]})
    link = f"{config.FRONTEND_URL.rstrip('/')}/vendor/consortia"
    await send_email(v["email"], f"[PMC] Invitation to join a consortium for {c['notice_ref']}",
                     wrap("Consortium invitation", f"<p>{c.get('lead_company') or 'A supplier'} has invited your company to join the consortium "
                          f"<b>{c['name']}</b> to bid for tender <code>{c['notice_ref']}</code> with a {body.share_pct:g}% share.</p>"
                          "<p>Sign in to accept or decline.</p>", "Review invitation", link))
    await db.notifications.insert_one({"user_email": v["email"], "user_ref": v.get("vendor_ref"), "role": "vendor",
                                       "subject": f"Consortium invitation · {c['notice_ref']}", "related_type": "consortium",
                                       "related_id": cid, "related_url": "/vendor/consortia", "related_notice_ref": c["notice_ref"],
                                       "body": f"<p>{c.get('lead_company')} invited you to join {c['name']}.</p>", "read": False, "created_at": now_iso()})
    return await view(c, vendor["id"])


@router.delete("/{cid}/members/{vid}")
async def remove_member(cid: str, vid: str, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor, lead_only=True)
    _editable(c)
    gone = next((m for m in c["members"] if m["vendor_id"] == vid), None)
    if not gone:
        raise HTTPException(status_code=404, detail="That supplier is not in this consortium")
    c["members"] = [m for m in c["members"] if m["vendor_id"] != vid]
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"members": c["members"], "agreement.signatures": [], "updated_at": now_iso()}})
    c["agreement"]["signatures"] = []
    await audit_log("consortium.member_removed", vendor, "consortium", cid, {"member": vid})
    await send_email(gone["email"], f"[PMC] You were removed from the consortium {c['name']}",
                     wrap("Consortium update", f"<p>{c.get('lead_company')} removed your company from the consortium <b>{c['name']}</b> "
                          f"for tender <code>{c['notice_ref']}</code>.</p>"))
    return await view(c, vendor["id"])


@router.post("/{cid}/respond")
async def respond(cid: str, body: RespondIn, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor)
    _editable(c)
    m = next((x for x in c["members"] if x["vendor_id"] == vendor["id"]), None)
    if not m or m["status"] != "invited":
        raise HTTPException(status_code=409, detail="There is no open invitation for you on this consortium")
    if body.accept:
        if await db.bids.find_one({"notice_ref": c["notice_ref"], "vendor_id": vendor["id"], "status": {"$nin": ["withdrawn", "rejected"]}}):
            raise HTTPException(status_code=409, detail="You already have your own bid on this tender — withdraw it before joining")
        if await busy_on_notice(vendor["id"], c["notice_ref"], except_id=c["_id"]):
            raise HTTPException(status_code=409, detail="You are already in another consortium for this tender")
    m.update(status="accepted" if body.accept else "declined", responded_at=now_iso())
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"members": c["members"], "updated_at": now_iso()}})
    await audit_log(f"consortium.member_{m['status']}", vendor, "consortium", cid, {})
    await send_email(c["lead_email"], f"[PMC] {vendor.get('company_name')} {m['status']} your consortium invitation",
                     wrap("Consortium update", f"<p>{vendor.get('company_name')} has {m['status']} the invitation to {c['name']} "
                          f"for tender <code>{c['notice_ref']}</code>.</p>", "Open consortium", f"{config.FRONTEND_URL.rstrip('/')}/vendor/consortia"))
    return await view(c, vendor["id"])


@router.post("/{cid}/leave")
async def leave(cid: str, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor)
    _editable(c)
    if c["lead_vendor_id"] == vendor["id"]:
        raise HTTPException(status_code=409, detail="The lead can't leave — withdraw the consortium instead")
    m = next((x for x in c["members"] if x["vendor_id"] == vendor["id"]), None)
    if not m or m["status"] != "accepted":
        raise HTTPException(status_code=409, detail="You are not an active member of this consortium")
    m.update(status="declined", left_at=now_iso())
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"members": c["members"], "agreement.signatures": [], "updated_at": now_iso()}})
    await audit_log("consortium.member_left", vendor, "consortium", cid, {})
    await send_email(c["lead_email"], f"[PMC] {vendor.get('company_name')} left your consortium",
                     wrap("Consortium update", f"<p>{vendor.get('company_name')} has left {c['name']} for tender <code>{c['notice_ref']}</code>. "
                          "Signatures have been reset.</p>", "Open consortium", f"{config.FRONTEND_URL.rstrip('/')}/vendor/consortia"))
    return {"ok": True}


@router.put("/{cid}/terms")
async def set_terms(cid: str, body: TermsIn, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor, lead_only=True)
    _editable(c)
    known = {m["vendor_id"] for m in c["members"]}
    if set(body.shares) - known:
        raise HTTPException(status_code=422, detail="Shares can only be set for members of this consortium")
    for m in c["members"]:
        if m["vendor_id"] in body.shares:
            m["share_pct"] = max(0.0, min(100.0, float(body.shares[m["vendor_id"]] or 0)))
    upd = {"lead_share_pct": body.lead_share_pct, "members": c["members"], "escrow_mode": body.escrow_mode,
           "deposit_mode": body.deposit_mode, "agreement.signatures": [], "updated_at": now_iso()}
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": upd})
    c.update({k: v for k, v in upd.items() if "." not in k})
    c["agreement"]["signatures"] = []
    await audit_log("consortium.terms", vendor, "consortium", cid, body.model_dump())
    return await view(c, vendor["id"])


@router.post("/{cid}/agreement/upload")
async def upload_agreement(cid: str, body: UploadIn, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor, lead_only=True)
    _editable(c)
    u = await db.uploads.find_one({"key": body.key})
    if not u:
        raise HTTPException(status_code=422, detail="Upload the agreement file first")
    up = {"key": body.key, "filename": body.filename, "by": vendor["email"], "at": now_iso()}
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"agreement.uploaded": up, "updated_at": now_iso()}})
    c["agreement"]["uploaded"] = up
    await audit_log("consortium.agreement_uploaded", vendor, "consortium", cid, {"file": body.filename})
    return await view(c, vendor["id"])


@router.post("/{cid}/agreement/sign")
async def sign_agreement(cid: str, body: SignIn, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor)
    _editable(c)
    if not body.consent:
        raise HTTPException(status_code=422, detail="Tick the box to sign the agreement")
    if vendor["id"] != c["lead_vendor_id"] and not any(m["vendor_id"] == vendor["id"] and m["status"] == "accepted" for m in c["members"]):
        raise HTTPException(status_code=409, detail="Accept the invitation before signing")
    sigs = [s for s in c["agreement"].get("signatures") or [] if s["vendor_id"] != vendor["id"]]
    sigs.append({"vendor_id": vendor["id"], "company": vendor.get("company_name"), "signer_name": body.signer_name.strip(),
                 "version": AGREEMENT_VERSION, "at": now_iso(), "token": secrets.token_hex(6)})
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"agreement.signatures": sigs, "updated_at": now_iso()}})
    c["agreement"]["signatures"] = sigs
    await audit_log("consortium.agreement_signed", vendor, "consortium", cid, {"signer": body.signer_name})
    return await view(c, vendor["id"])


@router.post("/{cid}/withdraw")
async def withdraw(cid: str, vendor=Depends(current_vendor)):
    c = await _mine(cid, vendor, lead_only=True)
    _editable(c)
    await db.consortia.update_one({"_id": c["_id"]}, {"$set": {"status": "withdrawn", "updated_at": now_iso()}})
    await audit_log("consortium.withdrawn", vendor, "consortium", cid, {})
    return {"ok": True}


async def for_bid(cid: str, vendor: dict, notice_ref: str) -> dict:
    """Validate a consortium at bid time; returns the snapshot stored on the bid."""
    c = await _mine(cid, vendor, lead_only=True)
    if c["notice_ref"] != notice_ref:
        raise HTTPException(status_code=422, detail="This consortium was formed for a different tender")
    _editable(c)
    n = await db.notices.find_one({"notice_ref": notice_ref}) or {}
    issues = _ready_issues(c, await notice_limit(n))
    if issues:
        raise HTTPException(status_code=409, detail="The consortium isn't ready: " + "; ".join(issues))
    accepted = [m for m in c["members"] if m["status"] == "accepted"]
    for m in accepted:
        if await db.bids.find_one({"notice_ref": notice_ref, "vendor_id": m["vendor_id"], "status": {"$nin": ["withdrawn", "rejected"]}}):
            raise HTTPException(status_code=409, detail=f"{m['company_name']} has its own bid on this tender")
    return {"id": str(c["_id"]), "name": c["name"], "lead_share_pct": c["lead_share_pct"], "escrow_mode": c["escrow_mode"],
            "deposit_mode": c["deposit_mode"], "agreement": _out(c)["agreement"],
            "members": [{k: m.get(k) for k in ("vendor_id", "company_name", "email", "vendor_ref", "capability", "share_pct")} for m in accepted]}


async def mark_submitted(cid: str, bid_id: str) -> None:
    await db.consortia.update_one({"_id": ObjectId(cid)}, {"$set": {"status": "bid_submitted", "bid_id": bid_id, "submitted_at": now_iso()}})


@router.get("/admin/by-notice/{ref}")
async def admin_list(ref: str, _=Depends(require_role("admin", "reviewer", "committee_member", "auditor"))):
    return {"items": [_out(c) async for c in db.consortia.find({"notice_ref": ref, "status": {"$ne": "withdrawn"}})]}
