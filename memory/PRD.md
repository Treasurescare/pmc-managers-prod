# PMC Managers v2 — PRD (as of 06 Oct 2026 / v51z)

## Original problem statement
End-to-end procurement & tender management platform (public notice board,
vendor portal, staff portal, admin console) built as React (CRA + CRACO) +
FastAPI + MongoDB. Option E forest-green / navy / brass visual system.
User manages their own S3 + CloudFront frontend and Elastic Beanstalk
backend deployments.

## Latest release — v51z (06 Oct 2026, this session)

Builds on v51y (Money-pages crash fix + reverse auction invite UI + notice
filter bar) with three operator enhancements:

1. **Invite vendors by email via Resend** — the Invite panel on each
   auction row now has an "Email vendors now via Resend" checkbox
   (default on). Backend `/invite` auto-sends from the verified
   pmcmanagers.com domain using the default auction-invite template, or
   a built-in fallback body if none is seeded. Un-check for links-only.

2. **Readiness badge on Draft auctions** — amber `0/2 participants` /
   `1/2 participants` or emerald `✓ 2/2 ready` next to each Draft row's
   status pill. Backed by a new `participant_count` field on the list
   endpoint.

3. **Notice filter memory in URL** — status, q, creator, from, to,
   templates all mirror into the URL via `history.replaceState`.
   Operators can bookmark / share the exact search. Clear wipes all
   params. Rehydrates on first paint for deep links.

## v51y highlights (previous)
- Root-caused and fixed "This panel hit an error" on every Admin → Money
  & compliance page: `InfoDot` was rendering `<button>` inside parent
  `<button>` elements, which React 18 production builds throw on. One
  component change (`<span role="img">`) clears every affected panel.
- Added inline **Invite vendors** panel to the Reverse auctions admin
  page with emails textarea, note, registered-participants list, and
  pending invite links with Copy-link.
- Notice filter bar (query, creator email, created from/to, status
  incl. Draft/Awaiting approval, template-only, clear).

## Deployment artifacts
- `frontend/public/downloads/pmc-frontend-v51z-prod-build.zip`
- `frontend/public/downloads/pmc-backend-v51z.zip`
- `frontend/public/downloads/DOWNLOAD_v51z.md`

Verified in preview; production rollout is user-managed (S3 upload +
CloudFront `/*` invalidation, Elastic Beanstalk upload).

## Architecture (unchanged)
- React CRA + CRACO + Tailwind + Radix + shadcn-ui (`/app/frontend/src/components/ui/*`).
- FastAPI + Motor (async MongoDB).
- Mongo config via `MONGO_URL` + `DB_NAME`; frontend API base via `REACT_APP_BACKEND_URL`.
- Admin/Vendor/Staff auth via JWT + CSRF (dual-header for admin POSTs).

## 3rd-party integrations
MongoDB, S3 + CloudFront, Elastic Beanstalk, Resend, DocuSign, Stripe,
Emergent LLM Key (AI drafting fallback).

## Known backlog
- Mobile-fix.css has grown large and brittle; defer refactor.
- Legacy and E routes coexist; occasional confusion about which is live.
- v51z production rollout verification pending user action.
