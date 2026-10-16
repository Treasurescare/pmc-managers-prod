# PMC Managers — Release v50u (cumulative: v50m → v50u)

## Fixes in this build (vendor portal navigation consistency)

### (a) My Bids "View" / "Continue" buttons — fixed routing
Both buttons pointed to `/vendor/bids/:id`, which has no route and fell
through to the public notices catch-all (the bug where clicking View on an
active bid landed on the tender/notices page). They now open the live
Bid Workspace at `/vendor/workspace/:bidId`. Pay EMD and Sign LOA actions
unchanged.

### (b) Sidebar count consistency (29 vs 33 flip) — fixed
The static vendor pages (EMD & payments, Reviews, Alerts, Bid Workspace)
rendered their own mockup sidebar with hard-coded badges (Find tenders 29,
My bids 1, Signatures 1). Live pages use real counts from the API, so the
number flipped as you navigated. Mockup badges removed — static pages now
show no stale numbers, live pages show real ones.

### (c) Bid Workspace sidebar links fixed
Every sidebar entry on the Bid Workspace was `href="#"`; now real
`/vendor/*` routes (Home / Find tenders / My bids / EMD / Signatures /
Company & KYC / Reviews / Account).

## Carried from v50t (critical)
- Runtime domain guard in api.js — production domains always use
  same-origin /api (fixes preview-URL bake-in that broke prod login/reset)
- Built with REACT_APP_BACKEND_URL=""

## Carried from v50s
- Upload tiles visible (amber dashed) + re-upload after delete
- My Bids fully live via /api/v1/bids/mine (+ notice title/deadline join)
- Live sidebar counts via VendorPortalChrome
- /vendor/auth/me returns business_categories (KYC header shows approvals)
- Back button on Categories page

## Deploy
- Frontend: `pmc-frontend-v50u-prod-build.zip` → S3 + CF invalidate `/*`
- Backend: `pmc-backend-v50u.zip` → EB (identical API to v50t; frontend-only changes)
