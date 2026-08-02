# PMC Managers Limited v2 — Product Requirements

## Original Problem
Global tender management CRM/e-Tender platform. Multi-role approval pipeline, dynamic
Approval Matrices, Bidding & EMD payments, BOQ, Evaluations, Contract Award, MFA,
Multi-Tenant portals, AI Audit Copilot. Built "for Portability" — Emergent MVP now,
AWS Phase 2 later.

## User Personas
- **Master Admin** — full RBAC.
- **Staff** — Escrow Agent, Certifier, Legal Counsel, Accounting, Committee, Reviewer, Auditor, Support. High-risk roles must have MFA.
- **Vendor** — self-registers or admin-invited (single or CSV bulk).
- **External Committee Invitee** — non-staff experts invited by email.

## Core Modules
- **Wave 1-7** — Auth (HTTPOnly + CSRF), Bidding + EMD (Stripe/PayPal/Kaspi), Evaluations, BOQ, Contracts, Vendor Intel, Analytics, MFA, Tenants, GDPR, Workflow Matrix
- **Wave 8** — AI Audit Copilot, high-risk role MFA enforcement, GDPR self-service, matrix-driven Bidding Ops, tenant portal skinning (`?tenant=CODE`), KYC stub
- **Wave 9** — Admin vendor invites + verify-email + registration form template, notice document uploads (primary + attachments), Permissions Matrix (9 roles × 5 actions), external committee invitees
- **Wave 10** — KYC-Checks live client (env-driven, stub fallback), Public notice attachments visible to vendors, Registration document slots (12 KYC upload slots across Sections A–D with view/download/delete), Vendor template download on `/register`, Committee Status Dashboard, **Slot Completion Meter** (progress bar + "N/M required" badge), **Admin Registration Document Viewer** (uploaded docs listed in review panel), **Bulk Vendor Invite** (CSV paste → per-row status)
- **Wave 11 (Quality)** — Code-review sweep: XSS fix in NotificationBell, test creds → env vars, `is True/False` → `== True/False`, array-index-key fixes across 6 flagged components, MastersPanel default password → empty

## Roadmap

### P0 (Next)
- Live KYC-Checks credentials — user to share `KYC_BASE_URL` + `KYC_API_KEY`; env-var scaffolding already wired

### P1
- Extract oversized panels (BiddingOpsPanel, MastersPanel, BOQContractsPanel, AdminDashboard nested panels) into standalone files with custom hooks
- Backend complexity reduction: extract helpers from decide_bid, audit_copilot, award_report, import_packages_csv, create_committee
- React exhaustive-deps enforcement — add missing deps or explicit `// eslint-disable` where intentional
- Domain-based multi-tenant routing (currently query-string only)

### P2
- Phase 2 — AWS migration (PostgreSQL RLS, S3 Object Lock, Cognito, Fargate)
- Real KYB corporate/UBO integration (if KYC-Checks doesn't cover)

## Deployment Notes
- MongoDB unique indexes MUST use `sparse=True` (see `db.py`)
- CSRF double-submit on state-changing routes
- Emergent LLM key powers AI Audit Copilot + bid anomaly
- Emergent Email key powers all send_email calls (best-effort if missing)
- `KYC_PROVIDER` env var: `stub` (default) or `kyc-checks` (real)

## Integrations
- Stripe (sandbox key in pod env)
- Emergent LLM key
- Emergent Email
- PyOTP + qrcode (MFA)
- KYC-Checks (real client wired; awaiting credentials to flip out of stub)
