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
- v48c (Feb 2026) — **4 user-reported bug fixes + Option E prod bundles ready**. Fixed: (1) Bidding ops sidebar tab added as first item under 'Money & Compliance' in AdminShell.jsx GROUPS; (2) Work-package Kanban cards now clickable → detail modal with full metadata (data-testid `pkg-detail-modal-<ref>`), drag-drop preserved; (3) Reverse-auction Start button shows `<count>/2` and is disabled with tooltip when <2 participants (backend already returned clear 400); (4) Meeting create + add-invitees endpoints now dispatch Resend email invites via new `_dispatch_meeting_invites` helper — response includes `invites_sent`. Testing iteration_28: 100% pass (backend 2/2, frontend 4/4). Not code bugs, tracked separately: DocuSign PO shows `TEST_WV26_Vendor_1` because that IS the vendor's registered `company_name` (data-quality); vendor registration blank-form download returns blank because admin has not uploaded a template via `POST /api/v1/vendors/registration-template/upload` (deployment setup). Bundles staged: `pmc-backend-v48c.zip` (334 KB), `pmc-frontend-v48c-prod-build.zip` (2.4 MB), `DOWNLOAD_v48c.md`.
- v48b-preview (Feb 2026) — Universal Option E theming + mockup-fidelity structural rewrites for Tenders / Notice detail / Vendor portal / Admin overview / full admin shell.
- v48a-preview (Feb 2026) — Initial Option E toggle groundwork.
- v47h (Sep 2026) — **Admin bid detail is a full page + vendor uploads viewable**. Root cause: bid documents stored only a storage `key`, never a servable `url`/`mime`. Both bid detail endpoints (`/bids/admin/{id}`, `/bids/{id}`) now enrich every document with URL + mime at read time (works for all legacy bids, no migration). BidTable View → dedicated page `/admin/bids/:bidId` (AdminBidDetailPage.jsx) showing the entire entry + every document with Open/Download/inline preview + workflow + print. Verified live: 3 docs on PMC-BID-2026-00017 fetch 200. SW `pmc-shell-v47h`. Bundles: `pmc-backend-v47h.zip`, `pmc-frontend-v47h-prod-build.zip`.
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
