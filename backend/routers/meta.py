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
    return [{"code": c, "name": n} for c, n in config.COUNTRIES]


@router.get("/public/stats")
async def public_stats() -> Dict[str, int]:
    """Homepage counters — public, no auth."""
    return {
        "notices_published": await db.notices.count_documents({"is_published": True}),
        "suppliers_approved": await db.vendors.count_documents({}),
        "packages_total": await db.packages.count_documents({}),
    }
