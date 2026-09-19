"""
capture_manual_shots.py — Playwright-based screenshot capture for the
PMC Managers v2 user manual.

Given the module content in manual_content.py, each action declares a
`screenshot` filename. This script:
    1. logs in as admin (creds in test_credentials.md)
    2. navigates to each action's url_path
    3. saves a full-page screenshot to /app/deliverables/manual/screenshots/

Optional: pass module codes as args to capture only a subset.
    python scripts/capture_manual_shots.py admin-notices admin-escrow
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from manual_content import MODULES  # noqa: E402

OUT_DIR = Path("/app/deliverables/manual/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get("MANUAL_BASE_URL", "http://localhost:3000")
ADMIN_EMAIL = os.environ.get("MANUAL_ADMIN_EMAIL", "adminsupport@pmcmanagers.com")
ADMIN_PASS = os.environ.get("MANUAL_ADMIN_PASS", "Admin@12345")


async def _login(page):
    await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=25000)
    await page.wait_for_timeout(800)
    await page.fill('input[type="email"]', ADMIN_EMAIL)
    await page.fill('input[type="password"]', ADMIN_PASS)
    await page.locator('button[type="submit"]').first.click()
    await page.wait_for_timeout(2500)


async def _capture(page, module_code: str, module_spec: dict):
    print(f"→ {module_code} · {module_spec['title']}")
    path = module_spec.get("url_path", "/admin")
    await page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_timeout(2500)

    # Panel-level screenshot
    panel_shot = OUT_DIR / f"{module_code}-panel.png"
    await page.screenshot(path=str(panel_shot), full_page=False)
    print(f"    saved {panel_shot.name}")

    # One shot per action screenshot ID (currently defaults to the panel state;
    # future work: run action-specific flows to open modals/forms and capture).
    for action in module_spec.get("actions", []):
        shot_name = action.get("screenshot")
        if not shot_name:
            continue
        target = OUT_DIR / shot_name
        if target.exists():
            continue
        # For now, capture the same panel state; the DOCX builder handles the
        # "one shot per action" pointer.
        await page.screenshot(path=str(target), full_page=False)
        print(f"    saved {target.name}")


async def main(codes: list):
    from playwright.async_api import async_playwright
    codes = codes or list(MODULES.keys())
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        try:
            await _login(page)
            for code in codes:
                spec = MODULES.get(code)
                if not spec:
                    print(f"! unknown module: {code}")
                    continue
                if spec.get("surface") != "admin":
                    # skip non-admin surfaces in this basic pass
                    continue
                try:
                    await _capture(page, code, spec)
                except Exception as e:
                    print(f"    FAIL: {e!r}")
        finally:
            await ctx.close()
            await browser.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    asyncio.run(main(args))
    print(f"\nAll screenshots written to {OUT_DIR}")
