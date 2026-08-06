"""Wave 40 — UNSPSC-lite Taxonomy.

Pared-down UNSPSC (v25) seed covering the segments PMC Managers actually
operates against. Not the full 150k-code catalog — a curated 60+ node set
across Construction, Medical, IT & Telecom, Professional Services, Utilities,
Facilities, and Education. Enough for spend analytics + product tagging.

Data model in `db.taxonomy_nodes`:
  { code: "72" | "7215" | "721510", parent_code, level, title, category }

Endpoints:
  GET  /api/v1/taxonomy/tree          (public)
  GET  /api/v1/taxonomy/search?q=…    (public)
  POST /api/v1/taxonomy/reseed        (admin) — idempotent
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends

from db import db
from models.base import BaseDocument, now_iso
from security import require_role
from unspsc_seed import UNSPSC_NODES
from audit import audit_log

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])


def _out(d: dict) -> dict:
    return BaseDocument.out(d)


@router.get("/tree")
async def get_tree():
    """PUBLIC — returns the full taxonomy grouped by segment (2-digit)."""
    nodes = [_out(n) async for n in db.taxonomy_nodes.find({}).sort("code", 1)]
    # Group by segment (level 1, code length 2)
    grouped: dict = {}
    for n in nodes:
        seg = n["code"][:2]
        grouped.setdefault(seg, []).append(n)
    segments = []
    for seg_code, items in grouped.items():
        seg_row = next((i for i in items if i["code"] == seg_code), None)
        segments.append({
            "segment_code": seg_code,
            "segment_title": seg_row["title"] if seg_row else seg_code,
            "nodes": sorted(items, key=lambda x: x["code"]),
        })
    return {"segments": sorted(segments, key=lambda s: s["segment_code"]),
            "total_nodes": len(nodes)}


@router.get("/search")
async def search_taxonomy(q: str = "", limit: int = 25):
    """PUBLIC — case-insensitive search on title + code prefix."""
    q = (q or "").strip()
    if not q:
        return {"items": [], "total": 0}
    query = {"$or": [
        {"code": {"$regex": f"^{q}", "$options": "i"}},
        {"title": {"$regex": q, "$options": "i"}},
    ]}
    items = [_out(n) async for n in db.taxonomy_nodes.find(query)
                                          .sort("code", 1).limit(limit)]
    return {"items": items, "total": len(items)}


@router.get("/lookup/{code}")
async def lookup(code: str):
    """PUBLIC — resolve a single UNSPSC code to its full ancestry chain."""
    node = await db.taxonomy_nodes.find_one({"code": code})
    if not node:
        raise HTTPException(status_code=404, detail=f"Code {code} not found")
    chain = [_out(node)]
    while node.get("parent_code"):
        node = await db.taxonomy_nodes.find_one({"code": node["parent_code"]})
        if not node:
            break
        chain.append(_out(node))
    return {"code": code, "chain": list(reversed(chain))}


@router.post("/reseed")
async def reseed(admin=Depends(require_role("admin"))):
    """Idempotent — only inserts missing codes. Safe to call any time."""
    inserted = 0
    for row in UNSPSC_NODES:
        if await db.taxonomy_nodes.find_one({"code": row["code"]}):
            continue
        doc = dict(row)
        doc["created_at"] = now_iso()
        await db.taxonomy_nodes.insert_one(doc)
        inserted += 1
    await audit_log("taxonomy.reseed", admin, "taxonomy", "*",
                    {"inserted": inserted, "total_defaults": len(UNSPSC_NODES)})
    return {"ok": True, "inserted": inserted, "total_defaults": len(UNSPSC_NODES)}
