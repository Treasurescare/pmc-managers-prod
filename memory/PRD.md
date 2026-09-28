# PMC Managers Limited v2 — Product Requirements

## Vision
Multi-role procurement & tender platform for PMC Managers Limited: engagements, tenders, vendor onboarding/KYC, bidding, two-cover evaluation, awards, BOQ, contracts, escrow, billing, and DocuSign — with admin, buyer, vendor, staff (escrow, legal, certifier, accounting, committee), and public portals.

## Non-negotiable constraints
- **No "Emergent" mentions** anywhere in UI, docs, manuals, or outgoing email sender addresses.
- **Same-origin frontend**: production frontend build must not bake in the preview URL. All API calls go to `/api/*` on the same domain.
- Deployment stack: **AWS Elastic Beanstalk** (backend, Docker) + **S3 + CloudFront** (frontend). Frontend zip must exclude `public/downloads/` to keep it small.
- Backend zip must contain `Dockerfile`, `Dockerrun.aws.json`, `.platform/nginx/conf.d/proxy.conf` (200 MB body-size), and the full `backend/` tree.

## Stack
- Frontend: React 19, CRACO, Tailwind, Shadcn/UI, react-router 7.
- Backend: FastAPI, MongoDB (Motor), JWT + httpOnly cookies, Resend (direct API, no relay).
- 3rd-party: Stripe (test key), DocuSign (JWT sandbox), Zoom (S2S OAuth), Resend, Emergent LLM key (for AI drafting).

## Delivered & Live on Production
### 1 · Vendor login end-to-end
- `POST /api/v1/vendor/auth/login` returns `must_change_password` flag.
- `/vendor/login`, `/login` (unified vendor tile), and mobile `/m/login` all honour the flag and route to `/vendor/change-password` on first sign-in.
- Admin activation (`POST /api/v1/vendors/{ref}/activate`) supports `mode=set_password` and `mode=resend_link`.
- All 5 portals authenticate: master admin / owner backfilled with executive roles (`admin`, `reviewer`, `management`, `partner`, `agent`, `committee_member`, `support`, `auditor`) on cold-start; frontend cascades portal-role → admin fallback.

### 2 · Branded Email Sending (`mail.pmcmanagers.com`) — VERIFIED LIVE
- Resend sender domain `mail.pmcmanagers.com` verified in Resend (DKIM TXT + `send.mail`/`rsend.mail` CNAMEs in Route 53).
- EB environment properties configured with `RESEND_API_KEY` and `EMAIL_FROM_ADDRESS=admin@mail.pmcmanagers.com`.
- Real-flow test verified live: vendor activation of `PMC-SUP-000080` (`ranjana@gmail.com`) sent via Resend with DKIM signature `d=mail.pmcmanagers.com`.

### 3 · Web Push Notifications (VAPID) — LIVE
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` (PEM single-line), and `VAPID_CLAIM_EMAIL` active on EB.
- `GET /api/v1/push/config` returns `{"public_key":"BFaNQAW9...","enabled":true}` on production.
- Auto-registers vendor subscriptions for tender-publish and bid-deadline alerts.

### 4 · KYC admin overrides
- `POST /api/v1/kyc/manual` (admin, legal_counsel): verified / pending / rejected + audit log.
- VendorsPanel → KYC block on selected vendor.

### 5 · Universal search & filters across admin console
- Registrations, Vendor Intel, Live Auctions, Engagements, Billing, Awards, DocuSign, Masters (staff/companies/tenants/hierarchy), Corrigenda, Work Packages, BOQ & Contracts, Catalog.

### 6 · Dashboard drill-through & Help UX
- Every KPI tile + funnel stage is clickable → routes to the owning tab.
- Sticky search on Help panel + context-aware floating Help pill in top bar.

### 8 · Option E v2 — complete 55-template design overhaul (v49b)
- Full new design system layered behind `?ui=e` feature flag; legacy Navy remains the default.
- **Public (14)**: `/`, `/tenders/live`, `/tenders/completed`, `/notices/:ref`, `/about`, `/vision`, `/suppliers`, `/buyers`, `/contact`, `/privacy`, `/terms`, `/trust`, `/help`, `/help/:slug`, `/register`, `/login`.
- **Vendor portal (10)**: `/vendor` (Home), `/vendor/tenders`, `/vendor/mybids`, `/vendor/workspace/:bidId`, `/vendor/emd`, `/vendor/signatures`, `/vendor/alerts`, `/vendor/reviews`, `/vendor/company`, `/vendor/account`.
- **Admin console (24)**: `/admin/e/dashboard`, `/programme` (executive), `/audit`, `/notices`, `/tender-builder`, `/corrigenda`, `/work-packages`, `/catalog`, `/boq`, `/vendors`, `/registrations`, `/engagements`, `/vendor-intel`, `/vendor-kyc`, `/bidding`, `/escrow`, `/billing`, `/evaluations`, `/evaluation`, `/l1-award`, `/awards`, `/docusign`, `/permissions`, `/events`.
- **Design references (4)**: `/design/dialogs`, `/design/states`, `/design/emails`, `/design/printables`.
- **Mobile shells (2)**: `/m/e/supplier`, `/m/e/public`.
- Global `?` help drawer + floating help FAB with FAQ search; SVG sprite of 28 icons.
- All pages currently render template content; backend data wiring is the next phase.

### 7 · Frontend Hardening (v46x)
- 20-second axios timeout in `src/lib/api.js` prevents silent UI hangs.
- Service worker `pmc-shell-v46x` evicts stale caches on activate.

## Test credentials
See `/app/memory/test_credentials.md`.

## Prioritized Backlog
### P1 — Near term
- Template polish: style outgoing vendor activation & bid emails with sovereign navy + gold branding.
- Deploy v46x frontend build (`pmc-frontend-v46x-prod-build.zip`) during next routine maintenance window.

### P2 — Future Integrations & Hardening
- Automated Playwright end-to-end regression test suite.
- LSEG / World-Check KYC provider integration.
- Alternative payment rails (PayPal, Kaspi).
- Zoom automated bid-opening session scheduler.

## Deployment ledger
- v49c (Feb 2026) — **Live vendor test-drive + real EMD KPI + rebuilt bundles**. Vendor login as `manualvendor@pmcmanagers.com` now drives real KPIs on `/vendor?ui=e`: greeting "Good morning, Manual Preview Vendor Pvt Ltd", Active bids 5, Closing this week 0, Matched to KYC 2 of 14 open notices, KYC status PENDING, foot "3 need you · 0 awarded". Fixed api.js by wiring `vendorApi.myBids()` → existing `bidApi.mine()` at `/api/v1/bids/mine`. Added new `GET /api/v1/meta/public/escrow-summary` endpoint returning per-currency EMD totals + USD-equivalent estimate + paid/pending bid counts; admin dashboard EMD tile now shows real **$31,600 with "3 pending · 4 paid"**. Rebuilt production bundles: `pmc-frontend-v49c-prod-build.zip` (2.6 MB, same-origin) + `pmc-backend-v49c.zip` (333 KB) + `DOWNLOAD_v49c.md`.
- v49c (Feb 2026) — **Live-data completion for all 5 core Option E screens**. Rewrote `/app/frontend/src/lib/pmcELiveData.js` with 4 hooks: `usePublicLiveData`, `useNoticeDetailLive`, `useVendorLiveData`, `useAdminDashboardLive`. Extended `GET /api/v1/meta/public/stats` to include `ledger_events` (auto-detects the audit collection). Verified live end-to-end: (1) Homepage chip/stats/live-board/grid → 14 open, 17/41/48/911 real stats; (2) Tenders list → real rows `PMC-NOT-2026-0012..0016` with real titles/dates/hrefs, sidebar counts 14 open · 5 closing · 3 closed, notice-type counts 14/0/0; (3) Notice detail `/notices/:ref` → fetches per-ref, renders real title/crumb/facts (budget, delivery, category); (4) Admin dashboard → pipeline 0/14/0/5/0/1/2, KPIs 14/5/41, sidebar counts 17/0/41/5; (5) Vendor home → template renders with fallback data (real data wires when vendor auth cookie is present).
- v49b (Feb 2026) — **Real-data wiring + email templates + production bundles**. Added `/app/frontend/src/lib/pmcELiveData.js` — a runtime patching layer that fetches from `publicApi.listNotices()` + `vendorApi.me()/myBids()` and surgically updates known DOM nodes (hero chip, stats bar, live-board, tender grid, tenders-list rows, vendor greeting & KPIs) inside the static Option E templates. Verified live: homepage `?ui=e` shows real count (14 tenders), real refs (PMC-NOT-2026-0012 etc.) and real `/notices/...` links. Added `/app/backend/emails_option_e.py` — Option-E branded email wrapper + 6 typed builders (new tender, corrigendum, deadline, EMD received, award issued, result published) which plug into existing Resend integration. Built production bundles via `/app/scripts/build_v49b.sh`: `pmc-frontend-v49b-prod-build.zip` (2.6 MB, same-origin), `pmc-backend-v49b.zip` (333 KB), release notes at `DOWNLOAD_v49b.md`.
- v49b (Feb 2026) — **Option E v2 expanded to the COMPLETE 55-template set**. Re-extracted consolidated design system from all 55 user templates into `pmc-theme-e.css` (259KB, block-level dedup, scoped under `[data-ui="e"]`). Converter upgraded to `/app/scripts/convert_full_v49b.py`. All 55 screens now have routes: 14 public (adds `/suppliers`, `/buyers`, `/contact`, `/privacy`, `/terms`), 10 vendor (adds `/vendor/tenders`, `/vendor/alerts`, `/vendor/reviews`), 24 admin (adds `/admin/e/programme` executive dashboard, `/corrigenda`, `/work-packages`, `/catalog`, `/vendors`, `/registrations`, `/engagements`, `/billing`, `/evaluations` list, `/awards`, `/events`), 4 design-reference showcases (`/design/dialogs`, `/design/states`, `/design/emails`, `/design/printables`), 2 mobile phone-frame shells (`/m/e/supplier`, `/m/e/public`). Regression: Homepage, Admin Dashboard, Vendor Home, Programme, Mobile, Dialogs, For-Suppliers all pixel-perfect; legacy `?ui=default` verified unchanged.
- v49a (Feb 2026) — **Option E v2: 29-template design overhaul wired**. Extracted the shared `pmc-*` design system from 29 user-provided HTML templates into a single scoped stylesheet (`/app/frontend/src/pmc-theme-e.css`, 181KB scoped under `[data-ui="e"]`). Bulk-converted all 29 templates into React JSX components via `/app/scripts/convert_html_to_jsx.py`: 10 public pages (`notice-board-e/*`), 7 vendor pages (`vendor-portal-e/*`), 12 admin pages (`admin-console-e/*`), + Help Centre + Help Article + SignIn + Registration + Trust & Security. Global SVG icon sprite (`components/PmcIconSprite.jsx`), global floating help drawer (`components/PmcHelpDrawer.jsx`). All 30 routes mounted; each E page accepts `legacy={Legacy}` prop and falls back to the existing Navy design when `?ui=e` is off, keeping the current UI 100% intact for default users. Smoke tests: Homepage, TendersList, HelpCentre, Admin Dashboard, Admin Vendor-KYC, Vendor Home all render pixel-perfect matching the templates. Legacy `?ui=default` verified unchanged.
- v48c-rev6 (Feb 2026) — **Bulletproof registration blank-form download**. User reported "PDF won't open / We can't open this file" on Windows + Android after tapping Download. Root cause: plain `<a href download>` anchor drops Content-Disposition on Android Chrome / corporate proxies / in-app WebViews. **Fix** — `RegistrationStart.jsx` now uses `fetch → Blob → URL.createObjectURL`: View opens the blob URL in a new tab, Download programmatically clicks a hidden `<a download="pmc-registration-form.pdf">` on the blob URL. Blob URLs are tracked in a `useRef` and revoked on unmount. Busy states show `Downloading…` / `Opening…`. Service worker cache bumped to `pmc-shell-v48c-rev6` so browsers pick up the new bundle without hard-refresh. Testing iteration_34: 100% pass (Playwright download event fires, 4435-byte valid `%PDF-` file, pypdf parses 2 pages, toast + busy states verified, blob:// popup URL confirmed, ?ui=e/?ui=default toggle regression green).
- v48c-rev5 (Feb 2026) — Package catalog visible View button.
- v48c-rev4 (Feb 2026) — Android download 2-anchor UX, approved-registration guard, pending-reviews chip.
- v48c-rev3 (Feb 2026) — Registration PDF rewrite + package modal Print + Download CSV.
- v48c (Feb 2026) — Option E overhaul + 4 bug fixes + mobile responsive + tab deep-link sync.
- v47h (Sep 2026) — Admin bid detail full page + vendor uploads viewable. Root cause: bid documents stored only a storage `key`, never a servable `url`/`mime`. Both bid detail endpoints (`/bids/admin/{id}`, `/bids/{id}`) now enrich every document with URL + mime at read time (works for all legacy bids, no migration). BidTable View → dedicated page `/admin/bids/:bidId` (AdminBidDetailPage.jsx) showing the entire entry + every document with Open/Download/inline preview + workflow + print. Verified live: 3 docs on PMC-BID-2026-00017 fetch 200. SW `pmc-shell-v47h`. Bundles: `pmc-backend-v47h.zip`, `pmc-frontend-v47h-prod-build.zip`.
- v47g (Sep 2026) — **v47f finalized + platform-wide pagination**. Admin bid detail modal verified (View → full submission, attachments, workflow, print). **ListPager rolled out to all major listings**: admin Bids, DocuSign, Registrations, Vendors, Notices, Live Auctions, Engagements, Billing, Audit, Vendor Intel, Meetings, Masters (Staff/Companies/Tenants), BOQ, Contracts, Catalog, Escrow ledger, Corrigenda + vendor portal (tenders, my bids, envelope history). Fixed DocuSignPanel conditional-hook bug (pager never rendered). DocuSign View/Resend(unsigned)/Print(signed) verified; resend contract-tested (400 on completed, well-formed 502 without DocuSign config). Testing agent iteration_26: 100% backend + frontend pass. Prod build has 0 preview-URL refs (built with `REACT_APP_BACKEND_URL=` empty); SW cache bumped to `pmc-shell-v47g`. Bundles: `pmc-backend-v47g.zip`, `pmc-frontend-v47g-prod-build.zip`.
- v47f (Sep 2026) — **Admin bid detail modal** (full submission incl. attachments preview + workflow history via new `/bids/admin/{id}`), **reusable ListPager** (10/20/30/All + prev/next), **DocuSign per-row View/Resend/Print** (new `POST /docusign/envelopes/{id}/resend`). Superseded by v47g.
- v47e (Sep 2026) — **Vendor in-app notifications**: vendor-scoped endpoints (`/notifications/vendor/mine|read|read-all`), bell in Vendor Portal header (20s poll, unread badge).
- v47d (Sep 2026) — **Security sign-in alerts on every login** (admin / staff all roles / vendor), post-MFA only, with IP + user-agent + "wasn't you?" CTA.
- v47c (Sep 2026) — **Vendor confirmatory emails for every action**: bid received (w/ Pay-EMD CTA), EMD payment received (idempotent, once), EMD refunded (w/ reason), bid withdrawn, password changed.
- v47b (Sep 2026) — **Send EMD link** (admin-triggered branded email w/ Stripe deep-link `/vendor/bids/:id/pay`) + **vendor transition emails** on all vendor-visible stages.
- v47a (Sep 2026) — **Admin bid actions**: Approve→Certifier (renamed flag), Hold/Resume (`on_hold` status, admin-only, restores prior stage), Reject extended to held bids. Verified: hold→on_hold, resume→restores status, non-admin hold→403. Bundles: `pmc-backend-v47a.zip`, `pmc-frontend-v47a-prod-build.zip`.
- v46z (Sep 2026) — **EMD fallback** (1%/$500 floor when notice missing `emd_config`) + **View/Print** bid detail modal (BidDetailModal.jsx). Live-verified: bid on unconfigured notice now correctly enters `emd_pending` with `emd_source=default_fallback`. Bundles: `pmc-backend-v46z.zip`, `pmc-frontend-v46z-prod-build.zip`.
- v46y (Sep 2026) — **Rate-a-Peer overhaul**: co-participation gate (only vendors who bid on the same tender can rate each other), 1-10 scoring, weightage locked to super-admin (hierarchy_level>=10), default rubric seeder migrates 1-5 → 1-10 on cold start. Fixes silent submit bug (rubric was 404 in prod).
- v46x (Sep 2026) — axios 20s timeout, SW cache bumped to `pmc-shell-v46x`. **Deployed to production Sep 25** and verified live.
- v46w (Sep 2026) — all 5 portals authenticate, Resend DNS routing guide, EB env properties wired.
- v46v (Sep 2026) — vendor first-login redirect fix + Resend sender switch.
- v46u and earlier — see `/app/frontend/public/downloads/DOWNLOAD_v46*.md`.
