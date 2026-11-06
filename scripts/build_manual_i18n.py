"""Translated editions of the Master Training Manual (same chapters as build_manual_v4 + module guide), rendered HTML -> PDF.

Usage: PMC_BASE=<preview url> python3 scripts/build_manual_i18n.py [lang ...]   (default: all 13 non-English languages)
Output: frontend/public/downloads/manual/PMC_Master_Training_Manual_<lang>.pdf + sections_<lang>.json.
Translations are cached in Mongo (manual_i18n), so re-runs only translate changed text.
"""
import asyncio
import hashlib
import html
import json
import os
import re
import sys
from datetime import date

import fitz
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/scripts")
sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
import build_manual_v4 as M  # noqa: E402
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Table  # noqa: E402
from routers.i18n_auto import LANGS  # noqa: E402

D = M.D
BASE = os.environ["PMC_BASE"].rstrip("/")
SITE = "https://www.pmcmanagers.com"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
FONTS = {"zh-Hans": "Noto Sans CJK SC", "zh-Hant": "Noto Sans CJK TC", "ja": "Noto Sans CJK JP", "ko": "Noto Sans CJK KR",
         "ar": "Noto Sans Arabic", "hi": "Noto Sans Devanagari"}
SYS = ("You translate a professional procurement / e-tendering training manual from English into {lang}. Input is a JSON array of strings "
       "that may contain simple HTML tags (<b>, <i>, <br/>, <font ...>). Reply with ONLY a JSON array of the same length and order. "
       "Keep every HTML tag and attribute exactly and translate only the text. Keep URLs, paths starting with /, numbers, dates, currency "
       "codes, emails, reference codes and the names PMC Managers, Global Tender Grid, PMC, Stripe, DocuSign, AWS, MongoDB unchanged. "
       "Keep the abbreviations EMD, KYC, BOQ, DPR, L1, PO, RFQ, RFP, API, AI, CSV, PDF, SHA-256.")
CSS = """
@page { size: A4; margin: 16mm 15mm 14mm 15mm; }
body { font-family: "Noto Sans", %s, sans-serif; font-size: 9.5pt; line-height: 1.45; color: #1f2a24; }
h1 { font-size: 21pt; color: #162921; margin: 0 0 6px; page-break-before: always; }
p.sec, h2 { font-size: 13pt; font-weight: 700; color: #162921; margin: 12px 0 4px; }
p.sm { font-size: 8pt; color: #555; }
table { border-collapse: collapse; width: 100%%; font-size: 8pt; margin: 4px 0 8px; }
td, th { border: .3pt solid #D8D0BD; padding: 3px 4px; vertical-align: top; text-align: start; }
tr:first-child td, th { background: #F3EFE4; font-weight: 700; }
img { max-width: 100%%; border: .6pt solid #C9C2B0; margin: 4px 0; }
.kt { break-inside: avoid; }
.cover { height: 260mm; background: #162921; color: #fff; padding: 60mm 18mm 0; box-sizing: border-box; }
.cover .gold { color: #d9bd72; letter-spacing: .15em; font-size: 11pt; }
.cover .t { font-size: 28pt; margin: 6mm 0 3mm; }
.toc a { color: #162921; text-decoration: none; }
.toc li { margin: 2px 0; }
"""


def _h(s):
    return hashlib.sha1(s.encode()).hexdigest()


PATHS = [s["path"] for s in M.SCREENS]


class Collector:
    def __init__(self):
        self.texts = []

    def t(self, s):
        s = str(s)
        if not re.search(r"[A-Za-z]{2}", re.sub(r"<[^>]+>", "", s)):
            return s
        self.texts.append(s)
        return f"\x00{len(self.texts) - 1}\x00"

    def cell(self, c):
        if isinstance(c, (list, tuple)):
            return "".join(self.cell(x) for x in c)
        if isinstance(c, str):
            return self.t(html.escape(c))
        return self.conv(c)

    def conv(self, f):
        if isinstance(f, Paragraph):
            cls = "sec" if f.style.name == "sec" else "sm" if f.style.fontSize < 9 else "b"
            mk = re.match(r"Screen: <font face='Courier'>(.+?)</font>", f.text or "")
            tag = f'<span dir="ltr" style="font-size:1pt;color:#fefefe"> SCRMK{PATHS.index(mk.group(1))}KM </span>' if mk and mk.group(1) in PATHS else ""
            return f'<p class="{cls}">{self.t(f.text)}{tag}</p>'
        if isinstance(f, KeepTogether):
            return '<div class="kt">' + "".join(self.conv(x) for x in f._content) + "</div>"
        if isinstance(f, Table):
            rows = f._cellvalues
            if len(rows) == 1 and len(rows[0]) == 1:
                return self.cell(rows[0][0])
            return "<table>" + "".join("<tr>" + "".join(f"<td>{self.cell(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>"
        if isinstance(f, Image):
            return f'<img src="file://{f.filename}">'
        if isinstance(f, PageBreak):
            return ""
        return ""


async def translate(lang, texts):
    uniq = list(dict.fromkeys(texts))
    got = {d["src"]: d["out"] for d in mdb.manual_i18n.find({"lang": lang, "h": {"$in": [_h(t) for t in uniq]}})}
    miss = [t for t in uniq if t not in got]
    sem = asyncio.Semaphore(6)

    async def one(part):
        async with sem:
            for k in range(3):
                try:
                    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"man-{lang}-{_h(''.join(part))[:10]}-{k}",
                                   system_message=SYS.format(lang=LANGS[lang])).with_model("anthropic", "claude-sonnet-5-5")
                    txt = await chat.send_message(UserMessage(text=json.dumps(part, ensure_ascii=False)))
                    m = re.search(r"\[.*\]", txt or "", re.S)
                    out = json.loads(m.group(0)) if m else []
                    if len(out) == len(part):
                        for s, o in zip(part, out):
                            if isinstance(o, str) and o.strip():
                                got[s] = o
                                mdb.manual_i18n.update_one({"lang": lang, "h": _h(s)}, {"$set": {"src": s, "out": o}}, upsert=True)
                        return
                except Exception as e:
                    print("retry", lang, str(e)[:80], flush=True)
    print(lang, "segments", len(uniq), "to translate", len(miss), flush=True)
    await asyncio.gather(*[one(miss[i:i + 15]) for i in range(0, len(miss), 15)])
    return got


def md(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s or "").replace("`", ""))


def build_html(lang, mods, vids):
    c = Collector()
    hidden = set() if os.environ.get("MANUAL_SHOW_INTERNAL") == "1" else M.HIDDEN_UNTIL_LIVE
    chapters = M.body_story(hidden)
    body = []
    toc = []
    for i, (title, fls) in enumerate(chapters):
        toc.append(f'<li><a href="#c{i}">{c.t(html.escape(title))}</a></li>')
        body.append(f'<h1 id="c{i}">{c.t(html.escape(title))}</h1>' + "".join(c.conv(f) for f in fls))
    app = [f'<h1 id="app">{c.t("Appendix — Module guide &amp; video index")}</h1>']
    for slug, m in mods.items():
        v = vids.get(slug)
        app.append('<div class="kt">' + f'<p class="sec">{c.t(md(m["title"]))}</p>'
                   + f'<p class="sm">{c.t("Where")}: {html.escape(m["url_path"])} · {c.t("Help page")}: {SITE}/help/{slug}'
                   + (f' · {c.t("Video")}: {SITE}{v["file"]}' if v else "") + "</p>"
                   + f'<p>{c.t(md(m["purpose"]))}</p>')
        for a in (m.get("actions") or [])[:3]:
            app.append(f'<p><b>{c.t(md(a["label"]))}</b></p><ol>' + "".join(f"<li>{c.t(md(s))}</li>" for s in a.get("steps", [])) + "</ol>")
        app.append("</div>")
    toc.append(f'<li><a href="#app">{c.t("Appendix — Module guide &amp; video index")}</a></li>')
    issued = date.today().strftime("%Y-%m-%d")
    cover = (f'<div class="cover"><img src="file:///app/backend/assets/pmc-logo-mark-256.png" style="width:34mm;border:0">'
             f'<div class="gold">PMC MANAGERS</div><div class="t">{c.t("Master Training Manual")}</div>'
             f'<div>{c.t("Whole-site edition · every portal, every screen, every process")}</div>'
             f'<div style="margin-top:60mm">{c.t("Issued")} {issued} · {LANGS[lang]}</div></div>'
             f'<h1 style="page-break-before:always">{c.t("Contents")}</h1><ol class="toc" style="list-style:none;padding:0">{"".join(toc)}</ol>')
    doc = cover + "".join(body) + "".join(app)
    return c.texts, doc


def render(lang, doc, tr):
    doc = re.sub(r"\x00(\d+)\x00", lambda m: tr.get(TEXTS[int(m.group(1))], TEXTS[int(m.group(1))]), doc)
    font = f'"{FONTS[lang]}"' if lang in FONTS else '"Noto Sans"'
    page = (f'<!doctype html><html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}"><head><meta charset="utf-8">'
            f"<style>{CSS % font}</style></head><body>{doc}</body></html>")
    src = f"/tmp/manual_{lang}.html"
    open(src, "w", encoding="utf-8").write(page)
    out = f"{D}/PMC_Master_Training_Manual_{lang}.pdf"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(f"file://{src}", wait_until="load", timeout=120000)
        pg.evaluate("document.fonts.ready")
        pg.pdf(path=out, format="A4", print_background=True, display_header_footer=True,
               margin={"top": "16mm", "bottom": "14mm", "left": "15mm", "right": "15mm"},
               header_template='<div style="font-size:7px;color:#888;width:100%;padding:0 15mm">PMC Managers · Master Training Manual</div>',
               footer_template='<div style="font-size:7px;color:#888;width:100%;text-align:right;padding:0 15mm"><span class="pageNumber"></span></div>')
        b.close()
    return out


def sections(lang, path):
    d = fitz.open(path)
    texts = [pg.get_text() for pg in d]
    pages = {}
    first = {}
    for i, t in enumerate(texts):
        for m in re.finditer(r"SCRMK(\d+)KM", t):
            s = M.SCREENS[int(m.group(1))]
            if len(s["path"]) > 1:
                pages.setdefault(s["path"], i + 1)
            first.setdefault(s["section"], i + 1)
    for key, sec in (("public", "Public website"), ("supplier", "Supplier portal"), ("admin", "Admin console"),
                     ("partner", "Partner portal"), ("staff", "Staff portal")):
        if sec in first:
            pages[key] = first[sec]
    json.dump({"file": f"/downloads/manual/PMC_Master_Training_Manual_{lang}.pdf", "pages": pages},
              open(f"{D}/sections_{lang}.json", "w"), indent=1)
    return len(d)


if __name__ == "__main__":
    langs = [a for a in sys.argv[1:] if a in LANGS] or list(LANGS)
    mods = requests.get(f"{BASE}/api/v1/meta/help", timeout=30).json()["modules"]
    for lg in langs:
        mf = f"/app/frontend/public/help-videos/{lg}/manifest.json"
        vids = {**json.load(open("/app/frontend/public/help-videos/manifest.json")), **(json.load(open(mf)) if os.path.exists(mf) else {})}
        TEXTS, doc = build_html(lg, mods, vids)
        tr = asyncio.new_event_loop().run_until_complete(translate(lg, TEXTS))
        path = render(lg, doc, tr)
        print("done", lg, sections(lg, path), "pages", os.path.getsize(path) // 1024, "KB", flush=True)
