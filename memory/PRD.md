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

### v49p (this fork) — Mobile responsive fix — 28 Feb 2026
Fixes user report: “this is the mobile view i want and i get is all stupid it
breaks badly”. User supplied `01-Mobile-Supplier.html` and
`02-Mobile-Public.html` as the target mobile experience.

Delivered:
- `frontend/src/mobile-fix.css` — comprehensive site-wide overrides at ≤767px
  - Forces `overflow-x: hidden` + `max-width: 100%` everywhere
  - `.pmc-wrap` → full width padded 16px
  - Hides desktop chrome: `.pmc-top`, `.pmc-vtop`, `.pmc-atop`, `.pmc-nav`,
    `.pmc-lnav`, `.pmc-side`, `.pmc-helpfab`, `.pmc-cmd`, `.pmc-desk`,
    `.pmc-who__t`
  - Collapses all 3-7 col grids (`.pmc-stages`, `.pmc-pipe`, `.pmc-kpis`,
    `.pmc-stats`, inline `repeat(N,1fr)` and `260px/280px 1fr`) to 1 col
  - Bid rows, next-action card, hero become single-column with 44px tap
    targets
  - Tables (except register-e) become block-stacked cards
  - Adds 76px bottom padding on every `[data-testid^="vendor-"]` page so the
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
