# PMC Managers Limited v2 — Product Requirements

## Original Problem
Global tender management CRM/e-Tender platform. Multi-role approval pipeline, dynamic
Approval Matrices, Bidding & EMD payments, BOQ, Evaluations, Contract Award, MFA,
Multi-Tenant portals, AI Audit Copilot, KYC integration. Built "for Portability" —
Emergent MVP now, AWS Phase 2 later; **now also shipped as PWA + Capacitor mobile app**.

## User Personas
- **Master Admin** — full RBAC.
- **Staff** — Escrow Agent, Certifier, Legal Counsel, Accounting, Committee, Reviewer, Auditor, Support. High-risk roles must have MFA.
- **Vendor** — self-registers or admin-invited (single or CSV bulk).
- **External Committee Invitee** — non-staff experts invited by email.

## Core Modules
- **Wave 1-7** — Auth (HTTPOnly + CSRF), Bidding + EMD (Stripe live + PayPal/Kaspi sandbox), Evaluations, BOQ, Contracts, Vendor Intel, Analytics, MFA, Tenants, GDPR, Workflow Matrix
- **Wave 8** — AI Audit Copilot, high-risk role MFA enforcement, GDPR self-service, matrix-driven Bidding Ops, tenant portal skinning, KYC stub
- **Wave 9** — Admin vendor invites + verify-email + registration template, notice document uploads (primary + attachments), Permissions Matrix, external committee invitees
- **Wave 10** — KYC-Checks live client (env-driven, stub fallback), Public notice attachments, Registration document slots (12 KYC slots + progress meter), Vendor template download, Committee Status Dashboard, Admin Document Viewer, Bulk Vendor Invite (CSV)
- **Wave 11 (Quality)** — XSS fix, test creds → env vars, array-index-key fixes, MastersPanel default password → empty, `is` → `==`
- **Wave 12 (Refactor)** — 4 nested admin panels (Registrations, Notices, Audit, Packages) extracted to standalone files; AdminDashboard slimmed from 687→140 lines; `bids_helpers.py` extracted from `decide_bid`
- **Wave 13 (Mobile)** — **PWA + Capacitor**: `public/manifest.json`, service worker with offline shell + push, iOS meta tags, unified `/m` mobile login (role auto-detection), `mobileBridge.js` (native camera / biometric / push / secure storage), `capacitor.config.ts`, full `docs/MOBILE_BUILD.md` guide for App Store + Play Store submission

## Roadmap

### P0 (Next)
- Live KYC-Checks credentials — user to share `KYC_BASE_URL` + `KYC_API_KEY`
- Backend send-push wiring (FCM/APNs adapters in `notifications.py`) once user provisions Firebase project
- Complete backend function refactoring (paused mid-batch: bids.decide_bid still needs body update to use bids_helpers; also analytics.audit_copilot, packages.import_packages_csv, committee.create_committee)

### P1
- iOS + Android store submission (needs user's Mac + $99 Apple + $25 Google)
- Domain-based multi-tenant routing (currently query-string only)
- Backend push adapter (once FCM keys arrive)

### P2
- Phase 2 — AWS migration (PostgreSQL RLS, S3 Object Lock, Cognito, Fargate)

## Deployment Notes
- MongoDB unique indexes MUST use `sparse=True`
- CSRF double-submit on state-changing routes
- Emergent LLM key powers AI Audit Copilot + bid anomaly
- Emergent Email key powers all send_email calls (best-effort if missing)
- `KYC_PROVIDER` env var: `stub` (default) or `kyc-checks` (real)
- For native mobile: cookies must be `SameSite=None; Secure` (already set)

## Integrations
- Stripe (sandbox key in pod env)
- Emergent LLM key
- Emergent Email
- PyOTP + qrcode (MFA)
- KYC-Checks (real client wired; awaiting credentials)
- **Capacitor 8.x** (camera, preferences, push-notifications) + **@aparajita/capacitor-biometric-auth**
