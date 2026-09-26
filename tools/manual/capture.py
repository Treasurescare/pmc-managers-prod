"""PMC v46m Master Training Manual — comprehensive Playwright capture.

Walks every public, vendor and admin surface — including modals, sub-tabs
and the new 5-portal Sovereign Gateway — and writes PNGs into
/app/deliverables/v46_manual/screens plus a JSON manifest that build.py
consumes.

Usage:  python3 /app/tools/manual/capture.py
"""
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                     "https://pmc-forest-green.preview.emergentagent.com").rstrip("/")
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


async def shot(page, idx, section, title, description, filename, full_page=False):
    path = OUT / filename
    await page.wait_for_timeout(700)
    try:
        await page.screenshot(path=str(path), full_page=full_page, type="png")
        add(idx, section, title, description, filename)
        print(f"  [{idx:03d}] {section:>10s}  · {filename}")
    except Exception as e:
        print(f"  !! screenshot {filename} failed: {type(e).__name__}: {e}")


async def safe_click(page, selector, timeout=4000):
    try:
        await page.click(selector, force=True, timeout=timeout)
        await page.wait_for_timeout(1200)
        return True
    except Exception:
        return False


async def safe_goto(page, url, timeout=25000):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(1600)
        return True
    except Exception as e:
        print(f"  !! goto {url} failed: {type(e).__name__}")
        return False


# ============================================================================
# PUBLIC — sovereign home, tender listings, about, vision, registration
# ============================================================================
async def capture_public(ctx):
    section = "Public"
    page = await ctx.new_page()
    print("== Public visitor ==")

    plans = [
        (1, "/",                    "Sovereign home — hero + live KPIs",
         "The public landing page. Editorial navy/gold hero with a Libre Baskerville headline, three live KPI cards (Notices Published, Suppliers Approved, Work Packages), and three primary CTAs — View Open Notices, Register as Supplier, and the Portal Gateways link.",
         "01_public_home.png", True),
        (2, "/notices",             "Public notice board",
         "The reverse-chronological list of every published notice. Fuzzy search, country/category filters, deadline chips and per-row EMD hints. This is the primary discovery surface for prospective bidders.",
         "02_public_notices.png", True),
        (3, "/tenders/live",        "Live tenders listing",
         "All tenders currently open for bidding. Same card structure as the notice board with a countdown chip on each card driving urgency.",
         "03_public_tenders_live.png", True),
        (4, "/tenders/completed",   "Completed tenders",
         "Public archive of every tender that has passed its submission deadline. Awards, final prices and winning bidders are shown once the award is finalised and cleared for publication.",
         "04_public_tenders_completed.png", True),
        (5, "/tenders/all",         "All tenders — unified archive",
         "The combined live + completed archive with a status filter. Used by researchers, auditors, and inbound partners doing due diligence on PMC.",
         "05_public_tenders_all.png", True),
        (6, "/about",               "About Us — company narrative",
         "Editorial About page. Charter, milestones, leadership grid, sector coverage, and press quotes. All copy is content-managed via the notice-board CMS.",
         "06_public_about.png", True),
        (7, "/vision",              "Vision & Mission",
         "The strategic doctrine page — Vision, Mission, Values, and the North-Star KPIs the platform is optimised for. Used in tender-committee briefings.",
         "07_public_vision.png", True),
        (8, "/register",            "Supplier registration — start",
         "Public entry point for vendor self-onboarding. Email, company name, country. A magic link is dispatched via Resend and the bidder resumes the deep intake wizard from that link.",
         "08_public_register.png", True),
    ]

    for idx, path, title, desc, fn, full in plans:
        if await safe_goto(page, f"{BASE}{path}"):
            await shot(page, idx, section, title, desc, fn, full_page=full)

    # Sovereign login — 5-portal picker
    if await safe_goto(page, f"{BASE}/login"):
        await shot(page, 9, section, "Sovereign Gateway — 5-portal picker",
                    "Five distinct credentials safeguard PMC. Selecting a card reveals a portal-specific credential form (per-role colour + badge).",
                    "09_public_login_grid.png", full_page=True)

        # Expand each portal to show its credential form
        portal_names = [
            ("admin",       10, "Admin portal — credential form",
             "The System Administrator portal — colours default to editorial slate + amber badge. Root-level control of the platform: user provisioning, master catalog, audit."),
            ("management",  11, "Management portal — credential form",
             "The PMC Management portal — executive dashboards, committee outcomes and escrow-level financials."),
            ("partners",    12, "Strategic Partners portal — credential form",
             "For GOC / Bank / Regulator personas — bank-guarantee verification, regulatory audit hooks, co-procurement dashboards."),
            ("agents",      13, "Procurement Agents portal — credential form",
             "Field-ops portal for procurement agents drafting tenders, reviewing bidder dossiers, publishing corrigenda and verifying BOQ line items."),
            ("vendors",     14, "Registered Vendors portal — credential form",
             "Bidder portal — purchase tender packs, submit digital bids, join live reverse auctions, sign contracts. Gold-accented CTA."),
        ]
        for pid, idx, title, desc in portal_names:
            if await safe_goto(page, f"{BASE}/login"):
                if await safe_click(page, f'[data-testid="portal-card-{pid}"]'):
                    await shot(page, idx, section, title, desc,
                                f"{idx:02d}_public_login_{pid}.png", full_page=True)

    await page.close()


# ============================================================================
# VENDOR — full portal walkthrough
# ============================================================================
async def login_vendor(ctx):
    page = await ctx.new_page()
    if not await safe_goto(page, f"{BASE}/vendor/login"):
        return page
    try:
        await page.fill('input[type="email"]', VENDOR_EMAIL)
        await page.fill('input[type="password"]', VENDOR_PASSWORD)
        await page.click('button[type="submit"]', force=True)
        await page.wait_for_timeout(3500)
    except Exception as e:
        print(f"  !! vendor login: {type(e).__name__}")
    return page


VENDOR_TABS = [
    ("tenders",     "Open tenders",             "Tenders the vendor may bid on, filtered to declared categories."),
    ("bids",        "My bids",                  "Every submitted bid with envelope status, score summary and award outcome."),
    ("rate",        "Ratings received",         "Reviews left by admins post-contract with an aggregate trust badge."),
    ("signatures",  "Contract signatures",      "DocuSign envelopes pending / signed by the vendor."),
]


async def capture_vendor(ctx):
    print("== Vendor portal ==")
    page = await login_vendor(ctx)
    await shot(page, 30, "Vendor", "Vendor landing (post-login)",
                "Vendor dashboard immediately after sign-in. Header shows company + trust badges; body shows open tenders, held EMDs, active auctions.",
                "30_vendor_landing.png", full_page=True)
    idx = 31
    for code, title, desc in VENDOR_TABS:
        if await safe_click(page, f'[data-testid="vendor-tab-{code}"]', timeout=3000):
            await shot(page, idx, "Vendor", f"Vendor · {title}", desc,
                        f"{idx:02d}_vendor_{code}.png", full_page=True)
        idx += 1
    await page.close()


# ============================================================================
# ADMIN — every top-level tab, then modal deep-dives
# ============================================================================
async def login_admin(ctx):
    page = await ctx.new_page()
    if not await safe_goto(page, f"{BASE}/admin/login"):
        return page
    try:
        await page.wait_for_selector('[data-testid="admin-login-email"]', timeout=10000)
        await page.fill('[data-testid="admin-login-email"]', ADMIN_EMAIL)
        await page.fill('[data-testid="admin-login-password"]', ADMIN_PASSWORD)
        await page.click('[data-testid="admin-login-submit"]', force=True)
        await page.wait_for_timeout(4500)
    except Exception as e:
        print(f"  !! admin login: {type(e).__name__}: {e}")
    return page


ADMIN_GROUPS = ["overview", "procurement", "market", "money", "events"]

ADMIN_TABS = [
    # (group, code, title, description)
    ("overview",   "analytics",       "Dashboard analytics",         "KPIs, funnel drills, revenue by module, activity heatmap."),
    ("overview",   "audit",           "Audit trail",                 "Immutable action log with entity filters."),
    ("procurement","notices",         "Notices — publish & manage",  "Create, publish, edit, withdraw, attach documents, EMD."),
    ("procurement","corrigenda",      "Corrigenda log",              "Publish addenda/amendments against any live notice."),
    ("procurement","tender-builder",  "Tender Builder & DPR AI",     "Master library, DPR deep-dive, AI Fill All, PDF export."),
    ("procurement","boq",             "BOQ templates & contracts",   "Bill of Quantities master + contract line items."),
    ("procurement","packages",        "Work packages",               "Modular deliverable packages for the KZ programme."),
    ("procurement","catalog",         "Product catalog",             "UNSPSC-mapped goods catalog."),
    ("market",     "vendors",         "Vendor directory",            "Full CRUD on suppliers, licences, compliance, tenants."),
    ("market",     "registrations",   "Vendor registrations queue",  "Approve, reject, resend activation, force-activate."),
    ("market",     "vintel",          "Vendor intel & ratings",      "Trust badges, moderation, criteria averages."),
    ("market",     "engagements",     "Consultant engagements",      "Retainer engagements, timesheets, invoices."),
    ("money",      "escrow",          "Escrow / EMD desk",           "EMD receipts, forfeitures, refunds."),
    ("money",      "billing",         "Billing & transactions",      "Fee ledger, refunds, Stripe reconciliation."),
    ("money",      "evaluation",      "Evaluation & scoring",        "Technical + financial scoring, QCBS, L1 comparison, envelope locking."),
    ("money",      "l1",              "L1 comparison",               "Head-to-head L1 comparison and award-ready report."),
    ("money",      "awards",          "Awards & POs",                "Letters of award, POs, contract award workflow."),
    ("money",      "docusign",        "DocuSign contracts",          "Envelope templates, signer routing, live status."),
    ("money",      "permissions",     "Roles & permissions",         "Fine-grained ACL matrix."),
    ("events",     "auctions",        "Reverse auctions",            "Live auction rooms, invitations, spectator link."),
    ("events",     "meetings",        "Pre-bid meetings",            "Scheduling, Zoom links, minutes, attendance."),
    ("events",     "masters",         "Masters — fees, roles, EMD",  "Fee slabs, staff roles, criteria, categories, countries."),
    ("events",     "help",            "Help & documentation",        "Contextual help + release notes."),
]


async def capture_admin(ctx):
    print("== Admin console ==")
    page = await login_admin(ctx)
    await shot(page, 50, "Admin", "Admin console landing (Operations Overview)",
                "First screen after admin login — collapsible sidebar grouped into Overview / Procurement / Market / Money & Compliance / Events, environment chip, AI Copilot shortcut.",
                "50_admin_landing.png", full_page=True)
    idx = 51
    for group, code, title, desc in ADMIN_TABS:
        # Expand the group first so the tab button is visible
        await safe_click(page, f'[data-testid="admin-sb-group-{group}"]', timeout=3000)
        clicked = await safe_click(page, f'[data-testid="admin-tab-{code}"]', timeout=4000)
        if clicked:
            await page.wait_for_timeout(2200)
            await shot(page, idx, "Admin", f"Admin · {title}", desc,
                        f"{idx:02d}_admin_{code}.png", full_page=True)
        idx += 1

    # ---------- Modal / sub-flow deep dives ----------
    # DPR modal + no-master helper + save-as-master
    if await safe_click(page, '[data-testid="admin-tab-tender-builder"]'):
        if await safe_click(page, '[data-testid="tb-open-dpr"]'):
            await page.wait_for_selector('[data-testid="dpr-modal"]', timeout=6000)
            await shot(page, idx, "Admin", "Tender Builder · AI DPR modal",
                        "Country-first DPR ingestion modal. Pick country → master → upload PDF → v46l map-reduce runs in the background with a live progress bar.",
                        f"{idx:02d}_admin_tb_dpr_modal.png", full_page=False)
            idx += 1
            try:
                await page.select_option('[data-testid="dpr-country"]', "KZ")
                await page.wait_for_timeout(1500)
                await shot(page, idx, "Admin", "Tender Builder · No-master helper",
                            "When the picked country has zero saved masters, two options appear: borrow a master from another country, or 'Build a brand-new master from this DPR'.",
                            f"{idx:02d}_admin_tb_no_master.png", full_page=False)
                idx += 1
            except Exception:
                pass

    # Evaluation panel with lock buttons + rubric editor
    if await safe_click(page, '[data-testid="admin-tab-evaluation"]'):
        await page.wait_for_timeout(2000)
        await shot(page, idx, "Admin", "Evaluation · Rubric + envelope locks",
                    "Scoring rubric (technical criteria weights, commercial weight, minimum technical cutoff) plus per-envelope Lock buttons. v46m: once locked, buttons swap to 'Sealed 🔒'.",
                    f"{idx:02d}_admin_evaluation_rubric.png", full_page=True)
        idx += 1

    # Masters library
    if await safe_click(page, '[data-testid="admin-tab-masters"]'):
        await page.wait_for_timeout(2000)
        await shot(page, idx, "Admin", "Masters · EMD, Fees, Rating criteria",
                    "Central master library — EMD/fee slabs by country + industry, rating rubric master, staff roles, category taxonomy, country register.",
                    f"{idx:02d}_admin_masters.png", full_page=True)
        idx += 1

    # Escrow desk
    if await safe_click(page, '[data-testid="admin-tab-escrow"]'):
        await page.wait_for_timeout(2000)
        await shot(page, idx, "Admin", "Escrow · Transactions ledger",
                    "Every EMD held, forfeited or refunded with signer attribution and joint-account snapshots.",
                    f"{idx:02d}_admin_escrow_transactions.png", full_page=True)
        idx += 1

    # Notices publish flow (open new)
    if await safe_click(page, '[data-testid="admin-tab-notices"]'):
        await page.wait_for_timeout(1500)
        if await safe_click(page, '[data-testid="notice-new-btn"], button:has-text("New notice")'):
            await shot(page, idx, "Admin", "Notices · New notice draft",
                        "Notice draft editor. Attach a Tender Builder template, set EMD/fee, upload the tender packet, and schedule publication.",
                        f"{idx:02d}_admin_notice_new.png", full_page=True)
            idx += 1

    await page.close()


# ============================================================================
async def main():
    global manifest
    manifest = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1600, "height": 900},
                                          device_scale_factor=1.25,
                                          ignore_https_errors=True)
        try:
            await capture_public(ctx)
            await capture_admin(ctx)
            await capture_vendor(ctx)
        finally:
            await browser.close()

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\nCaptured {len(manifest)} screens → manifest at {MANIFEST_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
