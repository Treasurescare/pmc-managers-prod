from typing import Optional, List, Dict, Any
from fastapi import APIRouter
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
async def countries() -> List[Dict[str, str]]:
    """Returns each country with trilingual labels. Client picks by current lang."""
    out = []
    for row in config.COUNTRIES:
        code, en, ru, kk = row if len(row) == 4 else (row[0], row[1], row[1], row[1])
        out.append({"code": code, "name": en, "name_en": en, "name_ru": ru, "name_kk": kk})
    return out


@router.get("/public/stats")
async def public_stats() -> Dict[str, int]:
    """Homepage counters — public, no auth."""
    return {
        "notices_published": await db.notices.count_documents({"is_published": True}),
        "suppliers_approved": await db.vendors.count_documents({}),
        "packages_total": await db.packages.count_documents({}),
    }
