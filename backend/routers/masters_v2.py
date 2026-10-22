"""v52cm — Masters API: UNSPSC codes, geography (country/state/city), country licenses.

All GET endpoints are admin-authed (`require_role('admin', 'reviewer', ...)`)
except the public read-only ones used by the registration portal, which are
mounted under `/public/*` without auth. All WRITE endpoints are admin-only.
"""
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from bson import ObjectId

from db import db
from security import require_role
from models.base import now_iso

router = APIRouter(prefix="/api/v1/masters", tags=["masters-v2"])


# v52cm — common procurement-term aliases. UNSPSC uses formal terminology
# ("Methane", "Digesters", "Anaerobic") but admins search in plain language
# ("biogas", "solar farm"). Expand the free-text match with any configured
# synonyms so the search feels natural.
_UNSPSC_ALIASES = {
    "biogas":          ["methane", "digester", "anaerobic"],
    "solar farm":      ["solar power", "photovoltaic"],
    "solar plant":     ["solar power", "photovoltaic"],
    "pv":              ["photovoltaic"],
    "wind farm":       ["wind turbine", "wind generator"],
    "cbg":             ["methane", "biogas", "compressed natural gas"],
    "hvac":            ["heating ventilation", "air conditioning"],
    "stp":             ["sewage treatment"],
    "etp":             ["effluent treatment", "waste water"],
}


def _title_match_regex(term: str) -> str:
    """Expand user search with aliases, return a case-insensitive OR regex."""
    terms = {term}
    low = term.lower().strip()
    for key, alts in _UNSPSC_ALIASES.items():
        if key in low or low in key:
            terms.update(alts)
    import re as _re
    parts = [_re.escape(t) for t in terms if t]
    return "|".join(parts) if parts else _re.escape(term)


# ---------- UNSPSC ----------
@router.get("/unspsc/search")
async def unspsc_search(
    q: str = Query("", description="Free text to filter title_en or code"),
    level: Optional[str] = Query(None, description="segment|family|class|commodity"),
    segment: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """v52cm — search the full 150k UNSPSC codeset by code or English title."""
    query: dict = {"is_active": True}
    if level:
        query["level"] = level
    if segment:
        query["segment"] = segment
    if q.strip():
        s = q.strip()
        # Allow either prefix on the code or a text match on title_en.
        if s.isdigit():
            query["code"] = {"$regex": f"^0*{s}"}
        else:
            query["title_en"] = {"$regex": _title_match_regex(s), "$options": "i"}
    cursor = db.masters_unspsc.find(query, {"_id": 0}).limit(limit)
    return [doc async for doc in cursor]


@router.get("/unspsc/public/search")
async def unspsc_public_search(
    q: str = Query("", description="Free text search"),
    limit: int = Query(30, le=100),
):
    """Public read for the registration portal — codes-only, lighter payload."""
    query: dict = {"is_active": True, "level": "commodity"}
    if q.strip():
        s = q.strip()
        if s.isdigit():
            query["code"] = {"$regex": f"^0*{s}"}
        else:
            query["title_en"] = {"$regex": _title_match_regex(s), "$options": "i"}
    cursor = db.masters_unspsc.find(
        query, {"_id": 0, "code": 1, "title_en": 1}
    ).limit(limit)
    return [doc async for doc in cursor]


# ---------- Countries ----------
@router.get("/countries")
async def list_countries():
    """v52cm — all 250 ISO countries with postal-code regex for ZIP validation."""
    cursor = db.masters_countries.find(
        {"is_active": True},
        {"_id": 0, "code": 1, "iso3": 1, "name": 1, "nationality": 1,
         "phone_code": 1, "currency": 1, "accepted_currencies": 1,
         "postal_code_format": 1, "postal_code_regex": 1, "emoji": 1},
    ).sort("name", 1)
    out = []
    async for doc in cursor:
        if not doc.get("accepted_currencies"):
            doc["accepted_currencies"] = [doc["currency"]] if doc.get("currency") else []
        out.append(doc)
    return out


class CountryCurrenciesUpdate(BaseModel):
    accepted_currencies: List[str]
    primary: Optional[str] = None


@router.patch("/countries/{code}/currencies")
async def set_country_currencies(
    code: str,
    payload: CountryCurrenciesUpdate,
    admin=Depends(require_role("admin", "reviewer")),
):
    """v56t — set the currencies a country accepts. `primary` is the default
    pre-loaded on notice/bid/EMD currency pickers for that country; any active
    currency can still be chosen manually."""
    cc = (code or "").upper()
    if len(cc) != 2 or not cc.isalpha():
        raise HTTPException(status_code=422, detail="country code must be ISO-2")
    valid = set()
    async for c in db.currencies.find({"is_active": True}, {"_id": 0, "code": 1}):
        valid.add((c.get("code") or "").upper())
    accepted: List[str] = []
    for raw in payload.accepted_currencies:
        u = (raw or "").strip().upper()
        if u and u in valid and u not in accepted:
            accepted.append(u)
    primary = (payload.primary or (accepted[0] if accepted else "")).upper()
    if primary and primary not in accepted:
        accepted.insert(0, primary)
    set_fields = {"accepted_currencies": accepted}
    if primary:
        set_fields["currency"] = primary
    res = await db.masters_countries.update_one({"code": cc}, {"$set": set_fields})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Country {cc} not found")
    return {"ok": True, "code": cc, "accepted_currencies": accepted, "primary": primary}


# ---------- States / Provinces ----------
@router.get("/states")
async def list_states(country_code: str = Query(..., min_length=2, max_length=3)):
    """v52cm — states / provinces for a given country."""
    cc = country_code.upper()
    cursor = db.masters_states.find(
        {"country_code": cc, "is_active": True},
        {"_id": 0, "state_code": 1, "name": 1},
    ).sort("name", 1)
    return [doc async for doc in cursor]


# ---------- Cities ----------
@router.get("/cities")
async def list_cities(
    country_code: str = Query(..., min_length=2, max_length=3),
    state_code: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """v52cm — city list, filterable by state and/or free-text (for 150k rows)."""
    query: dict = {"country_code": country_code.upper(), "is_active": True}
    if state_code:
        query["state_code"] = state_code
    if q and q.strip():
        query["name"] = {"$regex": q.strip(), "$options": "i"}
    cursor = db.masters_cities.find(
        query, {"_id": 0, "name": 1, "state_code": 1, "state_name": 1}
    ).sort("name", 1).limit(limit)
    return [doc async for doc in cursor]


# ---------- Country licenses ----------
class CountryLicenseItem(BaseModel):
    code: str
    name: str
    mandatory: bool = False


class CountryLicenseUpdate(BaseModel):
    licenses: List[CountryLicenseItem]


# ---------- Banks master (escrow banking picker) ----------
@router.get("/banks")
async def list_banks(country_code: str, q: Optional[str] = None, limit: int = 60):
    """v52cz rev6 — Public, used by the escrow registration banking step.
    Returns a short list of banks for the given country, filterable by free
    text (name or SWIFT). Admin can extend the master; the UI gracefully
    falls back to free-text when a country has no entries yet."""
    cc = (country_code or "").upper()
    if not cc:
        return []
    filt: dict = {"country_code": cc}
    if q:
        pat = {"$regex": q.strip(), "$options": "i"}
        filt["$or"] = [{"name": pat}, {"swift_prefix": pat}, {"aliases": pat}]
    rows = []
    async for d in db.masters_banks.find(filt).sort("name", 1).limit(max(1, min(limit, 200))):
        d["_id"] = str(d["_id"])  # keep id so admin UI can edit/approve/merge
        rows.append(d)
    return rows


class BankSuggestIn(BaseModel):
    country_code: str
    name: str
    swift_prefix: Optional[str] = None


@router.post("/banks")
async def suggest_bank(payload: BankSuggestIn):
    """v52cz rev9 — deliberate exception to "writes are admin-only": the
    escrow registration banking step is pre-auth, and its "+" affordance lets
    a registrant add a bank missing from the master. Upsert keyed on
    (country_code, name); tagged source=user_suggested for later curation."""
    cc = (payload.country_code or "").strip().upper()
    name = " ".join((payload.name or "").split())
    if len(cc) != 2 or not cc.isalpha():
        raise HTTPException(status_code=422,
            detail="country_code must be a 2-letter ISO code")
    if not (2 <= len(name) <= 120):
        raise HTTPException(status_code=422,
            detail="name must be 2-120 characters")
    doc = {"country_code": cc, "name": name,
           "aliases": [], "currencies": [],
           "swift_prefix": (payload.swift_prefix or "").strip().upper() or None,
           "source": "user_suggested"}
    await db.masters_banks.update_one(
        {"country_code": cc, "name": name}, {"$set": doc}, upsert=True)
    out = await db.masters_banks.find_one(
        {"country_code": cc, "name": name})
    out["_id"] = str(out["_id"])
    return out


# ---------- Admin bank curation (v52e) ----------

class BankApproveIn(BaseModel):
    swift_prefix: Optional[str] = None
    currencies: Optional[List[str]] = None
    aliases: Optional[List[str]] = None


class BankMergeIn(BaseModel):
    target_id: str  # ObjectId of the bank to keep


@router.get("/banks-admin/suggested")
async def list_suggested_banks(
        admin=Depends(require_role("admin", "reviewer"))):
    """v52e — admin curation queue for banks that registrants have added
    via the "+ Add" affordance. Returns oldest-first so new suggestions
    bubble up at the top of the list when reviewers sort by created_at."""
    rows = []
    async for d in db.masters_banks.find({"source": "user_suggested"}
                                           ).sort("name", 1).limit(200):
        d["_id"] = str(d["_id"])
        rows.append(d)
    return {"items": rows, "total": len(rows)}


@router.post("/banks-admin/{bank_id}/approve")
async def approve_suggested_bank(bank_id: str, payload: BankApproveIn,
                                   admin=Depends(require_role("admin"))):
    """Promote a user_suggested bank to a curated entry. Reviewer can
    enrich swift_prefix / currencies / aliases at the same time."""
    try:
        oid = ObjectId(bank_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Bad bank id")
    update: dict = {"source": "curated",
                     "curated_by": admin.get("email"),
                     "curated_at": now_iso()}
    if payload.swift_prefix is not None:
        update["swift_prefix"] = payload.swift_prefix.strip().upper() or None
    if payload.currencies is not None:
        update["currencies"] = [c.strip().upper() for c in payload.currencies if c.strip()]
    if payload.aliases is not None:
        update["aliases"] = [a.strip() for a in payload.aliases if a.strip()]
    r = await db.masters_banks.update_one({"_id": oid}, {"$set": update})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bank not found")
    doc = await db.masters_banks.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return doc


@router.post("/banks-admin/{bank_id}/merge")
async def merge_suggested_bank(bank_id: str, payload: BankMergeIn,
                                 admin=Depends(require_role("admin"))):
    """Mark the suggestion as a duplicate of `target_id` and delete it.
    Target gets the suggestion's name recorded as an alias so the search
    still finds it. Preserves audit continuity in masters_banks_merge_log."""
    try:
        src_oid = ObjectId(bank_id)
        tgt_oid = ObjectId(payload.target_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Bad bank id")
    src = await db.masters_banks.find_one({"_id": src_oid})
    tgt = await db.masters_banks.find_one({"_id": tgt_oid})
    if not src or not tgt:
        raise HTTPException(status_code=404, detail="Bank not found")
    if src["country_code"] != tgt["country_code"]:
        raise HTTPException(status_code=422,
            detail="Cannot merge banks across countries")
    await db.masters_banks.update_one(
        {"_id": tgt_oid},
        {"$addToSet": {"aliases": src["name"]}})
    await db.masters_banks.delete_one({"_id": src_oid})
    await db.masters_banks_merge_log.insert_one({
        "merged_at": now_iso(), "merged_by": admin.get("email"),
        "source": src, "target_id": str(tgt_oid)})
    return {"ok": True, "target_id": str(tgt_oid)}


@router.delete("/banks-admin/{bank_id}")
async def reject_suggested_bank(bank_id: str,
                                   admin=Depends(require_role("admin"))):
    """Hard-reject a suggestion (spam / wrong country / etc)."""
    try:
        oid = ObjectId(bank_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Bad bank id")
    src = await db.masters_banks.find_one({"_id": oid})
    if not src:
        raise HTTPException(status_code=404, detail="Bank not found")
    if src.get("source") != "user_suggested":
        raise HTTPException(status_code=400,
            detail="Can only reject user_suggested banks via this endpoint")
    await db.masters_banks.delete_one({"_id": oid})
    await db.masters_banks_merge_log.insert_one({
        "rejected_at": now_iso(), "rejected_by": admin.get("email"),
        "source": src})
    return {"ok": True}


# ---------- Country-specific business-identifier formats ----------
@router.get("/country-formats/{country_code}")
async def get_country_formats(country_code: str):
    """v52cz rev4 — reg-number / tax-id / VAT display label + example +
    validation regex for the given country. Public read, used by the escrow
    institution registration (and other KYC forms) to live-validate what
    the user types against the real local format instead of accepting any
    free-text garbage. Falls back to `{reg_number: null, tax_id: null,
    vat: null}` when a country isn't seeded yet, so the UI degrades to
    free text with no false negatives."""
    cc = country_code.upper()
    doc = await db.masters_country_formats.find_one({"country_code": cc}, {"_id": 0})
    if not doc:
        return {"country_code": cc, "reg_number": None, "tax_id": None, "vat": None}
    return doc


@router.get("/country-licenses/{country_code}")
async def get_country_licenses(country_code: str):
    """v52cm — public read: what licenses does this country require?"""
    doc = await db.masters_country_licenses.find_one(
        {"country_code": country_code.upper()}, {"_id": 0}
    )
    if not doc:
        return {"country_code": country_code.upper(), "licenses": []}
    return doc


@router.get("/country-licenses")
async def list_country_licenses(admin=Depends(require_role("admin", "reviewer"))):
    """Admin list — every country that has license entries configured."""
    cursor = db.masters_country_licenses.find({}, {"_id": 0}).sort("country_code", 1)
    return [doc async for doc in cursor]


@router.put("/country-licenses/{country_code}")
async def put_country_licenses(
    country_code: str,
    payload: CountryLicenseUpdate,
    admin=Depends(require_role("admin")),
):
    """Admin upsert the full license list for a country."""
    cc = country_code.upper()
    await db.masters_country_licenses.update_one(
        {"country_code": cc},
        {"$set": {"licenses": [l.model_dump() for l in payload.licenses]}},
        upsert=True,
    )
    doc = await db.masters_country_licenses.find_one({"country_code": cc}, {"_id": 0})
    return doc
