# PMC Managers v2 · Product Requirements Document

## Original Problem Statement
Global tender management application (PMC Managers Limited v2) — full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labelled AWS deployment. Zero "Emergent" branding.

## Roles
Admin (master + reviewer/sub-admin) · Vendor · Staff (Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor).

## Architecture
- Backend: FastAPI + MongoDB (Motor), 60+ routers.
- Frontend: React + Tailwind + Shadcn UI, 8 sub-apps (admin/vendor/staff/notice-board/registration/client/committee/mobile).
- Deploy: AWS Elastic Beanstalk (Docker) · S3 + CloudFront · `www.pmcmanagers.com`.

---

## Implemented (up to 4 Sep 2026)

### v4 bug-fix batch (all closed, 52/52 = 100%)
- V-02 · Vendor pending-verify dropdown filter.
- N-02 · Notice template pill is now a jump-link to Tender Builder.
- T-01 · Tender Builder combined **ALL KINDS** view.
- E-03 · Escrow reconciliation ledger-vs-bank sub-panel with delta pills.
- RA-01 · Reverse auction post-close summary panel (starting/floor/winning/savings%/winner/timing).
- MP-01 · Masters · Staff · **Clone role** column.
- AU-01 · Audit filter bar (actor / event_type / from date / to date + Clear).
- EN-03 · Engagements buyer email is a jump-link to Vendors master.

### Documentation
- **PMC_Master_Training_Manual_v4.docx / .pdf** — 71 screens, 141 PDF pages, ~8 MB. Chapters for every public / admin / vendor / staff route + token-gated pages + 6 bug-fix showcases.
- **PMC_Bug_Tracker_v6.xlsx** — 52/52 (100%) closed, 8 rows highlighted green with fix evidence.
- **PMC_Portal_Observations_Response_v6.docx** — matching v6 with fix descriptions per bug.
- v3 (121 pages), v2 (51 pages) manuals retained.

### Deployment artefacts (all served via `/api/v1/_dl/<token>/<name>`)
- `pmc-backend-v18.zip` (structured for EB Docker upload · Dockerfile + Dockerrun + backend/ + docs/)
- `pmc-backend-v18b.zip` (byte-identical, alternate label to avoid "version already exists")
- `pmc-frontend-v21.zip` (source tree, 43 MB — reference only)
- `pmc-frontend-v21-build.zip` (2 MB · production build with `REACT_APP_BACKEND_URL=https://pmc-backend-prod.eba-kmk3u8cp.eu-west-2.elasticbeanstalk.com`)
- `verify_prod.sh` (four-command smoke test)

### Deploy status
- **Frontend on S3 + CloudFront** at `https://www.pmcmanagers.com/` — LIVE, serving `main.4ed5ef24.js` from the new bundle.
- **Backend on EB** (`backend-v18b-final`) — Health **Ok** internally, HTTP :80 responds 404 (no `/` route, expected).
- **BLOCKER · Backend :443 HTTPS listener missing** — env is single-instance, no ALB provisioned. Frontend cannot reach backend from browser until this is fixed.

---

## Next task (parked by user 4 Sep 2026)

**P0 · Enable HTTPS on the backend.** Two paths documented:
- Path A · Convert EB env from Single instance → Load balanced, add :443 listener with ACM cert on the new ALB. ~$16/mo cost.
- Path B · Put CloudFront in front of the single-instance EB with ACM cert in us-east-1 + `api.pmcmanagers.com` Route 53 record + frontend rebuild.

## Backlog (P2/P3)
- P2 · Russian + Kazakh translations of Master Manual v4 (deferred by user).
- P2 · Resend email blast on new backend deployment.
- P2 · Investor exec preview (one-page summary of v4 manual).
- P3 · PayPal + Kaspi Pay real integration (blocked: merchant credentials).
- P3 · Firebase + APNs push (blocked: project ID + Service Account JSON).
- P3 · Live KYC provider (blocked: KYC_BASE_URL + KYC_API_KEY).

---

## Key APIs
- `/api/v1/admin/auth/*` · `/api/v1/vendor/auth/*` · `/api/v1/staff/auth/*`
- `/api/v1/notices` · `/api/v1/registrations` · `/api/v1/vendors` · `/api/v1/bids`
- `/api/v1/committee` · `/api/v1/escrow/*` · `/api/v1/evaluations/*` · `/api/v1/awards/*`
- `/api/v1/tender-templates/*` · `/api/v1/boqs/*` · `/api/v1/permissions/*`
- `/api/v1/dashboard-drill/*` · `/api/v1/stakeholder-reports/*` · `/api/v1/branding`
- `/api/v1/reverse-auctions/*` · `/api/v1/meetings` · `/api/v1/audit`
- `/api/v1/meta/health` — used by Docker HEALTHCHECK.
- `/api/v1/_dl/{token}/{name}` — internal file download.

## Test credentials
See `/app/memory/test_credentials.md`.

## Notes for next agent
- No GitHub auto-push — deliverables via `/api/v1/_dl/{TOKEN}/{name}` route (token: `sVGqLYK9RXjE8UnvXwT-uzDkV5wpdN2GfyAsHIYpQr4`).
- Zero "Emergent" branding in user-facing docs — always use `www.pmcmanagers.com`.
- ESLint bin is broken — remove `/app/frontend/node_modules/.bin/eslint*` before `finish`; DO NOT delete `eslint-scope` (webpack dependency).
- Manual v4 build pipeline: `python3 scripts/seed_manual_v4.py` then `PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python3 scripts/capture_manual_v3.py` then `python3 scripts/build_manual_v3.py`.
- EB env is single-instance (no ALB) — must convert to load-balanced before HTTPS works.
