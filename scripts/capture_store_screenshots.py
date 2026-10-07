import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path('/app/frontend/public/downloads/mobile_assets')
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://pmc-forest-green.preview.emergentagent.com'

async def capture_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. iOS Context (1290 x 2796 - iPhone 16 Pro Max / 15 Pro Max)
        ios_ctx = await browser.new_context(viewport={'width': 1290, 'height': 2796})
        ios_page = await ios_ctx.new_page()
        
        # iOS 1: Public Tenders
        await ios_page.goto(f'{BASE}/tenders/live', wait_until='networkidle', timeout=30000)
        await ios_page.wait_for_timeout(2000)
        await ios_page.screenshot(path=str(OUT / 'ios_6_7_public_tenders.png'), full_page=False)
        print('Saved ios_6_7_public_tenders.png')
        
        # iOS 2: Home Hero
        await ios_page.goto(f'{BASE}/', wait_until='networkidle', timeout=30000)
        await ios_page.wait_for_timeout(2000)
        await ios_page.screenshot(path=str(OUT / 'ios_6_7_home.png'), full_page=False)
        print('Saved ios_6_7_home.png')
        
        # iOS 3: Admin Login -> Admin Dashboard
        await ios_page.goto(f'{BASE}/admin/login', wait_until='networkidle', timeout=30000)
        await ios_page.wait_for_timeout(1000)
        await ios_page.fill('input[type="email"], input[name="email"]', 'adminsupport@pmcmanagers.com')
        await ios_page.fill('input[type="password"]', 'Admin@12345')
        btns = await ios_page.query_selector_all('button[type="submit"], button')
        for b in btns:
            t = (await b.inner_text()).strip().lower()
            if 'sign in' in t or 'login' in t:
                await b.click()
                break
        await ios_page.wait_for_timeout(4000)
        await ios_page.screenshot(path=str(OUT / 'ios_6_7_admin_dashboard.png'), full_page=False)
        print('Saved ios_6_7_admin_dashboard.png')
        
        # iOS 4: Admin Reverse Auctions
        await ios_page.goto(f'{BASE}/admin/e/auctions', wait_until='networkidle', timeout=30000)
        await ios_page.wait_for_timeout(3000)
        await ios_page.screenshot(path=str(OUT / 'ios_6_7_reverse_auction.png'), full_page=False)
        print('Saved ios_6_7_reverse_auction.png')
        
        # iOS 5: Vendor Login -> Vendor Dashboard
        ios_vendor_ctx = await browser.new_context(viewport={'width': 1290, 'height': 2796})
        ios_vendor_page = await ios_vendor_ctx.new_page()
        await ios_vendor_page.goto(f'{BASE}/vendor/login', wait_until='networkidle', timeout=30000)
        await ios_vendor_page.wait_for_timeout(1000)
        await ios_vendor_page.fill('input[type="email"], input[name="email"]', 'manualvendor@pmcmanagers.com')
        await ios_vendor_page.fill('input[type="password"]', 'Vendor@12345')
        btns = await ios_vendor_page.query_selector_all('button[type="submit"], button')
        for b in btns:
            t = (await b.inner_text()).strip().lower()
            if 'sign in' in t or 'login' in t:
                await b.click()
                break
        await ios_vendor_page.wait_for_timeout(4000)
        await ios_vendor_page.screenshot(path=str(OUT / 'ios_6_7_vendor_dashboard.png'), full_page=False)
        print('Saved ios_6_7_vendor_dashboard.png')

        # 2. Android Context (1080 x 2400 - Modern Android flagship portrait)
        and_ctx = await browser.new_context(viewport={'width': 1080, 'height': 2400})
        and_page = await and_ctx.new_page()
        
        # Android 1: Public Tenders
        await and_page.goto(f'{BASE}/tenders/live', wait_until='networkidle', timeout=30000)
        await and_page.wait_for_timeout(2000)
        await and_page.screenshot(path=str(OUT / 'android_phone_public_tenders.png'), full_page=False)
        print('Saved android_phone_public_tenders.png')
        
        # Android 2: Suppliers Overview
        await and_page.goto(f'{BASE}/suppliers', wait_until='networkidle', timeout=30000)
        await and_page.wait_for_timeout(2000)
        await and_page.screenshot(path=str(OUT / 'android_phone_for_suppliers.png'), full_page=False)
        print('Saved android_phone_for_suppliers.png')
        
        # Android 3: Admin Login -> Admin Dashboard
        await and_page.goto(f'{BASE}/admin/login', wait_until='networkidle', timeout=30000)
        await and_page.wait_for_timeout(1000)
        await and_page.fill('input[type="email"], input[name="email"]', 'adminsupport@pmcmanagers.com')
        await and_page.fill('input[type="password"]', 'Admin@12345')
        btns = await and_page.query_selector_all('button[type="submit"], button')
        for b in btns:
            t = (await b.inner_text()).strip().lower()
            if 'sign in' in t or 'login' in t:
                await b.click()
                break
        await and_page.wait_for_timeout(4000)
        await and_page.screenshot(path=str(OUT / 'android_phone_admin_dashboard.png'), full_page=False)
        print('Saved android_phone_admin_dashboard.png')
        
        # Android 4: Admin Reverse Auctions
        await and_page.goto(f'{BASE}/admin/e/auctions', wait_until='networkidle', timeout=30000)
        await and_page.wait_for_timeout(3000)
        await and_page.screenshot(path=str(OUT / 'android_phone_reverse_auction.png'), full_page=False)
        print('Saved android_phone_reverse_auction.png')
        
        # Android 5: Vendor Login -> Vendor Dashboard
        and_vendor_ctx = await browser.new_context(viewport={'width': 1080, 'height': 2400})
        and_vendor_page = await and_vendor_ctx.new_page()
        await and_vendor_page.goto(f'{BASE}/vendor/login', wait_until='networkidle', timeout=30000)
        await and_vendor_page.wait_for_timeout(1000)
        await and_vendor_page.fill('input[type="email"], input[name="email"]', 'manualvendor@pmcmanagers.com')
        await and_vendor_page.fill('input[type="password"]', 'Vendor@12345')
        btns = await and_vendor_page.query_selector_all('button[type="submit"], button')
        for b in btns:
            t = (await b.inner_text()).strip().lower()
            if 'sign in' in t or 'login' in t:
                await b.click()
                break
        await and_vendor_page.wait_for_timeout(4000)
        await and_vendor_page.screenshot(path=str(OUT / 'android_phone_vendor_dashboard.png'), full_page=False)
        print('Saved android_phone_vendor_dashboard.png')

        await browser.close()
        print('All screenshots captured successfully!')

if __name__ == '__main__':
    asyncio.run(capture_all())
