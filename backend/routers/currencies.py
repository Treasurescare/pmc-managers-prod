"""Currency master — ISO-4217 codes used by Notice/Bid/EMD money fields.

Keeps budget currencies out of hard-coded dropdowns so admins can
enable/disable regional currencies without a redeploy.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from pydantic import BaseModel, Field

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/masters", tags=["masters"])


def _out(doc: dict) -> dict:
    return BaseDocument.out(doc)


class CurrencyIn(BaseModel):
    code: str = Field(..., min_length=3, max_length=3, description="ISO-4217 (e.g. USD)")
    name: str = Field(..., min_length=1, max_length=120)
    symbol: Optional[str] = None
    decimals: int = 2
    is_active: bool = True


# ---------- Default seed (ISO-4217 common currencies) ----------
DEFAULT_CURRENCIES: List[dict] = [
    {"code": "USD", "name": "US Dollar", "symbol": "$", "decimals": 2},
    {"code": "EUR", "name": "Euro", "symbol": "€", "decimals": 2},
    {"code": "GBP", "name": "Pound Sterling", "symbol": "£", "decimals": 2},
    {"code": "INR", "name": "Indian Rupee", "symbol": "₹", "decimals": 2},
    {"code": "KZT", "name": "Kazakhstani Tenge", "symbol": "₸", "decimals": 2},
    {"code": "AED", "name": "UAE Dirham", "symbol": "د.إ", "decimals": 2},
    {"code": "SAR", "name": "Saudi Riyal", "symbol": "﷼", "decimals": 2},
    {"code": "RUB", "name": "Russian Rouble", "symbol": "₽", "decimals": 2},
    {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥", "decimals": 2},
    {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "decimals": 0},
    {"code": "SGD", "name": "Singapore Dollar", "symbol": "S$", "decimals": 2},
    {"code": "AUD", "name": "Australian Dollar", "symbol": "A$", "decimals": 2},
    {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$", "decimals": 2},
    {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF", "decimals": 2},
    {"code": "HKD", "name": "Hong Kong Dollar", "symbol": "HK$", "decimals": 2},
    {"code": "ZAR", "name": "South African Rand", "symbol": "R", "decimals": 2},
    {"code": "TRY", "name": "Turkish Lira", "symbol": "₺", "decimals": 2},
    {"code": "BRL", "name": "Brazilian Real", "symbol": "R$", "decimals": 2},
    {"code": "QAR", "name": "Qatari Riyal", "symbol": "ر.ق", "decimals": 2},
    {"code": "OMR", "name": "Omani Rial", "symbol": "ر.ع.", "decimals": 3},
    {"code": "KWD", "name": "Kuwaiti Dinar", "symbol": "د.ك", "decimals": 3},
    {"code": "BHD", "name": "Bahraini Dinar", "symbol": "د.ب", "decimals": 3},
    {"code": "UZS", "name": "Uzbekistani Som", "symbol": "сўм", "decimals": 2},
    {"code": "KGS", "name": "Kyrgyzstani Som", "symbol": "сом", "decimals": 2},
    {"code": "AZN", "name": "Azerbaijani Manat", "symbol": "₼", "decimals": 2},
]


async def seed_defaults() -> None:
    """Idempotent — insert any missing default currencies on cold start."""
    if await db.currencies.count_documents({}) >= len(DEFAULT_CURRENCIES):
        return
    now = now_iso()
    inserted = 0
    for c in DEFAULT_CURRENCIES:
        try:
            if await db.currencies.find_one({"code": c["code"]}):
                continue
            await db.currencies.insert_one({**c, "is_active": True, "created_at": now})
            inserted += 1
        except Exception:
            continue
    if inserted:
        import logging
        logging.info(f"Seeded {inserted} currencies into currency master")


# ---------- Routes ----------

@router.get("/currencies")
async def list_currencies(
    include_inactive: bool = False,
    admin=Depends(require_role("admin", "reviewer", "support", "committee_member")),
) -> List[dict]:
    q: dict = {} if include_inactive else {"is_active": True}
    rows = [_out(r) async for r in db.currencies.find(q).sort("code", 1)]
    return rows


@router.get("/currencies/public")
async def list_currencies_public() -> List[dict]:
    """PUBLIC — used by Notice/Bid create forms and vendor onboarding."""
    rows = [_out(r) async for r in
            db.currencies.find({"is_active": True}).sort("code", 1)]
    return rows


@router.post("/currencies")
async def create_currency(
    payload: CurrencyIn,
    admin=Depends(require_role("admin")),
) -> dict:
    code = payload.code.upper()
    if await db.currencies.find_one({"code": code}):
        raise HTTPException(status_code=409, detail="Currency code already exists")
    doc = payload.model_dump()
    doc["code"] = code
    doc.update({"created_at": now_iso(), "created_by": admin["id"]})
    res = await db.currencies.insert_one(doc)
    doc["_id"] = res.inserted_id
    await audit_log("currency.create", admin, "currency", code, {"name": payload.name})
    return _out(doc)


@router.patch("/currencies/{currency_id}")
async def update_currency(
    currency_id: str,
    payload: CurrencyIn,
    admin=Depends(require_role("admin")),
) -> dict:
    update = payload.model_dump()
    update["code"] = update["code"].upper()
    update["updated_at"] = now_iso()
    r = await db.currencies.update_one(
        {"_id": ObjectId(currency_id)}, {"$set": update},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.currencies.find_one({"_id": ObjectId(currency_id)})
    await audit_log("currency.update", admin, "currency", update["code"],
                    {"name": payload.name})
    return _out(doc)


@router.delete("/currencies/{currency_id}")
async def deactivate_currency(
    currency_id: str,
    admin=Depends(require_role("admin")),
) -> dict:
    doc = await db.currencies.find_one({"_id": ObjectId(currency_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await db.currencies.update_one(
        {"_id": ObjectId(currency_id)},
        {"$set": {"is_active": False, "updated_at": now_iso()}},
    )
    await audit_log("currency.deactivate", admin, "currency",
                    doc.get("code", ""), {"name": doc.get("name", "")})
    return {"ok": True, "deactivated": True}
