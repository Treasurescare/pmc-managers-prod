"""Wave 35 — Product Catalog (revenue-stream master).

Admin-editable catalog of every revenue line for the platform, decoupled from
the PDFs (CA-02 client-side + CA-03 supplier-side). All amounts are configurable
per row so admin controls monetisation, not hard-coded fees.

Pricing model options (extensible):
  * fixed              — one-off flat fee (e.g. $50k business case)
  * range              — one-off, quoted between min & max (advisory)
  * percentage         — % of an underlying value (contract, programme)
  * monthly            — recurring subscription (per calendar month)
  * annual             — recurring subscription (per year)
  * per_delegate       — one-off, quantity-based (e.g. training)
  * per_user_monthly   — recurring, quantity-based (additional users)
  * cost_recovery      — invoice at cost, no margin
  * package            — a bundle of other products (Bronze/Silver/…)

Sides:
  * client             — buyer-side (CA-02)
  * supplier           — vendor-side (CA-03)
  * both               — applicable to either

Every product carries a `code` (stable, admin-editable slug) and a Stripe
`lookup_key` — those two are what checkout uses; internal Mongo `_id` is never
exposed at the checkout boundary.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from audit import audit_log

router = APIRouter(prefix="/api/v1/products", tags=["products"])


PRICING_MODELS = [
    "fixed", "range", "percentage", "monthly", "annual",
    "per_delegate", "per_user_monthly", "cost_recovery", "package",
]
SIDES = ["client", "supplier", "both"]


class ProductIn(BaseModel):
    code: str = Field(..., min_length=2, max_length=64,
                       description="Stable slug used as Stripe lookup_key")
    name: str
    side: str = "client"                          # client | supplier | both
    category: str                                 # e.g. "Pre-Award", "Post-Award", "EOP", "Package"
    subcategory: Optional[str] = None
    description: str = ""
    pricing_model: str = "fixed"
    currency: str = "USD"                         # ISO 4217, admin can change per product
    amount: Optional[float] = None                # for fixed / monthly / annual / per_delegate
    min_amount: Optional[float] = None            # for range
    max_amount: Optional[float] = None            # for range
    percentage: Optional[float] = None            # for percentage (0-100)
    percentage_of: Optional[str] = None           # "contract_value" | "programme_value" | ...
    unit_label: Optional[str] = None              # "per delegate", "per month", …
    package_tier: Optional[str] = None            # Bronze | Silver | Gold | Platinum | SME | Mid | Tier1
    conditions: str = ""                          # eligibility / notes (from PDF)
    is_active: bool = True
    stripe_price_id: Optional[str] = None         # backfilled by catalog-sync job
    display_order: int = 100


class ProductOut(ProductIn):
    id: str
    created_at: str
    updated_at: str


def _out(doc: dict) -> dict:
    d = BaseDocument.out(doc)
    d.pop("tenant_id", None)
    return d


@router.get("")
async def list_products(side: Optional[str] = None,
                         category: Optional[str] = None,
                         active_only: bool = True,
                         admin=Depends(require_role("admin", "reviewer", "auditor", "accounting"))):
    q: dict = {}
    if side:
        q["$or"] = [{"side": side}, {"side": "both"}]
    if category:
        q["category"] = category
    if active_only:
        q["is_active"] = True
    docs = await db.products.find(q).sort([("display_order", 1), ("name", 1)]).to_list(500)
    return {"items": [_out(d) for d in docs], "count": len(docs)}


@router.get("/public")
async def list_products_public(side: str):
    """Public catalog — no auth. Vendor/client portals call this to render
    price pages. Only returns active products; secrets (stripe_price_id) stripped."""
    if side not in SIDES:
        raise HTTPException(status_code=400, detail="Invalid side")
    q = {"is_active": True, "$or": [{"side": side}, {"side": "both"}]}
    docs = await db.products.find(q).sort([("display_order", 1), ("name", 1)]).to_list(500)
    out = []
    for d in docs:
        d = _out(d)
        d.pop("stripe_price_id", None)
        out.append(d)
    return {"items": out, "count": len(out)}


@router.post("")
async def create_product(payload: ProductIn,
                          admin=Depends(require_role("admin"))):
    if payload.pricing_model not in PRICING_MODELS:
        raise HTTPException(status_code=400, detail=f"pricing_model must be one of {PRICING_MODELS}")
    if payload.side not in SIDES:
        raise HTTPException(status_code=400, detail=f"side must be one of {SIDES}")
    if await db.products.find_one({"code": payload.code}):
        raise HTTPException(status_code=409, detail=f"Product code '{payload.code}' already exists")
    doc = payload.model_dump()
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    doc["created_by"] = admin["email"]
    res = await db.products.insert_one(doc)
    await audit_log("product.create", admin, "product", payload.code,
                    {"name": payload.name, "pricing_model": payload.pricing_model})
    return _out(await db.products.find_one({"_id": res.inserted_id}))


@router.patch("/{product_id}")
async def update_product(product_id: str, payload: ProductIn,
                          admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product id")
    existing = await db.products.find_one({"_id": ObjectId(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.code != existing["code"]:
        clash = await db.products.find_one({"code": payload.code, "_id": {"$ne": ObjectId(product_id)}})
        if clash:
            raise HTTPException(status_code=409, detail=f"Code '{payload.code}' is taken")
    upd = payload.model_dump()
    upd["updated_at"] = now_iso()
    upd["updated_by"] = admin["email"]
    await db.products.update_one({"_id": ObjectId(product_id)}, {"$set": upd})
    await audit_log("product.update", admin, "product", payload.code,
                    {"name": payload.name})
    return _out(await db.products.find_one({"_id": ObjectId(product_id)}))


@router.delete("/{product_id}")
async def delete_product(product_id: str,
                          admin=Depends(require_role("admin"))):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product id")
    doc = await db.products.find_one({"_id": ObjectId(product_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.products.update_one({"_id": ObjectId(product_id)},
                                  {"$set": {"is_active": False, "updated_at": now_iso()}})
    await audit_log("product.deactivate", admin, "product", doc.get("code", product_id), {})
    return {"ok": True, "deactivated": True}


@router.post("/reseed")
async def reseed_catalog(admin=Depends(require_role("admin"))):
    """Re-run the default seed. Existing codes are left alone (idempotent);
    only new/missing codes are inserted."""
    from product_catalog_seed import DEFAULT_PRODUCTS
    inserted = 0
    for row in DEFAULT_PRODUCTS:
        if await db.products.find_one({"code": row["code"]}):
            continue
        doc = dict(row)
        doc["created_at"] = now_iso()
        doc["updated_at"] = now_iso()
        doc["created_by"] = admin["email"]
        await db.products.insert_one(doc)
        inserted += 1
    await audit_log("product.reseed", admin, "product", "*",
                    {"inserted": inserted, "total_defaults": len(DEFAULT_PRODUCTS)})
    return {"ok": True, "inserted": inserted, "total_defaults": len(DEFAULT_PRODUCTS)}
