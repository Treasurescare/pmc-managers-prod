# PMC Managers v2 · Product Requirements Document (Feb 2026)

## Original Problem Statement
Develop a global tender management application (PMC Managers Limited v2) supporting a full
multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ
Management, Evaluations, Contract Award, Multi-Tenant portals, and an AI Audit Copilot.

### Product Requirements
- **Roles**: Admin, Vendor, Staff (Escrow / Certifier / Legal / Accounting / Committee)
- **Core Modules**: Notice Board, Registration, Package Tracker, Bidding Management,
  BOQ Builder, Evaluation & Contracts, Vendor Intelligence, Tender/RFP/RFQ Template
  Builder, Joint-Signature Escrow
- **Monetization**: Product Catalog, Stripe checkout, Quote pipeline, Subscriptions
- **Integrations**: Stripe, Emergent LLM (AI Audit Copilot), KYC, Firebase, Resend, Zoom, DocuSign
- **CRITICAL**: Fully white-labeled AWS deployment. Zero "Emergent" branding in shipped code
  or Git history (investor code review)

## Architecture
- **Frontend**: React + CRACO, Shadcn UI, Tailwind, `sonner` toasts, i18n (EN/RU/KK)
- **Backend**: FastAPI + Motor (async MongoDB), Pydantic v2 models, cookie-based auth
  with CSRF double-submit-cookie
- **Deployment (production)**:
  - S3 + CloudFront serves the frontend (same-origin `/api/*` proxied to Elastic Beanstalk)
  - Elastic Beanstalk (eu-west-2) runs the FastAPI backend
  - Route 53 zone: `pmcmanagers.com` (apex 301→www CloudFront function)
  - MongoDB Atlas cluster

## Live production versions (Sep 2026)
- Frontend: **v36** (`main.99352d45.js`) — same-origin architecture
- Backend: **v22d** (`Cache-Control: no-store` on `/admin/all`)
- CloudFront function: `cf-function-apex-to-www.js` (301 redirect)

## Preview versions (pending AWS push)
- Frontend: **v40** — Batches #9 + #9b + #9c + #9d
- Backend: **v22f** — Batches #9 (evaluations validation) + #9c (escrow governance)

## Batches shipped locally, awaiting AWS deploy
| Batch | Type | Changes |
|-------|------|---------|
| #9 (v37/v22e) | 11 tracker items | #15, #20, #21, #28, #29, #30, #46, #49, #52, #63, #76, #84 |
| #9b (v38) | Hotfix | Committee dissolve/create CSRF fix |
| #9c (v39/v22f) | Hotfix | Escrow same-email governance guard |
| #9d (v40) | UX | Loud, verbatim error handling across escrow / committee / bidding |

## Backlog (P2, optional)
- Route 53 SOA min-TTL 86400 → 60
- Master Training Manual TR/RU/KK translations
- i18n coverage for remaining admin panels (BOQContractsPanel, EscrowPanel, PackagesPanel, AwardsPanel, LiveAuctionsPanel, MeetingsPanel, L1ComparisonPanel, DocuSignPanel, EngagementsPanel, PermissionsPanel, ProductCatalogPanel, TenderBuilderPanel)
- Firebase FCM + APNs push notifications (dev only)
- Live KYC provider (currently mocked)
- PayPal + Kaspi Pay live integration (currently mocked)
- Phase-2 vendor KPI (win-rate, avg turnaround, packages awarded)
- Advanced Vendor Intel: sanctions-list webhook feed
- AI Audit Copilot: cross-tender anomaly detection (batch mode)

## Test credentials
Live in `/app/memory/test_credentials.md`. Admin `adminsupport@pmcmanagers.com` /
`Admin@12345`. Vendor `manualvendor@pmcmanagers.com` / `Vendor@12345`.
