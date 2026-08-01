# PMC Managers Limited — v2 Product Requirements Document

**Legacy:** v1 archived at GitHub `pmc-tender-v1-legacy` tag `v1.0`
**Current build:** v2 (this workspace) → target repo `Treasurescare/pmc-tender-v2-aws`
**Strategy:** "Build for Portability" — build on Emergent stack now, structure exactly per AWS Build Sheet v2 for a low-cost Phase 2 migration to PostgreSQL + Cognito + S3 Object Lock + Fargate.

---

## Governing documents

1. **PMC Transaction Structure & Funds-Flow Report** (24 Jul 2026) — legal/commercial two-category-money framework
2. **PMC Build Sheet v2 AWS** (24 Jul 2026) — technical architecture (4 apps + 1 API)
3. **Domain_Spec.md** (this repo) — extracted business rules from v1
4. **BA_Gap_Analysis.pdf** (this repo) — comparison of v1 vs new scope for client discussion
5. **design_guidelines.md** (this repo) — Navy Trust visual language, retained verbatim from v1

## The four apps (Build Sheet Part 6)

| App | Name | Stack (v2 Phase-1 pilot) | Stack (Phase 2 AWS) |
|---|---|---|---|
| **App 1** | Milestone Evidence Capture (mobile) | **Deferred** — needs S3 Object Lock | React Native + SQLite + S3 |
| **App 2** | Package Tracker (internal) | React admin panel | Retool + RDS or same |
| **App 3** | Pre-Tender Registration Portal | React + FastAPI + MongoDB | React + FastAPI + RDS + Cognito |
| **App 4** | Public Tender Notice Board | React SPA | Next.js SSR + RDS |

## API contract (per Build Sheet Part 4)

Every endpoint is prefixed `/api` (Kubernetes ingress). Contract mirrors Build Sheet v2 Part 4 exactly so Phase 2 is a stack swap, not a rewrite.

### Public
- `GET  /api/v1/notices`
- `GET  /api/v1/notices/{notice_ref}`
- `POST /api/v1/registrations` — create draft
- `PATCH /api/v1/registrations/{id}` — update draft (magic-link token)
- `POST /api/v1/registrations/{id}/submit`
- `POST /api/v1/registrations/{id}/status` — status check (magic-link token)
- `POST /api/v1/uploads/presign` — presigned upload URL (S3 in Phase 2, direct upload endpoint in Phase 1)

### Authenticated (admin/reviewer)
- `GET  /api/v1/registrations` — admin queue with status filter
- `GET  /api/v1/registrations/{id}`
- `POST /api/v1/registrations/{id}/decision` — approve | reject | clarify
- `GET  /api/v1/vendors` — list, search
- `GET  /api/v1/vendors/{id}`
- `GET  /api/v1/packages` — filter project/status/phase
- `POST /api/v1/packages`
- `PATCH /api/v1/packages/{id}`
- `POST /api/v1/packages/import` — CSV bulk load
- `POST /api/v1/notices` — create/publish
- `GET  /api/v1/audit-events` — verify chain

**csrf_token cookie is JS-readable** (`httpOnly=false`) by design so JS can echo it to `X-CSRF-Token`. This is the double-submit-cookie pattern.

## Phase-1 Build Sequence

1. ✅ Repo bootstrap · scaffold · Domain_Spec extracted
2. ✅ **App 4 Public Notice Board** — 3 seeded notices, filters, hero, detail page
3. ✅ **App 3 Pre-Tender Registration Portal** — Sections A–E stepper, magic-link resume, 6 declarations, admin approve/reject/clarify
4. ✅ **App 2 Package Tracker** — 30 seeded KZ packages, 6-column drag-drop board, CSV importer, create-new modal
5. ✅ Admin auth (JWT) + admin registration queue + audit chain verify
6. ✅ SHA-256 hash-chained audit trail (carries over from v1)
7. ✅ i18n EN/RU/KK wired end-to-end
8. ✅ Client_Preview_Script.md for stakeholder walk-through

## Explicitly out of scope (Phase-1)

Per Build Sheet Part 5:
- Bid submission / opening
- Evaluation scoring
- Contract award
- Payment processing (fee flow is "pilot mode")
- Encryption / KMS
- S3 Object Lock
- AWS Cognito
- PostgreSQL RLS enforcement
- App 1 (Milestone Evidence — needs Object Lock)

## Test credentials

See `/app/memory/test_credentials.md`.
