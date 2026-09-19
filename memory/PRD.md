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

### 14 Feb 2026 — Bugs V2 Batch #4: Vendor Doc Crossover + Notices drafts + Registrations UX
- **Bug #78 — Vendor Document Crossover (CRITICAL security)**: on admin-create flow, Vendor B could inherit Vendor A's uploaded documents.
  - Backend fix (`vendor_full_invite.py`): `admin-create` now ignores `draft_registration_id` if the draft's email doesn't match the new vendor's email (defence in depth).
  - Frontend fix (`AdminVendorCreate.jsx`): if the admin changes the vendor's email after an auto-draft was created, the `draftId`/`draftToken`/`document_slots` state is reset. Previously the state was reused → old uploads were merged into the new vendor.
  - Regression test: `/app/backend/tests/test_regression_v22.py::test_bug78_admin_create_rejects_cross_email_draft` — PASSES.
- **Bucket A — Notices drafts invisible in Admin panel**: `list_notices` (public) filters `is_published=True`, so newly-created drafts were hidden. Added `GET /api/v1/notices/admin/all` (admin-scoped, returns drafts + published + tenant filter). Rewired `NoticesPanel.jsx` to use it. Regression test PASSES.
- **Bucket A — Registrations "Approve does nothing"**: on approve/reject/clarify the target row moved to a different status tab, so it disappeared from the current view. Reviewer perceived it as broken. `RegistrationsPanel.jsx` now auto-switches the filter to the new status.
- **Bucket C — Tender Builder Clone/Delete stale list**: added cache-buster `_=Date.now()` to `tenderTemplateApi.list()` so CloudFront never serves a stale list after a delete/clone. Verified clone endpoint returns 200 with correct payload on preview (the AWS 500 was a stale-backend issue prior to v21).



### 7 Sep 2026 — Staff Master: Edit / Role-change / Deactivate / Password-reset UI
- Concern: admin could add staff but couldn't edit them — only "Clone role" button existed.
- Backend already had `PATCH /api/v1/staff/{id}` for name/roles/hierarchy_level/is_active; added optional `password` to `StaffUpdateIn` for password reset (hashed server-side, never logged raw).
- Rewrote `admin-console/masters/StaffTab.jsx` — every row now has **Edit** + **Clone** buttons. Edit opens inline form with: name, roles (multi-checkbox), hierarchy level, active toggle, password reset field (blank = keep). Active checkmark is now a clickable toggle for one-click deactivate.
- Wired `updateStaff` handler in `MastersPanel.jsx` → calls `staffApi.updateStaff` → refreshes list.
- Verified: PATCH edits name/roles/level/is_active + password reset lets user re-login with new password.

### 6 Sep 2026 — Stripe checkout iframe-hang fix
- Stripe's CSP `frame-ancestors 'self'` blocks embedding, so `window.location.href = stripe_url` from inside the Emergent preview iframe hangs at a blank skeleton.
- Fixed in `VendorDashboard.jsx` (My Bids → Pay EMD), `BidSubmit.jsx` (Submit Bid), and `PurchaseGrid.jsx` (Product catalog) — all now use `window.open(url, "_blank")` with `window.top.location` fallback.

### 19 Sep 2026 — Bugs V2 Batch #3: retest + mobile funnel + committee verification
- **Retest results (via preview API + Mongo, using latest code):**
  - Notice draft creation as admin — endpoint accepts `is_published=false`, notice lands in drafts list. Was blocked in earlier test only because `category` is a required field on the create payload (frontend already sends it). Not a real bug.
  - Committee external-email listing — pulled 2 live committees, both carry the full `external_invitees` array (email + name + designation + accept_token + status + invited_at + decided_at). Backend list endpoint returns them. Frontend `CommitteeList.jsx` iterates over them correctly. Prior "not listed" report was almost certainly the CloudFront-cached-HTML issue.
  - Registration submit — hardened + verified.
- **Bug #79 Mobile Landing Pipeline Funnel labels overlapping**: fixed in `apps/notice-board/NoticeBoardHome.jsx::StatCard`. Added `min-w-0`, `break-words`, `leading-tight` and made the 3-card grid `grid-cols-1 xs:grid-cols-3 sm:grid-cols-3` so labels stack vertically on the smallest phone widths instead of overlapping.
- Bundled into `pmc-frontend-v28-build.zip` (43 MB) + refreshed `pmc-backend-v21.zip` (255 KB).

### 19 Sep 2026 — Bugs V2 Batch #2: Registration submit hardening
- New bug reported live: vendor completes 6 declarations + signature → clicks Submit for Review → toast "Request failed with status code 500".
- Root cause: multiple KeyError / InvalidId paths in `submit_registration` — malformed `registration_id` bubbled up as BSON InvalidId → 500; `doc["email"]` KeyError on legacy rows missing the field → 500; `send_email` failing on live Resend key → 500.
- Fix in `routers/registrations.py::submit_registration`: wrap `ObjectId(...)` in try/except → 400 · use `doc.get("status")` and `.get("email")` → 400 with clear detail · wrap the confirmation email in an inner try/except so a transport failure never fails a valid submission.
- Verified end-to-end via curl: malformed id → 400, missing token → 404, valid submit → 200.
- Rolled into `pmc-backend-v20.zip` (255 KB).

### 19 Sep 2026 — Bugs V2 Batch #1: registration guard + corrigenda + vendor isolation
- Bugs #23 + #77 (Registration double-approve → 500): backend now returns `409 Conflict` with a clear message when a registration is re-approved or re-rejected. Frontend `Approve/Clarify/Reject` buttons now disable + say "Working…" during the API call to prevent accidental double-clicks.
- Bugs #12 + #22 + #23 (Corrigenda withdraw): backend now returns the freshly-updated corrigendum in the withdraw response so the frontend can flip `is_active=false` without a second round-trip.
- Bug #29 (New vendor gets another vendor's documents): `approve_and_create_vendor` in `registrations_helpers.py` now explicitly excludes `documents`, `document_slots`, `attachments`, `uploads`, `primary_document`, `signed_documents` from the profile copy. Registration docs stay on the registration row; vendor row carries only the registration_id reference.
- Deliverables: `pmc-frontend-v27-build.zip` + `pmc-backend-v20.zip` — ready for AWS deploy.

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
