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

## Delivered (Feb 2026 · v46v)
### Vendor login end-to-end
- `POST /api/v1/vendor/auth/login` returns `must_change_password` flag.
- `/vendor/login`, `/login` (unified vendor tile), and mobile `/m/login` all honour the flag and route to `/vendor/change-password` on first sign-in. **Fixed in v46v** — was broken on the unified + mobile entry points.
- Admin activation (`POST /api/v1/vendors/{ref}/activate`) supports `mode=set_password` and `mode=resend_link`.

### KYC admin overrides
- `POST /api/v1/kyc/manual` (admin, legal_counsel): verified / pending / rejected + audit log.
- VendorsPanel → KYC block on selected vendor.

### Universal search & filters across admin console
- Registrations, Vendor Intel, Live Auctions, Engagements, Billing, Awards, DocuSign, Masters (staff/companies/tenants/hierarchy), Corrigenda, Work Packages, BOQ & Contracts, Catalog. Notices + Tender Builder had it earlier.

### Dashboard drill-through
- Every KPI tile + funnel stage is clickable → routes to the owning tab.

### Help UX
- Sticky search on the Help panel.
- Floating context-aware **Help pill** in top bar; pre-fills tab-specific search.

### Bid submit hardening
- Deadline banner + disabled submit past deadline.
- Inline API errors under the form.
- Strip partial doc uploads (fixes 422s).
- Service worker `pmc-shell-v46u`: all fetch branches return a real Response (503/504 fallbacks).

### Emails
- Sender switched to `admin@mail.pmcmanagers.com` (v46v). Requires DNS verification of `mail.pmcmanagers.com` in Resend (MX + SPF + DKIM).
- Legacy `emergentmails.com` relay removed from the code path; only Resend is used.

## Test credentials
See `/app/memory/test_credentials.md`.

## Backlog
### P1
- Verify Web Push end-to-end once VAPID keys are set in EB.
- Verify `mail.pmcmanagers.com` in Resend and confirm outgoing emails are landing (waiting on owner DNS action).

### P2
- Playwright regression suite (currently manual QA).
- LSEG / World-Check KYC provider swap-in.
- PayPal + Kaspi payments (Stripe is the sole rail today).
- Zoom bid-opening auto-scheduling polish.

## Deployment ledger
- v46x (Sep 2026) — axios 20s timeout (no more silent "VERIFYING…" hangs), SW cache bumped to `pmc-shell-v46x` (evicts all stale caches on activate). Frontend-only patch on top of v46w. Diagnosed prod outage: S3 missing `static/` folder + user browser stuck on 2024-era service worker → recovery playbook in `RECOVER_v46w_BLANK_SCREEN.md`.
- v46w (Sep 2026) — all 5 portals authenticate (admin/owner backfilled with full executive roles; frontend falls back portal-role → admin).
- v46v — vendor first-login redirect fix + Resend sender switch to `mail.pmcmanagers.com`.
- v46u — universal search bars, dashboard drill-through, KYC admin controls, SW crash fix.
- v46t and earlier — see `/app/frontend/public/downloads/DOWNLOAD_v46*.md`.
