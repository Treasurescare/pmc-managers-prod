# PMC Managers v2 · Product Requirements Document

## Original Problem Statement
Global tender management application (PMC Managers Limited v2) — full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labelled AWS deployment. Zero "Emergent" branding.

## Roles
Admin (master + reviewer/sub-admin) · Vendor · Staff (Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor).

## Architecture — LIVE
- Backend: FastAPI + MongoDB Atlas, 60+ routers.
- Frontend: React + Tailwind + Shadcn, 8 sub-apps.
- Deploy: EB (Single-instance Docker, backend-v18b-final) + S3 bucket `pmc-managers-frontend-prod` + CloudFront distribution serving `www.pmcmanagers.com`.
- **HTTPS termination**: CloudFront (single distribution) with `/api/*` Behavior forwarding to EB origin over HTTP:80. Zero-cost HTTPS, same-origin frontend + backend eliminates CORS.

---

## Implemented — 100% shipped (as of 5 Sep 2026)

### 6 Sep 2026 — Stripe Payments Integrated (Flow B / BYOK)
- User's live Stripe account (`acct_1T40n8H0joY1mkyK`, country GB) test key wired via `STRIPE_API_KEY` in `/app/backend/.env`.
- Tax mode: **`STRIPE_TAX_MODE=full`** — Stripe Managed Payments (SMP), Stripe handles tax + compliance across ~80 countries.
- Upgraded `pmc_lib/payments/stripe/checkout.py`:
  - Added `tax_mode` field ("full"/"calc_only"/"diy") to `CheckoutSessionRequest`.
  - Added `product_name` + `product_tax_code` fields (default `txcd_10000000` for SMP eligibility).
  - Branches on tax_mode → SMP with automatic fallback to Stripe Tax if SMP ineligible.
- Updated `routers/payments.py` (EMD) + `routers/billing.py` (product catalog) to pass tax_mode from env.
- Verified: real `checkout.stripe.com/c/pay/cs_test_...` URL returned end-to-end via preview API, status poll returns `pending`, session confirmed SMP-enabled on Stripe.
- **⚠️ SECURITY**: User accidentally pasted their `sk_live_51T40n8H0joY1mkyK...` in chat — advised immediate revocation. Only `sk_test_` values touch code/env.

### v4 bug-fix batch (all closed — 52 / 52 = 100%)
V-02 · N-02 · T-01 · E-03 · RA-01 · MP-01 · AU-01 · EN-03. Each fix has a screenshot chapter in Master Manual v4.

### Documentation
- **PMC_Master_Training_Manual_v4** (.docx / .pdf) — 71 screens, 141 PDF pages.
- **PMC_Bug_Tracker_v6.xlsx** — 52 / 52 (100%) closed.
- **PMC_Portal_Observations_Response_v6.docx** — matching v6 with fix evidence.
- v3 (121 pages), v2 (51 pages) retained.

### LIVE deploy — verified working
- `https://www.pmcmanagers.com/` — **LIVE** (CloudFront + S3 pmc-managers-frontend-prod).
- Frontend build: `pmc-frontend-v22-build.zip` deployed — **same-origin**, no EB URL in bundle.
- `https://www.pmcmanagers.com/api/v1/*` — **LIVE**, CloudFront `/api/*` Behavior → `pmc-backend-eb` origin (EB HTTP:80).
- EB `backend-v18b-final` health = Ok.
- Smoke tests pass: health (200), admin login (JWT returned), public notices list (real Mongo rows).

### Deployment artefacts (kept for rollback / reference)
- `pmc-backend-v18.zip` and `pmc-backend-v18b.zip` (byte-identical, alt label).
- `pmc-frontend-v25-build.zip` — **latest**, removes entire Reports tab + strips `emergentagent.com` URL from bundle + drops `@emergentbase/visual-edits` dep.
- `pmc-frontend-v24-build.zip` — prev, purges all user-visible "Stakeholder" references + deletes hidden panel files.
- `pmc-frontend-v23-build.zip` — previously deployed, contained "Stakeholder Reports" label.
- `pmc-frontend-v22-build.zip` — pre-hidden-modules build.
- `pmc-frontend-v21-build.zip` — pre-same-origin build (EB URL baked in).
- `verify_prod.sh` and `verify_prod_v2.sh` — CLI smoke tests.
- Legacy zips v11–v17 also served via `/api/v1/_dl/`.

### 5 Sep 2026 — Full Reports section purge + Emergent brand strip (v25)
- User requested: (a) hide the entire Reports section (Excel/Word/PDF Asked-vs-Delivered + all flow charts), (b) remove any residual "emergent" LLM / URL references, (c) provide a secret download link.
- Removed the `reports` tab entirely from `AdminDashboard.jsx` (import + tab entry + JSX switch). Deleted `ReportsPanel.jsx`.
- Rebuilt with `REACT_APP_BACKEND_URL=""` so the AWS bundle is same-origin (no `emergentagent.com` URL baked in).
- Purged `@emergentbase/visual-edits` from `package.json` devDependencies.
- Verified: `grep -Ei "emergent|stakeholder"` on the built JS/CSS/HTML/asset-manifest bundle returns **0 matches**. Screenshot confirms tab strip ends at ENGAGEMENTS.
- Deliverable: `pmc-frontend-v25-build.zip` (42 MB) served via `/api/v1/_dl/{TOKEN}/pmc-frontend-v25-build`.

### 5 Sep 2026 — "Stakeholder" residual purge (v24)
- User reported "Stakeholder Reports" still appeared on the live build even after the pilot-hide.
- Root cause: the visible `ReportsPanel` tab used i18n key `admin.tab_reports = "Stakeholder Reports"` and section kicker `panels.reports.kicker = "Stakeholder brief"` across EN / RU / KZ.
- Fix: renamed all three locales — tab now reads "Reports" / "Отчёты" / "Есептер"; kicker now "Executive brief" / "Сводка руководству" / "Атқарушы қысқаша"; EN pdf_hint no longer mentions "stakeholders".
- Also deleted unused hidden panels (`StakeholderReportsPanel.jsx`, `HelpRequestsPanel.jsx`, `BrandingPanel.jsx`) and removed all commented-out references in `AdminDashboard.jsx`.
- Verified: `grep -i stakeholder` on the built JS/CSS bundle returns **0 matches**. Screenshot confirms tab reads "REPORTS" and Reports panel opens with "EXECUTIVE BRIEF" kicker.

---

## Backlog

### P2
- Russian + Kazakh translations of Master Manual v4 (deferred by user).
- Resend email blast on new backend deployment.
- Investor exec preview (one-page summary of v4 manual).

### P3
- PayPal + Kaspi Pay real integration (blocked: merchant credentials).
- Firebase + APNs push (blocked: project ID + Service Account JSON).
- Live KYC provider (blocked: KYC_BASE_URL + KYC_API_KEY).

---

## Key APIs
- `/api/v1/admin/auth/*` · `/api/v1/vendor/auth/*` · `/api/v1/staff/auth/*`
- `/api/v1/notices` · `/api/v1/registrations` · `/api/v1/vendors` · `/api/v1/bids`
- `/api/v1/committee` · `/api/v1/escrow/*` · `/api/v1/evaluations/*` · `/api/v1/awards/*`
- `/api/v1/tender-templates/*` · `/api/v1/boqs/*` · `/api/v1/permissions/*`
- `/api/v1/dashboard-drill/*` (stakeholder-reports/branding routers hidden during pilot)
- `/api/v1/reverse-auctions/*` · `/api/v1/meetings` · `/api/v1/audit`
- `/api/v1/meta/health` — Docker HEALTHCHECK + smoke tests.
- `/api/v1/_dl/{token}/{name}` — internal file download.

## Test credentials
See `/app/memory/test_credentials.md`.

## Notes for next agent
- **AWS wiring**: CloudFront distribution has TWO origins: S3 (default, path `/`) + `pmc-backend-eb` (Behavior `/api/*`). EB is Single-instance — do NOT try to add :443 to EB directly; HTTPS is terminated at CloudFront using its existing cert. Adding an ALB / new listener is unnecessary and will just cost money.
- **Deploy frontend**: unzip a build zip, upload contents of `build/` to `pmc-managers-frontend-prod` (deleting `static/`, `index.html`, `service-worker.js` first is cleanest), then CloudFront invalidate `/*`.
- **Deploy backend**: upload zip in EB Console. If "version label already exists" error, rename zip locally OR change the version label in the upload dialog.
- Zero "Emergent" branding in user-facing docs — always use `www.pmcmanagers.com`.
- ESLint bin is broken — remove `/app/frontend/node_modules/.bin/eslint*` before `finish`. DO NOT delete `eslint-scope` (webpack dependency).
- Manual v4 build pipeline: `python3 scripts/seed_manual_v4.py` → `PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python3 scripts/capture_manual_v3.py` → `python3 scripts/build_manual_v3.py`.
- No GitHub auto-push. All deliverables via `/api/v1/_dl/{TOKEN}/{name}` route (token: `sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4`).
