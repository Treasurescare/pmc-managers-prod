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
- **Wave 22 (this iteration)** — **Sign-in hub redesign**: `/login` now shows **two clearly labelled cards**: a navy "PMC TEAM · Employee sign-in" (Admin + Escrow + Certifier + Legal + Accounting + Committee + Reviewer + Auditor + Support) and a green "VENDOR / SUPPLIER · Vendor sign-in" with a prominent Register-your-company link. TopBar nav renamed the old **Admin** entry to **Sign in** pointing at `/login`. Full trilingual (EN/RU/KK) copy for badges, card titles, sub-copy, submit buttons and role list. Playwright screenshots confirm desktop side-by-side + mobile stacked.
- **Wave 21** — Upload 500 fixed + admin-side uploads inside "Add & Fill Vendor" with draft banner
- **Wave 20** — Tender / RFP / RFQ Template Builder with 18 seeded PSU sections
- **Wave 18/19** — Mobile hamburger drawer + Sign Out + CNAME multi-tenant + code review r2

### P1 (Next)
- **Deploy Refresh** — user needs to click "Save to Github" + "Deploy" so Waves 15–18 land in production, then hit `POST /api/v1/admin/heal/rename-admin` once to purge the legacy `admin@pmcmanagers.com` row from prod
- **Firebase + APNs** — waiting for `google-services.json` + APNs auth key
- **Live KYC-Checks** — waiting for `KYC_BASE_URL` + `KYC_API_KEY`
- **Admin UI for subdomain/host_alias** — currently editable via API only; add fields to the `MastersPanel > Tenants` form so admins can set CNAME aliases from the UI (P2)

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
