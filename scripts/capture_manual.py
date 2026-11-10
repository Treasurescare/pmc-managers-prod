"""Capture every main screen of PMC for the user manual + training manual (preview only)."""
import asyncio
import json
import os

from playwright.async_api import async_playwright

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
OUT = os.environ.get("OUT_DIR", "/app/frontend/public/downloads/manual/screens")
CHROME = "/pw-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux-arm64/chrome-headless-shell"
DEMO_PW = "Demo@Pmc2026"
ACCOUNTS = {
    "public": None,
    "admin": ("admin", "adminsupport@pmcmanagers.com", "Admin@12345"),
    "supplier": ("supplier", "northfield@demo.pmcmanagers.com", DEMO_PW),
    "partner": ("partner", "partner@demo.pmcmanagers.com", DEMO_PW),
    "staff": ("staff", "committee1@demo.pmcmanagers.com", DEMO_PW),
    "loser": ("supplier", "kestrel@demo.pmcmanagers.com", DEMO_PW),
    "buyer": ("buyer", "buyer@demo.pmcmanagers.com", DEMO_PW),
}
SCREENS = json.load(open(os.environ.get("SCREENS_FILE", "/app/scripts/manual_screens.json")))


async def login(page, role, email, pw):
    await page.context.clear_cookies()
    await page.goto(f"{BASE}/login?role={role}", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(2500)
    await page.fill("[data-testid='signin-e-email']", email)
    await page.fill("[data-testid='signin-e-password']", pw)
    await page.click("[data-testid='signin-e-submit']")
    await page.wait_for_timeout(4500)


async def main():
    os.makedirs(OUT, exist_ok=True)
    done = {}
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path=CHROME)
        vw, vh = [int(x) for x in os.environ.get("VIEW", "1440x900").split("x")]
        ctx = await br.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=float(os.environ.get("SCALE", "1")))
        await ctx.add_init_script("try{if(!location.pathname.match(/^\\/(fr|de|es|ru|kk|ar|hi|ms|id|ko|ja|zh-Hans|zh-Hant)(\\/|$)/))localStorage.setItem('pmc_lang','en')}catch(e){}")
        page = await ctx.new_page()
        current = None
        for s in SCREENS:
            if s["as"] != current:
                current = s["as"]
                await page.context.clear_cookies()
                if ACCOUNTS[current]:
                    await login(page, *ACCOUNTS[current])
            try:
                await page.goto(BASE + s["path"], wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(s.get("wait", 3500))
                await page.add_style_tag(content="[data-testid*=help-fab],.pmc-help-fab,#help-fab,.pmc-helpfab,[data-testid=chat-toggle],[data-testid=lang-fab]{display:none!important}")
                for sel in s.get("click", []):
                    await page.locator(sel).first.click(force=True)
                    await page.wait_for_timeout(1800)
                await page.screenshot(path=f"{OUT}/{s['id']}.png", full_page=False)
                done[s["id"]] = page.url.replace(BASE, "")
                print("ok", s["id"], done[s["id"]])
            except Exception as e:
                print("FAIL", s["id"], str(e)[:120])
        if os.environ.get("SKIP_MOBILE"):
            await br.close()
            return
        mob = await (await br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)).new_page()
        await mob.goto(BASE + "/", wait_until="domcontentloaded")
        await mob.wait_for_timeout(3000)
        await mob.screenshot(path=f"{OUT}/zz-mobile-home.png")
        await br.close()
    json.dump(done, open(f"{OUT}/_captured.json", "w"), indent=1)


asyncio.run(main())
