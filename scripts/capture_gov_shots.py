import asyncio, os
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")
from playwright.async_api import async_playwright

BASE = "https://pmc-forest-green.preview.emergentagent.com"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"],
            executable_path="/pw-browsers/chromium_headless_shell-1208/chrome-linux/headless_shell")
        page = await browser.new_page(viewport={"width": 1600, "height": 950})
        await page.goto(f"{BASE}/admin/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        await page.fill('[data-testid="admin-login-email"]', "adminsupport@pmcmanagers.com")
        await page.fill('[data-testid="admin-login-password"]', "Admin@12345")
        await page.click('[data-testid="admin-login-submit"]', force=True)
        await page.wait_for_timeout(4000)
        print("after login:", page.url)
        try:
            await page.get_by_text("Governance & integrity", exact=True).first.click(force=True)
        except Exception as e:
            print("nav click failed", e)
        await page.wait_for_timeout(3000)
        print("gov url:", page.url)
        for t in ["exceptions", "buyer", "integrity", "fees", "legal", "incidents"]:
            try:
                await page.click(f'[data-testid="gov-tab-{t}"]', force=True)
                await page.wait_for_timeout(1500)
                await page.screenshot(path=f"/tmp/gov_{t}.png", full_page=True)
                print("captured", t)
            except Exception as e:
                print("fail", t, e)
        await browser.close()

asyncio.run(main())
