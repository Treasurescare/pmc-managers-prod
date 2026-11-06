"""Whole-page auto translation: phrases on screen are AI-translated once per language and cached for everyone."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from db import db

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
    from emergentintegrations.llm.chat import LlmChat, UserMessage
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
    texts = list(dict.fromkeys(t.strip() for t in body.texts if t and t.strip() and len(t) <= 600))
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
