import json
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ["PMC_BASE"]
PAGES = sys.argv[1:]

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    r = pg.request.post(f"{BASE}/api/v1/admin/auth/login",
                        data={"email": os.environ["PMC_ADMIN_EMAIL"], "password": os.environ["PMC_ADMIN_PW"]})
    print("login", r.status)
    for path in PAGES:
        pg.goto(BASE + path, wait_until="networkidle")
        pg.wait_for_timeout(1200)
        info = pg.evaluate("""() => {
          const t = (s) => [...document.querySelectorAll(s)].map(e => e.innerText.trim()).filter(Boolean);
          const main = document.querySelector('main') || document.body;
          return {h: t('main h1, main h2, main h3').slice(0, 8),
                  btn: [...main.querySelectorAll('button, a.pmc-btn')].map(e => e.innerText.trim()).filter(x => x && x.length < 40).slice(0, 14),
                  p: (main.innerText || '').replace(/\\s+/g, ' ').slice(0, 260)};
        }""")
        print(path, json.dumps(info, ensure_ascii=False))
    b.close()
