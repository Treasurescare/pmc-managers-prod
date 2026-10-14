"""v52cm — Masters API: UNSPSC codes, geography (country/state/city), country licenses.

All GET endpoints are admin-authed (`require_role('admin', 'reviewer', ...)`)
except the public read-only ones used by the registration portal, which are
mounted under `/public/*` without auth. All WRITE endpoints are admin-only.
"""
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from db import db
from security import require_role

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
         "phone_code": 1, "currency": 1, "postal_code_format": 1,
         "postal_code_regex": 1, "emoji": 1},
    ).sort("name", 1)
    return [doc async for doc in cursor]


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
