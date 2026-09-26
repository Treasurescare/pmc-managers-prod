"""Comprehensive screenshot + testing manual generator.

Uses Playwright (async, chromium) to walk every substantive PMC screen from
public → registration → admin login → each admin tab → vendor portal → logout.
Each capture is saved as a numbered PNG + a JSON manifest with the narrative
+ testing steps + expected outcome + relevant data-testid references.

Companion `build_screenshot_manual_pdf.py` stitches these into a PDF.
"""
import asyncio
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                       "https://pmc-forest-green.preview.emergentagent.com")
OUT_DIR = Path("/app/deliverables/manual_screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_EMAIL = "adminsupport@pmcmanagers.com"
ADMIN_PASS = "Admin@12345"

# Step blueprint — each entry becomes one page in the final PDF.
# fields: n, title, url, actions (list of Playwright expressions), narrative,
#         test_steps (list of {step, expected}), test_ids (data-testid list)
STEPS = [
    {
        "n": 1, "title": "Public landing page",
        "url": f"{BASE}/",
        "wait": 1200,
        "narrative": "Anyone who lands on the portal domain sees the tender-hub marketing page: brand identity, the four service lanes, and the top-right Sign in / Register CTAs.",
        "test_steps": [
            {"step": "Open the portal root URL in an incognito window", "expected": "Hero + Notices/Register/Sign-in in top nav render without a horizontal scroll on 375px viewports"},
            {"step": "Tap the language switcher (EN → RU → KK)", "expected": "Copy translates immediately; no console errors"},
        ],
        "test_ids": ["topbar-brand", "nav-notices", "nav-register", "nav-signin"],
    },
    {
        "n": 2, "title": "Public tender board",
        "url": f"{BASE}/notices",
        "wait": 1500,
        "narrative": "Public list of every published tender/RFP/RFQ across all tenants of the portal.",
        "test_steps": [
            {"step": "Verify at least one PUBLISHED notice appears with title + closing date + budget", "expected": "Cards render; DRAFT notices are hidden"},
            {"step": "Click a card to open the Notice Detail", "expected": "Detail page shows description, deadline, downloads and QA thread"},
        ],
        "test_ids": ["public-notice-card"],
    },
    {
        "n": 3, "title": "Vendor registration — start",
        "url": f"{BASE}/register",
        "wait": 1500,
        "narrative": "Section A (Identity) is the entry point. As soon as the vendor picks a file for any slot, a silent draft is created so nothing is lost.",
        "test_steps": [
            {"step": "Fill Section A (Company name, contact, email, phone, country)", "expected": "Continue button unlocks once required fields are valid"},
            {"step": "Attach a KYC doc to the ID slot", "expected": "File uploads with progress; a resume-link toast appears"},
        ],
        "test_ids": ["reg-section-a", "reg-continue"],
    },
    {
        "n": 4, "title": "Vendor registration — check status",
        "url": f"{BASE}/register/status",
        "wait": 1500,
        "narrative": "Any vendor with the emailed resume-token can paste it here to see current status without logging in.",
        "test_steps": [
            {"step": "Paste an invalid token", "expected": "Toast: 'Token invalid or expired — request a new resume link…' (Bug 7 fix)"},
            {"step": "Paste a valid token", "expected": "Status card shows stage + reviewer notes + submission timestamp"},
        ],
        "test_ids": ["status-token", "status-check", "status-result"],
    },
    {
        "n": 5, "title": "Admin login page",
        "url": f"{BASE}/admin/login",
        "wait": 1200,
        "narrative": "Dedicated admin login. HTTPOnly-cookie based, CSRF double-submit.",
        "test_steps": [
            {"step": "Try login with wrong password", "expected": "Toast surfaces backend error; no console stack trace"},
            {"step": "Try login with correct credentials", "expected": "Redirect to /admin dashboard within 1s"},
        ],
        "test_ids": ["admin-login-email", "admin-login-password", "admin-login-submit"],
    },
]

# Admin-authenticated tabs — captured after login.
ADMIN_TABS = [
    ("analytics",        "Dashboard · KPIs + AI-Anomaly drill cards"),
    ("registrations",    "Registrations pipeline · draft/submitted/approved"),
    ("vendors",          "Vendors master table + Bulk Invite"),
    ("notices",          "Notices · filter bar (search + status + template-only)"),
    ("corrigenda",       "Corrigenda · publish/withdraw with mandatory reason"),
    ("tender-builder",   "Tender Builder · sections + annexures + version history"),
    ("bidding",          "Bidding Ops · Committee UX overhaul (checkbox grid + dissolve + resend)"),
    ("auctions",         "Reverse Auctions · draft link hidden, participant validation"),
    ("escrow",           "Escrow · joint accounts, dual-signature releases"),
    ("evaluation",       "Evaluation · rubric + COI cross-check"),
    ("awards",           "Awards & POs · Regenerate with confirmation + version log"),
    ("boq",              "BOQ & Contracts · export/filter/versions"),
    ("meetings",         "Meetings · notice-ref required OR 'Internal meeting' tick"),
    ("l1",               "L1 Comparison · lowest-compliant winner + empty-state reasons"),
    ("docusign",         "DocuSign · Envelope Log with is_authoritative flag"),
    ("vendor-intel",     "Vendor Intel · BL/WL legend"),
    ("products",         "Product Catalog · price-change history"),
    ("engagements",      "Engagements · aging buckets + cancel reason ≥5 chars"),
    ("masters",          "Masters · roles + designations"),
    ("permissions",      "Permissions Matrix · tab-level RBAC + G2 effective view"),
    ("audit",            "Audit · every substantive action"),
    ("reports",          "Reports · Asked-vs-Delivered + flowcharts"),
    ("stakeholder",      "Stakeholder Reports · G4 rebuild (Tenders/Awards/Escrow/SLA)"),
    ("help",             "Help Requests · triage from public form"),
    ("branding",         "Portal Branding · logo history + theme colours"),
]


async def _shot(page, step_no: int, label: str, sub: str = "") -> Path:
    fname = f"{step_no:02d}_{label}.png"
    p = OUT_DIR / fname
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    await page.screenshot(path=str(p), full_page=False)
    print(f"  → shot #{step_no:02d} {label} ({p.stat().st_size // 1024} KB){' · ' + sub if sub else ''}")
    return p


async def capture():
    manifest = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        # -- 1..5 · Public + login screens
        for s in STEPS:
            print(f"[public] step {s['n']} · {s['title']}")
            try:
                await page.goto(s["url"], wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(s.get("wait", 1200))
                p = await _shot(page, s["n"], s["title"].replace(" ", "-").lower())
                manifest.append({**s, "image": p.name})
            except Exception as e:
                print(f"  ✗ {s['title']} failed: {e}")

        # -- Admin login (real credentials) --------------------------------
        print("[auth] logging in as admin…")
        try:
            await page.goto(f"{BASE}/admin/login", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)
            # Find the admin card email field
            try:
                await page.fill('[data-testid="admin-login-email"]', ADMIN_EMAIL, timeout=6000)
                await page.fill('[data-testid="admin-login-password"]', ADMIN_PASS, timeout=6000)
                await page.click('[data-testid="admin-login-submit"]', timeout=6000)
                await page.wait_for_url(lambda u: "/admin" in u, timeout=15000)
                await page.wait_for_timeout(2000)
                print("  ✓ admin logged in")
            except Exception as e:
                print(f"  ✗ admin login failed: {e}  — will screenshot login page only")
        except Exception as e:
            print(f"  ✗ admin login goto failed: {e}")

        # -- 6..30 · Admin tabs --------------------------------------------
        for i, (tab_key, sub) in enumerate(ADMIN_TABS, start=6):
            print(f"[admin] step {i} · tab={tab_key}")
            step = {
                "n": i,
                "title": f"Admin console · {tab_key.title().replace('-', ' ')}",
                "url": f"{BASE}/admin?tab={tab_key}",
                "narrative": sub,
                "test_steps": [
                    {"step": f"Click the '{tab_key}' tab in the admin sidebar", "expected": "Panel renders within 1s; no white screen; ErrorBoundary NOT triggered"},
                    {"step": "Interact with the primary CTA on the panel", "expected": "Backend responds; toast confirms success"},
                ],
                "test_ids": [f"admin-{tab_key}-panel"],
            }
            try:
                await page.goto(step["url"], wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(2500)
                p = await _shot(page, i, tab_key)
                step["image"] = p.name
                manifest.append(step)
            except Exception as e:
                print(f"  ✗ {tab_key} failed: {e}")

        # -- 31 · Logout ----------------------------------------------------
        print("[exit] step 31 · sign out")
        try:
            # Click the sign out button in the admin header
            try:
                await page.click('[data-testid="admin-logout"]', timeout=6000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            p = await _shot(page, 31, "sign-out-return")
            manifest.append({
                "n": 31, "title": "Sign out",
                "url": "post-logout",
                "narrative": "Confirms the user is back on the public login page and the admin cookie has been cleared.",
                "test_steps": [
                    {"step": "Click 'Sign out' in the admin header", "expected": "Redirect to /login within 1s; admin cookie cleared"},
                    {"step": "Try to hit /admin directly in the URL bar", "expected": "Bounce back to /login (401 on protected endpoints)"},
                ],
                "test_ids": ["admin-logout"],
                "image": p.name,
            })
        except Exception as e:
            print(f"  ✗ logout failed: {e}")

        await browser.close()

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nCAPTURED {len(manifest)} steps → {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(capture())
