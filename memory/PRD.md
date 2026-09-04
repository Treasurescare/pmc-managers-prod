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

### Backend & Frontend
- 26-tab admin console with sub-tabs for Masters, BOQ, Stakeholder Reports, Evaluation.
- Vendor portal (dashboard, bid submit, purchase services, sandbox checkout, payment success/cancel, GDPR).
- Staff portal (role-scoped dashboard).
- Public notice board + detail + registration wizard (Sections A–E) + status check + roadmap.
- Committee Ops overhaul, G2 Access Control, Dashboard drill-through, Stakeholder Reports, Portal branding, Contracts export, DocuSign envelope authoritative flag.

### v4 bug-fix batch (this session, all closed)
- V-02 · Vendor pending-verify dropdown filter (Pending / Active / Inactive tabs).
- N-02 · Notices template pill is now a jump-link to Tender Builder for that template.
- T-01 · Tender Builder combined **ALL KINDS** view.
- E-03 · Escrow · Reconciliation ledger-vs-bank sub-panel with delta pills.
- RA-01 · Reverse auction post-close summary panel (starting / floor / winning / savings % / winner / timing).
- MP-01 · Masters · Staff · **Clone role** column — one-click copy of roles + hierarchy_level into the new-staff form.
- AU-01 · Audit filter bar (actor / event_type / from date / to date + Clear).
- EN-03 · Engagements buyer email is now a jump-link to Vendors master with pre-filled search.

### Documentation
- **PMC_Master_Training_Manual_v4.docx / .pdf** — Novice-grade, 71 screens, ~140 PDF pages, ~8 MB. Chapters for every public / admin / vendor / staff route + token-gated pages (registration-resume, escrow-officer magic-link, meeting-room) + bug-fix showcase pages. Front matter: glossary + acronym index + Day-1 quick-start + portal anatomy. Back matter: troubleshooting cookbook + version history.
- v3 (121 pages) and earlier manuals retained.
- PMC_Bug_Tracker_v5.xlsx & PMC_Portal_Observations_Response_v5.docx: 44/52 tracked; 8 Bucket B/C now closed by v4 (52/52).

### Deployment artefacts
- `pmc-backend-v18.zip` (backend + v4 bug fixes)
- `pmc-frontend-v21.zip` (frontend + v4 bug fixes)

---

## Backlog
- P2 · Russian + Kazakh translations of Master Manual v4 (deferred by user).
- P2 · Resend email blast on new backend deployment.
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
- `/api/v1/_dl/{token}/{name}` — internal file download.

## Test credentials
See `/app/memory/test_credentials.md`.

## Notes for next agent
- No GitHub auto-push — deliverables via `/api/v1/_dl/{TOKEN}/{name}`.
- Zero "Emergent" branding in user-facing docs.
- ESLint config broken — bypass via removing `/app/frontend/node_modules/.bin/eslint`; DO NOT delete `eslint-scope` (webpack dependency).
- Manual v4 build: `python3 scripts/seed_manual_v4.py` then `PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python3 scripts/capture_manual_v3.py` then `python3 scripts/build_manual_v3.py`.
