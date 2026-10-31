"""Capture 1920x1080 screenshots of the PREVIEW with demo data for the promo-video editor. Output: /app/frontend/public/downloads/pmc-video-shots(.zip)"""
import asyncio
import os
import re
import shutil
import sys

from playwright.async_api import async_playwright

sys.path.insert(0, "/app/backend")
BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
OUT = "/app/frontend/public/downloads/pmc-video-shots"
PW = "Demo@Pmc2026"
cred = open("/app/memory/test_credentials.md").read().split("dmin", 1)[1]
ADMIN = (re.search(r"[\w.+-]+@[\w.-]+", cred).group(0), re.search(r"[Pp]assword[^:]*:\s*`?([^\s`]+)", cred).group(1))
REG_TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""


async def shot(page, name, url=None, wait=2500, full=False, before=None):
    try:
        if url:
            await page.goto(BASE + url, wait_until="domcontentloaded")
        await page.wait_for_timeout(wait)
        if before:
            await before(page)
            await page.wait_for_timeout(1200)
        await page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
        print("ok", name)
    except Exception as e:
        print("FAIL", name, str(e)[:120])


async def login(page, role, email, pw):
    await page.context.clear_cookies()
    await page.goto(f"{BASE}/login?role={role}")
    await page.wait_for_timeout(2500)
    await page.fill("[data-testid='signin-e-email']", email)
    await page.fill("[data-testid='signin-e-password']", pw)
    await page.click("[data-testid='signin-e-submit']")
    await page.wait_for_timeout(4000)


async def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await (await b.new_context(viewport={"width": 1920, "height": 1080})).new_page()
        # 1 Bidder journey
        await shot(page, "1-01-homepage", "/", 3500)
        await shot(page, "1-01b-homepage-partners-of-the-month", None, 500, before=lambda pg: pg.locator("[data-testid='home-partner-highlights']").scroll_into_view_if_needed())

        async def search(pg):
            box = pg.locator("input[type='search'], input[placeholder*='earch']").first
            await box.fill("hospital")
        await shot(page, "1-02-tender-listing", "/tenders/live", 3500)
        await shot(page, "1-02b-tender-listing-search", None, 500, before=search)
        await shot(page, "1-03-tender-detail", "/notices/DEMO-TND-001", 3500)
        await shot(page, "1-04-registration-start", "/register", 3000)
        if REG_TOKEN:
            await shot(page, "1-05-registration-form", f"/register/resume?token={REG_TOKEN}", 3500)
            for i, step in enumerate(["b", "c", "d", "e"], 1):
                async def go(pg, s=step):
                    btn = pg.locator(f"[data-testid='step-{s}'], [data-testid='register-step-{s}']").first
                    if await btn.count():
                        await btn.click()
                    else:
                        await pg.locator("[data-testid='btn-next']").first.click()
                await shot(page, f"1-05{chr(97 + i)}-registration-step-{step}", None, 800, before=go)
        await login(page, "supplier", "northfield@demo.pmcmanagers.com", PW)
        await shot(page, "1-06-bidder-dashboard", "/vendor", 3500)
        await shot(page, "1-07-tenders-for-bidder", "/vendor/tenders", 3500)
        await login(page, "supplier", "kestrel@demo.pmcmanagers.com", PW)
        await shot(page, "1-08-bid-submission-form", "/vendor/bid/new/DEMO-TND-003", 4000)
        await shot(page, "1-08b-bid-submission-form-full", None, 500, full=True)
        await login(page, "supplier", "northfield@demo.pmcmanagers.com", PW)
        await shot(page, "1-09-my-bids-sealed-confirmation", "/vendor/mybids", 3500)
        await shot(page, "1-10-emd-deposit", "/vendor/emd", 3500)
        await page.goto(f"file://{OUT}/../pmc-email-bid-received.html")
        await shot(page, "1-11-email-notification-bid-received", None, 800)
        # 2 + 4 Admin
        await login(page, "admin", *ADMIN)
        for name, url in [("2-01-create-tender-builder", "/admin/e/tender-builder"), ("2-02-tenders-published", "/admin/e/notices"),
                          ("2-03-bids-received", "/admin/e/bidding"), ("2-04-evaluation", "/admin/e/evaluations"),
                          ("2-05-award-decision", "/admin/e/l1-award"), ("2-06-awards", "/admin/e/awards"),
                          ("4-01-admin-dashboard", "/admin/e/dashboard"), ("4-02-supplier-management", "/admin/e/vendors"),
                          ("4-02b-registrations", "/admin/e/registrations"), ("4-03-tender-management", "/admin/e/notices"),
                          ("4-04-reports", "/admin/e/stakeholder-reports"), ("4-04b-audit-ledger", "/admin/e/audit"),
                          ("4-05-settings-masters", "/admin/e/masters"), ("4-05b-permissions", "/admin/e/permissions"),
                          ("4-06-escrow-emd", "/admin/e/escrow"), ("4-07-escrow-institutions", "/admin/e/escrow-institutions"),
                          ("4-08-partners", "/admin/e/partners"), ("4-09-billing", "/admin/e/billing"), ("4-10-marketing", "/admin/e/marketing")]:
            await shot(page, name, url, 4000)
        # extra: committee opening + partner portal
        await login(page, "staff", "committee1@demo.pmcmanagers.com", PW)

        async def opening(pg):
            await pg.get_by_text("Bid opening", exact=True).first.click()
        await shot(page, "5-01-committee-bid-opening", "/staff", 3500, before=opening)
        await login(page, "partner", "partner@demo.pmcmanagers.com", PW)
        await shot(page, "5-02-partner-portal", "/partner/me", 3500)
        await b.close()
    shutil.make_archive(OUT, "zip", OUT)
    print("zip", OUT + ".zip")


asyncio.run(main())
