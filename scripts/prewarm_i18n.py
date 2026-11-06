"""Pre-warm whole-page translations: crawl portal pages in English, collect visible phrases, AI-translate into all languages
and store them in i18n_cache, then export backend/seed/i18n_cache.json (loaded into production on startup)."""
import asyncio
import json
import os
import re
import sys

from playwright.async_api import async_playwright

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from db import db  # noqa: E402
from routers.i18n_auto import LANGS, _h, _llm  # noqa: E402

BASE = os.environ["PMC_BASE"]
APP = open("/app/frontend/src/App.js").read()
ROUTES = sorted({p for p in re.findall(r'path="(/[^"]*)"', APP) if ":" not in p and "*" not in p and not p.startswith(("/auth", "/escrow", "/pay"))})
COLLECT = r"""() => {
  const out = new Set(); const SKIP = new Set(["SCRIPT","STYLE","NOSCRIPT","CODE","PRE","TEXTAREA","SVG","KBD"]);
  const ok = (s) => s.length > 1 && s.length <= 600 && /\p{L}{2,}/u.test(s) && !/^[\w.+-]+@[\w-]+\.[\w.]+$/.test(s) && !/^https?:\/\//.test(s) && !/^[A-Z0-9][A-Z0-9-/.]{4,}$/.test(s);
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    if (n.nodeType === 3) { const p = n.parentElement; if (p && !SKIP.has(p.tagName) && !p.closest('.notranslate,[translate=no]')) { const t = n.nodeValue.trim(); if (ok(t)) out.add(t); } }
    else ["placeholder","title","aria-label"].forEach((a) => { const v = (n.getAttribute(a) || "").trim(); if (v && ok(v)) out.add(v); });
  }
  return [...out];
}"""


async def crawl() -> list:
    found = set()
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        ctx = await br.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        await page.goto(BASE + "/")
        await ctx.request.post(BASE + "/api/v1/admin/auth/login", data={"email": os.environ["PMC_ADMIN_EMAIL"], "password": os.environ["PMC_ADMIN_PW"]})
        await ctx.request.post(BASE + "/api/v1/vendor/auth/login", data={"email": os.environ["PMC_VENDOR_EMAIL"], "password": os.environ["PMC_VENDOR_PW"]})
        for r in ROUTES:
            try:
                await page.goto(BASE + r, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3500)
                found |= set(await page.evaluate(COLLECT))
            except Exception as e:
                print("skip", r, str(e)[:80], flush=True)
        await br.close()
    return sorted(found)


async def translate(texts: list) -> None:
    sem = asyncio.Semaphore(6)

    async def batch(lang, part):
        async with sem:
            try:
                res = await _llm(lang, part)
            except Exception:
                return
            for src, out in zip(part, res):
                if isinstance(out, str) and out.strip():
                    await db.i18n_cache.update_one({"lang": lang, "h": _h(src)}, {"$set": {"src": src, "out": out}}, upsert=True)
    jobs = []
    for lang in LANGS:
        have = {d["src"] async for d in db.i18n_cache.find({"lang": lang}, {"src": 1})}
        todo = [t for t in texts if t not in have]
        jobs += [batch(lang, todo[i:i + 60]) for i in range(0, len(todo), 60)]
    print("batches", len(jobs), flush=True)
    await asyncio.gather(*jobs)


async def main():
    texts = await crawl()
    print("phrases", len(texts), "routes", len(ROUTES), flush=True)
    await translate(texts)
    rows = [{"lang": d["lang"], "src": d["src"], "out": d["out"]} async for d in db.i18n_cache.find({}, {"_id": 0, "lang": 1, "src": 1, "out": 1})]
    os.makedirs("/app/backend/seed", exist_ok=True)
    with open("/app/backend/seed/i18n_cache.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    print("exported", len(rows), flush=True)


asyncio.run(main())
