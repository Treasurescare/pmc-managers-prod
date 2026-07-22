# PMC Managers Limited — Tender Management Platform (PRD)

## Original problem statement
Global tender management application titled **PMC Managers Limited**. Vendors register through a Pre-Tender Registration Form (Sections A–E). Multi-country support with Kazakhstan as primary jurisdiction.

## User personas
- **Vendor** — bidder, completes KYC, bids on tenders after approval.
- **Buyer** — publishes tenders, evaluates bids, awards contracts.
- **Admin / Contracts Committee** — PMC procurement office. Approves vendors, signs off tenders, manages orgs & departments, audits the ledger.

## Deployment
- Preview: `https://tender-hub-57.preview.emergentagent.com`
- Production (deployed): `https://tender-hub-57.emergent.host`

## Core requirements
- Multi-role auth (JWT httpOnly + Emergent Google OAuth)
- Vendor Pre-Tender Registration (Sections A–E per source docx)
- 30 countries, KZ tax/business ID default
- 6 declarations + electronic signature
- KYC uploads
- Tender lifecycle: draft → pending_approval → open → closed/awarded/rejected
- 200+ pre-classified categories
- Bidding + comparison + lowest-bid highlight
- Admin vendor approval + inspector panel
- Notifications (in-app + Resend email)
- Public landing page with live stats

## Version history

### v1.1
Resend emails, Google OAuth, Stripe fee, KZ licenses, CSV export, EN/RU/KK i18n.

### v1.5 — Live Feed
- Right-rail Tender Feed on **Server-Sent Events** (`/api/feed/stream`)
- Filter chips: All/RFP/RFQ/Tender/My country/Unread
- Per-user read/unread + mark-all-read
- Higher-contrast time-remaining chip
- Async email fan-out

### v1.6 — Two-envelope Sealed Bidding
- RFP `two_envelope: bool`; commercial fields hidden until buyer opens envelopes
- `/tenders/{id}/open-technical`, `/open-commercial`, `/bids/{id}/qualify`
- Award blocked on 2-envelope until commercial opened AND bid qualified
- UI: 3-stage envelope panel + qualify/reject + sealed price cells

### v1.7 — Governance & Collaboration (P1)
- Multi-level approval workflow driven by department budget thresholds
- Buyer Orgs + Departments hierarchy (seeded PMC-GLOBAL, MED, GEN)
- Pre-bid Q&A with vendor anonymization + buyer-published answers
- Corrigendum / Addenda publisher with vendor notifications
- EMD (Earnest Money Deposit) with real Stripe refund on losing bids
- 42/42 backend tests pass

### v1.8 — Code Quality Pass
- TenderFeed split into FeedFilters + FeedItem sub-components
- All empty catches now log via `console.warn`
- All useEffect hook-dep warnings resolved
- Frontend compiles with **0 eslint warnings**

### v1.9 — Deploy Hardening
- All list endpoints have `limit` (default 200, max 500)
- N+1 removed from `/api/bids` (single `$in` batch)
- Feed unread-count uses single count query (no Python loop)
- CORS env-driven (`CORS_ORIGINS=*`)
- Deployment agent: **PASS**

### v2.0 — P2 Green + Orange
- **SBD Template Library**: admin uploads .docx/.pdf templates at `/admin/sbd`; buyers pick via `ct-sbd-template` dropdown; auto-attaches to tender.
- **FX Conversion**: `/api/fx/rates`, `/api/fx/convert` (open.er-api.com, no API key, 6h cache). `FxChip` on TenderDetail shows budget in local currency with selectable target.
- **Immutable Audit Trail**: SHA-256 hash-chained `audit_events` collection. Hooks: tender.create, tender.approve, tender.reject, tender.addendum, tender.qa_answer, bid.award, bid.emd_refund, sbd.template.create, sbd.template.archive. Admin viewer at `/admin/audit` + `Verify chain integrity` button. Tampering detection verified via Mongo mutation + rollback (28/28 tests).
- **Vendor KPI Dashboard** at `/vendor/kpi`: win-rate, total bids, avg price, avg delivery, EMD forfeit/refund count, by-category last-12-months bar chart, suggestions.
- **Admin UI for Orgs & Departments** at `/admin/orgs`: create orgs, create departments with budget-driven approval thresholds.

## Test status
- Latest run: `iteration_10.json` — 28/28 P2 backend + full P2 frontend + 9/9 auth/health regression
- Full history: `iteration_1.json` … `iteration_10.json`

## Backlog (remaining P2 items)
- **Twilio SMS + WhatsApp** — needs Twilio Account SID + Auth Token + WhatsApp sender
- **DSC / eSign + PDF watermarking** — X.509 signing + PDF-lib (own iteration)
- **server.py refactor into /app/backend/routers/*** — mentioned but deferred until server.py > 2500 lines (currently 1948)
- **Approver as its own role** (currently piggybacks on admin)
- **Two-envelope SSE events** — broadcast envelope state changes so all viewers see live
- **Public tender board** (no login) with SSE + SEO

## Test credentials
See `/app/memory/test_credentials.md`.
