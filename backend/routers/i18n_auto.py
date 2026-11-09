"""Whole-page auto translation: phrases on screen are AI-translated once per language and cached for everyone."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from audit import audit_log
from db import db
from security import require_role

router = APIRouter(prefix="/api/v1/i18n", tags=["i18n"])
LANGS = {"ru": "Russian", "kk": "Kazakh", "zh-Hans": "Simplified Chinese (Mandarin)", "zh-Hant": "Traditional Chinese (Hong Kong, Cantonese readers)",
         "es": "Spanish", "fr": "French", "de": "German", "hi": "Hindi", "ms": "Malay (Bahasa Melayu)", "id": "Indonesian (Bahasa Indonesia)",
         "ko": "Korean", "ja": "Japanese", "ar": "Arabic (Modern Standard Arabic)"}
PER_MIN = 600
PER_DAY = 30000
SYS = ("You translate short UI texts of a professional procurement / e-tendering web portal from English (or any language) into {lang}. "
       "Input is a JSON array of strings; reply with ONLY a JSON array of the same length and order. Keep numbers, dates, currency codes, "
       "emails, URLs, reference codes (e.g. PMC-NOT-2026-0001), placeholders like {{x}} and the brand names 'PMC Managers', "
       "'Global Tender Grid', 'PMC' unchanged. Keep abbreviations EMD, KYC, BOQ, PO, RFQ, RFP, API. Company and person names stay as written.")


def _h(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()


class TrIn(BaseModel):
    lang: str
    texts: list[str] = Field(max_length=120)


async def _llm(lang: str, texts: list) -> list:
    from pmc_lib.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"autotr-{lang}-{_h(''.join(texts))[:12]}",
                   system_message=SYS.format(lang=LANGS[lang])).with_model("anthropic", "claude-sonnet-5-5")
    txt = await chat.send_message(UserMessage(text=json.dumps(texts, ensure_ascii=False)))
    m = re.search(r"\[.*\]", txt or "", re.S)
    out = json.loads(m.group(0)) if m else []
    return out if isinstance(out, list) and len(out) == len(texts) else []


@router.post("/translate")
async def translate(body: TrIn, request: Request):
    if body.lang not in LANGS:
        raise HTTPException(status_code=422, detail="Unsupported language")
    texts = list(dict.fromkeys(t.strip() for t in body.texts if t and t.strip() and len(t) <= 2000))
    found = {d["src"]: d["out"] async for d in db.i18n_cache.find({"lang": body.lang, "h": {"$in": [_h(t) for t in texts]}})}
    missing = [t for t in texts if t not in found]
    if missing:
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
        minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        u = await db.i18n_usage.find_one_and_update({"ip": ip, "m": minute}, {"$inc": {"n": len(missing)},
                                                    "$setOnInsert": {"exp": datetime.now(timezone.utc) + timedelta(hours=1)}},
                                                    upsert=True, return_document=True)
        day = await db.i18n_usage.find_one_and_update({"ip": "_global", "m": minute[:8]}, {"$inc": {"n": len(missing)},
                                                      "$setOnInsert": {"exp": datetime.now(timezone.utc) + timedelta(days=2)}},
                                                      upsert=True, return_document=True)
        if (u or {}).get("n", 0) <= PER_MIN and (day or {}).get("n", 0) <= PER_DAY:
            for i in range(0, len(missing), 60):
                part = missing[i:i + 60]
                try:
                    res = await _llm(body.lang, part)
                except Exception:
                    res = []
                for src, out in zip(part, res):
                    if isinstance(out, str) and out.strip():
                        found[src] = out
                        await db.i18n_cache.update_one({"lang": body.lang, "h": _h(src)},
                                                       {"$set": {"src": src, "out": out, "at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"map": found}


@router.get("/dict/{lang}")
async def dictionary(lang: str, response: Response):
    if lang not in LANGS:
        raise HTTPException(status_code=422, detail="Unsupported language")
    response.headers["Cache-Control"] = "public, max-age=300"
    return {"map": {d["src"]: d["out"] async for d in db.i18n_cache.find({"lang": lang}, {"src": 1, "out": 1}).limit(30000)}}


REVIEWERS = ("admin", "reviewer")


class ReviewIn(BaseModel):
    lang: str
    src: str = Field(min_length=1, max_length=600)
    out: str = Field(min_length=1, max_length=1200)


def _check(lang: str) -> None:
    if lang not in LANGS:
        raise HTTPException(status_code=422, detail="Unsupported language")


@router.get("/admin/stats")
async def review_stats(admin=Depends(require_role(*REVIEWERS))):
    rows = await db.i18n_cache.aggregate([{"$group": {"_id": "$lang", "total": {"$sum": 1},
                                                       "reviewed": {"$sum": {"$cond": [{"$eq": ["$reviewed", True]}, 1, 0]}}}}]).to_list(50)
    got = {r["_id"]: r for r in rows}
    return {"items": [{"lang": k, "name": v, "total": got.get(k, {}).get("total", 0), "reviewed": got.get(k, {}).get("reviewed", 0)}
                      for k, v in LANGS.items()]}


@router.get("/admin/phrases")
async def review_list(lang: str, q: str = "", status: Literal["all", "pending", "reviewed"] = "all",
                      skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), admin=Depends(require_role(*REVIEWERS))):
    _check(lang)
    flt: dict = {"lang": lang}
    if q.strip():
        rx = {"$regex": re.escape(q.strip()[:100]), "$options": "i"}
        flt["$or"] = [{"src": rx}, {"out": rx}]
    if status == "reviewed":
        flt["reviewed"] = True
    elif status == "pending":
        flt["reviewed"] = {"$ne": True}
    total = await db.i18n_cache.count_documents(flt)
    cur = db.i18n_cache.find(flt, {"_id": 0, "src": 1, "out": 1, "reviewed": 1, "reviewed_by": 1, "reviewed_at": 1}).sort("src", 1).skip(skip).limit(limit)
    items = [{"src": d["src"], "out": d["out"], "reviewed": bool(d.get("reviewed")), "reviewed_by": d.get("reviewed_by"),
              "reviewed_at": d.get("reviewed_at")} async for d in cur]
    return {"total": total, "items": items}


@router.put("/admin/phrases")
async def review_save(body: ReviewIn, admin=Depends(require_role(*REVIEWERS))):
    _check(body.lang)
    src, out = body.src.strip(), body.out.strip()
    if not src or not out:
        raise HTTPException(status_code=422, detail="Original and translation are required")
    prev = await db.i18n_cache.find_one({"lang": body.lang, "h": _h(src)}, {"out": 1})
    at = datetime.now(timezone.utc).isoformat()
    await db.i18n_cache.update_one({"lang": body.lang, "h": _h(src)}, {"$set": {
        "src": src, "out": out, "reviewed": True, "reviewed_by": admin.get("email"), "reviewed_at": at, "at": at}}, upsert=True)
    await audit_log("i18n.phrase_reviewed", admin, "i18n_cache", f"{body.lang}:{_h(src)[:12]}",
                    {"lang": body.lang, "src": src[:200], "old": (prev or {}).get("out", "")[:200], "new": out[:200]})
    return {"src": src, "out": out, "reviewed": True, "reviewed_by": admin.get("email"), "reviewed_at": at}


async def ensure_indexes() -> None:
    await db.i18n_cache.create_index([("lang", 1), ("h", 1)], unique=True)
    await db.i18n_usage.create_index("exp", expireAfterSeconds=0)
    import asyncio
    asyncio.create_task(_load_seed())


async def _load_seed() -> None:
    from pymongo import UpdateOne
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seed", "i18n_cache.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    if await db.i18n_cache.count_documents({}) >= len(rows):
        return
    ops = [UpdateOne({"lang": r["lang"], "h": _h(r["src"])}, {"$setOnInsert": {"src": r["src"], "out": r["out"]}}, upsert=True) for r in rows]
    for i in range(0, len(ops), 2000):
        await db.i18n_cache.bulk_write(ops[i:i + 2000], ordered=False)
