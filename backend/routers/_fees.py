"""Fee Type master + fee-rule computation shared by masters, tender builder and billing."""
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException

from db import db

# Default fee types (editable in Masters → Fee types). Attributes only — no prices.
DEFAULT_FEE_TYPES = [
    {"code": "subscription", "name": "Subscription", "timing": "upfront", "calc": "fixed",
     "amount_mode": "single", "category_scope": "all", "billing": "yearly", "used_in_tender_builder": True},
    {"code": "premium_subscription", "name": "Premium subscription", "timing": "upfront", "calc": "fixed",
     "amount_mode": "single", "category_scope": "all", "billing": "yearly", "used_in_tender_builder": False},
    {"code": "registration", "name": "Registration", "timing": "upfront", "calc": "fixed",
     "amount_mode": "single", "category_scope": "all", "billing": "one_time", "used_in_tender_builder": False},
    {"code": "emd", "name": "EMD payment", "timing": "upfront", "calc": "either",
     "amount_mode": "range", "category_scope": "all", "billing": "one_time", "used_in_tender_builder": False},
    {"code": "tender_fee", "name": "Tender fee", "timing": "upfront", "calc": "either",
     "amount_mode": "range", "category_scope": "all", "billing": "one_time", "used_in_tender_builder": False},
    {"code": "tender_management", "name": "Tender management fee", "timing": "on_completion", "calc": "either",
     "amount_mode": "range", "category_scope": "selected", "billing": "one_time", "used_in_tender_builder": True},
    {"code": "transaction", "name": "Transaction fee", "timing": "on_completion", "calc": "percentage",
     "amount_mode": "range", "category_scope": "all", "billing": "one_time", "used_in_tender_builder": False},
    {"code": "data_intel", "name": "Data intel", "timing": "upfront", "calc": "fixed",
     "amount_mode": "single", "category_scope": "all", "billing": "yearly", "used_in_tender_builder": False},
]


async def seed_fee_types() -> None:
    for ft in DEFAULT_FEE_TYPES:
        await db.fee_types.update_one({"code": ft["code"]},
            {"$setOnInsert": {**ft, "is_active": True, "is_system": True}}, upsert=True)


async def get_fee_type(code: str) -> Optional[dict]:
    return await db.fee_types.find_one({"code": code})


def validate_rule_against_type(ft: dict, body: dict) -> None:
    slabs = body.get("slabs") or []
    if not slabs:
        raise HTTPException(status_code=422, detail="Add an amount.")
    if ft.get("amount_mode") == "single":
        if len(slabs) != 1:
            raise HTTPException(status_code=422, detail=f"'{ft['name']}' uses a single amount — keep exactly one line.")
        slabs[0]["tender_value_min"], slabs[0]["tender_value_max"] = 0, None
    calc = ft.get("calc")
    for s in slabs:
        if calc in ("fixed", "percentage") and s.get("fee_type") != calc:
            raise HTTPException(status_code=422, detail=f"'{ft['name']}' must be {calc}.")
        if s.get("fee_type") == "fixed" and not (s.get("fixed_amount") or 0) > 0:
            raise HTTPException(status_code=422, detail="Fixed amounts must be greater than 0.")
        if s.get("fee_type") == "percentage" and not (s.get("percentage") or 0) > 0:
            raise HTTPException(status_code=422, detail="Percentages must be greater than 0.")
    cats = body.get("categories") or []
    if ft.get("category_scope") == "selected" and not cats:
        raise HTTPException(status_code=422, detail=f"'{ft['name']}' applies to selected categories — tick at least one.")
    if ft.get("category_scope") == "all":
        body["categories"] = []
    body["category"] = body["categories"][0] if len(body.get("categories") or []) == 1 else None


def compute_amount(rule: dict, value: Optional[float]) -> Optional[float]:
    """Fee for a tender value. None when the value is required but missing / no slab matches."""
    slabs = rule.get("slabs") or []
    if len(slabs) == 1 and slabs[0].get("fee_type") == "fixed" and not slabs[0].get("tender_value_max") \
            and not (slabs[0].get("tender_value_min") or 0):
        return float(slabs[0].get("fixed_amount") or 0)
    if value is None:
        return None
    v = float(value)
    for s in slabs:
        lo, hi = s.get("tender_value_min") or 0, s.get("tender_value_max")
        if v >= lo and (hi is None or v < hi):
            if s.get("fee_type") == "fixed":
                return float(s.get("fixed_amount") or 0)
            amt = v * float(s.get("percentage") or 0) / 100.0
            if s.get("pct_min"):
                amt = max(amt, float(s["pct_min"]))
            if s.get("pct_max"):
                amt = min(amt, float(s["pct_max"]))
            return round(amt, 2)
    return None


def _rule_matches_category(rule: dict, cat: str) -> int:
    """2 = category-specific match, 1 = all-category rule, 0 = no match."""
    cats = [str(c).strip().lower() for c in (rule.get("categories") or ([rule["category"]] if rule.get("category") else []))]
    if not cats:
        return 1
    return 2 if cat and cat.lower() in cats else 0


async def tender_builder_fees(country: Optional[str], doc: dict) -> list:
    """Per-tender fees (non-yearly fee types flagged for the tender builder) for a draft."""
    if not country:
        return []
    header = doc.get("header") or {}
    cat = str(header.get("product_category") or "").strip()
    value = header.get("tender_value") or header.get("budget_amount")
    try:
        value = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        value = None
    types = [t async for t in db.fee_types.find({"used_in_tender_builder": True, "is_active": True,
                                                 "billing": {"$ne": "yearly"}})]
    paid = doc.get("fees_paid") or {}
    out = []
    for ft in types:
        best, score = None, 0
        async for r in db.emd_masters.find({"kind": ft["code"], "country": country.upper(), "is_active": True}):
            s = _rule_matches_category(r, cat)
            if s > score:
                best, score = r, s
        if not best:
            continue
        amount = compute_amount(best, value)
        paid_total = float((paid.get(ft["code"]) or {}).get("amount") or 0)
        outstanding = None if amount is None else max(0.0, round(amount - paid_total, 2))
        out.append({"code": ft["code"], "name": ft["name"], "timing": ft["timing"],
                    "rule_id": str(best["_id"]), "rule_name": best.get("name"),
                    "currency": (best.get("currency") or "USD").upper(),
                    "amount": amount, "paid_amount": paid_total, "outstanding": outstanding,
                    "needs_value": amount is None,
                    "paid": amount is not None and outstanding <= 0.0})
    return out


async def assert_fees_paid(principal: dict, doc: Optional[dict], stage: str) -> None:
    """stage='work' → upfront fees must be paid; stage='submit' → every fee must be paid."""
    if not doc or principal.get("kind") != "vendor":
        return
    from routers._tender_access import vendor_country
    v = await db.vendors.find_one({"_id": ObjectId(principal["id"])})
    fees = await tender_builder_fees(vendor_country(v or {}), doc)
    due = [f for f in fees if not f["paid"] and (stage == "submit" or f["timing"] == "upfront")]
    if not due:
        return
    f = due[0]
    if f["needs_value"]:
        raise HTTPException(status_code=402,
            detail=f"Enter the tender value and save so the {f['name']} can be calculated, then pay it to continue.")
    raise HTTPException(status_code=402,
        detail=f"{f['name']} of {f['currency']} {f['outstanding']:,.2f} is due for this tender. Pay it from the Fees panel to continue.")
