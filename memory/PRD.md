# PMC Managers v2 — PRD (as of 07 Oct 2026 / v51ad)

## Latest release — v51ad
1. **Corrigenda — full workflow.** Numbered amendments with attachments,
   "extend deadline by N days" shortcut, field-level before/after
   amendments (versioned diff), mandatory vendor acknowledgement before
   next bid action. Backend auto-extends the parent notice's deadline
   when `extend_deadline_days` is set; vendor ack endpoint plus admin
   ack-list endpoint; audit-logged throughout.
2. **Saved views (filter presets).** Per-user, per-panel named filter
   presets on every Money & compliance panel (auctions, awards, billing,
   escrow, evaluation, L1, DocuSign). New `/api/v1/filter-presets` CRUD;
   MoneyFilterBar shows Load / Save / Delete controls.

## v51ac highlights (previous)
- Per-row Edit sections on every non-approved registration (opens the
  vendor's own 5-section flow in a new tab via admin-only resume-link).
- Expires-from/to fields hidden on panels without an expiry concept.

## v51aa–v51ab highlights
- Full Sections A–E bulk-invite CSV template + structured 409 detail.
- /admin/vendors/:ref/edit full-profile editor.
- MoneyFilterBar shared across all Money & compliance panels.
- Reverse auction row Edit button + inline edit.

## Deployment artifacts
- `frontend/public/downloads/pmc-frontend-v51ad-prod-build.zip`
- `frontend/public/downloads/pmc-backend-v51ad.zip`
- `frontend/public/downloads/DOWNLOAD_v51ad.md`

## Architecture
React CRA + CRACO + Tailwind + Radix + shadcn-ui frontend; FastAPI +
Motor backend; MongoDB; `REACT_APP_BACKEND_URL` + `MONGO_URL`/`DB_NAME`.

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key (AI drafting fallback).

## Up next
- Vendor-side banner "N corrigenda await your acknowledgement" wired to
  the vendor dashboard (API in place; UI pending).
- Bid-submit route to call `ensure_corrigenda_acknowledged()` as a 412
  pre-check (helper function in place; wiring pending).
- Financial model placeholders in Investment Memorandum to be filled in.
