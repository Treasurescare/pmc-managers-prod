# PMC Managers v2 · Product Requirements Document

## Original Problem Statement
Global tender management application (PMC Managers Limited v2) — full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labelled AWS deployment. Zero "Emergent" branding.

## Roles
Admin (master + reviewer/sub-admin) · Vendor · Staff (Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor).

## Architecture
- Backend: FastAPI + MongoDB (Motor), 60+ routers.
- Frontend: React + Tailwind + Shadcn UI, 8 sub-apps.
- Deploy: AWS Elastic Beanstalk (Docker) + S3 + CloudFront + Route 53 · `www.pmcmanagers.com`.
- **HTTPS termination**: CloudFront (single distribution) with `/api/*` Behavior forwarding to EB HTTP:80. Same-origin frontend + backend eliminates CORS.

---

## Implemented (as of 5 Sep 2026)

### v4 bug-fix batch (all closed — 52 / 52 = 100%)
V-02 · N-02 · T-01 · E-03 · RA-01 · MP-01 · AU-01 · EN-03. Each fix has a screenshot chapter in Master Manual v4.

### Documentation
- PMC_Master_Training_Manual_v4.docx / .pdf — 71 screens, 141 PDF pages, ~8 MB.
- PMC_Bug_Tracker_v6.xlsx — 52/52 closed, green highlights.
- PMC_Portal_Observations_Response_v6.docx — matching v6 with fix evidence.
- v3 (121 pages) and v2 retained.

### Deployment artefacts
- `pmc-backend-v18.zip` and `pmc-backend-v18b.zip` (byte-identical, alt label).
- `pmc-frontend-v22-build.zip` (2 MB) — **same-origin build**, REACT_APP_BACKEND_URL="".
- `pmc-frontend-v21-build.zip` — earlier build with EB URL baked in (currently live).
- `verify_prod.sh` and `verify_prod_v2.sh` — CLI smoke tests.
- Legacy zips v11–v17 also served via `/api/v1/_dl/`.

### LIVE deploy status
- `https://www.pmcmanagers.com/` — **LIVE**, serving `main.4ed5ef24.js` from CloudFront + S3.
- `https://www.pmcmanagers.com/api/v1/*` — **LIVE**, proxied via CloudFront `/api/*` Behavior → `pmc-backend-eb` origin (HTTP:80).
- EB `backend-v18b-final` running with health = Ok.
- Verified: health, admin login (returns JWT), notices list (3 real Mongo records).

---

## Backlog

### P1 (nice-to-have hygiene)
- Deploy `pmc-frontend-v22-build.zip` to S3 so the live JS calls `/api/*` same-origin (currently JS still calls EB URL directly — works today over HTTP:80 but not future-proof).
- Smoke-test the 8 v4 fixes on the live URL with Bug Tracker v6 open.

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
- `/api/v1/dashboard-drill/*` · `/api/v1/stakeholder-reports/*` · `/api/v1/branding`
- `/api/v1/reverse-auctions/*` · `/api/v1/meetings` · `/api/v1/audit`
- `/api/v1/meta/health` — used by Docker HEALTHCHECK + smoke tests.
- `/api/v1/_dl/{token}/{name}` — internal file download.

## Test credentials
See `/app/memory/test_credentials.md`.

## Notes for next agent
- CloudFront distribution has TWO origins: S3 (default, serves `/` etc.) + `pmc-backend-eb` (Behavior `/api/*`).
- EB env is **Single instance** — no ALB. HTTPS is terminated at CloudFront. Do NOT try to add :443 to EB directly; use CloudFront cert.
- Zero "Emergent" branding in user-facing docs — always use `www.pmcmanagers.com`.
- ESLint bin is broken — remove `/app/frontend/node_modules/.bin/eslint*` before `finish`. DO NOT delete `eslint-scope` (webpack dependency).
- Manual v4 build pipeline: `python3 scripts/seed_manual_v4.py` → `PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python3 scripts/capture_manual_v3.py` → `python3 scripts/build_manual_v3.py`.
- No GitHub auto-push. All deliverables via `/api/v1/_dl/{TOKEN}/{name}` route (token: `sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4`).
