"""Pricing bands, tiers, per-tender fee plan (charge / waive), award fee and per-supplier fee plan."""
import re
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from models.base import BaseDocument, now_iso
from routers._fees import band_code, compute_amount, find_rule
from security import require_role

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])
WAIVERS = ("admin", "reviewer")

DEFAULT_BANDS = [
    ("GLOBAL", "Global", ["US", "GB", "IE", "DE", "FR", "NL", "BE", "LU", "IT", "ES", "PT", "AT", "CH", "SE", "NO", "DK", "FI",
                          "PL", "CZ", "AE", "SA", "QA", "KW", "BH", "OM", "SG", "AU", "NZ", "CA", "JP", "KR", "HK"], 1),
    ("REGIONAL", "Regional", ["MY", "TH", "ID", "VN", "PH", "TR", "MX", "BR", "ZA"], 2),
    ("PROGRAMME", "Programme", ["KZ", "UZ", "KG", "TJ", "TM", "AZ", "GE", "AM", "MN", "PK", "BD", "LK", "NP", "AF",
                                "EG", "MA", "DZ", "TN", "LY", "ET", "KE", "TZ", "UG", "RW", "SO", "SD", "DJ", "ER"], 3),
    ("INDIA", "India", ["IN"], 4),
    ("CHINA", "China", ["CN"], 5),
]
DEFAULT_TIERS = ["Starter", "Professional", "Programme"]
NOTICE_FEES = [("tender_hosting", "Tender hosting fee"), ("tender_document_download", "Tender document download (suppliers)"),
               ("transaction", "Award fee")]
SUPPLIER_FEES = [("registration", "Extra business categories"), ("tender_document_download", "Tender document downloads"),
                 ("ai_tender_summary", "AI tender summary"), ("ai_bid_readiness", "AI bid readiness check"),
                 ("featured_listing", "Featured directory listing"), ("mkt_listing_fee", "Marketplace product listing")]


async def seed_pricing() -> None:
    for code, name, countries, order in DEFAULT_BANDS:
        await db.pricing_bands.update_one({"code": code}, {"$setOnInsert": {
            "code": code, "name": name, "countries": countries, "order": order, "is_active": code != "CHINA",
            "award_payer_default": "supplier" if code == "INDIA" else "buyer", "supplier_fees_default": "charge",
            "created_at": now_iso()}}, upsert=True)
    await db.pricing_config.update_one({"_id": "config"}, {"$setOnInsert": {"tiers": DEFAULT_TIERS}}, upsert=True)
    await db.fee_types.update_one({"code": "transaction", "name": "Transaction fee"}, {"$set": {"name": "Award fee"}})
    await db.pricing_bands.create_index("code", unique=True)


async def _tiers() -> list:
    c = await db.pricing_config.find_one({"_id": "config"}) or {}
    return c.get("tiers") or DEFAULT_TIERS


async def band_of(country: Optional[str]) -> Optional[dict]:
    code = await band_code(country)
    return await db.pricing_bands.find_one({"code": code}) if code else None


# ----------------------------- bands & tiers -----------------------------

class BandIn(BaseModel):
    code: Optional[str] = Field(default=None, max_length=20)
    name: str = Field(min_length=2, max_length=60)
    countries: list[str] = Field(default_factory=list)
    is_active: bool = True
    award_payer_default: Literal["buyer", "supplier"] = "buyer"
    supplier_fees_default: Literal["charge", "waive"] = "charge"
    notes: Optional[str] = Field(default=None, max_length=400)


class TiersIn(BaseModel):
    tiers: list[str] = Field(min_length=1, max_length=8)


@router.get("/bands")
async def list_bands(admin=Depends(require_role("admin", "reviewer", "accounting"))):
    return {"bands": [BaseDocument.out(b) async for b in db.pricing_bands.find({}).sort("order", 1)], "tiers": await _tiers()}


async def _clean_countries(cs: list, code: str) -> list:
    cs = sorted({c.strip().upper() for c in cs if c and c.strip()})
    bad = [c for c in cs if not re.fullmatch(r"[A-Z]{2}", c)]
    if bad:
        raise HTTPException(status_code=422, detail=f"Use 2-letter country codes: {', '.join(bad)}")
    clash = await db.pricing_bands.find_one({"code": {"$ne": code}, "countries": {"$in": cs}}, {"name": 1, "countries": 1})
    if clash:
        dup = sorted(set(cs) & set(clash["countries"]))
        raise HTTPException(status_code=409, detail=f"{', '.join(dup)} already in band '{clash['name']}'. Remove it there first.")
    return cs


@router.post("/bands")
async def create_band(body: BandIn, admin=Depends(require_role("admin"))):
    code = re.sub(r"[^A-Z0-9]+", "_", (body.code or body.name).upper()).strip("_")
    if await db.pricing_bands.find_one({"code": code}):
        raise HTTPException(status_code=409, detail="A band with this code exists")
    doc = {**body.model_dump(), "code": code, "countries": await _clean_countries(body.countries, code),
           "order": await db.pricing_bands.count_documents({}) + 1, "created_at": now_iso()}
    await db.pricing_bands.insert_one(doc)
    await audit_log("pricing.band_create", admin, "pricing_band", code, {"countries": doc["countries"]})
    return BaseDocument.out(doc)


@router.put("/bands/{code}")
async def update_band(code: str, body: BandIn, admin=Depends(require_role("admin"))):
    upd = {**body.model_dump(exclude={"code"}), "countries": await _clean_countries(body.countries, code), "updated_at": now_iso()}
    r = await db.pricing_bands.update_one({"code": code}, {"$set": upd})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Band not found")
    await audit_log("pricing.band_update", admin, "pricing_band", code, upd)
    return BaseDocument.out(await db.pricing_bands.find_one({"code": code}))


@router.put("/tiers")
async def set_tiers(body: TiersIn, admin=Depends(require_role("admin"))):
    tiers = [t.strip() for t in body.tiers if t.strip()]
    await db.pricing_config.update_one({"_id": "config"}, {"$set": {"tiers": tiers}}, upsert=True)
    await audit_log("pricing.tiers", admin, "pricing_config", "tiers", {"tiers": tiers})
    return {"tiers": tiers}


@router.get("/band-for/{country}")
async def band_for(country: str, admin=Depends(require_role("admin", "reviewer", "accounting"))):
    b = await band_of(country)
    return BaseDocument.out(b) if b else None


# ----------------------------- per-tender fee plan -----------------------------

def _rate_text(rule: dict, currency: str) -> str:
    parts = []
    for s in rule.get("slabs") or []:
        lo, hi = s.get("tender_value_min") or 0, s.get("tender_value_max")
        rng = "" if (not lo and hi is None) else f" ({lo:,.0f}–{'∞' if hi is None else f'{hi:,.0f}'})"
        if s.get("fee_type") == "fixed":
            parts.append(f"{currency} {float(s.get('fixed_amount') or 0):,.2f}{rng}")
        else:
            cap = f", max {float(s['pct_max']):,.0f}" if s.get("pct_max") else ""
            parts.append(f"{s.get('percentage')}%{cap}{rng}")
    if rule.get("nil_below"):
        parts.append(f"nil below {float(rule['nil_below']):,.0f}")
    return "; ".join(parts)


async def _notice(ref: str) -> dict:
    n = await db.notices.find_one({"notice_ref": ref})
    if not n:
        raise HTTPException(status_code=404, detail="Notice not found")
    return n


async def _plan_items(n: dict, tier: Optional[str]) -> list:
    out = []
    for code, label in NOTICE_FEES:
        rule = await find_rule(code, n.get("delivery_country"), n.get("category"), tier)
        cur = ((rule or {}).get("currency") or n.get("currency") or "USD").upper()
        est = compute_amount(rule, n.get("budget_amount")) if rule else None
        out.append({"code": code, "name": label, "has_rule": bool(rule), "rule_id": str(rule["_id"]) if rule else None,
                    "rule_name": (rule or {}).get("name"), "currency": cur, "rate": _rate_text(rule, cur) if rule else None,
                    "estimate": est, "charge": bool(rule)})
    return out


@router.get("/notices/{ref}/fee-plan")
async def get_fee_plan(ref: str, tier: Optional[str] = None, admin=Depends(require_role(*WAIVERS))):
    n = await _notice(ref)
    saved = n.get("fee_plan")
    band = await band_of(n.get("delivery_country"))
    t = tier or (saved or {}).get("tier")
    return {"notice_ref": ref, "country": n.get("delivery_country"), "band": BaseDocument.out(band) if band else None,
            "tiers": await _tiers(), "tier": t, "items": await _plan_items(n, t), "saved": saved,
            "award_payer_default": (band or {}).get("award_payer_default", "buyer"), "is_published": bool(n.get("is_published"))}


class PlanItemIn(BaseModel):
    code: str
    charge: bool
    reason: Optional[str] = Field(default=None, max_length=300)


class FeePlanIn(BaseModel):
    tier: Optional[str] = Field(default=None, max_length=40)
    award_payer: Literal["buyer", "supplier"]
    payer_email: Optional[str] = Field(default=None, max_length=200)
    items: list[PlanItemIn]


@router.put("/notices/{ref}/fee-plan")
async def save_fee_plan(ref: str, body: FeePlanIn, admin=Depends(require_role(*WAIVERS))):
    n = await _notice(ref)
    if n.get("is_published"):
        raise HTTPException(status_code=409, detail="Fees are fixed once a tender is published")
    if body.tier and body.tier not in await _tiers():
        raise HTTPException(status_code=422, detail="Unknown tier")
    choice = {i.code: i for i in body.items}
    items = []
    for it in await _plan_items(n, body.tier):
        c = choice.get(it["code"])
        charge = bool(c.charge) if c else it["charge"]
        if charge and not it["has_rule"]:
            raise HTTPException(status_code=422, detail=f"No fee rule is set for '{it['name']}' in this country or band. Add one in Masters → Fee rules, or waive it.")
        if not charge and it["has_rule"] and not (c and (c.reason or "").strip()):
            raise HTTPException(status_code=422, detail=f"Give a reason for waiving '{it['name']}'.")
        rule = await db.emd_masters.find_one({"_id": ObjectId(it["rule_id"])}) if it["rule_id"] else None
        items.append({**it, "charge": charge, "reason": (c.reason if c and not charge else None),
                      "rule_snapshot": {k: rule.get(k) for k in ("name", "currency", "slabs", "progressive", "nil_below")} if rule else None})
    award = next(i for i in items if i["code"] == "transaction")
    email = (body.payer_email or "").strip().lower()
    if award["charge"] and body.award_payer == "buyer" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Enter the buyer's billing email — the award fee link is sent there.")
    band = await band_of(n.get("delivery_country"))
    plan = {"tier": body.tier, "band": (band or {}).get("code"), "award_payer": body.award_payer, "payer_email": email or None,
            "items": items, "confirmed_by": admin["email"], "confirmed_at": now_iso()}
    pct = next((s.get("percentage") for s in (award.get("rule_snapshot") or {}).get("slabs") or [] if s.get("fee_type") == "percentage"), None)
    supplier_pays = award["charge"] and body.award_payer == "supplier"
    await db.notices.update_one({"notice_ref": ref}, {"$set": {"fee_plan": plan, "winner_fee_enabled": supplier_pays,
                                                               "winner_fee_pct": float(pct or 0) if supplier_pays else 0,
                                                               "winner_fee_note": award.get("rate") if supplier_pays else None}})
    await audit_log("notice.fee_plan", admin, "notice", ref, {"tier": body.tier, "award_payer": body.award_payer,
                    "items": [{"code": i["code"], "charge": i["charge"], "reason": i["reason"]} for i in items]})
    return {"ok": True, "fee_plan": plan}


def plan_waives(notice: dict, code: str) -> bool:
    it = next((i for i in ((notice or {}).get("fee_plan") or {}).get("items") or [] if i["code"] == code), None)
    return bool(it) and not it["charge"]


# ----------------------------- award fee -----------------------------

async def raise_award_fee(bid_id: str, by_email: str) -> Optional[dict]:
    if await db.award_fees.find_one({"bid_id": bid_id}):
        return None
    b = await db.bids.find_one({"_id": ObjectId(bid_id)}) or {}
    n = await db.notices.find_one({"notice_ref": b.get("notice_ref")}) or {}
    plan = n.get("fee_plan") or {}
    it = next((i for i in plan.get("items") or [] if i["code"] == "transaction"), None)
    if not it:
        return None
    price = float(b.get("price_amount") or 0)
    base = {"bid_id": bid_id, "bid_ref": b.get("bid_ref"), "notice_ref": n.get("notice_ref"), "notice_title": n.get("title"),
            "vendor_ref": b.get("vendor_ref"), "company_name": b.get("company_name"), "award_value": price,
            "payer": plan.get("award_payer"), "created_at": now_iso(), "created_by": by_email}
    if not it["charge"]:
        doc = {**base, "status": "waived", "reason": it.get("reason"), "amount": 0}
        await db.award_fees.insert_one(doc)
        return doc
    snap = it.get("rule_snapshot") or {}
    pct_rule = all(s.get("fee_type") == "percentage" for s in snap.get("slabs") or [])
    rule_cur = (snap.get("currency") or "USD").upper()
    bid_cur = (b.get("price_currency") or rule_cur).upper()
    mismatch = pct_rule and bid_cur != rule_cur
    if mismatch:
        snap = {**snap, "nil_below": None, "slabs": [{**s, "pct_max": None} for s in snap.get("slabs") or []]}
    amount = compute_amount(snap, price) or 0.0
    currency = bid_cur if pct_rule else rule_cur
    doc = {**base, "amount": amount, "currency": currency, "rate": it.get("rate"),
           "note": f"Bid in {bid_cur}, rule in {rule_cur}: cap and no-fee threshold not applied — check before chasing." if mismatch else None,
           "payer_email": plan.get("payer_email") if plan.get("award_payer") == "buyer" else (b.get("vendor_email") or "").lower(),
           "status": "nil" if amount <= 0 else "unpaid"}
    await db.award_fees.insert_one(doc)
    if amount > 0:
        await _send_award_link(doc)
    return doc


async def _send_award_link(doc: dict) -> None:
    from notify import notify_role, vendor_confirm
    from routers.payments_extra import _checkout, _site
    try:
        chk = await _checkout(doc["amount"], doc["currency"], "award_fee", "/pay/complete", "/pay/complete?cancel=1", _site(),
                              {"bid_ref": doc.get("bid_ref") or ""}, {"bid_id": doc["bid_id"], "notice_ref": doc.get("notice_ref"),
                                                                     "payer_email": doc.get("payer_email"), "label": "Award fee",
                                                                     "buyer_email": doc.get("payer_email"), "buyer_role": doc.get("payer"),
                                                                     "product_code": "award_fee", "fee_kind": "transaction",
                                                                     "context_ref": doc.get("notice_ref")})
    except Exception as e:
        await db.award_fees.update_one({"bid_id": doc["bid_id"]}, {"$set": {"link_error": str(e)[:300]}})
        for role in ("admin", "accounting"):
            await notify_role(role, f"Award fee link failed — {doc.get('notice_ref')}",
                              f"<p>The Stripe payment link for the award fee on {doc.get('notice_ref')} could not be created. "
                              f"Open Billing → Award fees and press Resend link.</p>", "award_fee", doc["bid_id"])
        raise HTTPException(status_code=502, detail="Stripe could not create the payment link. Try Resend link again shortly.")
    await db.award_fees.update_one({"bid_id": doc["bid_id"]}, {"$set": {"session_id": chk["session_id"], "checkout_url": chk["checkout_url"],
                                                                       "link_sent_at": now_iso(), "link_error": None}, "$inc": {"links_sent": 1}})
    amt = f"{doc['currency']} {doc['amount']:,.2f}"
    who = "buyer" if doc.get("payer") == "buyer" else "awarded supplier"
    if doc.get("payer_email"):
        await vendor_confirm(doc["payer_email"], f"Award fee for tender {doc.get('notice_ref')}",
            f"<p>The tender <b>{doc.get('notice_title') or doc.get('notice_ref')}</b> has been awarded to {doc.get('company_name') or 'the winning supplier'} "
            f"for {doc['currency']} {doc['award_value']:,.2f}.</p><p><b>Award fee:</b> {amt} ({doc.get('rate') or 'as agreed'}). "
            f"The payment link is valid for 24 hours; PMC will resend it if needed.</p>", f"Pay {amt}", chk["checkout_url"])
    html = (f"<p>Award fee of <b>{amt}</b> raised for {doc.get('notice_ref')} (bid {doc.get('bid_ref')}). Payer: {who} "
            f"&lt;{doc.get('payer_email') or 'no email'}&gt;. Follow up in Billing → Award fees.</p>")
    for role in ("admin", "accounting"):
        await notify_role(role, f"Award fee due — {doc.get('notice_ref')}", html, "award_fee", doc["bid_id"])


async def apply_award_fee_payment(tx: dict) -> None:
    await db.award_fees.update_one({"bid_id": tx.get("bid_id"), "status": {"$ne": "paid"}},
                                   {"$set": {"status": "paid", "paid_at": now_iso(), "paid_session_id": tx["session_id"]}})
    await audit_log("award_fee.paid", {"email": tx.get("payer_email"), "role": "payer"}, "bid", tx.get("bid_id"),
                    {"amount": tx.get("amount"), "currency": tx.get("currency")})


@router.get("/award-fees")
async def list_award_fees(status: Optional[str] = None, admin=Depends(require_role("admin", "reviewer", "accounting", "auditor"))):
    q = {"status": status} if status else {}
    return {"items": [BaseDocument.out(d) async for d in db.award_fees.find(q, {"checkout_url": 0}).sort("created_at", -1).limit(300)]}


@router.post("/award-fees/{bid_id}/resend")
async def resend_award_fee(bid_id: str, admin=Depends(require_role("admin", "reviewer", "accounting"))):
    doc = await db.award_fees.find_one({"bid_id": bid_id})
    if not doc or doc["status"] != "unpaid":
        raise HTTPException(status_code=409, detail="Only unpaid award fees can be resent")
    await _send_award_link(doc)
    await audit_log("award_fee.resend", admin, "bid", bid_id, {})
    return {"ok": True}


class WaiveIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/award-fees/{bid_id}/waive")
async def waive_award_fee(bid_id: str, body: WaiveIn, admin=Depends(require_role(*WAIVERS))):
    r = await db.award_fees.update_one({"bid_id": bid_id, "status": "unpaid"},
                                       {"$set": {"status": "waived", "reason": body.reason, "waived_by": admin["email"], "waived_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(status_code=409, detail="Only unpaid award fees can be waived")
    await audit_log("award_fee.waive", admin, "bid", bid_id, {"reason": body.reason})
    return {"ok": True}


# ----------------------------- per-supplier fee plan -----------------------------

class SupplierPlanIn(BaseModel):
    fees: dict[str, Literal["charge", "waive"]]
    reason: Optional[str] = Field(default=None, max_length=300)


def supplier_plan(fees: dict, reason: Optional[str], by: str) -> dict:
    codes = {c for c, _ in SUPPLIER_FEES}
    clean = {k: v for k, v in (fees or {}).items() if k in codes}
    if "waive" in clean.values() and not (reason or "").strip():
        raise HTTPException(status_code=422, detail="Give a reason for waiving supplier fees.")
    return {"fees": clean, "reason": reason, "set_by": by, "set_at": now_iso()}


@router.get("/supplier-fees/defaults")
async def supplier_defaults(country: Optional[str] = None, admin=Depends(require_role(*WAIVERS))):
    band = await band_of(country)
    d = (band or {}).get("supplier_fees_default", "charge")
    return {"band": (band or {}).get("name"), "fees": [{"code": c, "name": n, "default": d} for c, n in SUPPLIER_FEES]}


@router.get("/vendors/{vendor_ref}/fee-plan")
async def get_vendor_plan(vendor_ref: str, admin=Depends(require_role(*WAIVERS))):
    v = await db.vendors.find_one({"vendor_ref": vendor_ref}, {"fee_plan": 1, "country": 1})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"fee_plan": v.get("fee_plan"), **(await supplier_defaults(v.get("country"), admin))}


@router.put("/vendors/{vendor_ref}/fee-plan")
async def set_vendor_plan(vendor_ref: str, body: SupplierPlanIn, admin=Depends(require_role(*WAIVERS))):
    plan = supplier_plan(body.fees, body.reason, admin["email"])
    r = await db.vendors.update_one({"vendor_ref": vendor_ref}, {"$set": {"fee_plan": plan}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await audit_log("vendor.fee_plan", admin, "vendor", vendor_ref, plan)
    return {"ok": True, "fee_plan": plan}


def vendor_waived(v: dict, code: str) -> bool:
    return ((v or {}).get("fee_plan") or {}).get("fees", {}).get(code) == "waive"
