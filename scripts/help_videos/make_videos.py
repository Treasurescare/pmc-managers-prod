"""Generate narrated how-to videos for every help module.

Usage: python3 scripts/help_videos/make_videos.py [slug ...] [--force]
Env: PMC_BASE (preview URL), PMC_ADMIN_EMAIL/PW, PMC_VENDOR_EMAIL/PW, EMERGENT_LLM_KEY (backend/.env).
Output: frontend/public/help-videos/<slug>.mp4 + manifest.json. Unchanged narration is skipped (hash cache).
"""
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech
from playwright.sync_api import sync_playwright

load_dotenv("/app/backend/.env")
BASE = os.environ["PMC_BASE"].rstrip("/")
OUT = "/app/frontend/public/help-videos"
MANIFEST = os.path.join(OUT, "manifest.json")
VOICE, MODEL = "nova", "tts-1-hd"
TAB_MAP = {"analytics": "dashboard", "l1": "l1-award", "vintel": "vendor-intel", "packages": "work-packages"}
LOGIN = {"admin": ("/api/v1/admin/auth/login", "PMC_ADMIN_EMAIL", "PMC_ADMIN_PW"),
         "vendor": ("/api/v1/vendor/auth/login", "PMC_VENDOR_EMAIL", "PMC_VENDOR_PW")}

OVERLAY_JS = """([kind, text, hl]) => {
  let cap = document.getElementById('pmc-vid-cap');
  if (!cap) {
    cap = document.createElement('div'); cap.id = 'pmc-vid-cap';
    cap.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);max-width:1000px;z-index:2147483647;' +
      'background:rgba(22,41,33,.94);color:#fff;font:500 21px/1.4 system-ui,sans-serif;padding:14px 22px;border-radius:10px;' +
      'border-left:5px solid #d9bd72;box-shadow:0 10px 30px rgba(0,0,0,.35)';
    document.body.appendChild(cap);
  }
  let card = document.getElementById('pmc-vid-card');
  if (kind === 'title') {
    if (!card) { card = document.createElement('div'); card.id = 'pmc-vid-card'; document.body.appendChild(card); }
    card.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:rgba(22,41,33,.93);display:flex;flex-direction:column;' +
      'justify-content:center;padding:0 120px;color:#fff;font-family:system-ui,sans-serif';
    card.innerHTML = '<div style="color:#d9bd72;letter-spacing:.18em;font-size:16px;font-weight:600">PMC MANAGERS · HOW-TO</div>' +
      '<div style="font-size:54px;font-weight:700;margin:14px 0 0">' + hl + '</div>';
  } else if (card) { card.remove(); }
  cap.textContent = text;
  document.querySelectorAll('[data-pmc-hl]').forEach(e => { e.style.outline = ''; e.removeAttribute('data-pmc-hl'); });
  if (kind === 'step' && hl) {
    const want = hl.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();
    const els = [...document.querySelectorAll('button, a, [role=tab], label, th, h1, h2, h3, summary')]
      .filter(e => e.offsetParent && (e.innerText || '').toLowerCase().replace(/[^a-z0-9 ]/g, '').trim().includes(want));
    const el = els.sort((a, b) => a.innerText.length - b.innerText.length)[0];
    if (el) { el.setAttribute('data-pmc-hl', '1'); el.style.outline = '4px solid #d9bd72'; el.style.outlineOffset = '3px';
      el.scrollIntoView({block: 'center', behavior: 'smooth'}); return true; }
  }
  return false;
}"""


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", s or "")).strip()


def script_for(slug, m):
    segs = [("title", f"{m['title']}. {clean(m['purpose'])}", m["title"])]
    act = (m.get("actions") or [None])[0]
    if act:
        segs.append(("info", f"How to {act['label'][0].lower()}{act['label'][1:]}.", ""))
        for i, st in enumerate(act.get("steps", [])[:7], 1):
            bold = re.findall(r"\*\*(.+?)\*\*", st)
            segs.append(("step", f"Step {i}. {clean(st)}", bold[0] if bold else ""))
        if act.get("expected"):
            segs.append(("info", f"Result: {clean(act['expected'])}", ""))
    segs.append(("info", "For more help, open the Help Centre or contact the PMC tender desk.", ""))
    return segs


def target_url(slug, m):
    u = m["url_path"]
    t = re.match(r"^/admin\?tab=([\w-]+)", u)
    if t:
        u = f"/admin/e/{TAB_MAP.get(t.group(1), t.group(1))}"
    if m["surface"] == "magic":
        u = f"/help/{slug}"
    return u


async def tts_all(segs, d):
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    files = []
    for i, (_, text, _) in enumerate(segs):
        f = os.path.join(d, f"a{i}.mp3")
        open(f, "wb").write(await tts.generate_speech(text=text, model=MODEL, voice=VOICE))
        files.append(f)
    return files


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).strip())


def record(slug, m, segs, audio, d):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=d,
                            record_video_size={"width": 1280, "height": 720})
        login = LOGIN.get(m["surface"])
        if login:
            ctx.request.post(BASE + login[0], data={"email": os.environ[login[1]], "password": os.environ[login[2]]})
        t0 = time.monotonic()
        pg = ctx.new_page()
        pg.goto(BASE + target_url(slug, m), wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(1500)
        starts = []
        for (kind, text, hl), a in zip(segs, audio):
            try:
                pg.evaluate(OVERLAY_JS, [kind, text, hl])
            except Exception:
                pg.wait_for_load_state("networkidle")
                pg.wait_for_timeout(800)
                pg.evaluate(OVERLAY_JS, [kind, text, hl])
            starts.append(time.monotonic() - t0)
            length = dur(a) + 0.6
            if kind == "info":
                pg.mouse.wheel(0, 260)
            pg.wait_for_timeout(int(length * 1000))
        pg.wait_for_timeout(800)
        vid = pg.video.path()
        ctx.close()
        b.close()
    return vid, starts


def compose(vid, starts, audio, out):
    lead = max(0.0, starts[0] - 0.3)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{lead:.2f}", "-i", vid]
    for a in audio:
        cmd += ["-i", a]
    fil = "".join(f"[{i + 1}:a]adelay={int((s - lead) * 1000)}:all=1[a{i}];" for i, s in enumerate(starts))
    fil += "".join(f"[a{i}]" for i in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0[aout]"
    cmd += ["-filter_complex", fil, "-map", "0:v", "-map", "[aout]", "-r", "15", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    mods = requests.get(f"{BASE}/api/v1/meta/help", timeout=30).json()["modules"]
    for slug, m in mods.items():
        if args and slug not in args:
            continue
        segs = script_for(slug, m)
        h = hashlib.sha256(json.dumps([segs, target_url(slug, m), VOICE, MODEL]).encode()).hexdigest()[:16]
        out = os.path.join(OUT, f"{slug}.mp4")
        if not force and man.get(slug, {}).get("hash") == h and os.path.exists(out):
            print("skip", slug)
            continue
        with tempfile.TemporaryDirectory() as d:
            try:
                audio = asyncio.run(tts_all(segs, d))
                vid, starts = record(slug, m, segs, audio, d)
                compose(vid, starts, audio, out)
            except Exception as e:
                print("FAILED", slug, e)
                continue
        man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
        man[slug] = {"file": f"/help-videos/{slug}.mp4", "title": m["title"], "hash": h,
                     "seconds": round(dur(out)), "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        json.dump(man, open(MANIFEST, "w"), indent=1)
        print("ok", slug, man[slug]["seconds"], "s", os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
