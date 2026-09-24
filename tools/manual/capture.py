"""PMC v46 Master Training Manual — automated screenshot capture.

Runs a headless Chromium against the preview environment (browser
chrome/URL bar is never included in Playwright screenshots, so no
emergent hostnames leak into the manual). Saves PNGs into
/app/deliverables/v46_manual/screens and appends a JSON manifest that
the build script consumes.

Roles captured:
  * Public visitor  — landing, notices board, notice detail, vendor register
  * Vendor portal   — dashboard tabs
  * Admin console   — every top-level tab

Usage:  python3 /app/tools/manual/capture.py
"""
import asyncio, json, os, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                     "https://tender-hub-57.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASSWORD = "Admin@12345"
VENDOR_EMAIL = "manualvendor@pmcmanagers.com"
VENDOR_PASSWORD = "Vendor@12345"

OUT = Path("/app/deliverables/v46_manual/screens")
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = OUT.parent / "manifest.json"

manifest: list[dict] = []


def add(idx: int, section: str, title: str, description: str, filename: str):
    manifest.append({"n": idx, "section": section, "title": title,
                     "description": description, "file": filename})


async def shot(page, idx: int, section: str, title: str, description: str,
                filename: str, full_page: bool = False):
    path = OUT / filename
    await page.wait_for_timeout(800)
    await page.screenshot(path=str(path), full_page=full_page, type="png")
    add(idx, section, title, description, filename)
    print(f"  [{idx:03d}] {section:>18s}  · {filename}")


async def safe_click(page, selector: str, timeout: int = 4000) -> bool:
    try:
        await page.click(selector, force=True, timeout=timeout)
        await page.wait_for_timeout(1500)
        return True
    except Exception:
        return False


async def capture_public(pw, ctx):
    section = "Public"
    page = await ctx.new_page()
    print("== Public visitor ==")

    await page.goto(f"{BASE}/", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1500)
    await shot(page, 1, section, "Landing page — Kazakhstan programme hero",
                "Public homepage. Shows live counters (Notices Published, "
                "Suppliers Approved, Work Packages) and quick paths to browse "
                "open tenders or register as a supplier.",
                "01_public_home.png", full_page=True)

    await page.goto(f"{BASE}/notices", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1500)
    await shot(page, 2, section, "Notice board — all published tenders",
                "Filterable list of every published notice: country, category, "
                "budget currency, submission deadline, EMD terms, contact.",
                "02_public_notices.png", full_page=True)

    # First notice detail
    if await safe_click(page, '[data-testid^="notice-row-"], a[href*="/notices/"]'):
        await shot(page, 3, section, "Notice detail — full tender packet",
                    "Selecting any notice opens the public detail view with "
                    "full description, documents, EMD/tender-fee summary, "
                    "corrigenda log, Q&A, and download-tender-packet button.",
                    "03_public_notice_detail.png", full_page=True)

    await page.goto(f"{BASE}/register", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1500)
    await shot(page, 4, section, "Supplier registration",
                "Public 'Register as supplier' onboarding — email/password, "
                "company details, country, licences, consent to data "
                "processing. Verification email dispatched on submit.",
                "04_public_register.png", full_page=True)

    await page.goto(f"{BASE}/login", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1500)
    await shot(page, 5, section, "Unified sign-in — Choose your portal",
                "Employees on the left (any staff role), suppliers on the "
                "right. Role selector routes admins to /admin and staff to "
                "/staff automatically.",
                "05_public_login.png", full_page=True)

    await page.close()


async def login_admin(ctx):
    page = await ctx.new_page()
    await page.goto(f"{BASE}/admin/login", wait_until="networkidle", timeout=30000)
    await page.wait_for_selector('[data-testid="admin-login-email"]', timeout=15000)
    await page.fill('[data-testid="admin-login-email"]', ADMIN_EMAIL)
    await page.fill('[data-testid="admin-login-password"]', ADMIN_PASSWORD)
    await page.click('[data-testid="admin-login-submit"]', force=True)
    await page.wait_for_timeout(4000)
    return page


ADMIN_TABS = [
    # (tab code, section title, description)
    ("analytics",       "Dashboard analytics",         "KPIs, funnel drills, revenue by module, activity heatmap."),
    ("registrations",   "Vendor registrations queue",  "Approve, reject, resend activation, force-activate."),
    ("vendors",         "Vendor directory",            "Full CRUD on suppliers, licenses, compliance, tenants."),
    ("notices",         "Notices — publish & manage",  "Create, publish, edit, withdraw, attach documents, EMD."),
    ("corrigenda",      "Corrigenda log",              "Publish addenda/amendments against any live notice."),
    ("tender-builder",  "Tender Builder & DPR AI",     "Master library, DPR deep-dive, AI Fill All, PDF export."),
    ("bidding",         "Bidding operations",          "Bid room, submissions, seal/unseal, timing."),
    ("escrow",          "Escrow / EMD desk",           "EMD receipts, forfeitures, refunds."),
    ("evaluation",      "Evaluation & scoring",        "Technical + financial scoring, QCBS, L1 comparison."),
    ("awards",          "Awards & POs",                "Letters of award, POs, contract award workflow."),
    ("docusign",        "DocuSign contracts",          "Envelope templates, signer routing, live status."),
    ("auctions",        "Reverse auctions",            "Live auction rooms, invitations, spectator link."),
    ("meetings",        "Pre-bid meetings",            "Scheduling, Zoom links, minutes, attendance."),
    ("boq",             "BOQ templates & contracts",   "Bill of Quantities master + contract line items."),
    ("vintel",          "Vendor intel & ratings",      "Trust badges, moderation, criteria averages."),
    ("masters",         "Masters — fees, roles, EMD",  "Fee slabs, staff roles, criteria, categories, countries."),
    ("permissions",     "Roles & permissions",         "Fine-grained ACL matrix."),
    ("packages",        "Work packages",               "Modular deliverable packages for the KZ programme."),
    ("audit",           "Audit trail",                 "Immutable action log with entity filters."),
    ("catalog",         "Product catalog",             "UNSPSC-mapped goods catalog."),
    ("engagements",     "Consultant engagements",      "Retainer engagements, timesheets, invoices."),
]


async def capture_admin(pw, ctx):
    print("== Admin console ==")
    page = await login_admin(ctx)
    await shot(page, 10, "Admin", "Admin console landing (Operations Overview)",
                "First screen after admin login — tab strip, environment "
                "chip, alerts, AI Copilot shortcut, security/2FA badge.",
                "10_admin_landing.png", full_page=True)

    idx = 11
    for code, title, desc in ADMIN_TABS:
        try:
            await page.click(f'[data-testid="admin-tab-{code}"]', force=True, timeout=6000)
            await page.wait_for_timeout(3000)
            await shot(page, idx, "Admin", f"Admin · {title}", desc,
                        f"{idx:02d}_admin_{code}.png", full_page=True)
        except Exception as e:
            print(f"  !! tab {code} failed: {type(e).__name__}")
        idx += 1

    # Deep-dive: Tender Builder → DPR modal (unique v46 feature)
    try:
        await page.click('[data-testid="admin-tab-tender-builder"]', force=True)
        await page.wait_for_timeout(2500)
        await page.click('[data-testid="tb-open-dpr"]', force=True)
        await page.wait_for_selector('[data-testid="dpr-modal"]', timeout=6000)
        await shot(page, idx, "Admin", "Tender Builder · AI DPR modal (v46g deep-dive)",
                    "Country-first DPR ingestion. When the country has no "
                    "master, admins can borrow one from another country or "
                    "build a brand-new master. Deep-dive (v46g) discovers "
                    "12–30 real chapters from the DPR and drafts each body.",
                    f"{idx:02d}_admin_tender_builder_dpr_modal.png",
                    full_page=False)
        idx += 1
        # Pick KZ to show no-master flow
        await page.select_option('[data-testid="dpr-country"]', 'KZ')
        await page.wait_for_timeout(1200)
        await shot(page, idx, "Admin", "Tender Builder · No-master options",
                    "When the picked country has no saved masters, an amber "
                    "helper offers two options: (1) borrow a master from "
                    "another country (all masters listed with country-code "
                    "prefix), or (2) build a brand-new master from this DPR.",
                    f"{idx:02d}_admin_tender_builder_no_master.png",
                    full_page=False)
        idx += 1
    except Exception as e:
        print(f"  !! DPR modal capture failed: {type(e).__name__}")

    await page.close()


async def capture_vendor(pw, ctx):
    print("== Vendor portal ==")
    page = await ctx.new_page()
    await page.goto(f"{BASE}/vendor/login", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1500)
    await shot(page, 60, "Vendor", "Vendor sign-in", "Dedicated vendor login "
                "(also accessible via /login → right card).",
                "60_vendor_login.png", full_page=True)
    try:
        await page.fill('input[type="email"]', VENDOR_EMAIL)
        await page.fill('input[type="password"]', VENDOR_PASSWORD)
        await page.click('button[type="submit"]', force=True)
        await page.wait_for_timeout(4500)
        await shot(page, 61, "Vendor", "Vendor dashboard landing",
                    "Overview of open tenders the vendor may bid on, "
                    "invoice status, ratings tab, profile & licenses.",
                    "61_vendor_dashboard.png", full_page=True)
    except Exception as e:
        print(f"  !! vendor login failed: {type(e).__name__}")
    await page.close()


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1600, "height": 900},
                                          device_scale_factor=1.25,
                                          ignore_https_errors=True)
        try:
            await capture_public(pw, ctx)
            await capture_admin(pw, ctx)
            await capture_vendor(pw, ctx)
        finally:
            await browser.close()

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\nCaptured {len(manifest)} screens → manifest at {MANIFEST_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
