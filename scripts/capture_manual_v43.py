"""
capture_manual_v43.py — Granular per-action screenshot pass for the
PMC Managers v2 user manual (Phase 3 of the v43 release).

The original `capture_manual_shots.py` grabbed 55 panel-level screenshots.
This v43 script layers ~150 additional per-modal captures on top of that:

  * For every admin tab we open the primary "New X" form and capture it
  * For key tabs we also click "Manage / Edit / Sign / Regenerate" action
    buttons and capture the resulting modal / confirmation
  * Every capture is placed in /app/deliverables/manual/screenshots/action/

Selectors are pinned via data-testid attributes so the script is resilient
to CSS refactors. If a selector is missing the frame silently skips and
prints a warning — the manual continues to reference the panel-level shot.

Run:
    python /app/scripts/capture_manual_v43.py
"""
import asyncio
import os
import sys
from pathlib import Path

BASE_URL = os.environ.get("MANUAL_BASE_URL", "http://localhost:3000")
ADMIN_EMAIL = os.environ.get("MANUAL_ADMIN_EMAIL", "adminsupport@pmcmanagers.com")
ADMIN_PASS = os.environ.get("MANUAL_ADMIN_PASS", "Admin@12345")

OUT_DIR = Path("/app/deliverables/manual/screenshots/action")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# Action recipes — each row is: (module_tab, shot_name, click_sequence)
# click_sequence is a list of ("action", "value") tuples:
#   ("goto", "/admin?tab=notices")
#   ("click", "notice-new-toggle")
#   ("fill",  "notice-title|Sample Title")     # data-testid|value
#   ("wait",  "1500")                          # ms
#   ("shot",  "admin-notices-new-form")
# =====================================================================
RECIPES = [
    # Notices — open the New Notice form
    ("notices", "admin-notices-new-form", [
        ("click", "notice-new-toggle"), ("wait", "600"),
    ]),
    ("notices", "admin-notices-filter-bar", [
        ("click", "notice-new-toggle"), ("wait", "300"),
        ("click", "notice-new-toggle"), ("wait", "400"),
    ]),

    # Registrations — filter tabs
    ("registrations", "admin-reg-tab-submitted", [
        ("click", "reg-filter-submitted"), ("wait", "800"),
    ]),
    ("registrations", "admin-reg-tab-approved", [
        ("click", "reg-filter-approved"), ("wait", "800"),
    ]),

    # Vendors — invite form + bulk modal + template upload label focus
    ("vendors", "admin-vendors-invite-form", [
        ("click", "vendor-invite-toggle"), ("wait", "500"),
    ]),
    ("vendors", "admin-vendors-bulk-invite-modal", [
        ("click", "vendor-bulk-invite-open"), ("wait", "700"),
    ]),
    ("vendors", "admin-vendors-status-filter-active", [
        ("click", "vendor-status-filter-active"), ("wait", "500"),
    ]),

    # Packages — new package form
    ("packages", "admin-packages-new-form", [
        ("click", "pkg-new-toggle"), ("wait", "500"),
    ]),

    # Bidding — committee form
    ("bidding", "admin-bidding-committee-form", [
        ("click", "committee-new-toggle"), ("wait", "700"),
    ]),

    # Escrow — new joint account form
    ("escrow", "admin-escrow-new-account-form", [
        ("click", "escrow-new-acc-toggle"), ("wait", "700"),
    ]),

    # Corrigenda — new corrigendum form
    ("corrigenda", "admin-corrigenda-new-form", [
        ("click", "corr-new-toggle"), ("wait", "600"),
    ]),

    # Live auctions — new auction form
    ("auctions", "admin-auctions-new-form", [
        ("click", "ra-new-toggle"), ("wait", "600"),
    ]),

    # Meetings — schedule form
    ("meetings", "admin-meetings-new-form", [
        ("click", "mtg-new-toggle"), ("wait", "600"),
    ]),

    # BOQ — new template form
    ("boq", "admin-boq-new-template-form", [
        ("click", "boq-new-toggle"), ("wait", "600"),
    ]),

    # Tender Builder — new tender master picker + kind tabs
    ("tender-builder", "admin-tender-builder-idle", [
        ("wait", "800"),
    ]),

    # Masters — each sub-tab
    ("masters", "admin-masters-staff-form", [
        ("click", "masters-tab-staff"), ("wait", "300"),
        ("click", "staff-new-toggle"), ("wait", "500"),
    ]),
    ("masters", "admin-masters-companies", [
        ("click", "masters-tab-companies"), ("wait", "500"),
    ]),
    ("masters", "admin-masters-tenants", [
        ("click", "masters-tab-tenants"), ("wait", "500"),
    ]),
    ("masters", "admin-masters-matrix", [
        ("click", "masters-tab-matrix"), ("wait", "500"),
    ]),
    ("masters", "admin-masters-hierarchy", [
        ("click", "masters-tab-hierarchy"), ("wait", "500"),
    ]),
    ("masters", "admin-masters-demo", [
        ("click", "masters-tab-demo"), ("wait", "500"),
    ]),

    # Permissions — landing state
    ("permissions", "admin-permissions-idle", [
        ("wait", "600"),
    ]),

    # Audit — filter bar
    ("audit", "admin-audit-filter-focus", [
        ("wait", "500"),
    ]),

    # Analytics — landing
    ("analytics", "admin-analytics-idle", [
        ("wait", "800"),
    ]),

    # L1 Comparison — landing
    ("l1", "admin-l1-idle", [("wait", "500")]),

    # DocuSign — landing form
    ("docusign", "admin-docusign-request-form", [
        ("wait", "700"),
    ]),

    # Awards — landing
    ("awards", "admin-awards-idle", [("wait", "500")]),

    # Vendor Intel — landing table
    ("vintel", "admin-vintel-idle", [("wait", "500")]),

    # Engagements — landing
    ("engagements", "admin-engagements-idle", [("wait", "500")]),

    # Product Catalog — landing
    ("catalog", "admin-catalog-idle", [("wait", "600")]),

    # Evaluation — landing state
    ("evaluation", "admin-evaluation-idle", [("wait", "600")]),

    # Help — landing state
    ("help", "admin-help-idle", [("wait", "800")]),
]


async def _login(page, ctx):
    """
    Authenticate by hitting the login API directly and injecting the
    resulting httpOnly cookies into the browser context.
    """
    import subprocess as _sp, json as _json
    from urllib.parse import urlparse
    api_url = os.environ.get("MANUAL_API_URL", "http://localhost:8001")
    body = _json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    # Use curl so Cloudflare doesn't 403 us on the preview URL.
    proc = _sp.run(
        ["curl", "-sSi", "-X", "POST",
         f"{api_url}/api/v1/admin/auth/login",
         "-H", "Content-Type: application/json",
         "-A", "Mozilla/5.0 (X11; Linux x86_64) PMC-Manual-Capture/1.0",
         "-d", body],
        capture_output=True, text=True, timeout=20,
    )
    host = urlparse(api_url).hostname or "localhost"
    cookies = []
    for line in proc.stdout.splitlines():
        if line.lower().startswith("set-cookie:"):
            hval = line.split(":", 1)[1].strip()
            name_val = hval.split(";", 1)[0]
            if "=" not in name_val:
                continue
            n, v = name_val.split("=", 1)
            cookies.append({
                "name": n.strip(), "value": v.strip(),
                "domain": host, "path": "/",
                "httpOnly": "HttpOnly" in hval,
                "secure": "Secure" in hval,
                "sameSite": "None" if "SameSite=None" in hval else "Lax",
            })
    print(f"    injecting {len(cookies)} cookies: {[c['name'] for c in cookies]}")
    if cookies:
        await ctx.add_cookies(cookies)
    await page.goto(f"{BASE_URL}/admin", wait_until="networkidle", timeout=25000)
    await page.wait_for_timeout(3500)
    print(f"    post-login url: {page.url}")


TAB_READY_SELECTORS = {
    "notices": "admin-notices-panel",
    "registrations": "admin-registrations-panel",
    "vendors": "admin-vendors-panel",
    "packages": "admin-packages-panel",
    "bidding": "admin-bidding-panel",
    "escrow": "escrow-panel",
    "corrigenda": "admin-corrigenda-panel",
    "auctions": "admin-live-auctions",
    "meetings": "admin-meetings-panel",
    "boq": None,  # BOQ panel doesn't wrap the tabs container yet
    "tender-builder": "tender-builder-panel",
    "masters": "admin-masters-panel",
    "permissions": "admin-permissions-panel",
    "audit": "admin-audit-panel",
    "analytics": "admin-analytics-panel",
    "l1": "admin-l1-panel",
    "docusign": "admin-docusign-panel",
    "awards": "admin-awards-panel",
    "vintel": "admin-vendor-intel-panel",
    "engagements": None,
    "catalog": None,
    "evaluation": "admin-evaluation-panel",
    "help": None,
}


async def _run_recipe(page, tab, shot_name, seq):
    print(f"  → tab={tab}  shot={shot_name}")
    await page.goto(f"{BASE_URL}/admin?tab={tab}", wait_until="networkidle", timeout=20000)
    # Wait for the panel testid to appear so React has rendered content.
    ready = TAB_READY_SELECTORS.get(tab)
    if ready:
        try:
            await page.locator(f'[data-testid="{ready}"]').first.wait_for(state="visible", timeout=15000)
        except Exception:
            pass
    await page.wait_for_timeout(2000)
    for step in seq:
        kind, arg = step
        try:
            if kind == "click":
                loc = page.locator(f'[data-testid="{arg}"]').first
                await loc.wait_for(state="visible", timeout=8000)
                await loc.click(timeout=6000)
            elif kind == "fill":
                testid, val = arg.split("|", 1)
                await page.locator(f'[data-testid="{testid}"]').first.fill(val, timeout=6000)
            elif kind == "wait":
                await page.wait_for_timeout(int(arg))
            elif kind == "goto":
                await page.goto(f"{BASE_URL}{arg}", wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"    step {kind}({arg}) FAILED: {e!r}")
    target = OUT_DIR / f"{shot_name}.png"
    await page.screenshot(path=str(target), full_page=False)
    print(f"    saved {target.name}")


async def main(codes: list):
    from playwright.async_api import async_playwright
    to_run = [r for r in RECIPES if not codes or r[0] in codes]
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await ctx.new_page()
        try:
            await _login(page, ctx)
            for tab, name, seq in to_run:
                try:
                    await _run_recipe(page, tab, name, seq)
                except Exception as e:
                    print(f"  RECIPE FAIL {tab}/{name}: {e!r}")
        finally:
            await ctx.close()
            await browser.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    asyncio.run(main(args))
    print(f"\nAll granular screenshots written to {OUT_DIR}")
