"""Capture current-build screenshots for the PMC v51u Master Training Manual.

Uses local Playwright against http://localhost:3000 (same-origin) and writes
to /app/deliverables/manual_v51u_shots/*.png.

Order matches the manual's chapter order; the assembler picks them up by
numeric prefix. Each capture runs once; failures leave a sentinel .err
file so the run can retry individual shots without redoing the login.
"""
from __future__ import annotations
import asyncio, json, os, sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE = os.environ.get("MANUAL_BASE", "https://pmc-forest-green.preview.emergentagent.com")
OUT = Path("/app/deliverables/manual_v51u_shots"); OUT.mkdir(parents=True, exist_ok=True)
DESK = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}

ADMIN = ("adminsupport@pmcmanagers.com", "Admin@12345")
VENDOR = ("manualvendor@pmcmanagers.com", "Vendor@12345")

PUBLIC_SHOTS = [
    ("01_public_landing",        "/"),
    ("02_public_tender_board",   "/tenders/live"),
    ("03_registration_start",    "/register"),
    ("04_unified_login",         "/login"),
    ("05_admin_login",           "/admin/login"),
]

ADMIN_SHOTS = [
    ("10_admin_dashboard",       "/admin/e/dashboard"),
    ("11_admin_vendors",         "/admin/e/vendors"),
    ("12_admin_registrations",   "/admin/e/registrations"),
    ("13_admin_notices",         "/admin/e/notices"),
    ("14_admin_tender_builder",  "/admin/e/tender-builder"),
    ("15_admin_corrigenda",      "/admin/e/corrigenda"),
    ("16_admin_boq",             "/admin/e/boq"),
    ("17_admin_work_packages",   "/admin/e/work-packages"),
    ("18_admin_catalog",         "/admin/e/catalog"),
    ("19_admin_vendor_intel",    "/admin/e/vendor-intel"),
    ("20_admin_engagements",     "/admin/e/engagements"),
    ("21_admin_bidding_ops",     "/admin/e/bidding"),
    ("22_admin_escrow",          "/admin/e/escrow"),
    ("23_admin_billing",         "/admin/e/billing"),
    ("24_admin_evaluation",      "/admin/e/evaluation"),
    ("25_admin_l1",              "/admin/e/l1"),
    ("26_admin_awards",          "/admin/e/awards"),
    ("27_admin_docusign",        "/admin/e/docusign"),
    ("28_admin_permissions",     "/admin/e/permissions"),
    ("29_admin_events",          "/admin/e/events"),
    ("30_admin_masters",         "/admin/e/masters"),
    ("31_admin_audit",           "/admin/e/audit"),
]

VENDOR_SHOTS = [
    ("50_vendor_home",           "/vendor"),
    ("51_vendor_tenders",        "/vendor/tenders"),
    ("52_vendor_mybids",         "/vendor/mybids"),
    ("53_vendor_signatures",     "/vendor/signatures"),
    ("54_vendor_company_kyc",    "/vendor/company"),
    ("55_vendor_account",        "/vendor/account"),
    ("56_vendor_alerts",         "/vendor/alerts"),
]

# A handful of mobile shots so admins see how the mobile view looks today.
MOBILE_SHOTS = [
    ("70_mobile_vendor_home",    "/vendor",            VENDOR,  PHONE),
    ("71_mobile_vendor_mybids",  "/vendor/mybids",     VENDOR,  PHONE),
    ("72_mobile_admin_bidding",  "/admin/e/bidding",   ADMIN,   PHONE),
    ("73_mobile_admin_vendors",  "/admin/e/vendors",   ADMIN,   PHONE),
]

async def login(page, email: str, password: str, admin: bool) -> bool:
    url = f"{BASE}/admin/login" if admin else f"{BASE}/login"
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    try:
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]', force=True)
    except Exception as e:
        print(f"login fill fail: {e}")
        return False
    await page.wait_for_timeout(4500)
    print(f"logged in as {email}, now at {page.url}")
    return True


async def shoot(page, path: str, out_name: str, settle_ms: int = 3500):
    target = OUT / f"{out_name}.png"
    err = OUT / f"{out_name}.err"
    try:
        await page.goto(f"{BASE}{path}", wait_until="domcontentloaded")
        await page.wait_for_timeout(settle_ms)
        # Dismiss any accidental sonner toast that could cover content
        try:
            await page.evaluate("document.querySelectorAll('[data-sonner-toast]').forEach(t => t.remove())")
        except Exception:
            pass
        await page.screenshot(path=str(target), full_page=False, type="png")
        if err.exists(): err.unlink()
        size = target.stat().st_size // 1024
        print(f"  ✓ {out_name}.png  ({size} KB)")
    except Exception as e:
        err.write_text(f"{type(e).__name__}: {str(e)[:300]}")
        print(f"  ✗ {out_name}  — {type(e).__name__}: {str(e)[:120]}")


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"],
                                          executable_path="/usr/bin/google-chrome")

        # Pass 1 — public (no login) @ desktop
        ctx = await browser.new_context(viewport=DESK, ignore_https_errors=True)
        page = await ctx.new_page()
        print("=== PUBLIC pages (desktop) ===")
        for name, path in PUBLIC_SHOTS:
            await shoot(page, path, name, settle_ms=2500)
        await ctx.close()

        # Pass 2 — admin @ desktop
        ctx = await browser.new_context(viewport=DESK, ignore_https_errors=True)
        page = await ctx.new_page()
        print("=== ADMIN pages (desktop) ===")
        if await login(page, ADMIN[0], ADMIN[1], admin=True):
            for name, path in ADMIN_SHOTS:
                await shoot(page, path, name)
        await ctx.close()

        # Pass 3 — vendor @ desktop
        ctx = await browser.new_context(viewport=DESK, ignore_https_errors=True)
        page = await ctx.new_page()
        print("=== VENDOR pages (desktop) ===")
        if await login(page, VENDOR[0], VENDOR[1], admin=False):
            for name, path in VENDOR_SHOTS:
                await shoot(page, path, name)
        await ctx.close()

        # Pass 4 — mobile mix
        print("=== MOBILE pages ===")
        for name, path, creds, vp in MOBILE_SHOTS:
            ctx = await browser.new_context(viewport=vp, ignore_https_errors=True,
                                            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605.1.15")
            page = await ctx.new_page()
            if await login(page, creds[0], creds[1], admin=(creds[0]==ADMIN[0])):
                await shoot(page, path, name)
            await ctx.close()

        await browser.close()

    # Final manifest
    shots = sorted(OUT.glob("*.png"))
    manifest = [{"name": p.stem, "size_kb": p.stat().st_size // 1024} for p in shots]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nTotal: {len(shots)} screenshots")


if __name__ == "__main__":
    asyncio.run(run())
