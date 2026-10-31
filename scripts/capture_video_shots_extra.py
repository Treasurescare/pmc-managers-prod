"""Re-capture registration steps + tender search for the video shots."""
import asyncio
import shutil

from playwright.async_api import async_playwright

BASE = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env") if l.startswith("REACT_APP_BACKEND_URL=")][0].rstrip("/")
OUT = "/app/frontend/public/downloads/pmc-video-shots"
TOKEN = "Kp1lXjKIoTV8HxGaeFmfEM47sq9Ib08qIIgQ0ZbLpsc"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await (await b.new_context(viewport={"width": 1920, "height": 1080})).new_page()
        await page.goto(f"{BASE}/tenders/live")
        await page.wait_for_timeout(3500)
        try:
            await page.locator("input[placeholder^='Keyword']").first.fill("hospital", timeout=5000)
            await page.wait_for_timeout(1500)
            await page.screenshot(path=f"{OUT}/1-02b-tender-listing-search.png")
            print("ok search")
        except Exception as e:
            print("FAIL search", str(e)[:100])
        await page.goto(f"{BASE}/register/resume?token={TOKEN}")
        await page.wait_for_timeout(3500)
        for s in ["b", "c", "d", "directors", "e"]:
            try:
                await page.locator(f"[data-testid='step-{s}']").click(force=True, timeout=5000)
                await page.wait_for_timeout(1500)
                await page.screenshot(path=f"{OUT}/1-05-registration-step-{s}.png")
                print("ok", s)
            except Exception as e:
                print("FAIL", s, str(e)[:100])
        await b.close()
    shutil.make_archive(OUT, "zip", OUT)


asyncio.run(main())
