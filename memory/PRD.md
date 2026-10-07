# PMC Managers v2 — PRD (as of 07 Oct 2026 / v51ab)

## Original problem statement
End-to-end procurement & tender management platform (public notice board,
vendor portal, staff portal, admin console) built as React (CRA + CRACO) +
FastAPI + MongoDB. Option E forest-green / navy / brass visual system.
User manages their own S3 + CloudFront frontend and Elastic Beanstalk
backend deployments.

## Latest release — v51ab (07 Oct 2026)

Builds on v51aa with Money & compliance filter unification + reverse-auction edit:

1. **Shared `MoneyFilterBar` on every Money & compliance panel.** Reverse
   auctions, Bidding ops, Awards, Billing, Escrow/EMD, Evaluation, L1
   comparison, DocuSign — all now expose the same filter bar: search
   tender/title, created-by, created from→to, expires from→to, status
   dropdown, Clear. Reverse auctions filters its React state array
   directly; legacy panels use a MutationObserver that tags rendered
   rows with status and created-at data-attrs and then filters them.

2. **Reverse auction edit per row.** Every draft auction now has an
   **Edit** button next to Invite/Start/Open room. Inline form edits
   title, currency, starting/floor price, min decrement, duration and
   anti-snipe seconds. Backend PATCH /api/v1/reverse-auctions/{aid}
   enforces draft-only + floor<start.

## v51aa highlights still live
- Admin bulk-invite CSV template covering every Section A–E vendor field.
- Clear 409 handling on single-vendor invite with Edit full profile toast action.
- /admin/vendors/:ref/edit route to edit ENTIRE Sections A–E vendor profile.
- Notice blank Contact Email coerced to None (fixes 422).
- Money-pages crash fix (InfoDot button-in-button).
- Reverse auction invite + Resend auto-send + readiness badge.
- Notice filter URL memory.

## Deployment artifacts
- `frontend/public/downloads/pmc-frontend-v51ab-prod-build.zip`
- `frontend/public/downloads/pmc-backend-v51ab.zip`
- `frontend/public/downloads/DOWNLOAD_v51ab.md`

## Up next
- Corrigenda module (edit live tenders with amendment trail + vendor re-ack).
- Financial-model placeholders in the Investment Memorandum to be filled in.

## Architecture
React CRA + CRACO + Tailwind + Radix + shadcn-ui on the frontend;
FastAPI + Motor (async MongoDB) on the backend; Mongo config via
`MONGO_URL` + `DB_NAME`; frontend API base via `REACT_APP_BACKEND_URL`;
Admin/Vendor/Staff auth via JWT + CSRF.

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key (AI drafting fallback).
