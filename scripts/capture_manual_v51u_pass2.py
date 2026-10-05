"""Pass 2 — capture the pages missing from pass 1, using OLD manual filenames
so the comprehensive v7 builder (which references the legacy filenames)
picks up current-theme screenshots transparently.
"""
from __future__ import annotations
import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("MANUAL_BASE", "https://pmc-forest-green.preview.emergentagent.com")
# Stage directly with legacy filenames into the v7 staging dir
OUT = Path("/app/deliverables/manual_v7_screenshots"); OUT.mkdir(parents=True, exist_ok=True)
DESK = {"width": 1440, "height": 900}

ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
VENDOR = ("manualvendor@pmcmanagers.com", "Vendor@12345")

# (legacy filename expected by v2 builder, route)
ADMIN_EXTRA = [
    ("13_auctions.png",          "/admin/e/auctions"),
    ("19_l1.png",                "/admin/e/l1-award"),
    ("27_reports.png",           "/admin/e/stakeholder-reports"),
    ("28_stakeholder.png",       "/admin/e/stakeholder-reports"),
    ("30_branding.png",          "/admin/e/programme"),
    ("31x_admin_vendor_kyc.png", "/admin/e/vendor-kyc"),
    ("32x_admin_evaluations.png","/admin/e/evaluations"),
    ("33x_admin_vendor_requests.png", "/admin/e/vendor-requests"),
    ("34x_admin_profile_changes.png", "/admin/e/profile-changes"),
    ("35x_admin_help.png",       "/help"),
]
VENDOR_EXTRA = [
    ("36x_vendor_categories.png","/vendor/categories"),
    ("37x_vendor_emd.png",       "/vendor/emd"),
    ("38x_vendor_reviews.png",   "/vendor/reviews"),
    ("39x_vendor_help.png",      "/help"),
]
PUBLIC_EXTRA = [
    ("04_vendor-registration-—-check-status.png", "/register/status"),
    ("40x_public_notices.png",   "/notices"),
    ("41x_public_tenders_all.png", "/tenders"),
    ("42x_public_about.png",     "/about"),
]

async def login(page, email, password, admin):
    await page.goto(f"{BASE}/admin/login" if admin else f"{BASE}/login", wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]', force=True)
    await page.wait_for_timeout(4500)

async def shoot(page, path, name):
    try:
        await page.goto(f"{BASE}{path}", wait_until="domcontentloaded")
        await page.wait_for_timeout(3200)
        try:
            await page.evaluate("document.querySelectorAll('[data-sonner-toast]').forEach(t => t.remove())")
        except Exception:
            pass
        await page.screenshot(path=str(OUT / name), full_page=False)
        print(f"  ✓ {name} ({(OUT/name).stat().st_size//1024} KB)")
    except Exception as e:
        print(f"  ✗ {name} — {type(e).__name__}: {str(e)[:120]}")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"],
                                          executable_path="/usr/bin/google-chrome")
        ctx = await browser.new_context(viewport=DESK, ignore_https_errors=True)
        page = await ctx.new_page()
        for name, path in PUBLIC_EXTRA:
            await shoot(page, path, name)
        await ctx.close()

        ctx = await browser.new_context(viewport=DESK, ignore_https_errors=True)
        page = await ctx.new_page()
        await login(page, *ADMIN, admin=True)
        for name, path in ADMIN_EXTRA:
            await shoot(page, path, name)
        await ctx.close()

        ctx = await browser.new_context(viewport=DESK, ignore_https_errors=True)
        page = await ctx.new_page()
        await login(page, *VENDOR, admin=False)
        for name, path in VENDOR_EXTRA:
            await shoot(page, path, name)
        await ctx.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
