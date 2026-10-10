# PMC Managers — Release v51bb (10 Oct 2026)

## Downloads
- Frontend (production build): `/downloads/pmc-frontend-v51bb-prod-build.zip`
- Backend: unchanged from v51ba — no backend deploy needed for this release.

## What changed

### Admin → Add vendor (`/admin/vendors/new`)
1. **Back navigation** — the header button now says **"Back to vendors"** and
   returns to the Vendors tab (`/admin?tab=vendors`) instead of the dashboard,
   matching the Edit-full-profile behaviour. Label updated in EN / RU / KZ.
   (`AdminVendorCreate.jsx`, `i18n-strings.js`)
2. **Section D · Business categories** — verified (no code change needed):
   the picker is already 100% database-driven from the Categories master
   (`GET /api/v1/masters/categories/public` — 105 UNSPSC-backed categories,
   admin-managed from Masters → Categories). Nothing is hardcoded.
3. **Colour coding / visibility** — the create + edit vendor forms now render
   on a brighter light-grey page with a white raised card, dark-slate labels,
   clearly visible 1.5px input borders, a dark-green focus ring, and the
   draft banner switched to the brighter emerald info style used by the edit
   page. Scoped CSS carve-out for `admin-vendor-create` / `admin-vendor-edit`
   in `frontend/src/index.css`.

## Verification (preview)
- Add-vendor page: "BACK TO VENDORS" button present, routes to the vendors tab.
- Section D shows "Search 105 verticals…" and the live category list.
- All inputs, selects and textareas render white with visible borders.

## Deploy
Frontend only: unzip into S3 (overwrite), CloudFront `/*` invalidation.
Backend stays on v51ba.
