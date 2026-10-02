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

### v49p — Tender list row (.tl-row) mobile collapse fix — 29 Sep 2026
User: "in home page when i click browse all notices it is breaking totally".
Root cause: theme rule `.tl-row{display:grid;grid-template-columns:minmax(0,1fr) 170px 150px 110px}`
— on 390px the fixed tracks (430px) overflow the container, so the flexible
title column collapsed to 0px → title rendered one character per line.
Fix in mobile-fix.css (≤767px): `.tl-row` becomes `1fr 1fr`; `.tl-main` and
`.tl-act` span full width (title/tag row on top, follow+View actions as a
bottom row); budget/closes sit side-by-side. Also added mobile coverage for
`.pmc-kv`, `.pmc-inrow`, `.pmc-docrow`, `.dlg-h`, `.pmc-cols` (class-based
fixed-column grids the inline-style nuclear rule could not catch).
Verified: gtc computes to 162px 162px, title width 336px, scrollW=390.
Bundle rebuilt (01:54 UTC).

### v49p — My Bids + Alerts + Signatures + Toast pass — 29 Sep 2026
User-reported batch (mobile):
1. My Bids: 4 KPI boxes misaligned/overflowing → `.sp-kpis` 2×2 grid at ≤767px
   with contained figures (overflow-wrap). Tabs Active/Drafts/Closed/Withdrawn
   were cosmetic-only → `filterMyBidsRows()` in PmcLinkPatcher filters the bids
   table rows by status pill in place. Bid price flush to card edge → stacked
   `td` padding 6px 14px. Verified: KPIs 2×2 (174px each), Drafts tab 6→3 rows.
2. Alerts: tabs All/Needs action/Tenders/Payments were dead →
   `filterAlertRows()` filters `.al-r` rows (Needs action = `.un` class,
   Tenders/Payments by keyword). "Mark all read" now calls
   POST /api/v1/notifications/vendor/read-all and clears `.un` + h1 count.
   "See change" → /notices/{ref}, "See tenders" → /vendor/tenders,
   "Alert settings" → /vendor/account. Verified: tabs filter 5→2 rows,
   mark-all-read unread 2→0, toast "All alerts marked as read."
3. Toasts: error toasts capped at 10s auto-dismiss (was 12s), others 6-8s,
   close button retained.
4. Signatures page (vendor): Preview/View now open the envelope's current
   document PDF in a new tab (inline) via NEW endpoint
   GET /api/v1/docusign/mine/envelopes/{id}/document.pdf (works in ANY status —
   unsigned while pending, signed combined once completed); Download saves it
   (attachment) — new Download button auto-inserted on the hero card; Continue
   resumes the signing ceremony. Fixed `vendor_resume_signing`: email-mode
   envelopes previously failed to mint an embedded recipient view (no
   client_user_id) — now stamps client_user_id onto the recipient and retries.
   Also fixed dead admin route: `GET /docusign/envelopes/{id}/combined-pdf`
   was missing its @router decorator.
5. Bug introduced+fixed same session: `ctx is not defined` ReferenceError in
   resolveClickAction (destructured pageId missing) — broke all action clicks
   briefly; fixed and verified via alerts flow.
Backend restarted clean; bundle rebuilt (03:14 UTC).

### v49p — DocuSign "Close-only, cannot sign" root-cause fix — 29 Sep 2026
User: "docusign still does not let me sign" — screenshot showed the recipient
view rendering the PO with ONLY a "Close" button. That state means the signer
has ZERO tabs on the envelope (DocuSign hides Finish/Sign entirely).

Root causes found and fixed in backend/routers/docusign.py:
1. `_create_envelope` anchor SignHere tab was missing recipient_id and
   document_id → DocuSign silently dropped it. The fixed-position fallback
   (y=700) sat below the signature area. Result: envelopes went out with no
   usable Sign Here tab.
2. Award PDFs (PO/SLA/contract in routers/awards.py) contained no `/sig_here/`
   anchor marker, so even a well-formed anchor tab had nothing to land on.

Fixes:
- All tabs now carry recipient_id="1" + document_id="1". Anchored SignHere at
  `/sig_here/` + DateSigned at `/ds_here/`, plus fixed-position fallbacks at
  the supplier signature box (page 1, x=330, y=240 / y=285).
- awards.py PO/SLA/contract templates now embed invisible 1pt white
  `/sig_here/` and `/ds_here/` markers inside the supplier sig-box, so future
  envelopes anchor the tab exactly on the supplier line.
- `vendor_resume_signing` (POST /docusign/mine/{id}/sign) now runs two repair
  passes before minting the recipient view: (1) stamp client_user_id onto
  email-mode recipients, (2) list recipient tabs and CREATE a SignHere +
  DateSigned tab if none exist — this retro-fixes ALREADY-SENT envelopes like
  PMC-AWD-2026-00027 on the vendor's next "Review & sign" click. Repairs are
  audit-logged (`docusign.tabs_repaired`).

Environment note: preview pod's DocuSign sandbox key returns
`invalid_grant: issuer_not_found` (stale key) — live ceremony can only be
verified in production, where credentials work (user's screenshot proves the
view renders there).

### v49p — Help drawer close + tender-detail tabs + footer (mobile) — 29 Sep 2026
User report (3 items):
1. Help drawer required Esc to exit; no usable close on mobile. Root cause:
   every generated page embeds its own static `.pmc-drawer` whose Close button
   carries `data-help-close` — but no delegated handler existed, so the button
   was dead and only Esc worked. Fix: PmcLinkPatcher now handles
   `[data-help-close]` clicks AND scrim taps (scrim is a <div>, handled before
   the a/button guard) by removing `pmc-help-open` from documentElement.
   Mobile CSS: drawer becomes full-width sheet with sticky header, 44px close
   button, safe-area padding, footer CTAs full-width, "Esc" kbd hint hidden.
2. Tender detail tabs (Overview/Eligibility/Documents/Clarifications/
   Corrigenda) overflowed → changed from horizontal scroll to wrapped pill
   row (all 5 visible on one screen, selected = filled primary).
   Verified: 5/5 tabs in viewport at 390px, wrap=wrap.
3. Footers overflowed → footer .pmc-wrap stacks column on mobile, links wrap,
   safe-area bottom padding. Verified: flex-direction=column, all links
   within viewport, scrollW=390.

### v49p — Drawer close hardening (final) — 29 Sep 2026
Follow-up: scrim taps on the React help drawer didn't close it because the
scrim is mounted at app level (outside [data-pmc-e-page]) so the page-root
guard skipped it; also static-drawer closes could desync React state so the
next FAB click no-op'd. Fix: scrim taps handled first in the delegated
listener (before the root guard) and both scrim + data-help-close paths now
also click the React Close button to sync state. Verified via real open path:
open → Close btn → closed; reopen → scrim tap → closed. Tabs wrap + footer
stack verified same session (5/5 tabs visible at 390px; footer column, no
overflow). Bundle rebuilt 03:55 UTC.

### v49p — Desktop regression fix (PmcMobileFilters DOM surgery) — 29 Sep 2026
User: "in the enthusiasm to get the mobile view ready the desktop view has
been screwed". Root cause: PmcMobileFilters restructured the DOM (moved
aside.tl-filters into a fixed bottom-sheet wrapper) at ALL viewport widths.
On desktop the sheet is display:none, so the filters sidebar vanished and
the 272px+1fr results grid collapsed (results section shrank to 272px,
chips stacked vertically, cards squeezed). Diagnosed live: gridChildren were
[scrim, sheet, section] instead of [aside, section].
Fix: component now gates ALL DOM changes behind matchMedia("(max-width:
767px)") — install() only on mobile; uninstall() restores the aside to its
original parent/sibling position and removes FAB/scrim/sheet; a matchMedia
change listener re-applies on resize/rotate. Desktop DOM is never touched.
Verified: desktop 1920 → gridChildren [tl-filters, section], aside 272px
visible, results 976px, no FAB; home wrap 1280 centered at 1440; vendor
portal desktop app grid 248px+main intact, mobile tabbar display:none.
Mobile 390 regression: FAB present, bottom-sheet opens, scrollW=390.
SW cache bumped to pmc-shell-v49p-rev3. Bundle rebuilt 04:29 UTC.

### v49p — My Bids tabs: Recently-decided panel + empty states — 29 Sep 2026
User: "in vendor portal these tabs are not working" (Active/Drafts/Closed/
Withdrawn). The row filter worked but the "Recently decided" panel below the
table never hid, so the page always showed rows and tabs looked dead.
filterMyBidsRows() now: filters main table by status pill; shows the
Recently-decided panel ONLY on Closed; hides it (and its heading) otherwise;
shows "No {tab} bids right now." empty-state note when zero rows match.
Verified desktop 1440 (Drafts→1 row, Closed→1 row+decided panel,
Withdrawn→empty note, Active→2 rows) and mobile 390 (same behavior,
scrollW=390). Bundle rebuilt 04:50 UTC. Full 1440+390 regression sweep
launched via testing_agent (iteration_39).

### v49p — Regression sweep iteration_39 follow-ups — 29 Sep 2026
testing_agent sweep (12/14 pass) found 2 regressions; both fixed & verified:
1. My Bids "Recently decided" panel stayed visible on Active/Drafts/Withdrawn.
   (Agent ran against stale bundle; direct re-verification of the fixed code
   confirms: Withdrawn → 0 rows + "No withdrawn bids right now." + panel +
   heading hidden; Closed → 1 row + panel + heading shown; Active → 2 rows,
   panel hidden.)
2. /register at ≤767px rendered the mobile topbar over the registration
   page's own header. Added /register to the exclusion list in
   PmcMobileNav (alongside /login, /vendor/login, /forgot-password,
   /reset-password). Verified: topbar absent at 390px, register layout clean.
Bundle rebuilt 04:58 UTC (SW rev3).

### v49p — /tenders/live pagination fix — 29 Sep 2026
User: "pagination is not working". TendersListE.jsx had hardcoded footer
markup ("Showing 1–7 of 7", disabled Prev/Next, single "1"). Fix in
pmcELiveData.js renderRows(): 10 per page, dynamic label, windowed numbered
buttons (up to 7), working Prev/Next with correct disabled states, page
state on panel.dataset.pmcPage, resets to 1 on filter/query change (keyed by
JSON.stringify({q,status,types,country})). testing_agent iteration_40: 100%
pass on desktop 1440 + mobile 390. 14 notices → p1 10, p2 4; filter reset
verified ("TEST_Wave1" from p2 auto-resets to "Showing 1–3 of 3"). Bundle
rebuilt 05:26 UTC.

### v49p — Bidding-Ops redesign HTML review — 29 Sep 2026
User supplied /app/design/user/Bidding-Ops-redesign.html (571 lines, 76 KB).
Assessment: EXCELLENT fit for adoption — reuses our exact Option E theme
tokens (--primary, --brass, --chrome, --surface, --ink, --line-strong,
--radius-*, --font-display, --shadow-1) and PMC component classes (pmc-btn,
pmc-panel, pmc-tender, pmc-tag, pmc-pill — 71 references). Introduces a few
new page-specific classes (.bo-flow for the bidding operations flow section)
which we can convert to a component. Recommended plan: (a) extract the new
Bidding-Ops layout into
frontend/src/apps/admin-console-e/BiddingOpsE.jsx, (b) mount at
/admin/e/bidding, (c) verify mobile responsive behaviour with the same
mobile-fix.css nuclear rules. No conflict with the existing theme; drop-in
compatible. Awaiting user go-ahead to implement.

### v49p — Tender card equal-height fix — 29 Sep 2026
User screenshot: "Open for bids this week" home cards had 4 different
heights and misaligned content. Fixed .pmc-tender in pmc-theme-e.css:
height:100%, top row nowrap with ellipsis on ref and pinned countdown,
2-line clamp on title (min-height 2.83em) and 2-line clamp on meta dd.
Applies everywhere .pmc-tender is used. Screenshots at 1440 and 390
confirm alignment; no regression.

### v49q — Bidding Ops redesign adopted — 29 Sep 2026
Rewrote `apps/admin-console-e/AdminBiddingOpsE.jsx` using the supplied
`design/user/Bidding-Ops-redesign.html` shell and added scoped CSS at
`apps/admin-console-e/bidding-ops.css` (~90 lines of bo-* classes,
all using existing Option E tokens — zero new vars).

Wired to real data via a rewritten `useAdminBiddingOpsLive` in
`lib/pmcELiveData.js`:
- Fetches `/api/v1/bids`, buckets each row (supplier / pmc / awarded)
  from `status`, computes stage index & dots (6-step Escrow→Committee).
- Fills 7 flow counters (EMD/Escrow/Admin/Certifier/Legal/Accounts/
  Awarded), 4 tab counts, subtitle total + test-data count, and the
  sidebar `Bidding ops` badge (Needs-PMC count).
- Per-row: reference, title, notice+vendor sub-line, price, price-anomaly
  flag if bid > 1.5× notice budget, EMD line (paid / link sent / —),
  stage dots, next step, owner, waiting age, and a primary action button.
- Right panel: detail placeholder + Active-committee card driven by
  `/api/v1/committees` (open committee if any).

Component wires tabs, hide-test toggle, row select and bulk-select bar
via a `MutationObserver` so live data reflows work after `innerHTML`
replaces. All interactive elements have `data-testid`.

Smoke test at 1440 (admin authed): 9 real bids rendered, flow=4/1/0/1/
0/0/3, tabs=2/4/3/9, sidebar count=2. Mobile 390 layout stacks
correctly (empty state without auth).

New build script: `scripts/build_v49q.sh` produces
`pmc-frontend-v49q-prod-build.zip` (same-origin) and
`pmc-backend-v49q.zip`, plus release notes.

### v49q — Admin Dashboard redesign BLOCKED — 29 Sep 2026
User uploaded `E-Admin-Dashboard.html` (355 lines) with a new admin
dashboard layout (attention strip, tender pipeline chart, evaluation
scoring table, closing-this-week, approvals queue, live audit stream).
Blocker: the redesign uses a completely different DARK palette
(`#06201A` background, `#0B2C23` cards, `#EAF0EA` text, `#D2B46A` brass)
whereas the current Option E admin console is a LIGHT palette
(`--paper #f6f3ec`, `--surface #ffffff`, `--ink #14201a`). This is not
a drop-in adoption — it's an "admin goes dark" decision.
Two options for the user to pick:
(a) Full dark-admin refactor — new palette applies to every admin page.
(b) Port only the layout blocks (attention strip / pipeline chart /
    evaluation / audit stream) into our existing LIGHT theme, keeping
    parity with the other admin screens.
NOT started until user picks a path.

### v49q — Old-console redirect fix — 29 Sep 2026
User reported still seeing the old design. Root cause: the legacy
tab-based console at `/admin?tab=bidding` renders BiddingOpsPanel, while
the new redesign only lived at `/admin/e/bidding`. Fix in
`apps/admin-console/AdminDashboard.jsx`: render-time
`<Navigate to="/admin/e/bidding" replace />` when tab === "bidding"
(useEffect-based redirect raced and lost to the location.search sync
effect). Verified: login → /admin?tab=bidding → lands on
/admin/e/bidding with 9 real bids in the new pipeline/table.
v49q frontend bundle rebuilt to include this redirect.

### v49q — Admin Dashboard redesign ported to light theme — 29 Sep 2026
User chose option (b): port E-Admin-Dashboard.html sections into the
light Option E theme (NOT the dark navy palette). Rewrote
`apps/admin-console-e/AdminDashboardE.jsx` + new scoped
`admin-dashboard.css` (adh/ad-attn/ad-pipe/ad-appr/ad-audit classes, all
token-based). Sections: eyebrow+H1 head, ATTENTION strip (closing /
drafts / EMD-pending counts), 7-stage pipeline with vertical bars
(I Draft → VII Awarded, hot state on Bidding), 4 KPI cards (EMD
collected, active contracts, bids in pipeline, approved vendors),
Bids-waiting table (top 5 in-flight bids with status pills + next step),
Closing-this-week table (bids sealed + countdown per tender), Approvals
queue (draft notices), Audit stream (last 6 hash-chained events).
All wired in rewritten `useAdminDashboardLive` — fetches notices,
vendors, packages, stats, escrow-summary, /api/v1/bids and
/api/v1/audit-events in parallel. Verified admin-authed at 1440:
attn 05/00/04, pipeline 0/14/0/5/0/1/2, KPIs $31,600/14/6/41,
5 bid rows, 6 audit rows. Mobile 390: attention strip stacks,
pipeline 2-col. All CTAs are real links (audit, tender-builder,
notices, bidding). No mock content remains on the page.
v49q bundle rebuilt again with dashboard + redirect included.

### v49q — Bidding Ops action wiring + responsive layer — 29 Sep 2026
User reported dashboard pages broken; root causes: (a) the Bidding Ops
search box was never wired to a filter, (b) long refs/hashes blew out
grid columns (min-width:auto), tables had no card mode, sidebar never
collapsed at laptop/zoom widths.

Fixes:
1. Wired bo-search-input → row text filter in paint(); verified 0
   visible for junk query, correct subset when cleared.
2. Adopted user-supplied `pmc-responsive.css` (copied to
   `frontend/src/pmc-responsive.css`, imported in App.js AFTER
   mobile-fix.css): box-sizing, min-width:0 on grid children, word-wrap
   on hashes/refs, panel-internal table scroll, sidebar→drawer ≤1100,
   tables→cards ≤900 (via data-label), touch targets ≤760, print rules.
3. Adopted user-supplied `pmc-responsive.js` (copied to
   `frontend/src/pmc-responsive.js`, imported in index.js): injects
   .pmc-menu-btn into .pmc-atop/.pmc-vtop, toggles html.pmc-nav-open
   drawer, stamps data-label from thead onto cells, MutationObserver
   re-applies after SPA re-renders.
4. Row click → detail panel now fully populated (ref, pill, KV,
   6-step timeline, stage-appropriate actions) via root._bids stash
   set by useAdminBiddingOpsLive.
5. Row/detail actions wired to real APIs (bidApi): send EMD link,
   flag to certifier, hold, reject, open bid; bulk EMD remind; CSV
   export of the bids table.
6. useAdminBiddingOpsLive now takes {enabled, tick} — tick bumps
   after any action to re-fetch.

Verified at 1440 (authed admin): 9 bids, search filters, row click
populates detail (PMC-BID-2026-00017, Escrow pill, 6-step timeline,
3 actions). At 1280 and 900: no horizontal scroll, menu button +
drawer work. eslint warning in AdminDashboard.jsx (exhaustive-deps)
is benign pre-existing.

### v49q — Full admin sidebar sweep + old-console redirect — 29 Sep 2026
User: "almost all the leftsidebar options were breaking." Root causes
found via a 21-page × 2-viewport sweep:
1. The legacy tab console at `/admin` (dark "PMC Admin" shell) still
   rendered OLD panels for every tab except bidding — users landing
   there saw the broken old UI. Fix: `AdminDashboard.jsx` now has an
   E_TAB_ROUTES map and render-time `<Navigate>` for all 21 tabs with
   E equivalents (analytics→dashboard, packages→work-packages,
   vintel→vendor-intel, l1→l1-award, etc.). Tabs without E pages
   (auctions, meetings, masters, help) stay on the old console.
2. Dead sidebar link: new Dashboard/BiddingOps sidebars linked
   `/admin/e/l1` but the route is `/admin/e/l1-award`. Fixed in both.
   Link audit across all E-pages: no dead links remain.
3. Hooks called four 404/405 endpoints: `/vendors/all`→`/vendors`,
   `/packages/all`→`/packages`, `/vendor-intel/pending-count`→
   `/vendor-ratings/admin/pending-count` (field `pending`→count),
   `/boqs`→`/boq/templates`. All in pmcELiveData.js.
Sweep result after fixes: all 21 `/admin/e/*` pages OK at 1440+900
(no h-scroll, content renders, h1 present), zero 404s on dashboard,
redirect map verified for 8 sample tabs. Dashboard KPIs now real
($31,600 EMD, 40 vendors, 48 work packages in sidebar).
v49q frontend bundle rebuilt (07:31 UTC) with all of this.

### v49q — Post-rollback: sidebar links + Tender Builder rescue — 29 Sep 2026
User rolled back to v49p via platform checkpoint, then reported "tender
builder entire section is broken, almost the whole site is".

Diagnosis:
1. Every E-page sidebar (21 pages) had href="#" dead links — 441 links
   fixed via label→route map script across admin-console-e/*.jsx.
2. AdminTenderBuilderE was a static display-only mock (read-only
   inputs, fake 36 drafts, dead buttons). Rewrote it to mount the fully
   functional legacy TenderBuilderPanel (drafts, DPR AI fill, sections,
   save/history/PDF/publish) inside the Option E shell.
3. Legacy panel's form rows (Tailwind md:grid-cols-[220px_1fr]) broke
   inside the narrower E shell — labels overlapped inputs (user
   screenshots). Fix: tender-builder-e.css stacks label above input
   ≤1480px + min-width guards. Verified: 52 rows, 0 true 2D overlaps at
   1440/1280/390, no h-scroll; mobile stacks cleanly.

Note: rollback restored code but my later edits (sidebar links, E_TAB_
ROUTES redirect in AdminDashboard.jsx, bidding-ops.css, pmc-responsive
.*) were re-applied/retained after rollback — all present and verified.
v49q bundle rebuilt again (08:27 UTC) with tender-builder fix.

### v49q — Notices / Corrigenda / BOQ rescued with legacy panels — 29 Sep 2026
User: "notices list opens but Open button + checkbox do nothing; same
for corrigenda view/edit; same for BOQ view/edit/delete + design
breaks (screenshots showed rows wrapping one-word-per-line)".

Root cause: all three E-pages were static mocks with dead href="#"
actions and hardcoded rows. Legacy panels (NoticesPanel,
CorrigendaPanel, BOQContractsPanel) were fully API-wired and working
in the old console.

Fix: created shared `admin-console-e/AdminEShell.jsx` (Option E
sidebar + topbar, real links, active-state, testids) and rewrote
AdminNoticesE / AdminCorrigendaE / AdminBoqContractsE to mount the
legacy panels inside it. AdminEShell main uses default pmc-amain
padding (28px 32px 96px).

Verified (authed admin, 1440px):
- Notices: real list (17+ rows), PREVIEW AS BIDDER navigates to
  /notices/<ref>, NEW NOTICE toggle, filters work.
- Corrigenda: NEW CORRIGENDUM opens full form (7 fields), notice
  picker populated, publish button live.
- BOQ: templates tab lists real templates with Import Excel + View;
  View expands item table; CONTRACTS tab switches and lists real
  contracts with milestone Mark-complete actions.
Bundle rebuilt (10:27 UTC).

### v49q — 5 more static shells rescued (Work packages / Catalog / Vendors / Registrations / Vendor intel) — 29 Sep 2026
User reported five more broken pages: Work packages Open dead;
Catalog edit dead; Vendors "invite vendor" links missing + KPIs
static + KYC review/status tabs dead; Vendor intel Manage/Open-KYC
dead.

Same root cause + fix pattern: rewrote AdminWorkPackagesE,
AdminCatalogE, AdminVendorsE, AdminRegistrationsE and
AdminVendorIntelE to mount the fully-wired legacy panels
(PackagesPanel, ProductCatalogPanel, VendorsPanel,
RegistrationsPanel, VendorIntelPanel) inside AdminEShell.

Verified live (admin, 1440px):
- Work packages: kanban view (48 packages, Backlog 26 / Scoping 13 /
  SBD 6 / Ready 3), View button on every card, Import CSV, New
  package.
- Catalog: Client 33 / Supplier 21 / Both 1 / Active 54 header,
  EDIT + DISABLE actions per row, filter by side/category.
- Vendors: Invite vendor + Bulk invite (CSV) + Replace registration
  template + Download current + Add & fill full form buttons all
  wired, status tabs (All/Pending verify/Active/Inactive), Activate
  now per row.
- Registrations: Submitted/Under review/Needs clarification/Approved/
  Rejected/Draft + Nudge stale drafts tabs, all clickable, review
  pane on the right.
- Vendor intel: real vendor list, Manage buttons per row, ratings
  and trust badges, flags column live.
Bundle rebuilt (10:36 UTC).

### v49q — Remaining 10 static shells cleared — 29 Sep 2026
Batch-fixed every remaining static E-page via the AdminEShell +
legacy-panel pattern: Engagements (EngagementsPanel), Escrow/EMD
(EscrowPanel), Billing (BillingTransactionsPanel), Evaluation
(EvaluationPanel), L1 comparison (L1ComparisonPanel), Awards
(AwardsPanel), DocuSign (DocuSignPanel), Permissions
(PermissionsPanel), Audit ledger (AuditPanel).

Events & alerts had NO legacy panel — rebuilt AdminEventsE as a real
React component: fetches admin notifications via notifyApi.list(),
renders real rows with level pills + Acknowledge (markRead) buttons,
alert-rule checkboxes persist to localStorage. Fixed two build errors
en route (bad useState initializer; notifyApi vs notificationApi
export name).

Verified (admin, 1440px): all 10 pages render real content, no
h-scroll, working buttons; events page shows 50 real notifications,
rule toggle persists. Zero JS errors on all pages except pre-existing
benign button-nesting warnings + tenant-probe 404.
Bundle rebuilt (10:51 UTC). ALL admin E-pages are now functional —
no static shells remain.

### v49q — Admin avatar menu — 29 Sep 2026
User: dashboard avatar dead — no change password, no profile photo
change, no sign out. Root cause: every E top bar rendered a static
<span class="pmc-avatar">A</span> with no menu.

Fix: new shared `AdminAvatarMenu.jsx` component — dropdown with real
email (adminApi.me), Change photo (adminApi.uploadAvatar /
removeAvatar, 400KB cap), Change password (inline form →
adminApi.changePassword, min 8 chars), Sign out (adminApi.logout →
/admin/login). Click-outside and Esc close. Swapped into the 3
places the dead avatar appeared: AdminEShell (shared by 15 pages),
AdminDashboardE, AdminBiddingOpsE.

Verified live: menu opens with adminsupport@pmcmanagers.com, all 3
actions present, password form expands, sign-out redirects to login.
Bundle rebuilt (10:56 UTC).

### v49q — Dashboard drill-downs, avatar overflow, downloads — 29 Sep 2026
User: (a) dashboard pipeline/attention numbers all opened the full
unfiltered notices list; (b) avatar menu email overflowed; (c) notice
document links opened a new tab instead of downloading.

Fixes:
1. AdminDashboardE: stage cards now link to filtered destinations —
   I Draft→/admin/e/notices?status=draft, II–IV→?status=published,
   V–VII (bid stages)→/admin/e/bidding; attention strip closing→
   ?status=closing, drafts→?status=draft. Stage counts V–VII now real
   (computed from bid statuses: admin_flagged/certifier_cleared →
   Technical eval; legal/accounting_cleared → Commercial eval;
   awarded/closed → Awarded) instead of the fabricated closed/2 split.
2. NoticesPanel: reads ?status= URL param into filterStatus on mount;
   added "Closing this week" filter (published + deadline within 7d).
   Verified: clicking Draft shows 7 draft rows with filter pre-set.
3. AdminAvatarMenu: email clamped (maxWidth 150 + ellipsis). Verified:
   menuRight 1408 < viewport 1440, no overflow.
4. Downloads: backend /api/v1/uploads/files/{key} gained ?download=1
   (Content-Disposition: attachment; default stays inline). Notices
   primary-document link now uses relative URL + ?download=1 +
   download attr (drops cross-origin BACKEND_URL prefix that broke
   the download attribute).

### v49q — Mobile hamburger/drawer + real downloads — 29 Sep 2026
User: on mobile the hamburger is not visible and downloads open pages
instead of downloading files.

Root causes:
1. Hamburger: pmc-responsive.js injects .pmc-menu-btn into .pmc-atop,
   but mobile-fix.css hides .pmc-atop at ≤767px AND index.css hides
   .pmc-adm .pmc-side at ≤768px (higher specificity), so the button
   was inside a hidden parent and the drawer sidebar was display:none.
   Fix in pmc-responsive.css (loaded last): un-hide .pmc-atop and
   .pmc-adm .pmc-side inside the ≤1100px block with matching
   specificity ([data-ui="e"] .pmc-adm aside.pmc-side).
   Verified at 390px: hamburger visible, drawer slides in with all 21
   nav links, tapping Notices navigates to /admin/e/notices, scrim
   closes it.
2. Downloads: PmcLinkPatcher opened data-doc-url links via
   window.open → new tab with inline PDF. Now appends ?download=1 and
   clicks a temporary <a download> anchor — real file download,
   mobile-Safari safe (window.open is popup-blocked there).

### v49q — Open-bid gate + Help Centre link — 29 Sep 2026
User: (a) clicking an open bid should route unauthenticated users to
register / sign-in; (b) "Open the full Help Centre" button dead.

Fixes:
1. NoticeDetailE "Start bid" + "Download pack" — was href="#". Now
   href="/register" so anonymous visitors land on the registration page
   which already has a "Sign in" link in the top bar. Post-registration
   the vendor flow resumes from /vendor/e/find.
2. "Open the full Help Centre" — 30 files had href="#". Batch sed
   updated every instance to href="/help" (real HelpCentreE route).
   Verified: 0 remaining href="#" ... Open the full Help Centre links.

Bundle rebuilt.
User: still-broken file downloads inside bid detail + awards; resend
button "doesn't fire the email"; dashboard IV=11 Bidding vs "10 CLOSE
THIS WEEK" subtitle is inconsistent; ⋯ button in bid rows had no
distinct purpose.

Fixes:
1. AdminBidDetailPage: swapped target=_blank "Open" for a real
   Download button (?download=1 + download attr). Preview link kept
   as secondary. Same fix in AdminBidDetailModal.
2. AwardsPanel PO/Contract PDF link now ?download=1 + download attr
   (was target=_blank on a cross-origin URL that inline-rendered).
3. DocuSignPanel resend: pre-flight guard toasts a clear error when
   envelope is completed/voided/rejected (user was clicking Resend on
   COMPLETED rows with no feedback). Info toast added while waiting.
4. Dashboard stage IV now: count = closing-this-week (was
   "bidding=30d"), href = /admin/e/notices?status=closing so click
   destination matches the "10 CLOSE THIS WEEK" subtitle exactly.
   Verified: attention 05 = pipeline IV 05 = notices filtered 5 rows.
5. Bidding Ops ⋯ button: `data-bo-action="detail"` — opens the
   right-side clearance-path panel where Hold / Reject / History
   live. No longer redundant with Review (which goes to full bid
   page).

### v49r — Universal file download/view link fix — 29 Sep 2026
User: "all links still do not download the files or view the files" on
production after v49q backend deploy.

Root cause: `PmcLinkPatcher.jsx` global click delegation pushed EVERY
anchor with a real href starting with "/" through the React SPA router
(`navigate(href)`). Backend file URLs (`/api/v1/uploads/files/...`)
match no SPA route → dead/blank page. This broke attachment
Download/View anchors in admin panels (AdminBidDetailPage,
AdminBidDetailModal, AwardsPanel) and any page with real file hrefs
inside a `data-pmc-e-page` root.

Fixes (PmcLinkPatcher.jsx only):
1. `handleDownload` — real `/api/...` hrefs now force the attachment
   download in place (`?download=1` + temp `<a download>`) instead of
   falling through to the router.
2. Generic href handler — `/api/...` and `/downloads/...` hrefs bypass
   the SPA router entirely; browser opens them natively (inline view
   where `target="_blank"`, else Content-Disposition decides).

Verified on preview: notice PMC-NOT-2026-0020 Documents tab → Download
fires real download (fake_tender.pdf). Production backend already
confirmed serving attachment with ?download=1 (curl). Production EB
"100% 5xx" warning after v49q deploy was transient during container
swap — api.pmcmanagers.com fully healthy (all endpoints 200).

Bundle: `pmc-frontend-v49r-prod-build.zip` (main.7fd85d7d.js,
REACT_APP_BACKEND_URL="" same-origin). Backend unchanged (v49q).
Release notes: `frontend/public/downloads/DOWNLOAD_v49r.md`.

**Pending user action**: deploy v49r frontend zip to S3 + CloudFront
invalidate /*, then re-test download/view links on production.
**Known data issue**: notice-detail template shows 5 static doc rows but
only rows backed by a real uploaded attachment work (others correctly
show the sign-in/tender-desk gate).

### v49s — Sign-in ⇄ Register cross-links — 29 Sep 2026
User: home-page bid click lands on sign-in with no obvious register
option; register page has no sign-in option for existing suppliers.

Fixes:
1. `/login` (SignInE.jsx): prominent full-width outlined button
   "Register as a supplier — free, ~15 minutes" under Continue, with a
   "New supplier?" divider. Testid: signin-register-btn.
2. `/register` (RegistrationStart.jsx): form footer note "Already
   registered? Sign in to your supplier account" → /login.
   Testid: reg-start-signin-link.
3. Service-worker cache bumped to pmc-shell-v49s-rev1.

Verified on preview: button on /login; register link navigates to /login.
Bundle: `pmc-frontend-v49s-prod-build.zip` (main.c0d42a52.js) —
SUPERSEDES v49r (includes the v49r download-link fix). Backend v49q.
Release notes: `frontend/public/downloads/DOWNLOAD_v49s.md`.

**Pending user action**: deploy v49s frontend to S3 + CloudFront
invalidate /*; skip v49r entirely.

### v49t — Admin dashboard counts match linked lists — 29 Sep 2026
User: 0 drafts (actual 29); published 20 (actual 29); technical eval 1
(list 13); awarded 3 (list 13); bids waiting 6 (list >13).

Root cause: `useAdminDashboardLive` in pmcELiveData.js used
`publicApi.listNotices({})` which server-filters `is_published:True`
(drafts never returned) and defaults to limit=30 (published capped).
Stage V/VI/VII filters were too narrow (2 of 8 evaluation statuses).

Fixes (pmcELiveData.js only):
1. Switch notices source to `/api/v1/notices/admin/all?limit=500` (falls
   back to public list on 401).
2. Broaden stage filters:
   - Tech eval = emd_paid, escrow_accepted, admin_flagged, certifier_cleared
   - Comm eval = legal_cleared, accounting_cleared
   - Awarded  = awarded, closed
3. Attention "bids awaiting EMD" now includes blank status + submitted.
4. KPI "Active contracts" figure now = awarded bid count (was a
   form_of_contract heuristic that had no relationship to the list).
5. SW cache bumped to pmc-shell-v49t-rev1.

Bundle: `pmc-frontend-v49t-prod-build.zip` — supersedes v49r + v49s.
Backend unchanged (v49q). Release notes: DOWNLOAD_v49t.md.

**Pending user action**: deploy v49t frontend, invalidate `/*`,
re-check dashboard counts against list pages.

### v49u — Notifications fixed (vendor alerts + bells) — 29 Sep 2026
User: "notifications not working."

Root causes (frontend only):
1. `useVendorAlertsLive` hit `/api/v1/notifications` (admin-only
   `current_admin`) → vendors got 401 → page kept 5 static mock rows.
2. `.pmc-bell` on vendor/admin pages had no click handler;
   `.pmc-bell__n` badge hardcoded 0.

Fixes (pmcELiveData.js + PmcLinkPatcher.jsx):
1. Vendor alerts now use `/api/v1/notifications/vendor/mine`, render
   real rows (subject, body preview, relTime, unread highlight, View →
   /vendor/mybids), and patch the static H1 ("N alerts · N need action")
   + "All N" / "Needs action N" tab counts. Rows: vendor-alert-row.
2. Bell click → /vendor/alerts (vendor) or /admin/e/events (admin).
3. Bell unread badge refreshed on every route change from the correct
   realm endpoint; hidden at 0.
4. SW cache bumped to pmc-shell-v49u-rev1.

Verified on preview: vendor login → 50 real alert rows, badge 10;
admin dashboard bell badge 50, click → Events & alerts page.
Bundle: `pmc-frontend-v49u-prod-build.zip` (includes v49r + v49s +
v49t). Backend unchanged (v49q). Release notes: DOWNLOAD_v49u.md.

**Pending user action**: deploy v49u frontend to S3 + CloudFront
invalidate /* — this single zip supersedes v49r/v49s/v49t.

### v49v — Safari DocuSign popup fix — 29 Sep 2026
User: in Safari, "Review & sign" / Preview never opens the DocuSign
page; suspected popup blocker.

Root cause (frontend): every signing flow called window.open() AFTER an
await on the DocuSign API. Safari only allows popups synchronously
inside the click gesture, so the open was silently blocked.

Fix pattern (open blank tab in the click → steer to URL after await →
same-tab fallback if even sync open blocked → close placeholder tab on
error paths) applied to:
1. PmcLinkPatcher.jsx — handleReviewSign (vendor signatures Review &
   sign / Preview / Continue) via new _openSteeredTab/_steerTab/
   _closeTab helpers; handleSigDoc preview mode too.
2. VendorSignatures.jsx — legacy award signing popup.
3. DocuSignPanel.jsx — admin Sign + Resend + consent-URL redirect.
4. AwardsPanel.jsx — award signing + consent-URL redirect.
5. SW cache bumped to pmc-shell-v49v-rev1.

Verified on preview (Chromium): popup opens synchronously on click
(before API resolves) — the exact behaviour Safari requires.
Bundle: `pmc-frontend-v49v-prod-build.zip` — supersedes v49r–v49u.
Backend unchanged (v49q). Release notes: DOWNLOAD_v49v.md.

**Pending user action**: deploy v49v frontend, invalidate /*, then
verify DocuSign signing in Safari on production (also covers P1
DocuSign live-signing validation once a fresh envelope is created).

### v49w — 4 bugs fixed (DocuSign resend, sticky sidebar, sign-out dest, first-load Help) — 29 Sep 2026
User reports:
1. DocuSign resend doesn't email the signer (list-view + detail-view).
2. Admin left sidebar scrolls away with the page.
3. Sign-out from admin or supplier lands anywhere EXCEPT `/login`.
4. Help FAB / "Open the full Help Centre" dead on the very first page
   load; works only after navigating away and back.

Root causes & fixes:
1. docusign.py resend_envelope called `update_recipients` with
   `s.email = signer_email` (same value → no diff → DocuSign skipped
   the reminder). Now uses envelope-level
   `envelopes.update(..., resend_envelope="true")`; fallback refreshes
   signer name so the diff is non-empty. Returns `resent_to`.
2. pmc-responsive.css: `[data-ui="e"] .pmc-adm > aside.pmc-side` now
   `position: sticky; top: 0; height: 100vh; overflow-y: auto;`
   (desktop ≥1101 px — mobile drawer untouched).
3. AdminAvatarMenu.onSignOut: `navigate("/login", { replace: true })`
   (was `/admin/login`). Vendor side already went to `/login`.
4. PmcLinkPatcher's `data-help-open` branch now dispatches
   `pmc:open-help` custom event; PmcHelpDrawer listens for it and sets
   React state `open=true` directly — no more racing with multiple
   static `.pmc-helpfab` buttons on the page.
5. SW cache bumped to pmc-shell-v49w-rev1.

Bundles: frontend `pmc-frontend-v49w-prod-build.zip` (supersedes
v49r–v49v); **backend `pmc-backend-v49w.zip` REQUIRED for the
DocuSign resend fix** (first backend update since v49q).
Release notes: DOWNLOAD_v49w.md.

**Pending user action**: deploy BOTH zips (frontend to S3+CloudFront;
backend to EB), then verify resend actually mails the signer.

### v49x — Sidebar ACTUALLY fixed + Help Centre nav + DocuSign emails — 01 Oct 2026
User deployed v49w and reported (with screen recordings): sidebar still
scrolls, help still broken, DocuSign still not emailing. Production
verification (fresh browser on www.pmcmanagers.com) confirmed all three.

Root causes & fixes:
1. Sidebar: global `html, body { overflow-x: hidden }` in
   pmc-responsive.css (all widths) creates a body scroll container →
   silently breaks position:sticky (v49w fix never had a chance).
   Changed to `overflow-x: clip` AND hardened sidebar to
   `position: fixed; width: 260px; height: 100vh; overflow-y: auto`
   (desktop ≥1101px; grid's explicit 260px track keeps main column).
2. Help: the `/help|faqs/` label regex swallowed "Open the full Help
   Centre" anchors (dispatched drawer-open instead of navigating).
   Anchors with real /help href now navigate + close drawer first.
3. DocuSign: resend API verified working on prod (v49w backend,
   `resent_to` returned) BUT real envelopes are delivery=embedded →
   client_user_id suppresses DocuSign emails BY DESIGN. Added
   `_email_signer()` (Resend, portal link to /vendor/signatures) fired
   on: award-envelope create (embedded), bid-ack create, and embedded
   resend (`emailed` in response).
4. SW cache bumped to pmc-shell-v49x-rev1.

Bundles: `pmc-frontend-v49x-prod-build.zip` + `pmc-backend-v49x.zip`
(both required). Release notes: DOWNLOAD_v49x.md.

**Pending user action**: deploy BOTH v49x zips; verify sidebar fixed,
help-centre navigation, and DocuSign reminder emails (incl. spam).
**Then**: user-flagged cyber-security + tender-maker findings.

### v49y — DocuSign completion confirmation + status sync — 01 Oct 2026
User: signer completes (email + embedded modes) but admin panel never
shows completion. Also asked how the signing flow works.

Answer documented: single-signer flow (vendor signs; no PMC countersign
in DocuSign today). Two-party countersign flow offered as next feature.

Root cause: only the DocuSign Connect webhook updated our DB, and
Connect was never configured in the user's DocuSign account. Admin list
read stale Mongo rows → "sent" forever.

Fixes (docusign.py):
1. `_sync_recent_statuses()` — one `list_status_changes` call (30d),
   applied on admin list (`/docusign/envelopes`) and vendor list
   (`/docusign/mine`). Best-effort; lists never break if DocuSign down.
2. `_on_envelope_completed()` — admin notify (in-app + email), vendor
   confirmation email with portal link, audit entry
   `docusign.envelope_completed`, bid stamped `<kind>_signed_at`.
3. Webhook + get_envelope now route through `_apply_live_status()`.

Backend verified: syntax OK, boots clean, health 200 (sync degrades
gracefully on preview where DocuSign creds are invalid).
Bundle: `pmc-backend-v49y.zip`. Frontend stays v49x.
Release notes: DOWNLOAD_v49y.md.

**Pending user action**: deploy frontend v49x + backend v49y (user has
NOT deployed anything since v49w was built — v49w/x skipped, these two
zips contain everything). Then: cyber-security + tender-maker findings.

### v49z — Layout collapse + Help nav fix — 01 Oct 2026
User deployed v49w; sidebar + main overlapped (screenshot shared).
Also: "Back to tender board" dead, "Sign in" button nonsensical for
logged-in users, "Open the full Help Centre" opens new tab.

Root causes & fixes:
1. Prior sticky (v49w) + fixed (v49x) sidebar approaches both failed
   due to pre-existing CSS. v49z switches admin shell to two-pane
   scroll: `.pmc-adm { height:100vh; overflow:hidden }` + both
   sidebar and main `.pmc-amain` get `height:100vh; overflow-y:auto`.
   Window itself never scrolls on admin pages → sidebar literally
   cannot move. Verified on preview (sidebarStays:true, 500px scroll).
2. HelpCentreE.jsx + HelpArticleE.jsx: `href="#"` on Back-to-board +
   stray Sign-in button. Replaced with real `/admin/e/dashboard` href
   (testid: help-back-to-board) and removed Sign-in. Brand hrefs
   point to `/` and `/help` respectively.
3. "Open the full Help Centre" already navigates same-tab via SPA
   (v49x change retained).
4. SW cache bumped to pmc-shell-v49z-rev1.

Bundle: `pmc-frontend-v49z-prod-build.zip` (supersedes v49r→v49x).
Backend v49y unchanged. Release notes: DOWNLOAD_v49z.md.

**Pending user action**: deploy v49z frontend + v49y backend.

### v50a — Admin content scroll fix (v49z regression) — 01 Oct 2026
User: after v49z, sidebar fixed but content section cannot scroll —
everything below the fold unreachable (screenshot: DocuSign page).

Root cause: v49z scroll rule targeted `.pmc-adm > main.pmc-amain`, but
the real DOM wraps header+main in an UNNAMED div (`.pmc-adm > div >
header + main`) in AdminEShell, AdminDashboardE and AdminBiddingOpsE.
Rule matched nothing → `.pmc-adm{overflow:hidden;height:100vh}`
clipped the page with no scrollable element.

Fix (pmc-responsive.css, desktop ≥1101px): scroll container is now
`.pmc-adm > div:not(.pmc-drawer):not(.pmc-drawer-scrim)` (and
`.pmc-adm > main.pmc-amain` as fallback). Sticky `.pmc-atop` now sticks
inside the wrapper for free.
Verified on preview: /admin/e/docusign wrapper scrolls to 1500px,
sidebar top unchanged, window.scrollY=0; dashboard identical.

SW cache → pmc-shell-v50a-rev1.
Bundle: `pmc-frontend-v50a-prod-build.zip` (supersedes v49r→v49z).
Backend unchanged: `pmc-backend-v49y.zip`. Release notes: DOWNLOAD_v50a.md.

**Pending user action**: deploy v50a frontend + v49y backend.

### v50b — DPR "Not authenticated" diagnosis + stale-session UX — 01 Oct 2026
User: Tender builder → AI from DPR → 20MB PDF → "Not authenticated"
on the file row, "1 DPR(s) failed" toast.

Investigation on production:
- POST /dpr/analyze-async verified working with cookies: tiny AND 27MB
  payloads → 200 job queued. Endpoint, nginx 200MB cap, CloudFront,
  CSRF all healthy.
- 401 "Not authenticated" = browser sent no access_token cookie:
  session lapsed (24h cookie) or stale SW shell. Panel GETs fail
  silently so the page still "looked" logged in.

Fixes (api.js):
1. Response interceptor: 401 Not authenticated / Token expired →
   single redirect to /login?expired=1&next=<path> (skips /login,
   /register, /).
2. DPR analyze endpoints (sync + async kick) get timeout: 300000
   (5 min) — the 20s default was too short for multi-MB base64
   uploads.
3. SW cache → pmc-shell-v50b-rev1.

Bundle: `pmc-frontend-v50b-prod-build.zip` (supersedes v50a).
Backend unchanged: `pmc-backend-v49y.zip`. Release notes: DOWNLOAD_v50b.md.

**Open thread**: if a future failure shows a BACKEND error (not 401)
on the job row, that's the AI-extraction stage — needs job error text.

### v50c — DPR section headings carried through (editable) — 01 Oct 2026
User: order sections as read from the DPR, use the real headings as
tender maker section titles, with a small checkbox near each heading
to toggle "keep as read / edit before creating".

Finding: backend already returns `sections_blueprint` with ordered
real titles; the "new master" code path in DprGenerateModal.jsx was
discarding them and generating "Dpr 1", "Dpr 2"… from the codes.

Fix (DprGenerateModal.jsx):
1. New-master section titles now sourced from
   `preview.sections_blueprint` (ordered).
2. Per-preview panel with checkbox "Use the DPR's own section headings
   (N found, in order). Uncheck to edit before creating." — edit mode
   renders an inline input per heading; edited titles flow into the
   new master on create.
3. Scoped to new-master only; existing-master titles unchanged.
Testids: dpr-use-dpr-headings-<idx>, dpr-section-title-<idx>-<i>.

SW cache → pmc-shell-v50c-rev1.
Bundle: `pmc-frontend-v50c-prod-build.zip`. Backend unchanged (v49y).
Release notes: DOWNLOAD_v50c.md.

### v50d — DPR headings panel visible in both flows — 01 Oct 2026
User: v50c headings panel not visible. Root cause: panel required
`!p.masterId && sections_blueprint`, but picking a master in step 2
switches the backend to the template-aware path (no blueprint) and
sets p.masterId — panel had nothing to render.

Fix (DprGenerateModal.jsx): panel now renders whenever sections exist —
blueprint (new-master) or master's sections (existing master) — with
adaptive copy; overrides (`p.sectionTitles`) apply in BOTH branches of
cloneAndApply. Master template itself untouched (per-tender override).
SW cache → pmc-shell-v50d-rev1.
Bundle: `pmc-frontend-v50d-prod-build.zip`. Backend unchanged (v49y).
Release notes: DOWNLOAD_v50d.md.

### v50e — DPR flow: show all masters + always-visible "new master" — 01 Oct 2026
User: when a country has a master, that master might be a different
industry/format — show ALL masters in the dropdown and still allow
building brand-new.

Finding: v49x master dropdown filtered to country-only; borrow/new
options only appeared when ZERO country-masters existed, which
trapped admins into picking a wrong-industry master.

Fix (DprGenerateModal.jsx):
1. Dropdown now uses <optgroup> — "Masters saved for <COUNTRY> (N)"
   above "Other saved masters (N)". Option text always shows
   [COUNTRY · industry] name.
2. "Build a brand-new master from this DPR" checkbox is a permanent
   sibling of the dropdown (not conditional).
3. Compact amber note only when zero same-country masters (first-time
   guidance).
4. Editable section-headings panel (v50d) unchanged.

SW cache → pmc-shell-v50e-rev1.
Bundle: `pmc-frontend-v50e-prod-build.zip`. Backend unchanged (v49y).
Release notes: DOWNLOAD_v50e.md.

**Also started in this session**: security_audit_agent returned FAIL
(SEC-001 CRITICAL hard-coded staff/admin seed passwords in
config.py:47-62 + server.py:164-211; SEC-002 HIGH unauthenticated
upload+retrieval in uploads.py:27-82 with same-origin XSS; SEC-003
MEDIUM DocuSign webhook accepts unsigned callbacks when HMAC secret
unset). Fixes NOT yet applied — awaiting user prioritisation after
v50e deploy. See the audit report in-chat for full technical details.

**Prod EMD dry-run**: 14 bids total (6 submitted, 1 emd_pending,
3 emd_paid, 3 awarded, 1 certifier_cleared). Escrow summary: 5 paid,
1 pending; 102,576 USD-equivalent across INR/USD/KZT. No obvious
orphan EMD records; detailed cross-check pending v50e deploy.

### Avatar sign-out verification — 01 Oct 2026
User reported "signout from avatar not happening". Verified on BOTH
preview and production (v50e, main.bd6f0867.js confirmed live): avatar
menu opens, Sign out → /login with "Signed out" toast, and
/api/v1/admin/auth/me returns 401 after logout (session truly dead).
No JS errors. Conclusion: code is correct; user's browser was likely
running the stale service-worker shell. Asked user for specifics
(which avatar/page, exact behavior, browser) if a hard refresh
doesn't resolve it.

### Incident — admin login failure (02 Oct 2026)
User: "suddenly my admin username and password are not working".
Investigation on production:
- adminsupport@pmcmanagers.com / Admin@12345 → 401 Invalid email or
  password (seed default Admin@123 also 401) — password_hash changed.
- kannan@emeraldcorporates.com / Owner@123 → WORKS (full admin).
- committee@pmcmanagers.com / Bid@1234 → WORKS (roles include admin) —
  this is a LIVE demonstration of SEC-001 (hard-coded staff seeds).
- DB is intact (not wiped); only the adminsupport password_hash differs.
  Likely cause: password changed via the avatar "Change password"
  feature during yesterday's testing, or changed by another session.
- Recovery path: /login → Forgot password (portal=admin) →
  POST /api/v1/password-reset/request emails a reset link via Resend.

### Resolution — admin login incident (02 Oct 2026)
- Root cause: adminsupport password_hash changed (most likely via the
  avatar "Change password" feature during testing). Not a DB wipe —
  all other accounts intact.
- Immediate access restored via owner account
  (kannan@emeraldcorporates.com / Owner@123) — verified working.
- Recovery: POST /api/v1/auth/password-reset/request {email,
  portal:"admin"} → 200, reset email sent via Resend.
- Incident doubled as live proof of SEC-001: committee@pmcmanagers.com
  / Bid@1234 hard-coded staff seed grants admin access in production.
  Fix queued for today's security batch (requires operator-set
  ADMIN_PASSWORD/OWNER_PASSWORD env vars in EB + staff seed rotation).
