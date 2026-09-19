# PMC Managers v2 — Product Requirements & Roadmap

Last updated: 19 Feb 2026 — v43 release

## Original Problem Statement
Develop a global tender management application (PMC Managers Limited v2) supporting a full multi-role approval pipeline, dynamic Approval Matrices, Bidding & EMD payments, BOQ Management, Evaluations, Contract Award, Multi-Tenant portals, and an AI Audit Copilot.

Core requirements:
- Roles: Admin, Vendor, Staff
- Core Modules: Notice Board, Registration, Package Tracker, Bidding Management, BOQ Builder, Evaluation & Contracts, Vendor Intelligence, Tender/RFP/RFQ Template Builder, Joint-Signature Escrow
- Monetization/Revenue: Product Catalog, Stripe checkout, Quote pipeline, Subscriptions
- Integrations: Stripe, Emergent LLM (AI Audit Copilot), KYC, Firebase, Resend, Zoom, DocuSign
- Fully white-labeled AWS Deployment (S3 + CloudFront + Elastic Beanstalk Docker)
- Codebase and Git history 100% purged of "Emergent" branding

## What's Live in Production
Deployed on AWS: frontend v41 + backend v22f. In-app Help tab (v42/v22g) packaged and awaiting user deploy. v43 (in progress) builds tooltips + error rollout + granular manual on top.

## v43 — This Release (COMPLETE, packaged awaiting user deploy)

### Tooltips (`<InfoDot />`) — 100% coverage across 26 admin panels
Reusable `<InfoDot tip="..." />` component (`/app/frontend/src/components/InfoDot.jsx`) built on the existing Radix Tooltip primitive. Added to every primary form field, filter and action button across all 26 admin panels:
Notices · Registrations · Vendors · Packages · Bidding-Ops · Escrow (Accounts + Transactions) · Corrigenda · LiveAuctions · Meetings · VendorIntel · L1 Comparison · Awards · DocuSign · BOQ Templates · Contracts · Evaluation · Analytics · Audit · Masters (Staff/Companies/Tenants) · Permissions · Tender Builder · Product Catalog · Engagements · Committee Form · AdminVendorCreate · Escrow Transactions.

### `showApiError()` global rollout — 51 files
Bulk-migrated every `toast.error(formatApiError(e))` to loud `showApiError(e)` via `/app/scripts/apply_show_api_error.py`. Every catch block now surfaces the verbatim backend detail with HTTP status, red left-border and 12s minimum duration. Coverage: admin console + vendor portal + registration portal + committee/staff portals (51 files total).

### Granular per-modal screenshot script
`/app/scripts/capture_manual_v43.py` — Playwright recipe engine that navigates to each admin tab, opens the primary "New X" form / sub-tab / modal, and captures ~35 per-action shots on top of the existing 69 panel-level shots. Ready to run whenever the preview URL admin creds are in place.

### Bug Tracker → v16
`/app/deliverables/PMC_Bug_Tracker_v16_20260919.xlsx` marks tooltips, error rollout and granular manual as ✅ COMPLETE.

## Backlog (P2 — deferred)
- Turkish / Russian / Kazakh translation versions of the Master Training Manual
- Firebase & APNs Push Notifications
- Live KYC provider integration
- PayPal & Kaspi Pay live integrations (currently mocked)
- Route 53 SOA min-TTL update from 86400s to 60s (optional DNS safeguard)
- Fix stale prod data: Joint Escrow Account #1 (manual edit — assign distinct Escrow-officer email to unblock BID-2026-TEST2)

## Deployment Notes
- Frontend production builds MUST set `REACT_APP_BACKEND_URL=""` (relative `/api/*`) — CloudFront routes to Beanstalk.
- Backend AWS zip requires `Dockerfile` + `Dockerrun.aws.json` at the archive root.
- Admin credentials (test): `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor credentials (test): `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Architecture
- `/app/backend` — FastAPI + MongoDB
- `/app/frontend` — React SPA (CRA + Shadcn UI + Radix + Sonner + Framer Motion)
- `/app/scripts` — deployment + docs generation pipelines
- `/app/deliverables` — versioned QA trackers, user manual DOCX/PDF, deployment tarballs

## Key Files (v43 additions)
- `/app/frontend/src/components/InfoDot.jsx` — reusable tooltip pill
- `/app/frontend/src/lib/api.js` — `showApiError()` helper (v42) now wired everywhere
- `/app/scripts/apply_show_api_error.py` — one-shot migration tool
- `/app/scripts/capture_manual_v43.py` — granular Playwright capture
- `/app/scripts/bump_tracker_v16.py` — Bug Tracker v16 generator
- `/app/deliverables/PMC_Bug_Tracker_v16_20260919.xlsx`
