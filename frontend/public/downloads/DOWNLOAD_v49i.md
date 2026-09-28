# PMC Managers Limited — Release v49i

## What's new in v49i

### a) Home search bar now filters by country
The hero form on `/` (Search box + "All countries" select + Find tenders)
was purely decorative. It now:
- serialises the picked country + keyword into `?country=India&q=OPD`
  and navigates to `/tenders/live`.
- `initTenderFilters` in `pmcELiveData.js` reads those query params on
  mount and pre-ticks the matching Delivery-country checkbox + prefills
  the search box, so the results only show tenders for the chosen country.

### b) Mobile view — real responsive layout under 720 px
`index.css` gained a `@media (max-width: 720px)` block scoped to
`[data-ui="e"]` that:
- Stacks the hero (`grid-template-columns: 1fr`), makes the search form
  a full-width column of stacked inputs.
- Hides the desktop top-nav links + brand subtitle (they were causing the
  atrocious horizontal cram).
- Collapses `.pmc-stats` and `.pmc-kpis` from 4-col to 2-col.
- Collapses inline `repeat(4,1fr)` / `repeat(3,1fr)` / `1fr 1fr` grids
  used across Open-for-bids, How-it-works and admin panels to a single
  column.
- Turns the vendor sidebar (`.pmc-lnav`) into a horizontal scrollable pill
  bar; hides the "Your PMC desk" block on phones.
- Hides the admin fixed sidebar and lets the main pane use full width;
  admin top-bar wraps.
- Collapses the pmc-drawer / help drawer to full-screen on phones.
- Registration-portal 3-column layout collapses to single column.

### c) & d) Live board + Open-for-bids cards gate behind auth
Clicking any `.pmc-live__row`, `.pmc-live__all`, or the `View notice` /
whole `.pmc-tender` card on the PUBLIC home page:
- If the visitor has no `csrf_token` cookie (i.e. not signed in) →
  navigates to `/register`.
- If a `csrf_token` cookie is present (signed in) → navigates to
  `/vendor/tenders`.

Only the public marketing pages are gated — vendor and admin portals
keep their existing per-notice deep-links.

## Verified live
- Hero form → picked "India" + "OPD" → navigates to
  `/tenders/live?q=OPD&country=India`; the India checkbox is ticked
  automatically and only India-country rows render.
- Guest click on the Live-board row navigates to `/register`.
- Mobile viewport (390 × 844): hero uses a single column, search form
  stacks vertically, top-nav is hidden, stats collapse to 2 columns.

## Bundles
- **Frontend:** `pmc-frontend-v49i-prod-build.zip` (2.7 MB, same-origin)
- **Backend:** `pmc-backend-v49i.zip` (416 KB — unchanged from v49h)

## Deploy
- Frontend: unzip to S3, invalidate CloudFront `/*`.
- CloudFront SPA rule (still required): `403` → `/index.html` 200,
  `404` → `/index.html` 200.
- Backend: skip if v49f–v49h are already deployed.

## Test credentials (unchanged)
- Admin: `adminsupport@pmcmanagers.com` / `Admin@12345`
- Vendor: `manualvendor@pmcmanagers.com` / `Vendor@12345`

## Rollback
- Fall back to `v49h` if needed.
