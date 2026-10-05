"""Re-capture just the light-shell vendor pages after the v51v bg fix."""
import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "https://pmc-forest-green.preview.emergentagent.com"
OUT = Path("/app/deliverables/manual_v7_shots")
VENDOR = ("manualvendor@pmcmanagers.com", "Vendor@12345")
TARGETS = [
    ("66-vendor-bid-submit", "/vendor/bid/new/PMC-NOT-2026-0020"),
    ("63-vendor-sandbox-checkout", "/vendor/payment/sandbox"),
    ("64-vendor-payment-success", "/vendor/payment/success"),
    ("65-vendor-payment-cancel", "/vendor/payment/cancel"),
    ("61-vendor-change-password", "/vendor/change-password"),
]

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"],
                                          executable_path="/usr/bin/google-chrome")
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900},
                                        ignore_https_errors=True)
        page = await ctx.new_page()
        await page.goto(f"{BASE}/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await page.fill('input[type="email"]', VENDOR[0])
        await page.fill('input[type="password"]', VENDOR[1])
        await page.click('button[type="submit"]', force=True)
        await page.wait_for_timeout(4500)
        print("vendor at:", page.url)
        for slug, path in TARGETS:
            try:
                await page.goto(f"{BASE}{path}", wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                await page.screenshot(path=str(OUT / f"{slug}.png"), full_page=True)
                print(f"  ✓ {slug}.png ({(OUT / f'{slug}.png').stat().st_size // 1024} KB)")
            except Exception as e:
                print(f"  ✗ {slug}: {type(e).__name__} {str(e)[:100]}")
        await browser.close()

asyncio.run(run())
