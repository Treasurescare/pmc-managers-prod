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
- **Wave 15** — trilingual bundle now covers every FORM FIELD (Sections A/B/C/D/E, DocSlot, UnifiedLogin, AdminVendorCreate, RegistrationStart, RegistrationResume). Backend cyclomatic-complexity refactor via `bids_helpers.py`, `analytics_helpers.py`, `packages_helpers.py`, `committee_helpers.py`. Verified iteration_18.
- **Wave 16** — code review fixes: test creds via env vars, prod console guards, mount-only useEffect annotations, flat-config global ignores.
- **Wave 17 (this iteration)** — (a) Country dropdown fully localized: `config.COUNTRIES` now carries EN/RU/KK names, `/api/v1/meta/countries` exposes `name_en`/`name_ru`/`name_kk`, both `SectionA.jsx` and `RegistrationStart.jsx` pick by current lang (verified via screenshots: Kazakhstan → Казахстан → Қазақстан). (b) Panel Split Sprint: all four 250–370 LOC admin panels broken into focused sub-components under `admin-console/bidding/`, `admin-console/masters/`, `admin-console/evaluation/`, `admin-console/boq/`. Main panel files reduced to 64–202 LOC each while preserving every data-testid.

### P1 (Next)
- **Deploy Refresh** — user needs to click "Save to Github" + "Deploy" so Waves 15–17 land in production, then hit `POST /api/v1/admin/heal/rename-admin` once to purge the legacy `admin@pmcmanagers.com` row from the prod DB
- **Firebase + APNs** — waiting for user to drop `google-services.json` and APNs auth key
- **Live KYC-Checks** — waiting for `KYC_BASE_URL` + `KYC_API_KEY` env vars

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
