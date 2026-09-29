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
