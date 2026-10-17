from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import config
from db import db

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "service": "pmc-tender-v2-api", "phase": "pilot"}


@router.get("/kz-licenses")
async def kz_licenses() -> Dict[str, Any]:
    return {"licenses": config.KZ_LICENSE_TYPES,
            "category_map": config.KZ_CATEGORY_LICENSE_MAP}


@router.get("/countries")
async def countries() -> List[Dict[str, Any]]:
    """Returns the full country master (dr5hn, 250 rows) with trilingual
    display labels. The vendor registration portal uses this to populate
    the Section A country dropdown.

    v54a — previously served only the 30 pilot-config countries, which left
    vendors in Bangladesh / Nigeria / etc with no way to self-register.
    Now reads from `masters_countries` and falls back to config.COUNTRIES
    only if the master collection is empty (first boot, offline cache).
    """
    rows: List[Dict[str, Any]] = []
    try:
        async for c in db.masters_countries.find({}, {
            "_id": 0, "code": 1, "name": 1, "iso3": 1, "nationality": 1,
            "phone_code": 1, "currency": 1, "emoji": 1,
        }).sort("name", 1):
            name = c.get("name") or c.get("code") or ""
            rows.append({
                "code": c.get("code"),
                "name": name,
                # trilingual label slots — populated with the English name as
                # a safe default so existing frontend keys never resolve to
                # undefined. The i18n team can override specific rows later.
                "name_en": name, "name_ru": name, "name_kk": name,
                "iso3": c.get("iso3"), "nationality": c.get("nationality"),
                "phone_code": c.get("phone_code"), "currency": c.get("currency"),
                "emoji": c.get("emoji"),
            })
    except Exception:
        rows = []
    if rows:
        return rows
    out = []
    for row in config.COUNTRIES:
        code, en, ru, kk = row if len(row) == 4 else (row[0], row[1], row[1], row[1])
        out.append({"code": code, "name": en, "name_en": en, "name_ru": ru, "name_kk": kk})
    return out


@router.get("/public/stats")
async def public_stats() -> Dict[str, int]:
    """Homepage counters — public, no auth."""
    # Ledger event count: pick the first collection that exists among the known
    # audit-ledger names so this remains valid whichever migration ran.
    ledger_events = 0
    for coll_name in ("audit_events", "audit_ledger", "ledger_events", "events"):
        try:
            n = await db[coll_name].count_documents({})
            if n:
                ledger_events = n
                break
        except Exception:
            continue
    return JSONResponse(
        content={
            "notices_published": await db.notices.count_documents({"is_published": True}),
            "suppliers_approved": await db.vendors.count_documents({}),
            "packages_total": await db.packages.count_documents({}),
            "ledger_events": ledger_events,
        },
        # v52cu — no-store so the landing "tenders open for bids" counter
        # updates the instant a notice is published.
        headers={"Cache-Control": "no-store, no-cache, must-revalidate",
                 "Pragma": "no-cache", "Expires": "0"},
    )


@router.get("/public/escrow-summary")
async def public_escrow_summary() -> Dict[str, Any]:
    """Aggregate EMD figures — safe, only totals never per-vendor amounts.

    Returns per-currency totals plus a USD-equivalent estimate (using a very
    coarse fixed FX table; refined by the reporting job downstream).
    """
    FX_TO_USD = {"USD": 1.0, "INR": 0.012, "KZT": 0.0021, "EUR": 1.08, "GBP": 1.27}
    per_currency: Dict[str, Dict[str, Any]] = {}
    total_usd = 0.0
    total_bids = 0
    async for row in db.bids.aggregate([
        {"$match": {"emd_paid_amount": {"$gt": 0}}},
        {"$group": {"_id": "$emd_currency", "total": {"$sum": "$emd_paid_amount"}, "count": {"$sum": 1}}},
    ]):
        cur = row["_id"] or "USD"
        per_currency[cur] = {"total": float(row["total"]), "bids": int(row["count"])}
        total_usd += float(row["total"]) * FX_TO_USD.get(cur, 1.0)
        total_bids += int(row["count"])
    pending = await db.bids.count_documents({"status": "emd_pending"})
    return {
        "per_currency": per_currency,
        "total_usd_equiv": round(total_usd, 2),
        "bids_paid": total_bids,
        "bids_pending": pending,
    }
