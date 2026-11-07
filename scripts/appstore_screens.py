"""App Store screenshots: iPhone 6.9" (1290x2796) from the live-looking preview site.
Usage: PMC_BASE=<url> python3 scripts/appstore_screens.py"""
import os

from playwright.sync_api import sync_playwright

BASE = os.environ["PMC_BASE"].rstrip("/")
OUT = "/app/deliverables/appstore/screenshots"
SHOTS = [("01-home", "/"), ("02-live-tenders", "/tenders/live"), ("03-global-tenders", "/tenders/global"),
         ("04-suppliers", "/suppliers"), ("05-help", "/help"), ("06-arabic", "/ar")]

os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_CHROME_EXECUTABLE_PATH") or None)
    ctx = b.new_context(viewport={"width": 430, "height": 932}, device_scale_factor=3, is_mobile=True, has_touch=True,
                        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
    ctx.add_init_script("try{localStorage.setItem('pmc_lang','en');localStorage.setItem('pmc_cookie_consent','1')}catch(e){};window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'ios'}")
    pg = ctx.new_page()
    for name, path in SHOTS:
        pg.goto(BASE + path, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(3500)
        pg.add_style_tag(content="[data-testid=chat-toggle],[data-testid=lang-fab],[data-testid*=cookie]{display:none!important}")
        pg.screenshot(path=f"{OUT}/{name}.png")
        print("ok", name)
    b.close()
