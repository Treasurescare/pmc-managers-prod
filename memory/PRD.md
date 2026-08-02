# PMC Managers Limited v2 — Product Requirements

## Original Problem
Global tender management CRM/e-Tender platform mirroring a 39-page Enterprise Report.
Multi-role approval pipeline (Escrow, Certifier, Legal, Accounting), dynamic
Approval Matrices, Bidding & EMD payments (Stripe/PayPal/Kaspi), BOQ Management,
Evaluations, Contract Award, MFA for staff, Multi-Tenant portals, AI Audit Copilot.
Built "for Portability" — Emergent MVP now, AWS Phase 2 (PostgreSQL RLS, S3 Object
Lock, Cognito, Fargate) later.

## User Personas
- **Master Admin** — PMC executive; full RBAC.
- **Staff (specialist roles)** — Escrow Agent, Certifier, Legal Counsel, Accounting, Committee Member, Reviewer, Auditor, Support. High-risk roles must have MFA.
- **Vendor** — Corporate supplier; either self-registers via /register or is invited by admin.
- **External Committee Invitee** — Non-staff experts invited by email for a specific tender's evaluation committee.

## Core Modules

### Wave 1 — Auth + Bidding + EMD
- Admin console, Vendor portal, Staff portal (multi-role login)
- HTTPOnly cookie auth + double-submit CSRF
- Bidding pipeline: submit → EMD pending → EMD paid → Escrow → Admin → Certifier → Legal → Accounting → Committee → Awarded
- Stripe checkout (live sandbox) + PayPal/Kaspi (in-app sandbox)

### Wave 2-6 — Evaluation, BOQ, Contracts, Vendor Intel, Analytics
- Technical/Commercial two-envelope evaluations
- BOQ builder + Contracts + Milestones
- Vendor Intel dashboard (per-vendor KPI)
- Analytics + AI bid-anomaly

### Wave 7 — MFA + Tenants + GDPR
- TOTP MFA (PyOTP + QR)
- Tenant master (multi-portal)
- GDPR right-to-be-forgotten (admin + vendor self-service)
- Dynamic Workflow Matrix (drag editor)

### Wave 8 — AI Copilot, MFA Enforcement, KYC Stub, Tenant Skin
- AI Audit Copilot in admin header — reviews any bid's workflow_history + LLM narrative
- **High-risk role MFA enforcement** — escrow_agent / legal_counsel / accounting BLOCKED at login until MFA enabled
- **GDPR self-service** on vendor portal
- **Matrix-driven Bidding Ops** — active_step column + gated Admin-Flag button
- **Tenant portal skinning** — `?tenant=CODE` query string, sessionStorage persistence
- **KYC stub** — swap-ready connector (Sumsub / Onfido / KYC-Checks)

### Wave 9 — Admin Vendor Invites + Doc Uploads + RBAC Matrix + External Committee
- **Admin invites vendors**: `POST /api/v1/vendors/invite` → magic-link email → `/vendor/verify/{token}` → password set → active.
- **Registration form template**: admin uploads a blank PDF/DOCX template that vendors can download for reference.
- **Notice documents**: primary PDF + multiple attachments per tender/RFP/RFQ, uploaded during creation.
- **Permissions Matrix**: 9 roles × 5 actions × doc_type — configurable via `Permissions` tab, enforced server-side on all `/notices` mutations.
- **Committee — designation + external invitees**: staff picker shows `email — designation`; external experts get an email invite with tender no + budget + deadline + accept/decline link.

## Roadmap

### P0 (Next)
- KYC-Checks (or Sumsub/Onfido) live integration — swap the stub in `/app/backend/routers/kyc.py`
- Deployment retest after Wave 9

### P1
- Vendor portal — download registration template button on registration start page
- Public notice detail — surface primary_document + attachments to vendors
- Committee dashboard — show external invitee acceptance status
- Domain-based multi-tenant routing (currently query-string only)

### P2
- Refactor AdminDashboard.jsx (559 lines) into smaller panel files
- Analytics option/span dev warning (cosmetic — ve-dynamic wrapping)
- Phase 2 — AWS migration (PostgreSQL RLS, S3 Object Lock, Cognito, Fargate)

## Deployment Notes
- MongoDB unique indexes must use `sparse=True` — enforced in `db.py`. Any new model with a unique index MUST follow this or deployments will fail with DuplicateKeyError.
- CSRF double-submit is enforced on all state-changing routes. Frontend must send `X-CSRF-Token` header from the csrf_token cookie.
- Emergent LLM key powers AI Audit Copilot + bid anomaly (`openai/gpt-4o-mini` model).
- Emergent Email key powers all send_email calls; if missing, emails are skipped silently (best-effort).

## Integrations
- Stripe (production sandbox key in pod env)
- Emergent LLM key (Audit Copilot, bid anomaly)
- Emergent Email
- PyOTP + qrcode (MFA)
- KYC-Checks / Sumsub / Onfido — pending real credentials, currently stub
