# PMC Managers Limited — PRD

## Original problem statement
Build and operate PMC Managers Limited (pmcmanagers.com), a multi-role procurement and tender-management platform for Kazakhstan and CIS markets. Roles include Admin, Management, Partners, Agents and Registered Vendors. Core surfaces: public tender notice board (About Us, Vision & Mission, Live/Completed/All Tenders lists), vendor registration, admin tender workbench, evaluations, awards, escrow, auctions and analytics. AI-assisted DPR ingestion must handle very large tender/DPR documents "of any size and any number of characters" and produce genuine section-level extraction, not stubs.

## Architecture

- Frontend: React (CRA), Tailwind, shadcn/ui — hosted on S3 + CloudFront.
- Backend: FastAPI on AWS Elastic Beanstalk (Docker) with 25 MB nginx body limit.
- Data: MongoDB (via `MONGO_URL`).
- AI: Emergent LLM Universal Key (map-reduce DPR pipeline in `backend/routers/tender_pro.py`).
- Auth: Cookie sessions, three realms (admin, staff, vendor). Same-origin `/api` calls required in production bundles.
- Assets: Public `/downloads/` folder for release artifacts and manuals — NEVER deleted with `s3 sync --delete` at bucket root.

- **v46u KYC admin controls + universal search (P1)** — new `POST /api/v1/kyc/manual` endpoint lets admins override a vendor's KYC status (verified / pending / rejected) with an audit row per change. VendorsPanel: added a KYC controls block on the selected vendor's KPI panel with **Run KYC provider**, **Mark verified**, **Mark pending**, **Mark rejected** buttons and a colored current-status pill. `RegistrationsPanel` and `VendorIntelPanel` now each have a search input (`reg-search` / `vintel-search`) that filters by company/email/reference — matching the existing `VendorsPanel` search UX. E2E verified via curl: admin login → `/api/v1/kyc/manual` → vendor kyc_status set to `verified` → vendor successfully created bid `PMC-BID-2026-00018` on PMC-NOT-2026-0013.

## Implemented (as of 2026-09-25 pm4 — v46u vendor-activation vanish fix + Resend direct path)

- **Vendor "record vanishes on activation" fix (P0)** — root cause was frontend filter state, not data loss: activating a vendor flips `email_verified`/`is_active`, so the row instantly fell out of the "Pending verify"/"Inactive" filter the admin was viewing. `activateVendor` in `VendorsPanel.jsx` now resets `statusFilter` to "all" before reloading (same pattern `sendInvite` already used) and the row stays visible with the highlight. Verified via API: activate PMC-SUP-000036 → record still listed → vendor login succeeds with admin-set password (`must_change_password=true` → forced change screen).
- **Resend direct email path** — `emails.py` sends via `https://api.resend.com/emails` from `PMC Managers Limited <admin@pmcmanagers.com>` when `RESEND_API_KEY` is set (added to backend `.env`); legacy relay remains as fallback. Test send returned 403 "domain not verified" — waiting on user to verify pmcmanagers.com in Resend (DNS records). Also scrubbed remaining user-facing "Emergent" strings in `UnifiedLogin.jsx` (login briefing bullets) and `AnalyticsPanel.jsx` (AI tooltip).

## Implemented (as of 2026-09-25 pm3 — v46u production bundles built)

- **v46u production bundles staged** — `pmc-frontend-v46u-prod-build.zip` (2.3 MB, same-origin build, zero preview-URL hits in app code, `/downloads/` excluded per S3-sync convention, SW cache `pmc-shell-v46u`) and `pmc-backend-v46u.zip` (288 KB, Dockerfile + Dockerrun + .platform/nginx + backend incl. new `kyc.py /manual` endpoint and `push.py`; no `.env` inside). Manifest: `DOWNLOAD_v46u.md` with EB + S3/CloudFront deploy steps. Awaiting user upload to AWS.

## Implemented (as of 2026-09-25 pm2 — v46u clickable dashboard + procurement-wide search)

- **Dashboard KPI tiles now drill through (P1)** — every tile in `AnalyticsPanel.jsx` (Published notices, Vendors, Bids, Awarded, Pending EMD, EMD collected, Active contracts) is now a button navigating to its owning tab (`?tab=notices/vendors/bidding/awards/escrow/billing/boq`). Pipeline-funnel stage boxes and Top-priced-bids rows also click through to the bid pipeline. Verified: Published-notices tile → Notices tab; `emd_paid` funnel stage → Bidding tab.
- **Procurement tab — universal search coverage** — Notices (existing) and Tender Builder (existing filter bar) confirmed; added: Corrigenda (notice-picker search `corr-notice-search` + corrigenda list search `corr-search`), Work Packages kanban (`pkg-search` filters title/category/phase before column grouping), BOQ & Contracts (`boq-search` filters templates or contracts per active sub-tab), Product Catalog (`catalog-search` added alongside side/category dropdowns, matches code/name/category/description).

## Implemented (as of 2026-09-25 pm — v46u universal filters + help pill + LiveAuctions crash fix)

- **Reverse Auctions crash fix (P0)** — `LiveAuctionsPanel.jsx` referenced `publicApi.listNotices` without importing `publicApi`; ReferenceError bubbled up to the panel error boundary ("This panel hit an error"). Added the missing import.
- **Universal filter + search rollout** across:
  - **Live Auctions** — status filter (All / Draft / Live / Closed) + free-text search by title or notice ref.
  - **Engagements** — existing status filter kept; added search on product, buyer email, buyer company.
  - **Billing transactions** — new status filter (All / Paid / Unpaid / Refunded) + search on buyer, product code, session id, context ref.
  - **Awards** — search bar above the awarded-bid picker (filters bids by bid_ref, company, vendor email, award_ref, notice_ref).
  - **DocuSign** — envelope log now has status filter (All / Sent / Waiting / Signed / Rejected / Voided) + search by ref / signer / email.
  - **Masters** — universal search bar per data tab (staff, companies, tenants, hierarchy) that filters the visible list live.
- **Help panel** — sticky search bar and module counter at the top of the left rail (no more scrolling down to search).
- **Context-help pill** — new "Help" button in the admin top bar on every tab (except Help itself). Clicking it jumps to the Help panel with the search pre-filtered to the tab you were on. Verified end-to-end: pressing Help on Vendors landed on the Help tab with search value = `vendors`.

## Implemented (as of 2026-09-25 — v46u bid-submit UX + SW crash fix)

- **v46u KYC/EMD verification pass** — test vendor `manualvendor@pmcmanagers.com` had no KYC record (kyc: None) so every bid returned 412; marked `kyc.status=verified` in preview DB. Full chain verified via curl: bid create on PMC-NOT-2026-0014 → `PMC-BID-2026-00016` (EMD USD 10,500) → Stripe checkout URL generated (test mode) → bid withdrawn to free the slot. EMD payment pipeline is functional.

- **v46u Bid-submit silent-failure fix (P0)** — root cause: notice `PMC-NOT-2026-0020` deadline (2026-05-07) had passed and the vendor already held an active bid; backend correctly returned 400/409 but the page only showed a fleeting toast. `BidSubmit.jsx` now: shows a persistent red inline banner when the deadline has passed and disables the submit button ("Deadline passed"); renders any API error inline under the form (`bid-submit-error` testid) in addition to the toast; strips partially-uploaded documents from the payload (eliminates the 422 "Field required ×6" regression); upload guard refuses to push docs without a storage key. Verified in preview via Playwright: banner visible, button disabled.
- **v46u Service worker crash fix** — `TypeError: Failed to convert value to 'Response'` eliminated; navigate + static-asset branches now always resolve to a real Response (503/504 fallbacks). Cache bumped to `pmc-shell-v46u`.
- **v46t lint unblock** — missing `EnablePushButton` import added in `TopBar.jsx`; oxlint 0 errors.

## Implemented (as of 2026-09-24 pm — v46t push + escrow signer edit + E.164)

- **v46t Web Push (Firebase-free, standard VAPID)** — full stack shipped: `backend/routers/push.py` (subscribe / unsubscribe / config / test / admin list); service worker `push` + `notificationclick` handlers; frontend hook `lib/push.js` + `EnablePushButton` mounted in TopBar; trigger hooks fan out on `bid.awarded` and on new corrigendum publish. VAPID key generator at `tools/push/generate_vapid_keys.py`. Works on Android Chrome/Edge/Samsung and iOS 16.4+ **installed** PWAs.
- **v46t Escrow signer edit** — new `EscrowSignerEditor.jsx` panel under the Escrow tab lets admins update PMC or Escrow institution officer name/email/designation on an existing joint account without cancelling. Uses the existing `PATCH /api/v1/escrow/accounts/{id}` endpoint; every change writes an audit row.
- **v46t E.164 phone hardening** — `FormPrimitives.PhoneInput` now enforces `+?[1-9]\d{6,14}` after stripping punctuation. All forms using `<PhoneInput>` inherit the tighter rule automatically.
- **Manual v3 — full Emergent-reference scrub (P0)** — 16 occurrences across 13 pages removed; verified via pypdf: zero occurrences in every v3 PDF.
- **v46s Android install prompt (P1)** — explicit "Install on your phone" card capturing `beforeinstallprompt`; iOS shows Share → Add to Home Screen guided steps. Hidden in standalone mode, dismissal persisted 7 days.
- **v46s iPhone notch/safe-area fix (P1)** — `.pmc-safe-top/.pmc-safe-bottom/.pmc-safe-x` utilities applied to TopBar header + drawer and AdminShell sticky header + drawer; admin hamburger tap target 34px → 44px.
- **v46r Dashboard Drill-cards & raw `fetch` eradication (P0)** — all components migrated off raw `fetch(REACT_APP_BACKEND_URL...)` onto `@/lib/api`; zero red toasts in same-origin prod builds.
- **v46r Exhaustive Help content authored for ALL 28 modules (P0)** — user screenshot showed "Content in progress — this module's actions will be authored in the next batch" on Meetings, Corrigenda, Tender Builder, Awards, DocuSign, Reverse Auctions, etc. Authoring completed for all 28 modules (zero modules with 0 actions). Every single module now has 1–4 detailed step-by-step actions with preconditions, when-to-run, controls, expected outcomes, and common error fixes.
- **v46r EB Docker Package layout** — backend zip contains `Dockerfile`, `Dockerrun.aws.json`, `.platform/nginx/conf.d/proxy.conf` (200MB body size tuning), and `backend/pmc_lib/help_content_data.py`.
- **v46p Deliverables pack** — 151-page Master Training Manual, 33-page Testing Manual, Process Flow + Data Flow diagrams in PDF + SVG.
- **v46p Bug Blitz Round Two** — all five P0 bug tracker items verified and passing 5/5.
- **v46q TenderBuilder tab-refetch fix** — clicking the kind tabs (Tender / RFP / RFQ / All Kinds) now refetches the sidebar list with the correct `?kind=` filter so masters + drafts no longer leak across kinds. `switchKind()` calls `load(k)`; `load` passes the filter to `tenderTemplateApi.list()`.
- **v46q i18n audit** — verified: all three locales (EN / RU / KK) have symmetric key coverage at 653 keys each and no English fall-through values in the RU/KK blocks. No backfill required.
- **v46q Firebase FCM playbook received** — Push Notifications design gathered from integration_playbook_expert_v2. Waiting on the user's Firebase project keys (see backlog) before wiring the frontend enable-notifications button and the backend `send_to_user()` bridge.
- **v46p PWA re-enabled** — proper 4-icon manifest, 4 launcher shortcuts, stale-while-revalidate service worker that bypasses `/api/*`. Installable on Android + iOS 16.4+.
- **v46p Deliverables pack** — 151-page Master Training Manual (PDF + DOCX), 33-page Testing Manual, Process Flow + Data Flow diagrams (PDF + SVG) — all staged in `/app/frontend/public/downloads/`.
- **v46p Bug Blitz Round Two (fully closed)** — all five P0 items (registration step gate · reports snapshot JSON · rubric max defensive · locked-eval reopen · mobile toolbar overflow) verified 5/5 by testing agent (iteration_25.json).
- **v46o Per-section AI hotfix Round Two** — `ai_draft_section` delegates to `tender_pro._llm_complete` so `sk-emergent-*` keys route through the Emergent integrations proxy.
- **v46m Manual v2 (final)** — 130-page (67-chapter) master training manual with sovereign cover + PMC crest + "CONFIDENTIAL — INTERNAL USE ONLY" watermark on every page. 32 screenshots + 8000+ words of narrative across all app surfaces + regulator liaison + ESG questionnaire + role runbooks + MoU + RACI + cost-benefit + sample corrigenda / DocuSign / stakeholder reports / audit trail / bid + procurement policy + committee constitution + DR drill + acceptance-test matrix + localisation strings + Q&A digest + standard clauses + comms templates + NPS + debarment + release plan.
- **v46n Per-section AI hotfix Round One** — superseded by v46o.
- **v46m Manual v2** — regenerated 66-page (25-chapter, 32-screen) master training manual against the deployed sovereign design.
  - Screens: 8 public + 6 five-portal logins + 14 admin tabs + 5 vendor tabs = **32** full-page captures at 1600×900 @ 1.25 DSR (retina-clean).
  - Chapters: architecture, roles matrix, security/audit, public journey, vendor journey, admin tour, DPR deep-dive, evaluation/escrow deep-dive, reverse auctions, UX safeties, deploy runbook, troubleshooting, API index, release history, glossary, 30/60/90 onboarding, monthly cadence, KPIs, escalation matrix, keyboard shortcuts, FAQ, sample tender lifecycle, data-model appendix, release archive, sign-off.
  - Artefacts: PDF (9 MB), DOCX (8 MB), MD (49 KB) plus a single-file bundle zip (16 MB).
  - Regenerate at any time with `python3 /app/tools/manual/capture.py && python3 /app/tools/manual/build.py`.
- **v46m Bug Blitz Round Two** (backend + frontend zips staged).
  - `GET /api/v1/evaluations/lock-state/{notice_ref}` added; frontend `EvaluationPanel` now disables Lock buttons + shows sealed timestamp banner once an envelope is locked.
  - `POST /api/v1/evaluations/lock-envelope` refuses re-lock (409) so a rogue call cannot overwrite the timestamp / attribution.
  - `AuctionRoom` recent-bids row rebuilt as `flex-col sm:flex-row` with `break-all` on money column — resolves mobile overflow (bug tracker items 78/81/82).
  - Rubric max + Registration Section-A step gate re-verified in code (were shipped earlier; still enforcing).
  - Stakeholder-snapshot JSON parse: no live frontend caller in current source — deferred with "no repro" note.
- **v46l Unlimited DPR + async worker** (staged 2026-09-24).
- **v46k Sovereign Redesign** (deployed 2026-09-24)
  - Rebuilt `/login` as a 5-portal picker (Admin, Management, Partners, Agents, Vendors) with per-portal branding, badges, icons and dedicated credential forms.
  - Sovereign navy (#0B132B) + gold (#D4AF37) accent palette across public surfaces.
  - Refreshed home hero with editorial serif headline, gold kicker, gold primary CTA.
  - Home now uses `PmcFooter` (Snapchat / Instagram / WhatsApp social icons + gold seal strip).
  - New Tailwind tokens: `brand-gold`, `brand-gold-hover`, `brand-gold-soft`, `brand-navy-sovereign`.
- **v46j Map-Reduce AI DPR ingestion** (backend zip staged; production deployment pending).
- **v46i editorial public surfaces** (About Us, Vision & Mission, live/completed/all tender lists, admin shell with 5-section collapsible sidebar + hamburger drawer). Deployed to production.
- **v46f no-master AI DPR flow** (editable tender name, save-as-master persists, master reusable across countries).
- **v46b/c/d/g bug blitz** (bulk of the 87-item bug tracker fixed and shipped).

## Open backlog (P0/P1/P2)

**P0 (blocking)**
- ~~Deploy v46j backend + v46k frontend to production and run KMT DPR validation end-to-end.~~
- ~~Address "unlimited size" DPR ingestion~~ — completed.
- **Deploy v46u to production** — production bundle rebuild + redeploy to pick up bid-submit UX, service-worker crash fix, KYC admin controls, and universal search.

**P1 (open bugs — historical, kept for context)**
- ✅ Registration wizard step-validation gate between Section A and B/C. — **CLOSED v46p**
- ✅ Stakeholder Reports save-snapshot JSON parse error. — **CLOSED v46p**
- ✅ Evaluation rubric max-value client-side gate. — **CLOSED v46p**
- ✅ Locked-evaluation should refuse re-open + show saved report. — **CLOSED v46p**
- ✅ Mobile CSS overflow: reverse-auction summary button. — **CLOSED v46p** (funnel + vendor-intel already fixed earlier)
- TenderBuilder Tender/RFP/RFQ tab switch should refetch.
- Escrow — modify email IDs on transaction signer flow.
- i18n Russian/Kazakh strings backfill (deferred by user in this session).
- Profile avatar cache invalidation after re-login.
- Global email + mobile regex validation across forms.

**P2 (feature backlog)**
- Manual v2 (130–160 pages) covering admin sub-tabs, modals, workflows, vendor journey — capture after v46k design settles.
- Firebase / APNs push notifications.
- LSEG / World-Check integration.
- PayPal / Kaspi payments alongside Stripe.
- Zoom integration for evaluation committees.

## Guardrails

- Never use `aws s3 sync ... --delete` at bucket root — it previously deleted `/downloads/`.
- Production frontend bundle MUST be built with no `REACT_APP_BACKEND_URL` (same-origin `/api`).
- Service worker registration remains disabled/self-cleaning.
- Do not package `backend/.env` in EB deployment archives — use EB environment properties.

## Recent artifacts

- `/app/frontend/public/downloads/pmc-backend-v46j.zip` — map-reduce DPR backend for EB.
- `/app/frontend/public/downloads/pmc-frontend-v46k-prod-build.zip` — sovereign redesign frontend.
- `/app/frontend/public/downloads/DEPLOY_v46k_README.md` — deploy instructions.
- `/app/deliverables/v46c/Bugs_Tracker_v46h.xlsx` — bug tracker current status.
