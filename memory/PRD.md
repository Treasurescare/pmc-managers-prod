# PMC Managers Limited — v2 Product Requirements Document

**Master Admin:** `adminsupport@pmcmanagers.com` / `Admin@123`
**Preview URL:** `REACT_APP_BACKEND_URL` in `/app/frontend/.env`
**Current status:** All 6 Enterprise Waves shipped in Feb 2026. Backend 63/63 tests green (Wave 1: 34, Wave 2-6: 29). Deferred items in `/app/memory/ENTERPRISE_ROADMAP.md`.

## Scope

Full enterprise CRM + e-Tender platform per `PMC_Managers_Enterprise_CRM_eTender_Revised_Integrated_Report.pdf`. Six delivery waves, all shipped:

| Wave | Scope | Status |
|---|---|---|
| 1 | Bidding & Financial Core | 🟢 |
| 2 | Evaluation Engine | 🟢 |
| 3 | Contract & BOQ | 🟢 |
| 4 | Vendor Intelligence + Masters UI | 🟢 |
| 5 | Intelligence & Integrations | 🟢 |
| 6 | Governance (auctions, helpdesk) | 🟢 |

## Roles

`admin`, `reviewer`, `escrow_agent`, `certifier`, `legal_counsel`, `accounting`, `committee_member`, `auditor`, `support`. Staff records carry a LIST of roles; login picks active role.

## Apps

- **Admin Console** (`/admin`) — 11 tabs: Dashboard · Registrations · Vendors · Notices · Bidding Ops · Evaluation · BOQ & Contracts · Vendor Intel · Masters · Packages · Audit. NotificationBell in header (polls /notifications every 20s).
- **Vendor Portal** (`/vendor/*`) — login, forced first-login password change, tender browse, bid submit (PDF uploads), Stripe EMD checkout, payment result.
- **Staff Portal** (`/staff/*`) — single login with role dropdown, role-aware queue dashboard, certifier site-inspection with photo/video upload.
- **Public Notice Board** (`/`) + **Registration Portal** (`/register`) — unchanged from Wave 1.

## Key API groupings (`/api/v1/*`)

- Auth: `admin/`, `staff/`, `vendor/` (httpOnly cookies + CSRF)
- Bidding: `bids`, `payments/emd`, `committees`
- Evaluation: `evaluations/{rubric,coi,score,award-report,lock-envelope}`
- BOQ + Contracts: `boq/templates`, `boq/submissions`, `boq/compare`, `contracts`
- Vendor Intel: `vendor-intel/{ratings,blacklist,watchlist,esg,summary}`
- Analytics + AI: `analytics/dashboard`, `analytics/ai/bid-anomaly/{id}`
- Governance: `auctions`, `support/tickets`
- Cross-cutting: `notifications`, `tasks`, `chat`, `inspections`, `masters/{companies,roles,approval-matrices}`
- Webhook: `POST /api/webhook/stripe`

## Test credentials

See `/app/memory/test_credentials.md`.

## Deferred backlog (post-launch)

- PayPal + Kaspi payment gateways
- MFA (TOTP), GDPR consent flow
- Sanctions screening, ML duplicate-bid detection
- Subscription monetisation for vendors
- Configurable workflow-engine UI (approval_matrix backend done)
- Multi-tenant Corporate / Government CRM portals
- Phase 2: AWS migration (Cognito, RDS Postgres, S3 Object Lock, Fargate)
