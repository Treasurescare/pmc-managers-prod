# PMC Managers Limited — v2 Product Requirements Document

**Legacy:** v1 archived at GitHub `pmc-tender-v1-legacy` tag `v1.0`
**Current build:** v2 (this workspace) → target repo `Treasurescare/pmc-tender-v2-aws`
**Strategy:** "Build for Portability" — build on Emergent stack now, structure exactly per AWS Build Sheet v2 for a low-cost Phase 2 migration to PostgreSQL + Cognito + S3 Object Lock + Fargate.

**Scope pivot (Feb 2026):** User adopted Option C — build the **full enterprise CRM + e-Tender platform** per the revised report `PMC_Managers_Enterprise_CRM_eTender_Revised_Integrated_Report.pdf`. See `/app/memory/ENTERPRISE_ROADMAP.md` for the 6-wave delivery plan.

---

## Governing documents

1. **PMC Enterprise CRM & e-Tender Revised Integrated Report** (Feb 2026) — full-scope target
2. **PMC Transaction Structure & Funds-Flow Report** (Jul 2026) — funds-flow legal framework
3. **PMC Build Sheet v2 AWS** (Jul 2026) — technical architecture (portability target)
4. **Domain_Spec.md** — extracted business rules from v1
5. **BA_Gap_Analysis.pdf** — v1 vs v2 gap comparison for client
6. **design_guidelines.md** — Navy Trust visual language

## Core apps

| App | Name | Stack (v2 Phase-1 pilot) | Stack (Phase 2 AWS) |
|---|---|---|---|
| **App 1** | Milestone Evidence Capture (mobile) | Deferred | React Native + S3 |
| **App 2** | Package Tracker + Admin Console (BIDDING OPS) | React admin panel | Retool + RDS |
| **App 3** | Pre-Tender Registration Portal | React + FastAPI + Mongo | React + FastAPI + RDS + Cognito |
| **App 4** | Public Tender Notice Board | React SPA | Next.js SSR + RDS |
| **App 5** | Vendor Portal (Wave 1) | React + cookie auth | + Cognito |
| **App 6** | Staff Portal — multi-role (Wave 1) | React + cookie auth | + Cognito |

## Roles (Wave 1)

`admin`, `reviewer`, `escrow_agent`, `certifier`, `legal_counsel`, `accounting`, `committee_member`, `auditor`, `support`. Staff records hold a LIST of roles; on login user picks active role.

## Wave-1 API endpoints (added Feb 2026)

- `POST /api/v1/staff/auth/{login,logout}`, `GET /api/v1/staff/auth/me`, `GET /api/v1/staff/roles`
- `GET|POST|PATCH /api/v1/staff/{id?}` — staff master
- `POST /api/v1/vendor/auth/{login,logout,change-password}`, `GET /me`
- `POST|GET /api/v1/bids`, `GET /api/v1/bids/mine`, `POST /api/v1/bids/{id}/decision`, `POST /api/v1/bids/{id}/assign-certifier`, `POST /api/v1/bids/{id}/withdraw`
- `POST /api/v1/payments/emd/checkout`, `GET /api/v1/payments/status/{sid}`, `POST /api/webhook/stripe`, `POST /api/v1/payments/emd/refund`
- `POST|GET /api/v1/committees`, `POST /vote`, `POST /close`, `POST /{id}/deadline-close`
- `CRUD /api/v1/tasks` + `/api/v1/tasks/{id}/followups`
- `POST|GET|DELETE /api/v1/chat/messages`
- `POST|GET|PATCH /api/v1/inspections` + `/media` add/delete
- `CRUD /api/v1/masters/{companies,roles,approval-matrices}`

## What's been implemented

**2026-01 — v2 foundation:** Modular routers, httpOnly cookies + CSRF, App 3 (Sections A–E), App 4 (Notice Board), App 2 (Kanban + CSV importer), Vendor KPI dashboard, i18n EN/RU/KK, audit chain.

**2026-02 — Wave 1 (Bidding & Financial Core):**
- 9 new backend routers + 9 new Pydantic model files
- Vendor Portal (5 screens): login, change-password, dashboard, bid submit, payment result
- Staff Portal (2 screens): unified login with role dropdown, role-aware dashboard (bid queue + certifier inspection panel)
- Admin Console: new **Bidding Ops** tab with bid queue, filter, committee builder, certifier assignment modal
- Notice creation: added EMD Fixed + Percentage fields
- Stripe Flow B integration (`sk_test_emergent`, webhook `/api/webhook/stripe`)
- Sequential approval pipeline enforced by state machine + role guard
- Bid Committee (per-tender, chair + members + quorum + vote + close)
- Site Inspection (assign, schedule, media upload, pass/fail)
- CRM Tasks + Followups + Internal Chat with attachments
- Masters: Company, Role, Approval Matrix CRUD
- Owner account switched to `kannan@emeraldcorporates.com`
- 34/34 backend pytest passing (wave1_test.py); frontend flows verified

## Backlog (P0 → P3)

- **P0 · Wave 2:** Multi-envelope bidding, evaluation scoring, award recommendation
- **P1 · Wave 3:** BOQ builder, contract management, multi-currency
- **P1 · Wave 4:** CRM masters UI, Vendor Intelligence, workflow engine, helpdesk
- **P2 · Wave 5:** BI/AI, integration gateway, PayPal + Kaspi
- **P2 · Wave 6:** MFA, GDPR, auctions, subscription, sandbox

## Test credentials

See `/app/memory/test_credentials.md`. Owner: `kannan@emeraldcorporates.com / Admin@123`.
