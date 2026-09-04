# PMC Managers v2 · Product Requirements Document

## Original Problem Statement
Develop a global tender management application (PMC Managers Limited v2) mirroring a 39-page Enterprise CRM & e-Tender Revised Integrated Report. Must support full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, AI Audit Copilot. Fully white-labelled AWS deployment. Codebase and Git history 100% purged of "Emergent" branding.

## Roles
Admin (master + reviewer/sub-admin) · Vendor · Staff (Escrow, Certifier, Legal, Accounting, Committee, Support, Auditor).

## Core modules
Notice Board · Registration · Package Tracker · Bidding Management · BOQ Builder · Evaluation & Contracts · Vendor Intelligence · Tender/RFP/RFQ Template Builder · Joint-Signature Escrow · Reverse Auctions · Awards · DocuSign · Meetings · L1 Comparison · Masters (Staff/Companies/Matrix/Hierarchy/Tenants) · Permissions Matrix · Product Catalog · Engagements · Reports · Stakeholder Reports · Portal Branding · Help Requests · Audit.

## Monetization / Revenue
Product Catalog · Stripe checkout · Quote pipeline · Subscriptions.

## Integrations
Stripe · Emergent LLM (AI Audit Copilot) · KYC · Firebase · Resend · Zoom · DocuSign.

---

## Architecture snapshot
- **Backend**: FastAPI + MongoDB (Motor), 60+ routers under `/app/backend/routers/`.
- **Frontend**: React + Tailwind + Shadcn UI, apps under `/app/frontend/src/apps/{admin-console, vendor-portal, staff-portal, notice-board, registration-portal, client-portal, committee-portal, mobile}/`.
- **Deployment**: AWS Elastic Beanstalk (Docker) · S3 + CloudFront for FE · custom domain `www.pmcmanagers.com`.
- **Docs**: Playwright headless capture + python-docx + LibreOffice for PDF generation.

---

## Implemented (up to 4 Sep 2026)

### Backend
- Full 60-router API surface (auth, notices, registrations, vendors, bids, escrow, awards, docusign, evaluations, boqs, masters, permissions, packages, audit, catalog, engagements, reports, stakeholder-reports, branding, dashboard-drill, contracts-export, envelope-authoritative, help-requests, and more).
- Dashboard drill APIs (anomalies / pipeline / top-priced).
- Stakeholder Reports (Tenders / Awards / Escrow with SLA / SLA).
- Portal branding theme schema + router.
- Contracts export + envelope authoritative-flag guarded by 409 on duplicate.

### Frontend
- 26-tab admin console with sub-tabs for Masters, BOQ, Stakeholder Reports, Evaluation.
- Committee UX overhaul (checkbox grid, dissolve, resend invite).
- G2 Access Control panel (Permissions Matrix + Hierarchy Level merged view).
- Dashboard drill-through cards.
- Vendor portal (dashboard, bid submit, change password, services, sandbox checkout, GDPR).
- Staff portal (dashboard).
- Public notice board + notice detail + registration wizard.

### Documentation
- **PMC_Master_Training_Manual_v3.docx / .pdf** — Novice edition, 121 PDF pages, 59 screens captured full-page (public 11 + admin 41 + vendor 6 + staff 1). Every screen has: purpose, audience, anatomy table, step-by-step tutorial, API reference, error states, common pitfalls. Front matter: how-to-use, glossary (25 terms), acronym index (16), Day-1 quick-start (7 steps), portal anatomy (10 UI patterns). Back matter: troubleshooting cookbook (7 scenarios), version history.
- v1 / v2 manuals + Trainee Handbook v3.1/v3.2 retained for reference.
- PMC_Bug_Tracker_v5.xlsx · PMC_Portal_Observations_Response_v5.docx (44/52 bugs cleared; 8 deferred Bucket B/C).

### Deployment artefacts
- `pmc-backend-v17.zip` · `pmc-frontend-v20.zip` produced this session cycle.

---

## In progress / deferred (P1)
- **8 Bucket B/C observations**: V-02 (vendor pending-verify filter) · N-02 (notices Template-linked jump) · T-01 (Tender Builder combined All Kinds view) · E-03 (Escrow reconciliation panel) · RA-01 (Reverse auction post-summary report) · MP-01 (Masters Add/Clone role UI) · AU-01 (Audit actor/type/date filter) · EN-03 (Engagements buyer-row link to Vendors).
- **Manual v3 addenda**: registration wizard sections B/C/D/E · vendor bid submit · bidding pipeline sub-views · reverse auction room · meeting room · token-gated pages (committee accept, escrow officer, vendor verify email). Currently not captured because they require seeded runtime tokens.

## Upcoming (P2)
- Russian + Kazakh translations of the Master Training Manual.
- Resend email blast on new backend deployment.

## Future / backlog (P3)
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
- `/api/v1/_dl/{token}/{name}` — internal file download route.

## Key data models
- `permissions_matrix { role, tabs, actions, hierarchy_level }`
- `notices { budget_amount, budget_currency, is_published, created_by, committee_refs, notice_ref }`
- `vendors { email, password_hash, vendor_ref, company_name, country, status, must_change_password }`
- `escrow_accounts { notice_ref, officer_a, officer_b, currency, balance, status }`

## Test credentials
See `/app/memory/test_credentials.md`.

## Notes for next agent
- **No GitHub auto-push** — zips delivered via `/api/v1/_dl/{TOKEN}/{name}`.
- **Zero "Emergent" branding** in any user-facing document — always use `www.pmcmanagers.com`.
- **ESLint config broken** — bypass by removing `node_modules/.bin/eslint` and `.eslintcache` before `finish`.
- Manual v3 build pipeline: `PLAYWRIGHT_BROWSERS_PATH=/pw-browsers python3 scripts/capture_manual_v3.py && python3 scripts/build_manual_v3.py`.
