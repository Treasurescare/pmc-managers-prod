# PMC Managers · Release v52bx

**Date:** 11 Oct 2026 · **Supersedes:** v52bw

## What's new in v52bx

### 1. Round-6 bug #34 — Session cross-contamination fixed
Admin, staff and vendor login endpoints now actively **delete the OTHER role's cookie** on every successful login. Logging into Admin wipes `vendor_token`; logging into Vendor wipes `access_token`. The two account contexts can never silently mix on the same browser again.

### 2. Round-6 #46 — Corrigenda search bars re-labelled
Two distinct search boxes:
- `corr-search-notice` — "Find a notice by reference or title to view/add its corrigenda…"
- `corr-search-within` — "Filter THIS notice's corrigenda by number, title or summary…"

### 3. User-feedback — Vendor can see reverse-auction invites
New endpoint `GET /api/v1/reverse-auctions/mine` returns every reverse auction tied to a notice the vendor already bid on, OR where they were explicitly invited by email. New vendor page `/vendor/auctions` renders them with an "Enter" / "View details" button, and a new KPI tile **Reverse auctions** on the vendor landing (`vhome-kpi-auctions`) shows the count.

### 4. User-feedback — Vendor Categories back button to supplier portal
`VendorCategories.jsx` back button now navigates to `/vendor` (supplier portal home) via `useNavigate` instead of the fragile `window.history.back()` fallback.

## Mid-release corrections baked in
- Backend route `/api/v1/reverse-auctions/mine` was double-prefixed in the first draft; corrected to `@router.get("/mine")` and placed **above** `/{aid}` to avoid FastAPI route shadowing.
- `CorrigendaPanel.jsx` had duplicate `data-testid` props after the search-label rename; stale ids removed.

## Known gaps (queued for v52by)
- **#43 Rubric save**, **#44 Scoring=0** — need investigation of `compute_award_report`; not shipped in v52bx.
- **#48 / #57 BOQ export** — Excel/PDF export per template; design pending.
- **#49 Corrigendum withdraw refresh** — backend already sets `is_active: False`; need deeper look at frontend state after withdraw.
- **#58 Product disable** — need the exact error text/screenshot.
- **#59/#60/#64 Reverse auction create/start** — need deeper investigation of the `ReverseAuctionIn` payload and start flow.
- **#41 Escrow login error** — needs the specific error text or a reproduction screenshot.
- **Vendor sidebar wrapping on `/vendor/categories` and `/vendor/services`** — bigger chrome refactor; current fix: back button to supplier portal.

## Deployment
- Backend EB: upload `pmc-backend-v52bx.zip`.
- Frontend S3 + CloudFront: unzip `pmc-frontend-v52bx-prod-build.zip`, sync, invalidate `/*`.
