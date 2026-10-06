# PMC Managers v2 — PRD (as of 06 Oct 2026 / v51y)

## Original problem statement
End-to-end procurement & tender management platform (public notice board,
vendor portal, staff portal, admin console) built as React (CRA + CRACO) +
FastAPI + MongoDB. Multiple release waves — currently on Option E
forest-green / navy / brass visual system. User manages their own
S3 + CloudFront frontend and Elastic Beanstalk backend deployments.

## Latest release — v51y (06 Oct 2026, this session)

### P0 fixes delivered
1. **Admin → Money & compliance panels — "This panel hit an error" FIXED**
   Root cause (missed by prior passes that blamed stale production): the
   shared `InfoDot` component rendered a `<button>` and sat **inside parent
   `<button>`** elements on Evaluation, L1 comparison, Permissions, Awards
   and similar panels. React 18 production builds throw an actual error on
   button-nested-in-button, which the shared `ErrorBoundary` surfaced as
   "This panel hit an error … role-mismatched cookies can cause this." Fix
   in `frontend/src/components/InfoDot.jsx` only — the trigger now renders
   as `<span role="img" tabIndex=0>`, which is valid HTML inside a button
   and still focusable / tooltipable via Radix.

2. **Reverse auction HTTP 400 on Start — remedied in UI**
   The 400 is a correct guardrail ("need at least 2 registered
   participants"). The admin console had no way to invite vendors from
   the Reverse auctions page, so the admin was stuck. `AdminAuctionsE`
   now provides an inline **Invite vendors** panel per row with:
   - emails textarea (comma / space / newline separated)
   - optional note
   - list of registered participants + aliases
   - list of pending invite links with **Copy link** buttons
   Flow: Draft → Invite vendors → vendors register → Start.

3. **Admin Notices filter bar** — complete (date created, creator, tender
   number / title, status incl. Draft / Awaiting approval). Already
   present from v51x; retained in v51y.

### Deployment artifacts
- `frontend/public/downloads/pmc-frontend-v51y-prod-build.zip`
- `frontend/public/downloads/pmc-backend-v51y.zip`
- `frontend/public/downloads/DOWNLOAD_v51y.md`

Verified in preview; production rollout is user-managed (S3 + CloudFront
invalidation `/*`, Elastic Beanstalk upload).

## Architecture (unchanged)
- Frontend: React CRA + CRACO + Tailwind + Radix UI + shadcn-ui components
  at `/app/frontend/src/components/ui/*`.
- Backend: FastAPI + Motor (async MongoDB).
- Mongo config via `MONGO_URL` + `DB_NAME`; frontend API base via
  `REACT_APP_BACKEND_URL`.
- Admin/Vendor/Staff auth via JWT + CSRF (dual-header for admin POSTs).

## Known backlog (not blockers)
- Mobile-fix.css has grown large and brittle; defer refactor.
- Legacy and E routes coexist; occasional confusion about which is live.
- v51y production rollout verification pending user action.

## 3rd-party integrations (unchanged)
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key (AI drafting fallback).
