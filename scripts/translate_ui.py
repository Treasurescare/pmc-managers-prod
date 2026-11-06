"""AI-translate the English UI bundle into extra languages -> frontend/public/i18n/<code>.json (review by native speakers later)."""
import asyncio
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

LANGS = {"zh-Hans": "Simplified Chinese (Mandarin, mainland China/Malaysia/Singapore)",
         "zh-Hant": "Traditional Chinese as used in Hong Kong (Cantonese readers)", "es": "Spanish", "fr": "French", "de": "German",
         "hi": "Hindi", "ms": "Malay (Bahasa Melayu)", "id": "Indonesian (Bahasa Indonesia)", "ko": "Korean", "ja": "Japanese",
         "ar": "Arabic (Modern Standard Arabic)"}
OUT = "/app/frontend/public/i18n"
EN = json.loads(subprocess.check_output(["node", "-e",
    "import('/app/frontend/src/lib/i18n-strings.js').then(m=>process.stdout.write(JSON.stringify(m.STRINGS.en)))"], text=True))


def chunks(d: dict, size=9000):
    cur, n = {}, 0
    for k, v in d.items():
        s = len(json.dumps(v, ensure_ascii=False))
        if cur and n + s > size:
            yield cur
            cur, n = {}, 0
        cur[k] = v
        n += s
    if cur:
        yield cur


async def tr(lang: str, name: str, part: dict) -> dict:
    sys_msg = (f"Translate the JSON values from English to {name} for a professional procurement / e-tendering web portal. "
               "Keep every key, nesting and placeholder like {name}, {{count}}, %s, HTML tags and URLs exactly. Keep brand names "
               "'PMC Managers' and 'Global Tender Grid' and abbreviations (EMD, KYC, BOQ, PO, RFQ, RFP) untranslated. "
               "Reply with ONLY the translated JSON.")
    for attempt in range(3):
        chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"i18n-{lang}-{attempt}-{id(part)}",
                       system_message=sys_msg).with_model("anthropic", "claude-sonnet-5-5")
        txt = await chat.send_message(UserMessage(text=json.dumps(part, ensure_ascii=False)))
        m = re.search(r"\{.*\}", txt or "", re.S)
        try:
            out = json.loads(m.group(0))
            if set(out) == set(part):
                return out
        except Exception:
            pass
    return part


async def one(lang: str, name: str):
    path = f"{OUT}/{lang}.json"
    if os.path.exists(path):
        return
    res = {}
    for part in chunks(EN):
        res.update(await tr(lang, name, part))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    print("done", lang, flush=True)


async def main():
    os.makedirs(OUT, exist_ok=True)
    sem = asyncio.Semaphore(4)

    async def guarded(code, name):
        async with sem:
            await one(code, name)
    await asyncio.gather(*(guarded(c, n) for c, n in LANGS.items() if len(sys.argv) < 2 or c in sys.argv[1:]))


asyncio.run(main())
