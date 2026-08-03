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
- Unified `/login` on web · legacy admin removal · Admin fills full A–E form
- **Wave 15/16/17/18/19/20** — trilingual · panel splits · country i18n · mobile hamburger + CNAME · code review r2 · Tender Template Builder
- **Wave 21 (this iteration)** — **Vendor doc upload 500 fix + admin-side uploads**:
  - Backend `routers/registrations.py`: `upload_registration_doc` + `delete_registration_doc` now guard against malformed `ObjectId` — return **400 "Malformed registration id — save the draft first"** instead of a 500.
  - Frontend `sections/DocSlot.jsx`: blocks the upload when `regId`/`token` are missing and shows a friendly toast.
  - New "Save draft & enable uploads" flow inside `AdminVendorCreate.jsx`: green/amber banner drives the admin to create a token-authed draft *first*, then per-section `DocSlot` uploads flow through the standard public endpoint.
  - `POST /api/v1/vendors/admin-create` gains `draft_registration_id` — on activation the draft's `document_slots` merge into the final registration and the draft is marked `superseded_by_admin`.

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
