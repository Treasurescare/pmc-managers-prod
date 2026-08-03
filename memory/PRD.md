# PMC Managers Limited v2 — Product Requirements

## Original Problem
Global tender management CRM/e-Tender platform. Multi-role approval pipeline, dynamic
Approval Matrices, Bidding & EMD payments, BOQ, Evaluations, Contract Award, MFA,
Multi-Tenant portals, AI Audit Copilot, KYC integration. Built "for Portability" —
Emergent MVP now, AWS Phase 2 later; also shipped as PWA + Capacitor mobile app.

## User Personas
- **Master Admin** — full RBAC.
- **Staff** — Escrow Agent, Certifier, Legal Counsel, Accounting, Committee, Reviewer, Auditor, Support. High-risk roles must have MFA.
- **Vendor** — self-registers OR admin-invited (magic email, CSV bulk, or **full form fill-in on behalf**).
- **External Committee Invitee** — non-staff experts invited by email.

## Core Modules
- **Wave 1-13** (previous waves) — Auth, Bidding + EMD, Evaluations, BOQ, Contracts, Vendor Intel, Analytics, MFA, Tenants, GDPR, Workflow Matrix, AI Copilot, Permissions Matrix, KYC-Checks client, Registration docs, Mobile PWA + Capacitor scaffold, Unified mobile login `/m`
- **Wave 14 (Prod-parity)** — Fixed `admin@pmcmanagers.com` legacy default in `config.py` (now `adminsupport@pmcmanagers.com`), deleted stale `backend/tests/backend_test.py`, added self-heal endpoint `POST /api/v1/admin/heal/rename-admin` for prod cleanup, added **Unified web login `/login`** (same auto-detect as mobile `/m`), added **Admin creates vendor with full Sections A–E form** at `/admin/vendors/new` with two modes (`activate` immediately with admin-set password OR `verify` via magic-link email). Vendors panel gains "Add & fill full form" button.

## Roadmap

### P0 — Verified this session ✅
- Unified `/login` on web
- Kill `admin@pmcmanagers.com` — config default fixed + heal endpoint + stale test deleted
- Admin fills full Sections A–E registration form for a vendor with activate/verify modes
- **Wave 15 (this fork)** — Fixed unused import lint blocker in AdminVendorCreate.jsx. Expanded trilingual bundle so every FORM FIELD switches EN/RU/KK (Sections A/B/C/D/E, DocSlot, UnifiedLogin, AdminVendorCreate, RegistrationStart, RegistrationResume). Legal-type dropdown options + declaration checkboxes + activation radios + submit buttons all localized. Backend cyclomatic-complexity refactor applied via helper modules: `bids_helpers.py`, new `analytics_helpers.py`, `packages_helpers.py`, `committee_helpers.py`. Verified end-to-end by testing agent (iteration_18) — all backend refactor tests pass; RU + KK verified across login/register/admin-vendor-create pages.

### P1 (Next)
- (Optional polish) Localize country dropdown `<option>` labels — currently returned from backend `/api/v1/meta/countries` in English only. Small enhancement not covered by the trilingual bundle.
- Firebase + APNs setup (needs your `google-services.json` + APNs auth key)
- Live KYC-Checks credentials (need `KYC_BASE_URL` + `KYC_API_KEY`)
- On production: after redeploy, admin can hit `POST /api/v1/admin/heal/rename-admin` to auto-clean the legacy `admin@pmcmanagers.com` row

### P2
- Refactor big frontend components (BiddingOpsPanel, MastersPanel, BOQContractsPanel) — deferred
- Domain-based multi-tenant routing (currently query-string)
- Phase 2 AWS migration

## Deployment Notes
- MongoDB unique indexes MUST use `sparse=True`
- CSRF double-submit on state-changing routes
- Emergent LLM key powers AI Audit Copilot + bid anomaly
- Emergent Email key powers all send_email calls (best-effort if missing)
- `KYC_PROVIDER` env var: `stub` (default) or `kyc-checks` (real)
- **Production self-heal**: after redeploy, hit `POST /api/v1/admin/heal/rename-admin` once to clean the legacy `admin@pmcmanagers.com` row

## Integrations
- Stripe (sandbox key in pod env)
- Emergent LLM key
- Emergent Email
- PyOTP + qrcode (MFA)
- KYC-Checks (real client wired; awaiting credentials)
- Capacitor 8.x (camera, preferences, push-notifications) + biometric-auth
