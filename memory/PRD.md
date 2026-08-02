# PMC Managers Limited v2 — Product Requirements

## Original Problem
Global tender management CRM/e-Tender platform. Multi-role approval pipeline, dynamic
Approval Matrices, Bidding & EMD payments (Stripe/PayPal/Kaspi), BOQ, Evaluations,
Contract Award, MFA, Multi-Tenant portals, AI Audit Copilot. Built "for Portability" —
Emergent MVP now, AWS Phase 2 later.

## User Personas
- **Master Admin** — full RBAC.
- **Staff** — Escrow Agent, Certifier, Legal Counsel, Accounting, Committee Member, Reviewer, Auditor, Support. High-risk roles must have MFA.
- **Vendor** — Self-register or admin-invited.
- **External Committee Invitee** — Non-staff experts invited by email.

## Core Modules
- **Wave 1** — Auth (HTTPOnly cookies + CSRF), Bidding, EMD (Stripe live + PayPal/Kaspi sandbox), staff/vendor portals
- **Wave 2-6** — Two-envelope evaluations, BOQ, Contracts, Vendor Intel, Analytics + AI bid anomaly
- **Wave 7** — TOTP MFA, Tenants master, GDPR endpoints, dynamic Workflow Matrix
- **Wave 8** — AI Audit Copilot, high-risk role MFA enforcement, GDPR self-service, matrix-driven Bidding Ops, tenant portal skinning (`?tenant=CODE`), KYC stub
- **Wave 9** — Admin vendor invites + verify-email + registration form template, notice document uploads (primary + attachments), Permissions Matrix (9 roles × 5 actions), external committee invitees with email accept/decline
- **Wave 10** — **KYC-Checks live client** (env-driven; falls back to stub if creds missing) · **Public notice detail** now surfaces primary_document + attachments to vendors · **Registration document slots** — 12 canonical upload slots across Sections A–D (incorporation cert, address proof, TIN, audited financials, previous works, ISO, licenses, articles of incorporation, bank ref, POA, other, signed declaration) with view/download/delete · **Vendor template download** on `/register` · **Committee Status Dashboard** shows accepted/declined/pending per external invitee

## Roadmap

### P0 (Next)
- Live KYC-Checks credentials — user needs to share `KYC_BASE_URL` + `KYC_API_KEY` in backend/.env (currently `KYC_PROVIDER=stub` fallback active)
- Public-side download of committee acceptance status per committee (admin already sees it)

### P1
- Refactor AdminDashboard.jsx (600+ lines) into smaller panel files
- Analytics option/span dev warning (cosmetic React hydration)
- Domain-based multi-tenant routing (currently query-string only)

### P2
- Phase 2 — AWS migration (PostgreSQL RLS, S3 Object Lock, Cognito, Fargate)
- Real KYB corporate/UBO integration (if KYC-Checks doesn't cover)

## Deployment Notes
- MongoDB unique indexes MUST use `sparse=True` — see `db.py`
- CSRF double-submit enforced on state-changing routes
- Emergent LLM key powers AI Audit Copilot + bid anomaly
- Emergent Email key powers all send_email calls (best-effort if missing)
- KYC_PROVIDER env var: `stub` (default) or `kyc-checks` (real)

## Integrations
- Stripe (sandbox key in pod env)
- Emergent LLM key
- Emergent Email
- PyOTP + qrcode (MFA)
- KYC-Checks (real client wired; awaiting credentials to flip out of stub)
