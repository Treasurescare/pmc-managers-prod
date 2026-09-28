# PMC Managers Limited v2 — Product Requirements Document

## Original problem statement
Build and continuously enhance a React + FastAPI + MongoDB multi-role procurement
platform for public visitors, vendors/suppliers, staff and administrators.
Core surfaces:
- Public notice/tender board, tenders list, notice detail, awards, Help centre
- Vendor portal (Home / Find tenders / My bids / Bid workspace / EMD & payments
  / Signatures / Company & KYC / Account / Alerts / Reviews)
- Admin console (dashboard, notices, tender builder, corrigenda, work packages,
  catalog, BoQ, vendors, registrations, engagements, vendor intel, KYC,
  bidding ops, escrow, billing, evaluations, L1 & awards, DocuSign, permissions,
  events, audit)
- Staff, committee, escrow-officer and meeting portals
- Auth: unified `/login`, vendor register/verify/reset, admin/staff logins
- Payments (Stripe EMD + billing), DocuSign contracts, Resend transactional email

## Design system
Option E forest-green/gold/cream is the exclusive UI (attribute `data-ui="e"`).
55 mocked HTML screens have been converted into JSX under
`frontend/src/apps/{notice-board-e,vendor-portal-e,admin-console-e,auth-e,
registration-e,help-centre,mobile-e,reference-e}/`. The generated markup is
mostly static; live data + click routing is patched at runtime via:
- `frontend/src/lib/pmcELiveData.js` — hydrates counts/labels/status/tables
- `frontend/src/components/PmcLinkPatcher.jsx` — global event delegation that
  intercepts static anchors and drives real navigation / actions
  (Pay EMD → Stripe checkout, Start Bid → `/vendor/bid/new/{ref}`, Review &
  sign → DocuSign, KPI tiles, sign-out, avatar menu, downloads, …)

## Deployment topology
- Frontend: S3 + CloudFront (same-origin API paths — production frontend
  builds must be created with `REACT_APP_BACKEND_URL=""`)
- Backend: AWS Elastic Beanstalk (Docker) — backend zip must retain
  `Dockerfile`, `Dockerrun.aws.json` and `.platform/` at zip root
- No preview URLs may appear in release docs/builds

---

## What is implemented

### v49o (previous release) — Public notice/detail
- Notice detail tabs actually switch section visibility (Documents /
  Corrigenda / Q&A / Timeline)
- Corrigenda: friendly fallback when there are none
- Guest download / follow / ask gates route to `/login` (not `/register`)
- Start Bid deep link parses nearest `data-notice-ref` or card href
- `testing_agent` iteration_37.json: green

### v49p (this fork) — Mobile responsive fix + PWA install rescue — 28 Feb 2026
Fixes user reports:
1. "this is the mobile view i want and i get is all stupid it breaks badly"
   → site-wide mobile responsive layout (see below).
2. "permanent install app does not work in few of the machines and browsers,
   in some samsung phones and samsung browser it does not work"
   → per-browser install instructions (see PWA rescue below).

Delivered:
- `frontend/src/mobile-fix.css` — **nuclear** site-wide overrides at ≤767px
  covering every class in the 55-screen theme AND every inline `style="grid-
  template-columns:…"` pattern found in the JSX:
  - Forces `overflow-x: hidden` + `max-width: 100%` universally
  - `.pmc-wrap` → full width padded 16px
  - Hides desktop chrome: `.pmc-top`, `.pmc-vtop`, `.pmc-atop`, `.pmc-nav`,
    `.pmc-lnav`, `.pmc-side`, `.pmc-helpfab`, `.pmc-cmd`, `.pmc-desk`,
    `.pmc-who__t`, `.pmc-crumb`
  - `.pmc-app` / `.pmc-adm` shells → single column
  - Every desktop grid class collapses to 1 col (`.pmc-hero__in`, `.pmc-stats`,
    `.pmc-kpis`, `.pmc-stages`, `.pmc-pipe`, `.pmc-facts`, `.pmc-feats`,
    `.pmc-steps`, `.pmc-cats`, `.pmc-grid3`, `.pmc-track`, `.pmc-cols`,
    `.pmc-bidrow`, `.pmc-next`, `.pmc-inbox`, `.pmc-tender__meta`, `.dg-grid`,
    `.ak`, `.st-grid`, `.flow`, `.hb`, `.rk`, `.ad-grid`, `.ad-chain`,
    `.ad-score`, `.pmc-drawer__foot`)
  - Every inline `style="grid-template-columns:…"` value collapses via
    attribute-selector rules — narrow icon+content rows (36px 1fr auto,
    40px 1fr, 20px 1fr, auto 1fr, 1fr auto) preserved with `min-width:0`
  - Stats / KPIs / Ak rows use 2-col at phone width for information density
  - Tables collapse to block-stacked rows (except `.e-register-table` which
    already has a custom mobile card layout)
  - Long headings wrap via `overflow-wrap: anywhere`
  - All buttons get `min-height: 44px` tap target
  - Adds 88px bottom padding on every `[data-testid^="vendor-"]` page so the
    fixed bottom tab bar never covers content
- `frontend/src/components/PmcMobileNav.jsx` — mobile chrome component
  - Public routes (`/`, `/notices`, `/tenders/*`, `/about`, `/vision`,
    `/help*`, `/suppliers`, `/buyers`, `/trust`, `/contact`, etc.): sticky
    top bar with brand + hamburger. Hamburger opens a slide-in drawer with
    10 nav links + `Sign in` / `Register` CTAs. All items have
    `data-testid`. ESC and scrim close the drawer.
  - Vendor routes (`/vendor`, `/vendor/*` except `/vendor/login`): fixed
    bottom tab bar `Home / Tenders / Bids / Alerts / Account`; active tab
    gets `is-active`; `data-testid` per tab: `mnav-home`, `mnav-tenders`,
    `mnav-bids`, `mnav-alerts`, `mnav-account`.
  - Suppressed on `/login`, `/vendor/login`, `/admin/login`, `/admin/*`,
    `/staff/*`, `/m/*` — those keep their own layouts.
- Zero changes to `PmcLinkPatcher`, routing logic, or existing page markup.

**PWA install rescue (Samsung Internet fix):**
- New `frontend/src/lib/pmcInstallInstructions.js` — UA-based detector
  (`detectPmcBrowser`) + `pmcInstallSteps()` returning browser-specific
  step-by-step install instructions for iOS Safari, Chrome iOS, Samsung
  Internet, Firefox Android, Opera Android, Chrome Android, Edge Android,
  desktop Chromium (Chrome/Edge/Opera), macOS Safari and Firefox desktop
  (which cannot install PWAs — instructs user to open on phone).
- `PmcMobileNav` hamburger "Install app" now ALWAYS renders those steps
  inline in the drawer when no native `beforeinstallprompt` is available
  or on browsers where `.prompt()` reliably no-ops (Samsung, Firefox).
  Previously only iOS was handled; Samsung + Firefox users hit a dead end.
- `PwaInstallPrompt` auto banner now also fires on Samsung + Firefox (2.5s
  delay identical to iOS) and its "Install app" button falls back to the
  same step-by-step instructions.
- Testids: `pmc-mobile-menu-install-steps`, `pwa-install-steps`.
- Service-worker cache version bumped to `pmc-shell-v49p-rev1` so returning
  visitors pick up the new SW on next load.

Verified in `test_reports/iteration_38.json` (frontend, testing_agent):
- **No horizontal scrolling** at 390×844 or 320×568 on public home, tenders
  list, notice detail, vendor home, vendor tenders, vendor bids, vendor
  alerts, vendor account.
- Hamburger drawer opens (body class `pmc-mob-menu-open`, drawer transform
  matrix(1,0,0,1,0,0)), 10 nav links + signin + register present, close via
  button removes body class.
- Bottom tab bar: 5 tabs, all navigate, `is-active` applied.
- Desktop 1440×900 regression: mobile chrome hidden (`display:none`),
  desktop `.pmc-nav`, `.pmc-vtop`, `.pmc-lnav` visible.
- `/login` and `/vendor/login` correctly suppress the mobile top bar.
- Manual verification: Pay EMD on `/vendor` (mobile) redirects to
  `checkout.stripe.com/c/pay/cs_test_...` — action still fully functional.

## Test credentials
`/app/memory/test_credentials.md`
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

---

## Priorities & backlog

### P0 (next up)
- (none open)

### P1 — Verification pending by user
- Mobile experience end-to-end on a real phone (iOS Safari + Android Chrome)
- Real inbox verification for 52 Option E email templates via Resend
- Real DocuSign resend / sign flow with an actual unsigned envelope
- Real EMD payment E2E in Stripe test mode from a mobile browser

### P1 — Optional next builds
- v49p AWS release bundle (frontend/backend zips + `DOWNLOAD_v49p.md`)
  once user approves; must be built with `REACT_APP_BACKEND_URL=""`
- Add “Alerts” badge (unread count) on the mobile bottom tab bar
- Add role-adaptive top bar for admin/staff mobile shells if user requests
  admin-on-phone workflows

### P2 — Backlog
- Navy reskin (Option A palette) — analysis complete, awaiting user go-ahead
- Web-push validation and E2E regression suite
- Orphan EMD backfill script
- Vendor `Change password` UX polish (current-pw + new-pw form vs. reset
  flow) — user previously flagged the flow feels off

---

## File map (most-recent-touch)

Frontend
- `App.js` — mounts `<PmcMobileNav />`, imports `mobile-fix.css`
- `mobile-fix.css` — ≤767px overrides + mobile chrome styles
- `components/PmcMobileNav.jsx` — mobile top bar + drawer + bottom tab bar
- `components/PmcLinkPatcher.jsx` — global click delegation (unchanged)
- `lib/pmcELiveData.js` — live-data hydration for Option E pages
- `pmc-theme-e.css` — Option E desktop stylesheet (55 mocks merged)
- `apps/notice-board-e/HomeE.jsx` — public home
- `apps/vendor-portal-e/VendorHomeE.jsx` — vendor home
- `design/mobile/01-Mobile-Supplier.html` — user reference
- `design/mobile/02-Mobile-Public.html` — user reference

Backend
- `server.py`, `routers/{password_reset,payments,vendor_auth,docusign,
  registrations,notices}.py`, `emails_option_e.py`

Test reports
- `test_reports/iteration_37.json` — public notice fixes (v49o)
- `test_reports/iteration_38.json` — mobile responsive fix (v49p)

### v49p — Mobile polish + Safari safe-area + Samsung install fix — 28 Feb 2026
User feedback: "mobile view stupidity continues in the safari the hamburger
is on top of the screen unaccessible; in samsung i just get the instruction
when i click the hamburger but after that nothing happens".

Fixed in this iteration:
1. **Safari (iOS) hamburger unreachable** — the `apple-mobile-web-app-status-
   bar-style` was `black-translucent`, causing installed-PWA mode to draw
   content under the notch/status bar. Switched to `default` and added
   explicit `env(safe-area-inset-top / left / right)` padding on
   `.pmc-mobile-topbar` and `.pmc-mobile-menu-drawer` so the hamburger and
   nav drawer always sit below the notch on every iPhone.
2. **Samsung Internet install** — my code had `preferManualSteps = "samsung"
   || "firefox"` which SKIPPED calling `deferred.prompt()` on Samsung
   Internet even when `beforeinstallprompt` had fired. Result: the button
   only showed instructions, never triggered the OS install dialog.
   Removed the shortcircuit — now the code ALWAYS tries the captured native
   prompt first, falls back to instructions only if the browser never fired
   the event or `.prompt()` rejects.
3. **Home page "Open for bids this week" one-word-per-line** — the JSX has
   `<div style="display: flex; justify-content: space-between; align-items: end">`
   with heading on left + `<button.pmc-chip>All/Tender/RFP/RFQ/Browse all</button>`
   row on right. On mobile the flex row was preserved so the chips row stole
   the width, leaving 57 px for the heading. New CSS forces every inline
   "flex space-between" section header to stack vertically at mobile width;
   the chips row becomes a full-width horizontally-scrollable strip.
4. **Card polish** — softer 12 px radius, subtle drop-shadow, 26 px display
   heading clamp, 34 px hero heading, 46 px min-height CTAs, stats/KPI grid
   as a bordered 2×2 tile with the accent line as gap.
5. **Toast position** — pushed down to `env(safe-area-inset-top) + 72 px`
   so post-login toasts never overlap the mobile top bar.

- Public (11 routes): /, /tenders/live, /tenders/completed, /about, /vision,
  /suppliers, /buyers, /trust, /help, /contact, /privacy
- Vendor (9 routes): /vendor, /vendor/tenders, /vendor/mybids, /vendor/emd,
  /vendor/signatures, /vendor/company, /vendor/account, /vendor/alerts,
  /vendor/reviews
- Admin (8 routes): /admin/e/dashboard, /admin/e/notices, /admin/e/tender-
  builder, /admin/e/bidding, /admin/e/escrow, /admin/e/evaluations,
  /admin/e/awards, /admin/e/audit
All 28 routes report `document.documentElement.scrollWidth === 390` at
390×844 viewport → zero horizontal overflow.

### v49p — Chips wrap fix (final mobile pass) — 28 Feb 2026
User spotted in screenshots: "Browse all notices" button rendered off-screen
because chip rows were set to horizontal scroll. Changed all chip/pill/tab
rows (section-header chips + generic .pmc-chips/.pmc-filters) from
`overflow-x: auto` to `flex-wrap: wrap`; trailing CTA buttons inside chip
rows get their own full-width line. Verified: button rect right=370 ≤ vw=390,
fullyVisible=true, scrollW=390. Bundle rebuilt at 16:52 UTC.
