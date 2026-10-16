# PMC Managers · Release v52bv

**Date:** 11 Oct 2026 · **Supersedes:** v52bu

## New in v52bv

### 1. Back button on the Services page (`/vendor/services`)
- `VendorPurchase.jsx` now renders a **Back** button (`data-testid="services-back-btn"`) above the services grid.
- Signed-in vendors get **"Back to supplier portal"** → `/vendor`; public visitors get **"Back to home"** → `/`.

### 2. "Service quotes" counter on the vendor landing page
- New vendor-scoped endpoint `GET /api/v1/engagements/mine` (401 unauth; scoped to the vendor's own email) — deliberately registered above `/{eid}` to avoid FastAPI route shadowing.
- Vendor home (`/vendor`) KPI strip gains a 5th tile: **Service quotes** (`data-testid="vhome-kpi-services"`) with a briefcase icon, live count of engagements in `quote_requested / quoted / invoiced`, sub-line "requested · awaiting PMC pricing" (or "no requests yet"), linking to `/vendor/services`.

## Deployment
- Backend EB: upload `pmc-backend-v52bv.zip`.
- Frontend S3 + CloudFront: sync `pmc-frontend-v52bv-prod-build.zip` contents, invalidate `/*`.

## Verify after deploy
1. Vendor → Services → a Back button sits above the grid and returns you to the supplier portal.
2. Vendor → Home → a "Service quotes" KPI tile shows the number of your quote requests (request a quote on /vendor/services, reload home, count increments).
3. Public visitor on /vendor/services sees "Back to home".
